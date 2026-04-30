---
description: Final retirement check — verifies legacy module has zero inbound traffic and can be deleted. Provided by the Strangler Fig methodology.
---

# /strangler-retire — Final Retirement Check

> The point of no return. After retire, legacy module is deleted.

## When to use

- All routing rules target `new`
- Coverage = 100%
- Legacy module has had 0 inbound traffic for 30+ days (manually verified)
- Ready to delete legacy code from the repository

**This is the highest-stakes transition.** Misuse means deleting code that's still serving production traffic.

## Prerequisites

- Plan in `new-primary` state
- All `routing_rules` have `target: new`
- `coverage.percent` == 100
- (Manual) production telemetry confirms legacy module has 0 calls

## Usage

```
/strangler-retire <plan-id>
```

This is an alias for `/strangler advance <plan-id> retired`.

## Instructions

### Step 1 — Pre-flight check

Before advancing:
```shell
python3 .harness/methodologies/strangler-fig/scripts/sf.py show <plan-id>
```

Verify:
- All routing rules `target: new`
- `coverage.percent: 100`
- `coverage.unrouted: []`

### Step 2 — Manual verification (off-system)

The methodology cannot check production traffic. The user MUST verify before retiring:

1. Application logs / APM: 0 calls to legacy module functions in last 30 days
2. Database query logs (if applicable): 0 reads from legacy-specific tables
3. Feature flag system (if used): legacy paths fully disabled
4. Stakeholder sign-off (for client projects): client has reviewed cutover

### Step 3 — Run retire

```shell
python3 .harness/methodologies/strangler-fig/scripts/sf.py retire <plan-id>
```

The script enforces (auto):
- Plan in `new-primary` state
- All rules target `new`
- Coverage 100%

If any check fails, the script blocks. Use `--force` only with explicit reason recorded.

### Step 4 — Post-retire actions

After advancing to `retired`:
> "Plan `{id}` retired. You may now safely delete the legacy module:
>   - Remove `{legacy_module.path}` directory in a separate commit
>   - Update facade to remove legacy fallback code
>   - If facade itself becomes unnecessary, remove it after one more cycle
>   - Mark related ADRs as superseded"

Best practices:
- **Separate the state transition commit from the legacy deletion commit** — easier to review, easier to revert
- Keep the plan file (`.harness/strangler-fig/plans/<id>.yaml`) as audit trail — do not delete

### Step 5 — Final state

After retire:
- Plan state: `retired`
- Facade can be simplified (no more legacy branch)
- Legacy code deleted from repo
- Plan stays in plans/ as historical record (gates skip it)

## Constraints

- `retired` is terminal — no transition out
- Cannot retire from `legacy-only` or `coexist` (must pass through new-primary)
- `--force` is logged in `history[].forced` and `history[].unmet_criteria`

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| `all rules must target new — N still target legacy` | Some endpoints permanently kept in legacy | Either: (1) migrate them to new before retire, or (2) remove the rules + accept those endpoints simply don't exist anymore |
| `coverage must be 100%` | unrouted endpoints | Add rules for them (target legacy if intentionally kept, or new if migrated) |
| Legacy traffic spikes after retire | Cached client referencing old endpoints | Roll back via manual yaml edit (state: new-primary), restore legacy code, investigate cache TTL |

## Anti-patterns

- ❌ Retiring without 30-day quiet period — clients with cached configs may still call legacy
- ❌ Retiring + deleting legacy in same commit — hard to roll back if monitoring missed something
- ❌ Forcing retire because "we'll just fix it later" — this is the hardest fix in the project lifecycle
- ❌ Skipping facade simplification — the facade outlives the plan and accumulates dead routing logic over time
