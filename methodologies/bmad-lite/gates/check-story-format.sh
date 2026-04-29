#!/usr/bin/env bash
# check-story-format.sh — BMAD-lite warning gate
# Severity: warning. Validates BMAD-lite story files for format compliance.
#
# Checks each .harness/bmad-lite/stories/*.yaml file for:
#   1. narrative.persona / capability / outcome all present
#   2. acceptance_criteria count >= 1
#   3. each AC has given/when/then filled
#   4. no weasel words in AC text without measurable metric
#
# Exit code:
#   0 — all stories OK or no stories found
#   0 — warnings printed to stderr but never blocks (severity: warning)
#
# Activated only when bmad-lite is in active methodology composition.

set -u

STORIES_DIR=".harness/bmad-lite/stories"
STATE_FILE=".harness/state/bmad-lite.yaml"
WEASEL_WORDS=("fast" "easy" "intuitive" "robust" "secure" "scalable" "user-friendly" "seamless" "smooth")
WARN_COUNT=0

# Skip silently if methodology not active
if [[ ! -d "$STORIES_DIR" ]]; then
    exit 0
fi

if [[ ! -f "$STATE_FILE" ]]; then
    exit 0
fi

# Helper — read YAML field via python3
yaml_get() {
    local file="$1"
    local key="$2"
    python3 -c "
import yaml, sys
try:
    with open('$file') as f:
        data = yaml.safe_load(f) or {}
    keys = '$key'.split('.')
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            val = None
            break
    print(val if val is not None else '')
except Exception:
    print('')
"
}

yaml_count_list() {
    local file="$1"
    local key="$2"
    python3 -c "
import yaml
try:
    with open('$file') as f:
        data = yaml.safe_load(f) or {}
    keys = '$key'.split('.')
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            val = None
            break
    print(len(val) if isinstance(val, list) else 0)
except Exception:
    print('0')
"
}

ac_text_dump() {
    local file="$1"
    python3 -c "
import yaml
try:
    with open('$file') as f:
        data = yaml.safe_load(f) or {}
    acs = data.get('acceptance_criteria') or []
    for ac in acs:
        if isinstance(ac, dict):
            for k in ('given', 'when', 'then'):
                v = ac.get(k) or ''
                print(f'{ac.get(\"id\",\"?\")}|{k}|{v}')
except Exception:
    pass
"
}

for story in "$STORIES_DIR"/*.yaml; do
    [[ -f "$story" ]] || continue

    # Skip template placeholder values
    persona=$(yaml_get "$story" "narrative.persona")
    capability=$(yaml_get "$story" "narrative.capability")
    outcome=$(yaml_get "$story" "narrative.outcome")
    ac_count=$(yaml_count_list "$story" "acceptance_criteria")

    sid=$(basename "$story" .yaml)

    # Check 1: narrative completeness
    if [[ -z "$persona" || "$persona" == *"<"* ]]; then
        echo "⚠ [bmad-lite] $sid: narrative.persona missing or placeholder" >&2
        WARN_COUNT=$((WARN_COUNT + 1))
    fi
    if [[ -z "$capability" || "$capability" == *"<"* ]]; then
        echo "⚠ [bmad-lite] $sid: narrative.capability missing or placeholder" >&2
        WARN_COUNT=$((WARN_COUNT + 1))
    fi
    if [[ -z "$outcome" || "$outcome" == *"<"* ]]; then
        echo "⚠ [bmad-lite] $sid: narrative.outcome missing or placeholder" >&2
        WARN_COUNT=$((WARN_COUNT + 1))
    fi

    # Check 2: AC count
    if [[ "$ac_count" -lt 1 ]]; then
        echo "⚠ [bmad-lite] $sid: 0 acceptance_criteria (need ≥ 1)" >&2
        WARN_COUNT=$((WARN_COUNT + 1))
        continue
    fi

    # Check 3: each AC field filled + weasel words
    while IFS='|' read -r ac_id field text; do
        [[ -z "$ac_id" ]] && continue
        if [[ -z "$text" || "$text" == *"<"* ]]; then
            echo "⚠ [bmad-lite] $sid::$ac_id.$field is empty or placeholder" >&2
            WARN_COUNT=$((WARN_COUNT + 1))
        fi
        # Weasel word scan (case-insensitive)
        lower=$(echo "$text" | tr '[:upper:]' '[:lower:]')
        for w in "${WEASEL_WORDS[@]}"; do
            if [[ "$lower" == *"$w"* ]]; then
                # Only warn if no number nearby (heuristic: digit within ±20 chars)
                if ! [[ "$lower" =~ [0-9] ]]; then
                    echo "⚠ [bmad-lite] $sid::$ac_id.$field has weasel word '$w' without metric" >&2
                    WARN_COUNT=$((WARN_COUNT + 1))
                fi
            fi
        done
    done < <(ac_text_dump "$story")
done

if [[ "$WARN_COUNT" -gt 0 ]]; then
    echo "" >&2
    echo "[bmad-lite] $WARN_COUNT story format warning(s). Run /story refine <id> to fix." >&2
fi

# Always exit 0 — this is a warning gate
exit 0
