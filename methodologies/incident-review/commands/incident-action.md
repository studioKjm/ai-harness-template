---
description: Add or resolve action items on an incident. Provided by the Incident Review methodology.
---

# /incident-action — Manage Action Items

> A postmortem without action items is just a story. Make the learning durable.

## When to use

- During or after `/incident analyze` — capture each follow-up
- When a follow-up actually ships (or is decided not to ship)
- When converting a follow-up into a tracked task/story/ADR

## Usage

```
/incident-action add <incident-id> \
    --description "..." \
    --owner NAME \
    --due YYYY-MM-DD \
    [--priority high|medium|low] \
    [--action-id ID]

/incident-action resolve <incident-id> \
    --action-id ID \
    --status done|dropped|converted \
    [--converted-to TASK_OR_STORY_OR_ADR_ID]
```

## Action item format requirements

| Field | Required | Format |
|-------|---------|--------|
| description | yes | Specific. "Add alert for X" not "improve monitoring" |
| owner | yes | One person, not a team |
| due_date | yes | YYYY-MM-DD. Realistic, not aspirational |
| priority | yes | high / medium / low (default: medium) |
| status | auto | open → in-progress → done/dropped/converted |

## Status semantics

| Status | Meaning |
|--------|---------|
| open | Not started |
| in-progress | Being worked on |
| done | Fix shipped, verified |
| dropped | Decided not to do — must record reason in notes field |
| converted | Moved to longer-form artifact (task/story/ADR) — must specify `--converted-to` |

## Instructions

### Step 1 — Add action items during analyze

```shell
# After RCA reveals: alert was missing
python3 .harness/methodologies/incident-review/scripts/inc.py \
  action add inc-2026-04-30-billing-outage \
  --description "Add alert when DB connection pool > 80% for 5min" \
  --owner "jimin" \
  --due "2026-05-15" \
  --priority high

# Process change action
python3 .harness/methodologies/incident-review/scripts/inc.py \
  action add inc-2026-04-30-billing-outage \
  --description "Update billing runbook with new failure mode" \
  --owner "jimin" \
  --due "2026-05-08" \
  --priority medium
```

### Step 2 — Update status as work progresses

When work starts, manually edit yaml `action_items[].status: in-progress` (script doesn't have a separate "start" command — use `add` then `resolve`).

### Step 3 — Resolve when complete

```shell
# Fix shipped
python3 .harness/methodologies/incident-review/scripts/inc.py \
  action resolve inc-2026-04-30-billing-outage \
  --action-id ai-1 \
  --status done

# Decided not to do
python3 .harness/methodologies/incident-review/scripts/inc.py \
  action resolve inc-2026-04-30-billing-outage \
  --action-id ai-2 \
  --status dropped
# (Then manually edit yaml to add reason in notes field)

# Converted to a task/story/ADR
python3 .harness/methodologies/incident-review/scripts/inc.py \
  action resolve inc-2026-04-30-billing-outage \
  --action-id ai-3 \
  --status converted \
  --converted-to "ADR-016"
```

### Step 4 — Anti-patterns to avoid

❌ **"Improve X"** — vague, untestable
✅ "Add metric Y when condition Z, alert when above threshold W"

❌ **Owner: "team"** — no individual accountability
✅ Owner: specific name (rotate ownership on next incident if needed)

❌ **Due: "ASAP"** or **3 months out**
✅ Realistic date — most action items should ship in 1-2 weeks

❌ **Status: open** for 3+ months
→ Either ship it, drop it (with reason), or convert to a tracked task

### Step 5 — Reporting

After `add`:
> "Added action item `{ai_id}` to `{incident_id}`: {description}.
>  Owner: {owner}, Due: {due}, Priority: {priority}.
>  {N} action items now open on this incident."

After `resolve`:
> "Resolved `{ai_id}`: {status}.
>  {0/N} action items still open on `{incident_id}`.
>  When all resolved, run `/incident close {incident_id}`."

## Constraints

- `--action-id` must be unique within incident (auto-generated as `ai-N` if omitted)
- `--converted-to` required when `status=converted` (script enforces)
- Cannot un-resolve — once `done/dropped/converted`, change requires manual yaml edit
- Status values are strict — only `open | in-progress | done | dropped | converted`

## Composition

When other methodologies are active, action items can convert into their artifacts:

| Convert to | Method | When |
|-----------|--------|------|
| `task-id` | ouroboros decompose | Specific implementation work |
| `story-id` | bmad-lite | User-facing change with AC |
| `spike-id` | exploration | Need to investigate further |
| `ADR-N` | (any) | Architectural decision required |
| `pc-...` | parallel-change | Breaking change required |
| `sf-...` | strangler-fig | Module-level migration revealed |

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| `action_id 'ai-X' already exists` | Manual ID conflict | Omit --action-id (auto) |
| `--converted-to required` | Status=converted without target | Provide target ID |
| `--status must be one of [...]` | Typo | Use exact values |
| Action item due date passed, still open | `check-incident-actions.sh` warns | Resolve or extend due_date |
