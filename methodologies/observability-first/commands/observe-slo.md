---
description: Manage Service Level Objectives (SLO) — define, activate, retire, track violations. Provided by the Observability First methodology.
---

# /observe-slo — Service Level Objectives

> SLI = what we measure. SLO = what we promise. Error Budget = what we can spend.

## When to use

- Service has user-facing reliability target
- Deciding "is it ready to ship?" requires measurable bar
- Track reliability across releases (without SLOs every change feels arbitrary)
- Tying ops investment to user impact

## Usage

```
/observe-slo new <slug> \
    --service NAME \
    --sli-good "QUERY" \
    --sli-valid "QUERY" \
    --target PCT \
    --window "30d"

/observe-slo list [--status proposed|active|retired]
/observe-slo show <slo-id>
/observe-slo activate <slo-id>            # proposed → active
/observe-slo retire <slo-id>              # active → retired
/observe-slo record-violation <slo-id> --duration MIN --burn-rate RATE [--incident-id ID]
```

## State machine

```
[proposed] → [active] → [retired]
```

| State | Meaning |
|-------|---------|
| proposed | Defined but not yet enforcing alerts |
| active | Measuring + alerting + reporting |
| retired | Replaced by newer SLO or feature deprecated |

## Instructions

### Step 1 — Define SLI before writing SLO

The SLI (Service Level Indicator) is a ratio: `good_events / valid_events`.

Examples by SLO type:

**Availability SLO**:
```
good_events:  rate(refund_request_total{status_code!~"5.."}[5m])
valid_events: rate(refund_request_total[5m])
target:       99.5%
```

**Latency SLO**:
```
good_events:  rate(refund_request_total{le="500"}[5m])    # under 500ms
valid_events: rate(refund_request_total[5m])
target:       95%
```

**Quality SLO** (if data integrity matters):
```
good_events:  rate(refund_validation_total{outcome="valid"}[5m])
valid_events: rate(refund_validation_total[5m])
target:       99.9%
```

### Step 2 — Create SLO

```shell
python3 .harness/methodologies/observability-first/scripts/obs.py \
  slo-new refund-availability \
  --service "billing-api" \
  --sli-good 'sum(rate(refund_request_total{status_code!~"5.."}[5m]))' \
  --sli-valid 'sum(rate(refund_request_total[5m]))' \
  --target 99.5 \
  --window "30d" \
  --metric-source "prometheus" \
  --description "99.5% of refund requests succeed (no 5xx) over rolling 30d"
```

### Step 3 — Edit yaml for fields the script doesn't fill

Add these manually:
- `error_budget.policy` — what happens when budget exhausted
- `alert_policy.fast_burn` and `slow_burn` — page vs ticket thresholds
- `links.dashboard_url` and `runbook_url` — operational links

### Step 4 — Activate after operational readiness

Activate only when:
- SLI metrics actually emit data (verified in production)
- Alert policy notifications go to a real channel
- Runbook exists for what to do when alerts fire

```shell
python3 .harness/methodologies/observability-first/scripts/obs.py \
  slo-activate slo-refund-availability
```

### Step 5 — Record violations as they happen

When SLO breach occurs (linked to an incident):

```shell
python3 .harness/methodologies/observability-first/scripts/obs.py \
  slo-record-violation slo-refund-availability \
  --duration 45 \
  --burn-rate 18 \
  --incident-id inc-2026-04-30-billing-outage
```

This appends to `violations[]` for trend analysis.

### Step 6 — Reporting

After `slo-new`:
> "SLO `{id}` defined. Service: {service}, target: {target}% over {window}.
>  Error budget: {budget}.
>  Activate when SLI metrics live + alerts wired: `/observe-slo activate {id}`."

After `slo-activate`:
> "SLO `{id}`: proposed → active. Alerts now enforce burn rate thresholds."

After `slo-record-violation`:
> "Violation recorded on `{id}`: {duration}min, {burn_rate}x burn rate.
>  Linked incident: {incident_id}.
>  Total violations in last 90d: check `/observe-slo show {id}`."

## Burn rate concept

Burn rate = how fast you're spending error budget vs. allowed pace.

| Burn rate | Meaning | Typical action |
|-----------|---------|---------------|
| 1x | Normal — budget lasts the full window | Nothing |
| 6x | Slow burn — budget gone in 1/6 of window | Ticket, investigate |
| 14x | Fast burn — budget gone in 1/14 of window | Page on-call immediately |
| 100x | Crisis | Stop deploys, war room |

## Common SLO targets

| Target | Where appropriate |
|--------|------------------|
| 99% (3.65d/year) | Internal tools, low-stakes endpoints |
| 99.5% (1.83d/year) | Most APIs |
| 99.9% (52.6m/year) | Critical user-facing services |
| 99.99% (52.6s/year) | Payment, auth, infra critical |
| 99.999% (5.26s/year) | Probably overkill — verify cost justifies |

**Don't pick 100% — there's no error budget for any change.**

## Composition

| Combo | Effect |
|-------|--------|
| `+ incident-review` | Each violation links to incident; patterns across SLOs reveal systemic issues |
| `+ ouroboros` | SLO targets become MUST-have AC in seed |
| `+ parallel-change` | Cutover to new module requires SLO parity (auto-checked) |
| `+ strangler-fig` | Strangle plan tracks SLO metrics legacy vs new |

## Anti-patterns

- ❌ **100% target** — no room for any change. Pick 99.9% or 99.99%
- ❌ **SLO without alert** — measuring but not acting = decoration
- ❌ **Alert without runbook** — page fires, on-call doesn't know what to do
- ❌ **SLO on synthetic prober only** — measure user experience, not just probes
- ❌ **Per-customer SLO** — explosion of SLOs. Aggregate, then segment by tenant in dashboards

## Constraints

- Cannot un-retire a retired SLO (create a new one)
- Burn rate calculations require actual SLI data — `recent.*` fields are manual until v0.2 (auto-sync from monitoring)
- One service can have many SLOs (availability + latency + quality typical)
- Window typically 30d — shorter windows are noisy, longer hide trends

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| SLI returns no data | Metric not emitted yet | Verify metric exists in monitoring system |
| Burn rate alerts firing constantly | Target too aggressive | Re-evaluate target (or accept reality, fix performance) |
| Violations rarely recorded | Manual recording forgotten | Process: every incident → record SLO violation |
| Multiple SLOs with same SLI | Confusion about authoritative target | Consolidate; one SLI → one SLO is cleanest |
