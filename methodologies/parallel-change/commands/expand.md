---
description: Verify the expand phase of a parallel-change plan — both old and new signatures must coexist in the codebase. Provided by the Parallel Change methodology.
---

# /expand — Verify Expand Phase

> Expand 단계: 신·구 시그니처 공존 상태 확인

## When to use

- Right after creating a plan with `/parallel-change new <id>` and registering both old/new signatures
- Before running `/migrate-traffic` (this verifies the expand-phase invariants are met)

## Prerequisites

- Plan exists in `phase=expand`
- `old.caller_pattern` and `new.caller_pattern` set in the plan

## Usage

```
/expand <plan-id>
```

## Instructions

This command does NOT advance phase — it only verifies expand criteria and reports caller counts.

### Step 1 — Locate the script

```
.harness/methodologies/parallel-change/scripts/pc.py
```

### Step 2 — Run callers count

```shell
python3 .harness/methodologies/parallel-change/scripts/pc.py callers <plan-id>
```

This prints:
- Caller count of OLD pattern (should be > 0 in expand phase)
- Caller count of NEW pattern (should be > 0 if implementation started)

### Step 3 — Report

Surface the count to the user. Add interpretation:

| OLD callers | NEW callers | Interpretation |
|------------|------------|----------------|
| > 0 | > 0 | ✅ Expand healthy — both coexist |
| > 0 | 0 | ⏳ New not yet implemented — finish implementation before /migrate-traffic |
| 0 | > 0 | ⚠ Old already gone — was migration done out-of-band? Use `pc.py advance <id> contract` |
| 0 | 0 | ❌ Patterns wrong or change abandoned — re-check `caller_pattern` |

### Step 4 — Suggest next step

If healthy expand:
> "Expand verified. When all callers are ready to switch, run `/migrate-traffic <plan-id>`"

If new not yet present:
> "Implement the new signature alongside the old, then re-run /expand"

## Constraints

- /expand never modifies the plan beyond updating `last_check` timestamps
- /expand does not advance phase — that's `/migrate-traffic`'s job
- Pattern false positives can inflate counts — adjust regex specificity if numbers seem off

## Notes

- The `check-parallel-state.sh` gate runs this same logic on every commit and BLOCKS commits that put a plan in inconsistent state. So you don't need to run /expand manually before each commit — it just helps you understand current state on demand.
