---
description: Advance a parallel-change plan from expand to migrate phase. Verifies both old and new exist before transition. Provided by the Parallel Change methodology.
---

# /migrate-traffic — Advance to Migrate Phase

> Expand → Migrate 전환

## When to use

- After verifying with `/expand <id>` that both old and new coexist
- When ready to start switching callers from old to new (one PR at a time)

## Prerequisites

- Plan in `phase=expand`
- Both `old.caller_pattern` and `new.caller_pattern` registered
- Both patterns currently match in the codebase

## Usage

```
/migrate-traffic <plan-id>
```

## Instructions

### Step 1 — Run advance

```shell
python3 .harness/methodologies/parallel-change/scripts/pc.py advance <plan-id> migrate
```

The script:
- Validates both `caller_pattern`s are set
- Counts callers of old (must be > 0) and new (must be > 0)
- If valid: updates `phases.current = "migrate"` and appends to history
- If invalid: refuses transition with reason

### Step 2 — Report

On success:
> "Plan {id}: expand → migrate. Now switch callers one at a time. The state gate enforces both old and new continue to exist until /contract."

On failure (script's stderr will explain):
- "old signature has 0 callers" → either migration done out-of-band (advance to contract instead) or pattern wrong
- "new signature not found" → implement new alongside old before transitioning

### Step 3 — Migration guidance

After advancing to migrate, instruct the user on the workflow during this phase:

> "**Migrate phase rules:**
> - Switch callers from old → new in small commits (per consumer or per PR)
> - Each commit must keep both old and new working (state gate enforces this)
> - When all callers migrated and `pc.py callers <id>` shows 0 for old, run `/contract`"

## Constraints

- Cannot skip from expand to contract — must pass through migrate
- Cannot return to expand once advanced (state machine is forward-only; revert requires manual yaml edit)
- The migrate phase is where most of the work happens — it can take days/weeks. Plans stay open until /contract.

## Side effects

- Plan file `phases.current` changes to `migrate`
- Plan file `phases.history` gains an entry
- Plan file `last_check.timestamp` updated
- No code changes — this is purely a state transition
