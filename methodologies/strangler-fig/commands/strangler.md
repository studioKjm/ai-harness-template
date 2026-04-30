---
description: Create or manage strangler-fig plans for module-level legacy migration. Provided by the Strangler Fig methodology.
---

# /strangler — Module-level Legacy Migration

> Replace a legacy module gradually via a facade — coexist, then cut over, then retire.

## When to use

- Legacy module is too risky for full rewrite
- Multiple consumers/endpoints — can't migrate atomically
- New implementation will replace legacy over weeks/months
- Want graceful rollback at each phase

**Not for**:
- Single-function signature change → use `parallel-change` (it's function-level)
- Greenfield work → use `ouroboros` (no legacy to strangle)
- One-shot rewrite where downtime is acceptable → just rewrite

## Usage

```
/strangler new <slug> --legacy <path> --new <path> --facade <path> [--title "..."]
/strangler list [--state legacy-only|coexist|new-primary|retired]
/strangler show <plan-id>
/strangler advance <plan-id> <state> [--note "..."] [--force]
```

For routing rules:
```
/strangler-route add <plan-id> --pattern "..." --target legacy|new [--reason "..."]
/strangler-route remove <plan-id> --rule-id <id>
```

For final retirement:
```
/strangler-retire <plan-id>
```

## Prerequisites

None. Strangler-fig is usable any time.

## Instructions

### Step 1 — Locate the script

```
.harness/methodologies/strangler-fig/scripts/sf.py
```

### Step 2 — Run the requested subcommand

```shell
python3 .harness/methodologies/strangler-fig/scripts/sf.py \
  new billing-rewrite \
  --legacy "src/legacy/billing/" \
  --new "src/billing/" \
  --facade "src/billing-facade/" \
  --title "Replace 2018 billing module with v2 architecture"
```

### Step 3 — Communicate state changes

After `new`:
> "Strangler plan `{id}` created. State: legacy-only.
>  Build the facade and at least one routed pattern in the new module before advancing.
>  Add routing rules with `/strangler-route add {id} --pattern '...' --target new`."

After `advance`:
> "Plan `{id}`: {from} → {to}. {N} routing rules. Coverage {pct}%.
>  {next-step hint based on state}"

State-specific guidance:
- legacy-only → coexist: "Now run traffic in production. Monitor for 1-2 weeks before advancing."
- coexist → new-primary: "Verify no incidents from new module in last 14 days. Performance parity check passed?"
- new-primary → retired: "Confirm legacy module has 0 inbound traffic for 30+ days before deletion."

### Step 4 — State machine semantics

```
[legacy-only] → [coexist] → [new-primary] → [retired]
                    ↓             ↓
              [legacy-only]  [coexist]    (rollback allowed)
```

| State | Meaning | Coverage typical |
|-------|---------|------------------|
| legacy-only | Initial. New + facade not built yet. | 0% |
| coexist | Facade routes per rules. New + legacy both serve. | 10-80% |
| new-primary | New serves majority. Legacy = fallback only. | 80-99% |
| retired | Legacy deleted from codebase. | 100% |

### Step 5 — Cutover criteria (auto-checked)

The script blocks state transitions if criteria unmet (use `--force` to override with audit trail):

| Target state | Auto-checked criteria |
|-------------|----------------------|
| coexist | facade.exists_yet=true, ≥1 routing rule, new_module.exists_yet=true |
| new-primary | ≥80% rules target new |
| retired | all rules target new, coverage 100% |

Manual criteria (in template, not auto-checked):
- "no production incidents in last N days"
- "performance parity verified"
- "rollback plan documented"

These should be added to the plan's `cutover_criteria` block and reviewed manually before advancing.

## Composition with other methodologies

| Combo | Effect |
|-------|--------|
| `+ ouroboros` | New module's design follows seed spec; facade routing decisions are AC of stories |
| `+ parallel-change` | Within new module, function-level breaking changes use parallel-change (nested state machines) |
| `+ exploration` | Spike before strangling — measure legacy behavior, pick architecture |
| `+ bmad-lite` | Each routed pattern → story with persona/AC. Useful when migration has UX implications |
| `+ living-spec` | If new module's seed evolves during migration — diff tracks impact on routing rules |

## Constraints

- Only ONE retired transition per plan (irreversible — delete plan to start over)
- Rollback (coexist → legacy-only or new-primary → coexist) is allowed but logged
- A plan with > 100 routing rules is a smell — probably should be split into multiple plans
- Routing rule patterns must be unique within a plan (script enforces)

## Failure modes

| Symptom | Likely cause | Fix |
|---------|------------|-----|
| `cutover criteria not met` on advance | Manual checklist not run, or auto criteria genuinely unmet | Address criteria, or `--force` with explicit note |
| Coverage stuck at low % | `legacy_endpoints` list is empty | Run `coverage <id> --scan-endpoints "src/legacy/**/*.ts"` |
| Same pattern routed by multiple rules | Inconsistent state | `route remove` duplicate, keep most recent |
| Legacy module re-grows during coexist | Anti-pattern: stop adding to legacy | Lock legacy directory, all new code goes in new |
