#!/usr/bin/env bash
# check-strangler-coverage.sh — Strangler Fig warning gate
# Severity: warning. Warns about endpoints not yet covered by routing rules.
#
# Checks each .harness/strangler-fig/plans/*.yaml file for:
#   1. Plan in 'coexist' or 'new-primary' state
#   2. coverage.unrouted entries — endpoints without explicit routing rule
#   3. Plans stuck in 'coexist' for > 90 days (stagnation warning)
#
# Exit code:
#   0 — always (warning gate, never blocks)

set -u

PLANS_DIR=".harness/strangler-fig/plans"
WARN_COUNT=0

if [[ ! -d "$PLANS_DIR" ]]; then
    exit 0
fi

# Helper to read YAML fields
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
        val = val.get(k) if isinstance(val, dict) else None
        if val is None:
            break
    print(val if val is not None else '')
except Exception:
    print('')
"
}

stagnation_days() {
    local file="$1"
    python3 -c "
import yaml, datetime
try:
    with open('$file') as f:
        data = yaml.safe_load(f) or {}
    history = data.get('history') or []
    coexist_entries = [h for h in history if h.get('to') == 'coexist']
    if not coexist_entries:
        print(0); exit()
    last = coexist_entries[-1].get('timestamp', '')
    if not last:
        print(0); exit()
    last_dt = datetime.datetime.fromisoformat(last.replace('Z', '+00:00'))
    now = datetime.datetime.now(datetime.timezone.utc)
    days = (now - last_dt).days
    print(days)
except Exception:
    print(0)
"
}

unrouted_list() {
    local file="$1"
    python3 -c "
import yaml
try:
    with open('$file') as f:
        data = yaml.safe_load(f) or {}
    unrouted = (data.get('coverage') or {}).get('unrouted') or []
    for ep in unrouted:
        print(ep)
except Exception:
    pass
"
}

for plan in "$PLANS_DIR"/*.yaml; do
    [[ -f "$plan" ]] || continue

    pid=$(basename "$plan" .yaml)
    state=$(yaml_get "$plan" "state")

    # Only warn for active plans
    case "$state" in
        coexist|new-primary)
            ;;
        *)
            continue
            ;;
    esac

    # Check 1: unrouted endpoints
    unrouted=()
    while IFS= read -r ep; do
        [[ -z "$ep" ]] && continue
        unrouted+=("$ep")
    done < <(unrouted_list "$plan")

    if [[ ${#unrouted[@]} -gt 0 ]]; then
        echo "⚠ [strangler-fig] $pid ($state): ${#unrouted[@]} unrouted endpoint(s)" >&2
        for ep in "${unrouted[@]:0:5}"; do
            echo "    - $ep" >&2
        done
        if [[ ${#unrouted[@]} -gt 5 ]]; then
            echo "    ... +$((${#unrouted[@]} - 5)) more (run /strangler show $pid)" >&2
        fi
        WARN_COUNT=$((WARN_COUNT + 1))
    fi

    # Check 2: stagnation
    if [[ "$state" == "coexist" ]]; then
        days=$(stagnation_days "$plan")
        if [[ "$days" -gt 90 ]]; then
            echo "⚠ [strangler-fig] $pid: in 'coexist' for $days days — consider advance or abandon" >&2
            WARN_COUNT=$((WARN_COUNT + 1))
        fi
    fi
done

if [[ "$WARN_COUNT" -gt 0 ]]; then
    echo "" >&2
    echo "[strangler-fig] $WARN_COUNT coverage/stagnation warning(s)." >&2
    echo "  Add rules: /strangler-route add <plan-id> --pattern '...' --target new|legacy" >&2
    echo "  Advance:   /strangler advance <plan-id> <state>" >&2
fi

# Always exit 0 — this is a warning gate
exit 0
