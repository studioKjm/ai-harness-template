---
description: Manage incident records — blameless postmortem capture with state machine. Provided by the Incident Review methodology.
---

# /incident — Manage Incident Records

> "What system allowed this?" — not "who did it?"

## When to use

- Production incident detected (alert fired, user-reported, or self-discovered)
- Want to capture timeline + root cause + action items in a durable format
- Avoid the "fixed in Slack and forgot" anti-pattern

## Usage

```
/incident new <slug> --title "..." --severity sev1|sev2|sev3|sev4 [--reporter NAME]
/incident list [--status ...] [--severity sev1|sev2|sev3|sev4]
/incident show <incident-id>
/incident timeline add <id> --time TIME --event "..." [--source SRC]
/incident analyze <id>          # recording → analyzing
/incident publish <id>           # analyzing → published (requires blameless review)
/incident close <id>             # published → acted-on (all action items resolved)
/incident archive <id>           # acted-on → archived
```

For action items see `/incident-action`. For pattern analysis see `/incident-patterns`.

## Prerequisites

None. Incident review can run any time, even before any other methodology.

## Severity guide

| Sev | Meaning | Response time |
|-----|---------|--------------|
| sev1 | Total outage / data loss / security breach | < 1 hour |
| sev2 | Major degradation (significant subset broken) | < 4 hours |
| sev3 | Partial degradation (specific feature/segment) | Same day |
| sev4 | Minor / cosmetic | Next day |

## State machine

```
[recording] → [analyzing] → [published] → [acted-on] → [archived]
```

| State | Meaning | Move to next when |
|-------|---------|-------------------|
| recording | Timeline being captured, response active or just ended | Response done, ready to investigate |
| analyzing | Root cause investigation (5-whys, contributing factors) | Postmortem doc written, blameless review passed |
| published | Postmortem distributed to stakeholders | All action items resolved (done/dropped/converted) |
| acted-on | All action items closed | After ~6 months (or manual archive) |
| archived | Historical record only | (terminal) |

## Instructions

### Step 1 — Locate the script

```
.harness/methodologies/incident-review/scripts/inc.py
```

### Step 2 — Run the requested subcommand

```shell
# Open a new incident
python3 .harness/methodologies/incident-review/scripts/inc.py \
  new billing-outage \
  --title "Refund API 503 errors for 23 minutes" \
  --severity sev2 \
  --reporter "alertmanager"

# Add timeline entries (called repeatedly during response)
python3 .harness/methodologies/incident-review/scripts/inc.py \
  timeline add inc-2026-04-30-billing-outage \
  --time "2026-04-30T14:23:00Z" \
  --event "First 503 from /api/refunds" \
  --source "alert"

# When response is over, advance to analyzing
python3 .harness/methodologies/incident-review/scripts/inc.py \
  analyze inc-2026-04-30-billing-outage
```

### Step 3 — Edit incident yaml during analyze phase

The script does NOT auto-fill these fields — they require human reasoning:

| Field | What to fill |
|-------|--------------|
| `started_at`, `detected_at`, `mitigated_at`, `resolved_at` | Timestamps from timeline |
| `impact.affected_users`, `duration_minutes`, etc. | Quantify damage |
| `detection.method`, `delay_minutes` | How was it caught? |
| `response.mttr_minutes`, `who_responded` | Response metrics |
| `five_whys.why_1` through `why_5` + `root_cause` | Drill down to system cause |
| `contributing_factors[]` | Things that made it worse but weren't the root |
| `what_went_well[]` | Don't skip — important for morale |

### Step 4 — Blameless review

Before `publish`:
1. Re-read the entire yaml
2. Look for blame language: "X person did Y wrong", "Y team didn't"
3. Reframe: "system allowed X", "process didn't catch Y"
4. Set `blameless_review_passed: true` in yaml
5. Run `/incident publish <id>` (script blocks if review not passed)

### Step 5 — Action items (separate command)

Each action item must have: description, owner, due_date. Run:
```
/incident-action add <id> --description "..." --owner NAME --due YYYY-MM-DD --priority high|medium|low
```

When closing an action item:
- `done` — fix shipped
- `dropped` — decided not to do (record reason in notes)
- `converted` — moved to a task/story/ADR (specify --converted-to ID)

### Step 6 — Close

```shell
/incident close <id>
```

Script blocks if any action items still `open` or `in-progress`. Use `--force` only when accepting permanent debt (recorded in history).

## Reporting templates

When announcing state changes:

After `new`:
> "Incident `{id}` opened. Severity `{sev}`. Status: recording.
>  Capture timeline as response progresses: `/incident timeline add {id} ...`"

After `analyze`:
> "Incident `{id}`: recording → analyzing.
>  Now fill in: started_at/detected_at/mitigated_at, impact, five_whys, contributing_factors, action_items.
>  When done: set blameless_review_passed=true and run `/incident publish {id}`."

After `publish`:
> "Incident `{id}` published. Action items pending: {N}.
>  Stakeholder notification: <link to postmortem doc, if attached>.
>  Close once all action items resolved."

## Constraints

- Cannot skip states — must follow `recording → analyzing → published → acted-on → archived`
- Cannot publish without blameless review
- Cannot close with open action items (use `--force` with audit trail)
- archived is terminal
- One incident = one event. If multiple cascading incidents, file separately and link via `links.related_incidents`

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| `blameless_review_passed must be true` | Forgot review step | Re-read yaml, fix blame language, set flag |
| `five_whys.root_cause must be filled` | Skipped RCA | Drill down 5 whys before publishing |
| `N action items still open` on close | Forgot to resolve | Resolve via `/incident-action resolve` |
| Same root cause keeps appearing | Pattern! | Run `/incident-patterns` to see frequency |
| Timeline entries out of order | Auto-sorted by `time` field | Just add — script sorts on save |
