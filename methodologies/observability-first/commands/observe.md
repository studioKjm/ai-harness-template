---
description: Define observability spec (metrics/logs/traces) for a target before implementation. Provided by the Observability First methodology.
---

# /observe — Define Observability Before Implementation

> Telemetry is a design output, not a retrofit.

## When to use

- New story with performance or availability AC
- New endpoint added
- Logic-layer module touches business-critical operation
- Before writing implementation code (so signals are designed in, not bolted on)

## Usage

```
/observe define <slug> --target-kind story|feature|endpoint|module --target-ref REF
/observe list-specs [--status draft|defined|instrumented|measuring|review-due]
/observe show-spec <spec-id>
/observe instrument <spec-id>     # defined → instrumented (after coverage verified)
/observe measure <spec-id>        # instrumented → measuring (production data flowing)
/observe coverage <spec-id> --files F1 [F2 ...] --symbols S1 [...]
/observe add-metric <spec-id> --name N --type counter|gauge|histogram|summary --question "..."
/observe add-log <spec-id> --event E --level info|warn|error --field F1 [--field F2:pii]
```

For SLOs, see `/observe-slo`.

## State machine

```
[draft] → [defined] → [instrumented] → [measuring] → [review-due]
                                            ↑              ↓
                                            └──────────────┘  (90d cycle)
```

| State | Meaning | Move when |
|-------|---------|-----------|
| draft | Spec being written | First metric/log/trace added (auto) |
| defined | Spec complete | Code emits matching telemetry |
| instrumented | Code verified | Production data flowing |
| measuring | SLOs computable | 90 days passed (review-due triggered) |
| review-due | Time for refresh | After review, back to measuring |

## Instructions

### Step 1 — Locate the script

```
.harness/methodologies/observability-first/scripts/obs.py
```

### Step 2 — Run the requested subcommand

```shell
# Define spec for a story
python3 .harness/methodologies/observability-first/scripts/obs.py \
  define refund-api \
  --target-kind story \
  --target-ref st-2026-04-30-refund \
  --description "Refund API observability"

# Add metrics one at a time
python3 .harness/methodologies/observability-first/scripts/obs.py \
  add-metric obs-2026-04-30-refund-api \
  --name "refund_request_total" \
  --type counter \
  --labels "method" "status_code" "merchant_id" \
  --question "How many refund requests, segmented by outcome?"

python3 .harness/methodologies/observability-first/scripts/obs.py \
  add-metric obs-2026-04-30-refund-api \
  --name "refund_processing_duration_ms" \
  --type histogram \
  --labels "merchant_id" \
  --question "Distribution of refund processing time" \
  --unit "milliseconds"

# Add log events
python3 .harness/methodologies/observability-first/scripts/obs.py \
  add-log obs-2026-04-30-refund-api \
  --event "refund.requested" \
  --level info \
  --field "merchant_id" \
  --field "amount" \
  --field "user_id:pii"
```

### Step 3 — Add traces and SLOs by editing yaml

Traces and SLO links are added by editing the spec yaml directly:

```yaml
traces:
  - span_name: "RefundService.process"
    attributes: ["merchant.id", "refund.amount"]
    parent_kind: "http_server"

slos:
  - id: "slo-refund-availability"
    summary: "99.5% of refund requests succeed (5xx-free) over 30d"
```

For full SLO definition use `/observe-slo new`.

### Step 4 — Mark coverage when implementing

```shell
python3 .harness/methodologies/observability-first/scripts/obs.py \
  coverage obs-2026-04-30-refund-api \
  --files src/billing/refund.ts src/billing/refund-handler.ts \
  --symbols "RefundService.process" "POST /api/refunds"
```

### Step 5 — Advance state

```shell
# After code is written and verified
/observe instrument obs-2026-04-30-refund-api

# After production deploy + data flowing
/observe measure obs-2026-04-30-refund-api
```

### Step 6 — Reporting

After `define`:
> "Observability spec `{id}` created. Status: draft.
>  Add metrics/logs/traces — status auto-advances to 'defined' when first telemetry added."

After `instrument`:
> "Spec `{id}`: defined → instrumented.
>  Coverage: {N} files, {M} symbols.
>  When production data flows: `/observe measure {id}`."

## Choosing metric types

| Type | When | Example |
|------|------|---------|
| counter | Counting events (only goes up) | request_total, errors_total |
| gauge | Point-in-time value (up or down) | active_connections, queue_depth |
| histogram | Distribution of measurements | request_duration_ms, payload_size_bytes |
| summary | Pre-computed quantiles | (rarely needed in modern setups; prefer histogram) |

## Common metrics for any service

Always consider these unless explicitly N/A:
- `*_total` (counter) — request count by outcome
- `*_duration_ms` (histogram) — latency distribution
- `*_in_flight` (gauge) — concurrent operations
- `*_errors_total` (counter) — error count by type

## Composition with other methodologies

| Combo | Effect |
|-------|--------|
| `+ ouroboros` | SLO targets become AC ("system MUST achieve 99.5% availability") |
| `+ bmad-lite` | Stories with performance AC trigger spec requirement |
| `+ incident-review` | Incidents inform new metrics + SLOs (links.related_incidents) |
| `+ exploration` | Spike measures observability cost/feasibility before adoption |
| `+ parallel-change` | New module's spec mirrors legacy's signals during cutover |
| `+ strangler-fig` | facade emits routing decision metrics |

## Constraints

- Cannot skip states (draft → defined → instrumented → measuring)
- Status auto-advances draft → defined when first metric/log/trace added
- `instrument` requires `coverage.files` or `coverage.symbols` populated
- High-cardinality labels (user_id, request_id) auto-warn — log them, don't label
- One spec per target — multiple specs for same target = noise

## Anti-patterns

- ❌ Adding observability AFTER incident — defeats the purpose, defines it as `observability-first`
- ❌ Logging everything at info — drowns signal in noise. Use levels deliberately
- ❌ User_id as metric label — cardinality explosion. Log it, don't label
- ❌ "We use Datadog/Grafana" without spec — tools don't substitute for designed signals
- ❌ Metrics without question — if you can't say what question it answers, it's noise

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| `coverage.files must be populated` on instrument | Forgot to mark coverage | Run `/observe coverage <id> --files ...` |
| Status stuck in draft | No metrics/logs/traces added | Add at least one |
| High cardinality warnings | Using request_id/user_id as labels | Move to log fields, not metric labels |
| Metric name collisions | Same name used for different metrics | Prefix with service: `billing_refund_total` |
