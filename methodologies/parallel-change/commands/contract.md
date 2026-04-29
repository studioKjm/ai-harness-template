---
description: Advance a parallel-change plan from migrate to contract phase, verifying zero callers reference the old signature. Provided by the Parallel Change methodology.
---

# /contract — Advance to Contract Phase

> Migrate → Contract 전환. 구버전 제거 직전 게이트.

## When to use

- All callers have been switched from old to new signature
- Old code/schema is ready to be removed
- Tests pass against new signature

## Prerequisites

- Plan in `phase=migrate`
- `pc.py callers <id>` shows **0 callers of old**
- All migration commits merged

## Usage

```
/contract <plan-id>
```

## Instructions

This is the **highest-stakes transition** in the methodology — past contract phase, the old code/schema disappears. Two layers of verification:

### Step 1 — Pre-flight check

Before advancing, run:
```shell
python3 .harness/methodologies/parallel-change/scripts/pc.py callers <plan-id>
```

If old callers > 0, do NOT proceed. Tell the user which files still need migration.

### Step 2 — Advance

```shell
python3 .harness/methodologies/parallel-change/scripts/pc.py advance <plan-id> contract
```

The script verifies (one more time):
- Plan in phase=migrate
- Old callers count == 0
- If either fails, refuses transition

### Step 3 — Two gates now active for this plan

After contract phase:

| Gate | What it does |
|------|-------------|
| `check-parallel-state.sh` | On every commit: verifies old still has 0 callers AND new still exists. Blocks regressions. |
| `check-parallel-callers.sh` | On every commit: laser-focused — if old returns to >0 callers, BLOCK commit. |

Both gates are blocking (severity: blocking). Even if a commit accidentally re-introduces a reference to the old signature, it cannot be committed while plan is in contract phase.

### Step 4 — Removal of old code

After advancing to contract:
> "Contract phase active. You may now safely remove old code/schema files. Each removal commit must keep the gate in PASS — no caller references must reappear. When old files are deleted from disk, run `/parallel-change advance <id> done` to mark plan complete."

### Step 5 — Final transition: contract → done

When the user has actually removed old code/schema files:

```shell
python3 .harness/methodologies/parallel-change/scripts/pc.py advance <plan-id> done
```

This is mostly cosmetic — the plan moves to a "completed audit log" state. Gates stop checking it.

## Constraints

- This is irreversible by design. Once contract phase is entered, regressing to migrate requires manual yaml edit (intentional friction).
- DB migration order: usually `expand` (add new column) → `migrate` (dual-write or backfill) → `contract` (drop old column). Contract DB step should be a separate migration file from contract code.
- Do not commit the contract advancement and the old-code removal in the same commit. Advance phase first, then remove in subsequent commits — easier to audit and roll back.

## Failure modes

| Symptom | Likely cause | Fix |
|---------|------------|-----|
| "still has N caller(s)" | Migration incomplete | Switch remaining callers in `pc.py callers <id>` output |
| Caller appears after advance | False positive in pattern OR new code accidentally references old | Make pattern more specific in `caller_scan.exclude_files`, or fix the regression |
| Test files match old pattern | Tests still exercise old API | Move tests to new API or add test paths to `exclude_files` |
