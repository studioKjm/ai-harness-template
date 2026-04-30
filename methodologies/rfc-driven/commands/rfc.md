---
description: Manage RFCs — design review for high-stakes changes before code. Provided by the RFC-driven methodology.
---

# /rfc — RFC Lifecycle Management

> "Architectural changes need a paper trail. Code changes don't have to wait for a meeting."

## When to use

- Change touches >1 module's design or contract
- Migration affecting multiple consumers
- New dependency / framework / language
- Security-relevant architecture (encryption, auth)
- Scale/cost decisions ($X/month threshold)
- Deprecation with stakeholder impact

**Not for**:
- Bug fixes
- Single-feature additions following existing patterns
- Refactors that don't change interfaces
- Dependency patch updates

## Usage

```
/rfc new <slug> --title "..." [--authors A1 A2 ...]
/rfc list [--status draft|proposed|accepted|rejected|superseded]
/rfc show <rfc-id>
/rfc propose <rfc-id>             # draft → proposed (validates completeness)
/rfc accept <rfc-id> --decided-by NAME --rationale "..." [--conditions C1 ...]
/rfc reject <rfc-id> --decided-by NAME --rationale "..."
/rfc supersede <rfc-id> --by <new-rfc-id>
/rfc link <rfc-id> --files F1 [F2 ...] [--modules M1 [...]]
```

For per-PR linking, see `/rfc-link`.

## State machine

```
[draft] → [proposed] → [accepted] → [superseded]
            ↓             ↑
        [rejected]    (replaced by new RFC)
            ↓
       [draft]            (rollback for revision)
```

| State | Meaning | Move when |
|-------|---------|-----------|
| draft | Author iterating | Author ready for review |
| proposed | Under review | Stakeholder decision made |
| accepted | Decision: yes | Implementation can begin |
| rejected | Decision: no | (terminal — record reason) |
| superseded | Replaced by newer RFC | (terminal — links to replacement) |

## Instructions

### Step 1 — Locate the script

```
.harness/methodologies/rfc-driven/scripts/rfc.py
```

### Step 2 — Create RFC

```shell
python3 .harness/methodologies/rfc-driven/scripts/rfc.py \
  new eventbus-replacement \
  --title "Replace in-process event bus with Kafka for cross-service events" \
  --authors jimin
```

### Step 3 — Fill yaml fields (manual)

The script bootstraps but author fills:
- `summary` — 2-3 sentences
- `motivation` — why now? evidence (incidents, metrics)
- `design` — concrete architecture
- `alternatives` — ≥2 entries (including "do nothing")
- `drawbacks` — ≥1 entry (be honest)
- `adoption_plan` — phased rollout

### Step 4 — Propose (gate-checked)

```shell
python3 .harness/methodologies/rfc-driven/scripts/rfc.py \
  propose rfc-2026-04-30-eventbus-replacement
```

Script blocks if any of: summary/motivation/design empty, alternatives <2, drawbacks <1.
Override: `--force` (recorded with `unmet_criteria` in history).

### Step 5 — Decision (accept or reject)

```shell
# Accept
python3 .harness/methodologies/rfc-driven/scripts/rfc.py \
  accept rfc-2026-04-30-eventbus-replacement \
  --decided-by "team-lead" \
  --rationale "Aligned with quarterly OKR; ROI clear from inc-* incident pattern" \
  --conditions "Phase 1 limited to non-critical events; phase 2 after 60d soak"

# Reject
python3 .harness/methodologies/rfc-driven/scripts/rfc.py \
  reject rfc-2026-04-30-eventbus-replacement \
  --decided-by "team-lead" \
  --rationale "Cost not justified at current scale; revisit at 10x volume"
```

Both `--decided-by` and `--rationale` are required (script enforces).

### Step 6 — Link governed files

After accept, link the RFC to files/modules it governs:

```shell
python3 .harness/methodologies/rfc-driven/scripts/rfc.py \
  link rfc-2026-04-30-eventbus-replacement \
  --files src/events/* \
  --modules src/event-bus/
```

This populates `.harness/rfc-driven/.rfc-links.yaml` — gate uses it to suppress warnings on declared files.

### Step 7 — Supersede (when replaced)

When a newer RFC replaces an accepted one:

```shell
# First, accept the new RFC
python3 .harness/methodologies/rfc-driven/scripts/rfc.py \
  accept rfc-2026-09-01-eventbus-v2 \
  --decided-by "..." --rationale "..."

# Then supersede the old
python3 .harness/methodologies/rfc-driven/scripts/rfc.py \
  supersede rfc-2026-04-30-eventbus-replacement \
  --by rfc-2026-09-01-eventbus-v2
```

The new RFC's `links.supersedes` is auto-set; old RFC's `links.superseded_by` is set.

## Reporting

After `new`:
> "RFC `{id}` created. Status: draft.
>  Fill: summary, motivation, design, ≥2 alternatives, ≥1 drawback.
>  When ready: `/rfc propose {id}`."

After `propose`:
> "RFC `{id}`: draft → proposed. Awaiting decision.
>  Decide via `/rfc accept|reject {id} --decided-by NAME --rationale "..."`."

After `accept`:
> "RFC `{id}`: proposed → accepted by {decided_by}.
>  Implementation may proceed. Link governed files: `/rfc link {id} --files ...`"

## Composition with other methodologies

| Combo | Effect |
|-------|--------|
| `+ ouroboros` | Accepted RFC's design becomes seed input |
| `+ parallel-change` | RFC's adoption_plan references parallel-change plans |
| `+ strangler-fig` | Module-level migration RFC creates strangler plan as artifact |
| `+ bmad-lite` | Stories implementing RFC link to it |
| `+ exploration` | Spike findings inform RFC alternatives |
| `+ incident-review` | Incidents motivate RFCs (links.related_incidents) |
| `+ threat-model-lite` | Security RFC has linked threat model |
| `+ observability-first` | RFC's design specifies SLO targets |

## Constraints

- `propose` requires summary/motivation/design + ≥2 alternatives + ≥1 drawback (or --force)
- `accept`/`reject` require both `--decided-by` and `--rationale`
- `accepted → superseded` requires the superseding RFC to be `accepted` (not draft/proposed)
- Cannot un-supersede or un-reject — terminal
- One RFC per change; multi-change PRs link multiple RFCs

## Anti-patterns

- ❌ **RFC after code** — defeats the purpose; use ADR instead
- ❌ **Single alternative** ("we considered nothing else") — script blocks this
- ❌ **No drawbacks listed** — every design has tradeoffs; pretend awareness > discovered drawback
- ❌ **Decision rationale: "approved"** — substantive reasoning required
- ❌ **Accepted RFCs never superseded** — RFCs accumulate; supersede explicitly when replaced

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| `not ready for proposal` | Missing required fields | Fill summary/motivation/design + 2 alternatives + 1 drawback |
| `--decided-by is required` | Script enforces explicit owner | Pass actual name/role |
| `superseding RFC must be 'accepted'` | Trying to supersede with draft | Accept new RFC first |
| Many RFCs in 'proposed' state | Decision bottleneck | Time-box review; default to "no decision = continue draft" after N days |
