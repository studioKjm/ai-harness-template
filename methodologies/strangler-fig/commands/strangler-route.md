---
description: Add or remove routing rules for a strangler-fig plan. Provided by the Strangler Fig methodology.
---

# /strangler-route — Manage Routing Rules

> Decide which endpoints/patterns flow to legacy vs new module.

## When to use

- After `/strangler new` — register the first patterns to route
- During coexist phase — flip patterns from legacy to new as new module catches up
- When discovering an unrouted endpoint (gate warned about it)

## Usage

```
/strangler-route add <plan-id> --pattern "PAT" --target legacy|new [--reason "..."] [--rule-id ID]
/strangler-route remove <plan-id> --rule-id <id>
```

## Prerequisites

- Plan exists (created via `/strangler new`)
- For `add`: `--pattern` and `--target` required

## Instructions

### Step 1 — Run the script

```shell
# Add rule
python3 .harness/methodologies/strangler-fig/scripts/sf.py route add \
  sf-2026-04-30-billing-rewrite \
  --pattern "POST /api/refunds" \
  --target new \
  --reason "validated 2 weeks in coexist, no incidents"

# Remove rule
python3 .harness/methodologies/strangler-fig/scripts/sf.py route remove \
  sf-2026-04-30-billing-rewrite \
  --rule-id rule-3
```

### Step 2 — Pattern formats supported

The pattern is a free-form string. Common conventions:

| Pattern style | Example | Use case |
|--------------|---------|---------|
| HTTP route | `POST /api/refunds` | REST API |
| HTTP wildcard | `GET /api/refunds/*` | URL family |
| Function symbol | `BillingService.calculate` | Direct function call routing |
| Queue topic | `events:refund.processed` | Async/event-driven |
| Feature flag | `flag:new-billing-enabled` | Flag-gated routing |

The facade implementation (in `<plan>.facade.path`) interprets these patterns. The methodology doesn't enforce a specific format.

### Step 3 — Coverage auto-recompute

Adding/removing rules triggers `_recompute_coverage`:
- `coverage.routed_count` updates
- `coverage.unrouted` list refreshes
- `coverage.percent` recomputes

If `coverage.legacy_endpoints` is empty, coverage stays at 0% even with many rules. Run `/strangler` show to verify endpoint list, or use `--scan-endpoints` to populate it from the codebase.

### Step 4 — Reporting

After `add`:
> "Added rule `{rule_id}`: `{pattern}` → `{target}`.
>  Coverage now {pct}% ({routed}/{total} endpoints)."

After `remove`:
> "Removed rule `{rule_id}`.
>  Coverage now {pct}%."

## Constraints

- `--rule-id` must be unique within the plan (auto-generated as `rule-N` if not specified)
- `--target` must be `legacy` or `new` (no third option)
- Pattern format is free-form — methodology trusts the user
- Cannot remove a rule that's the only `target: new` rule when in `new-primary` state (would force unintended rollback) — script doesn't enforce, but gate may warn

## Composition

When `parallel-change` is also active:
- Routing rule patterns can reference parallel-change function signatures
- Cross-link via plan's `links.parallel_changes`

When `exploration` is active:
- Spike findings can justify a routing rule (`reason: "see learning ln-2026-04-29-..."`)

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| `rule_id 'rule-X' already exists` | Manual ID conflict | Use auto-generated ID (omit --rule-id) |
| `--target must be 'legacy' or 'new'` | Typo | Fix arg |
| Coverage doesn't change after adding rule | `legacy_endpoints` empty | Run `coverage --scan-endpoints` first |
| Many `unrouted` endpoints listed | Legacy module has many endpoints, few rules | Either add rules incrementally, or accept some endpoints stay in legacy permanently (mark with `target: legacy`) |
