#!/usr/bin/env bash
# check-observability-coverage.sh — Observability First warning gate
# Severity: warning. Detects observability gaps in the codebase.
#
# Logic:
#   1. Read all observability specs to learn covered files/symbols
#   2. For each Logic-layer file in repo (heuristic: src/services/, src/logic/,
#      src/usecases/, src/domain/, etc.), check if covered
#   3. Detect specs in 'measuring' state for >90d (review-due)
#
# Exit code:
#   0 — always (warning gate)

set -u

SPECS_DIR=".harness/observability-first/specs"
WARN_COUNT=0

if [[ ! -d "$SPECS_DIR" ]]; then
    exit 0
fi

# Collect covered files from all specs
covered_files=""
covered_symbols=""

if [[ -d "$SPECS_DIR" ]]; then
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        case "$line" in
            FILE::*) covered_files+="${line#FILE::}"$'\n' ;;
            SYM::*)  covered_symbols+="${line#SYM::}"$'\n' ;;
        esac
    done < <(python3 -c "
import yaml
from pathlib import Path
for f in Path('$SPECS_DIR').glob('*.yaml'):
    try:
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        cov = data.get('coverage') or {}
        for fp in (cov.get('files') or []):
            print(f'FILE::{fp}')
        for sym in (cov.get('symbols') or []):
            print(f'SYM::{sym}')
    except Exception:
        pass
")
fi

# Check 1: Logic-layer heuristic coverage
# (Common conventional directories)
logic_dirs=(
    "src/services"
    "src/logic"
    "src/usecases"
    "src/use-cases"
    "src/domain"
    "src/core"
    "app/services"
    "app/usecases"
    "lib/services"
)

uncovered=()
for d in "${logic_dirs[@]}"; do
    [[ -d "$d" ]] || continue
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        # Skip test files
        case "$f" in
            *.test.* | *.spec.* | *_test.* | *__tests__*) continue ;;
        esac
        if ! echo "$covered_files" | grep -qF "$f"; then
            uncovered+=("$f")
        fi
    done < <(find "$d" -type f \( -name "*.ts" -o -name "*.js" -o -name "*.py" -o -name "*.go" -o -name "*.rs" -o -name "*.java" -o -name "*.kt" \) 2>/dev/null)
done

if [[ ${#uncovered[@]} -gt 0 ]]; then
    echo "⚠ [observability-first] ${#uncovered[@]} Logic-layer file(s) without observability spec coverage:" >&2
    for f in "${uncovered[@]:0:5}"; do
        echo "    - $f" >&2
    done
    if [[ ${#uncovered[@]} -gt 5 ]]; then
        echo "    ... +$((${#uncovered[@]} - 5)) more" >&2
    fi
    WARN_COUNT=$((WARN_COUNT + 1))
fi

# Check 2: Specs in 'measuring' state >90 days (review-due)
overdue_count=$(python3 -c "
import yaml, datetime
from pathlib import Path

cutoff_days = 90
now = datetime.datetime.now(datetime.timezone.utc)
overdue = []
for f in Path('$SPECS_DIR').glob('*.yaml'):
    try:
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if data.get('status') != 'measuring':
            continue
        history = data.get('history') or []
        measuring_entries = [h for h in history if h.get('to') == 'measuring']
        if not measuring_entries:
            continue
        last = measuring_entries[-1].get('timestamp', '')
        if not last:
            continue
        last_dt = datetime.datetime.fromisoformat(last.replace('Z', '+00:00'))
        days = (now - last_dt).days
        if days > cutoff_days:
            overdue.append((data.get('id', '?'), days))
    except Exception:
        pass
for sid, days in overdue:
    print(f'{sid}|{days}')
print(f'COUNT::{len(overdue)}')
" | tee /tmp/.obs_overdue_$$ | grep "^COUNT::" | sed 's/COUNT:://')

if [[ "${overdue_count:-0}" -gt 0 ]]; then
    echo "" >&2
    echo "⚠ [observability-first] ${overdue_count} spec(s) in 'measuring' for >90 days (review due):" >&2
    grep -v "^COUNT::" /tmp/.obs_overdue_$$ 2>/dev/null | head -3 | while IFS='|' read -r sid days; do
        echo "    - $sid (${days} days)" >&2
    done
    WARN_COUNT=$((WARN_COUNT + 1))
fi
rm -f /tmp/.obs_overdue_$$

if [[ "$WARN_COUNT" -gt 0 ]]; then
    echo "" >&2
    echo "[observability-first] $WARN_COUNT coverage/staleness warning(s)." >&2
    echo "  Define spec: /observe define <slug> --target-kind module --target-ref <path>" >&2
    echo "  Mark coverage: /observe coverage <spec-id> --files F1 ..." >&2
fi

exit 0
