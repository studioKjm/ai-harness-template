#!/usr/bin/env bash
# check-rfc-required.sh — RFC-driven warning gate
# Severity: warning by default (configurable to blocking via config.yaml).
#
# Logic:
#   1. Read .harness/rfc-driven/config.yaml — thresholds + always-required paths
#   2. Read .harness/rfc-driven/.rfc-links.yaml — file→rfc mapping
#   3. For staged files (git diff --cached --numstat):
#      a. If file matches always_exempt_paths → skip
#      b. If file matches always_required_paths AND not linked to accepted RFC → warn
#      c. If file LOC change > per_file_loc threshold AND not linked → warn
#   4. If total LOC change > total_loc threshold AND no RFC link → warn
#
# Exit code:
#   0 — always (warning gate; set on_violation: block in config to enforce)

set -u

CONFIG_FILE=".harness/rfc-driven/config.yaml"
LINKS_FILE=".harness/rfc-driven/.rfc-links.yaml"
WARN_COUNT=0

if [[ ! -f "$CONFIG_FILE" ]]; then
    exit 0
fi

# Read config + on_violation
read_config() {
    python3 -c "
import yaml, sys
try:
    with open('$CONFIG_FILE') as f:
        c = yaml.safe_load(f) or {}
    thr = c.get('rfc_required_threshold') or {}
    print(f'PER_FILE::{thr.get(\"per_file_loc\", 500)}')
    print(f'TOTAL::{thr.get(\"total_loc\", 1000)}')
    print(f'VIOLATION::{c.get(\"on_violation\", \"warn\")}')
    for p in c.get('always_required_paths') or []:
        print(f'REQ::{p}')
    for p in c.get('always_exempt_paths') or []:
        print(f'EXEMPT::{p}')
except Exception as e:
    pass
"
}

per_file_thr=500
total_thr=1000
on_violation="warn"
required_patterns=()
exempt_patterns=()

while IFS= read -r line; do
    case "$line" in
        PER_FILE::*) per_file_thr="${line#PER_FILE::}" ;;
        TOTAL::*) total_thr="${line#TOTAL::}" ;;
        VIOLATION::*) on_violation="${line#VIOLATION::}" ;;
        REQ::*) required_patterns+=("${line#REQ::}") ;;
        EXEMPT::*) exempt_patterns+=("${line#EXEMPT::}") ;;
    esac
done < <(read_config)

# Read linked files
declare -A linked
if [[ -f "$LINKS_FILE" ]]; then
    while IFS= read -r f; do
        [[ -n "$f" ]] && linked["$f"]=1
    done < <(python3 -c "
import yaml
try:
    with open('$LINKS_FILE') as fh:
        d = yaml.safe_load(fh) or {}
    for f in (d.get('files') or {}).keys():
        print(f)
    for m in (d.get('modules') or {}).keys():
        # We emit modules as prefixes; the bash side uses 'startswith' check
        print(f'PREFIX::{m}')
except Exception:
    pass
")
fi

# Helper: glob match
glob_match() {
    local path="$1"
    local pattern="$2"
    # Convert glob to a basic shell match
    case "$path" in
        $pattern) return 0 ;;
    esac
    return 1
}

# Helper: check if file is linked
is_linked() {
    local f="$1"
    if [[ -n "${linked[$f]:-}" ]]; then
        return 0
    fi
    # Check module prefix matches
    for key in "${!linked[@]}"; do
        case "$key" in
            PREFIX::*)
                prefix="${key#PREFIX::}"
                if [[ "$f" == "$prefix"* ]]; then
                    return 0
                fi
                ;;
        esac
    done
    return 1
}

# Process staged files
total_loc_change=0
violations=()

while IFS=$'\t' read -r added removed file; do
    [[ -z "$file" ]] && continue
    [[ "$added" == "-" || "$removed" == "-" ]] && continue  # binary file

    # Skip exempt paths
    exempt=0
    for pat in "${exempt_patterns[@]}"; do
        if glob_match "$file" "$pat"; then
            exempt=1
            break
        fi
    done
    [[ "$exempt" == "1" ]] && continue

    loc_change=$((added + removed))
    total_loc_change=$((total_loc_change + loc_change))

    # Check always_required paths
    required=0
    for pat in "${required_patterns[@]}"; do
        if glob_match "$file" "$pat"; then
            required=1
            break
        fi
    done

    if [[ "$required" == "1" ]] && ! is_linked "$file"; then
        violations+=("$file: in always-required path, no RFC link")
        WARN_COUNT=$((WARN_COUNT + 1))
        continue
    fi

    # Check per-file threshold
    if [[ "$loc_change" -gt "$per_file_thr" ]] && ! is_linked "$file"; then
        violations+=("$file: $loc_change LOC change (threshold: $per_file_thr), no RFC link")
        WARN_COUNT=$((WARN_COUNT + 1))
    fi
done < <(git diff --cached --numstat 2>/dev/null)

# Total LOC threshold (only warn if NO file in this commit is linked)
if [[ "$total_loc_change" -gt "$total_thr" ]]; then
    any_linked=0
    while IFS=$'\t' read -r added removed file; do
        [[ -z "$file" ]] && continue
        if is_linked "$file"; then
            any_linked=1
            break
        fi
    done < <(git diff --cached --numstat 2>/dev/null)

    if [[ "$any_linked" == "0" ]]; then
        violations+=("Total commit: $total_loc_change LOC (threshold: $total_thr), no RFC link")
        WARN_COUNT=$((WARN_COUNT + 1))
    fi
fi

if [[ "$WARN_COUNT" -gt 0 ]]; then
    echo "⚠ [rfc-driven] $WARN_COUNT change(s) without RFC link:" >&2
    for v in "${violations[@]:0:5}"; do
        echo "    - $v" >&2
    done
    if [[ ${#violations[@]} -gt 5 ]]; then
        echo "    ... +$((${#violations[@]} - 5)) more" >&2
    fi
    echo "" >&2
    echo "Options:" >&2
    echo "  - Link to existing RFC: /rfc-link <rfc-id> --files ..." >&2
    echo "  - Create new RFC:       /rfc new <slug> --title ..." >&2
    echo "  - Mark exempt:          add path to .harness/rfc-driven/config.yaml::always_exempt_paths" >&2

    if [[ "$on_violation" == "block" ]]; then
        echo "" >&2
        echo "[rfc-driven] BLOCKING (config.yaml::on_violation = 'block')" >&2
        exit 1
    fi
fi

exit 0
