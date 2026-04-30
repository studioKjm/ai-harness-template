#!/usr/bin/env bash
# check-threat-coverage.sh — Threat Model (Lite) warning gate
# Severity: warning. Detects sensitive code without linked threat models.
#
# Logic:
#   1. Read .harness/threat-model-lite/triggers.yaml — sensitive paths/endpoints/keywords
#   2. Read .harness/threat-model-lite/models/*.yaml — extract target.ref values
#   3. For each sensitive path matched in repo: if no model targets it, warn
#   4. For each story under .harness/bmad-lite/stories/ with sensitive keywords
#      in narrative: if no model linked, warn
#
# Exit code:
#   0 — always (warning gate)

set -u

MODELS_DIR=".harness/threat-model-lite/models"
TRIGGERS_FILE=".harness/threat-model-lite/triggers.yaml"
STORIES_DIR=".harness/bmad-lite/stories"
WARN_COUNT=0

if [[ ! -f "$TRIGGERS_FILE" ]]; then
    exit 0  # Methodology not initialized — silently skip
fi

# Helper: list all target.ref values across existing models
covered_targets() {
    if [[ ! -d "$MODELS_DIR" ]]; then
        return
    fi
    python3 -c "
import yaml
from pathlib import Path
for f in Path('$MODELS_DIR').glob('*.yaml'):
    try:
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        ref = (data.get('target') or {}).get('ref') or ''
        if ref:
            print(ref)
        # Also check links
        links = data.get('links') or {}
        for k in ('story', 'spike'):
            v = links.get(k)
            if v:
                print(v)
    except Exception:
        pass
"
}

# Helper: get sensitive_paths globs and entity_patterns from triggers
trigger_paths() {
    python3 -c "
import yaml
try:
    with open('$TRIGGERS_FILE') as f:
        t = yaml.safe_load(f) or {}
    for p in t.get('sensitive_paths') or []:
        print(p)
except Exception:
    pass
"
}

trigger_keywords() {
    python3 -c "
import yaml
try:
    with open('$TRIGGERS_FILE') as f:
        t = yaml.safe_load(f) or {}
    ents = t.get('sensitive_entities') or {}
    seen = set()
    for cat, block in ents.items():
        for p in (block.get('patterns') or []):
            kw = p.rstrip('*').lower()
            if kw and kw not in seen:
                seen.add(kw)
                print(kw)
except Exception:
    pass
"
}

# Build covered targets list
covered=$(covered_targets | sort -u)

# Check 1: sensitive paths (file-level coverage)
uncovered_paths=()
while IFS= read -r pattern; do
    [[ -z "$pattern" ]] && continue
    # Use find with the pattern (simplified glob)
    clean_pattern="${pattern//\*\*\//}"
    clean_pattern="${clean_pattern//\/\*\*/}"
    # Skip if pattern is just **/ or empty after cleaning
    [[ -z "$clean_pattern" ]] && continue

    # Find matches
    while IFS= read -r match; do
        [[ -z "$match" ]] && continue
        if ! echo "$covered" | grep -qF "$match"; then
            uncovered_paths+=("$match")
        fi
    done < <(find . -path "./.harness" -prune -o -path "./node_modules" -prune \
                -o -path "./*${clean_pattern}*" -type f -print 2>/dev/null | head -50)
done < <(trigger_paths)

if [[ ${#uncovered_paths[@]} -gt 0 ]]; then
    # Dedup
    uniq_paths=($(printf "%s\n" "${uncovered_paths[@]}" | sort -u))
    if [[ ${#uniq_paths[@]} -gt 0 ]]; then
        echo "⚠ [threat-model-lite] ${#uniq_paths[@]} sensitive file(s) without threat model:" >&2
        for f in "${uniq_paths[@]:0:5}"; do
            echo "    - $f" >&2
        done
        if [[ ${#uniq_paths[@]} -gt 5 ]]; then
            echo "    ... +$((${#uniq_paths[@]} - 5)) more" >&2
        fi
        WARN_COUNT=$((WARN_COUNT + 1))
    fi
fi

# Check 2: stories with sensitive keywords (when bmad-lite is active)
if [[ -d "$STORIES_DIR" ]]; then
    keywords=$(trigger_keywords)
    if [[ -n "$keywords" ]]; then
        # Build pipe-separated regex
        kw_regex=$(echo "$keywords" | tr '\n' '|' | sed 's/|$//')
        uncovered_stories=()
        for story in "$STORIES_DIR"/*.yaml; do
            [[ -f "$story" ]] || continue
            sid=$(basename "$story" .yaml)
            if echo "$covered" | grep -qF "$sid"; then
                continue
            fi
            # Check narrative for sensitive keywords (case-insensitive)
            if grep -iE "$kw_regex" "$story" >/dev/null 2>&1; then
                uncovered_stories+=("$sid")
            fi
        done
        if [[ ${#uncovered_stories[@]} -gt 0 ]]; then
            echo "⚠ [threat-model-lite] ${#uncovered_stories[@]} story/stories touch sensitive entities without threat model:" >&2
            for s in "${uncovered_stories[@]:0:5}"; do
                echo "    - $s" >&2
            done
            WARN_COUNT=$((WARN_COUNT + 1))
        fi
    fi
fi

if [[ "$WARN_COUNT" -gt 0 ]]; then
    echo "" >&2
    echo "[threat-model-lite] $WARN_COUNT coverage warning(s)." >&2
    echo "  Create model: /threat new <slug> --target-kind story|module --target-ref REF" >&2
    echo "  Suppress: add path to triggers.yaml exemptions with reason" >&2
fi

exit 0
