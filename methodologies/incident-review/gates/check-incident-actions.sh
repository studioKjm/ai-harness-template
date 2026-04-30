#!/usr/bin/env bash
# check-incident-actions.sh — Incident Review warning gate
# Severity: warning. Detects overdue / orphan action items.
#
# Checks each .harness/incident-review/incidents/*.yaml for:
#   1. Action items with due_date in the past, still in (open | in-progress)
#   2. Published incidents with 0 action items (suspicious)
#   3. Action items with no owner
#
# Exit code:
#   0 — always (warning gate)

set -u

INCIDENTS_DIR=".harness/incident-review/incidents"
WARN_COUNT=0

if [[ ! -d "$INCIDENTS_DIR" ]]; then
    exit 0
fi

today=$(date -u +%Y-%m-%d)

dump_actions() {
    local file="$1"
    python3 -c "
import yaml
try:
    with open('$file') as f:
        data = yaml.safe_load(f) or {}
    items = data.get('action_items') or []
    status = data.get('status', '')
    print(f'STATUS::{status}')
    print(f'ITEMS::{len(items)}')
    for ai in items:
        if not isinstance(ai, dict):
            continue
        aid = ai.get('id', '?')
        st = ai.get('status', 'open')
        owner = ai.get('owner', '')
        due = ai.get('due_date', '')
        desc = (ai.get('description', '') or '')[:50]
        print(f'AI::{aid}::{st}::{owner}::{due}::{desc}')
except Exception:
    pass
"
}

for inc in "$INCIDENTS_DIR"/*.yaml; do
    [[ -f "$inc" ]] || continue
    iid=$(basename "$inc" .yaml)

    inc_status=""
    item_count=0
    overdue=()
    orphan=()

    while IFS= read -r line; do
        case "$line" in
            STATUS::*)
                inc_status="${line#STATUS::}"
                ;;
            ITEMS::*)
                item_count="${line#ITEMS::}"
                ;;
            AI::*)
                rest="${line#AI::}"
                IFS='::' read -ra parts <<< "$rest"
                # parts: [aid, status, owner, due, desc]
                # Note: bash split on :: doesn't always split cleanly with read -ra,
                # so use python parsing inline instead — but to keep this gate
                # bash-only, we use a simpler delimiter parsing approach.
                aid=$(echo "$rest" | awk -F'::' '{print $1}')
                ai_status=$(echo "$rest" | awk -F'::' '{print $2}')
                owner=$(echo "$rest" | awk -F'::' '{print $3}')
                due=$(echo "$rest" | awk -F'::' '{print $4}')
                desc=$(echo "$rest" | awk -F'::' '{print $5}')

                # Overdue check
                if [[ "$ai_status" == "open" || "$ai_status" == "in-progress" ]]; then
                    if [[ -n "$due" && "$due" < "$today" ]]; then
                        overdue+=("$aid|$due|$desc")
                    fi
                    if [[ -z "$owner" ]]; then
                        orphan+=("$aid|$desc")
                    fi
                fi
                ;;
        esac
    done < <(dump_actions "$inc")

    # Issue 1: overdue items
    if [[ ${#overdue[@]} -gt 0 ]]; then
        echo "⚠ [incident-review] $iid: ${#overdue[@]} overdue action item(s)" >&2
        for entry in "${overdue[@]:0:3}"; do
            aid=$(echo "$entry" | awk -F'|' '{print $1}')
            due=$(echo "$entry" | awk -F'|' '{print $2}')
            desc=$(echo "$entry" | awk -F'|' '{print $3}')
            echo "    - $aid (due $due): $desc" >&2
        done
        if [[ ${#overdue[@]} -gt 3 ]]; then
            echo "    ... +$((${#overdue[@]} - 3)) more" >&2
        fi
        WARN_COUNT=$((WARN_COUNT + 1))
    fi

    # Issue 2: published with 0 actions
    if [[ "$inc_status" == "published" && "$item_count" == "0" ]]; then
        echo "⚠ [incident-review] $iid: published with 0 action items (suspicious)" >&2
        WARN_COUNT=$((WARN_COUNT + 1))
    fi

    # Issue 3: orphan (no owner)
    if [[ ${#orphan[@]} -gt 0 ]]; then
        echo "⚠ [incident-review] $iid: ${#orphan[@]} action item(s) with no owner" >&2
        WARN_COUNT=$((WARN_COUNT + 1))
    fi
done

if [[ "$WARN_COUNT" -gt 0 ]]; then
    echo "" >&2
    echo "[incident-review] $WARN_COUNT action-item warning(s)." >&2
    echo "  Resolve: /incident-action resolve <id> --action-id ID --status done|dropped|converted" >&2
    echo "  Extend due: edit yaml directly (note reason in action_items[].notes)" >&2
fi

exit 0
