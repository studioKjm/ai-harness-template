---
description: Manage parallel-change plans (Expand → Migrate → Contract). Provided by the Parallel Change methodology. Use this for backward-incompatible changes (DB schema, API signatures, breaking type changes) that require zero-downtime migration.
---

# /parallel-change — Plan Manager

> 호환 깨는 변경을 다운타임 0으로 처리하는 상태머신

## When to use

- DB 스키마 변경 (컬럼 타입·이름·제약 변경)
- API 시그니처 변경 (필수 파라미터 추가/제거)
- 함수/타입 시그니처 breaking change
- `/diff-spec`이 🔴 Breaking-change indicator를 띄웠을 때

## Prerequisites

- Parallel Change methodology active: `/methodology compose ouroboros parallel-change`

## Subcommands

```
/parallel-change new <id> [--title TITLE]    Create new plan in phase=expand
/parallel-change list                         List all plans + current phase
/parallel-change show <id>                    Print full plan
```

For phase transitions, use the dedicated commands:
- `/expand` — register/verify expand phase
- `/migrate-traffic` — advance to migrate
- `/contract` — advance to contract

## Instructions

Delegate to the Python script. Do not hand-edit plan YAML files — they are state-machine artifacts owned by the dispatcher.

### Step 1 — Locate the script

```
.harness/methodologies/parallel-change/scripts/pc.py
```

### Step 2 — Resolve subcommand

```shell
python3 .harness/methodologies/parallel-change/scripts/pc.py new <id> --title "<title>"
python3 .harness/methodologies/parallel-change/scripts/pc.py list
python3 .harness/methodologies/parallel-change/scripts/pc.py show <id>
```

### Step 3 — Plan ID convention

Use `pc-<YYYY-MM-DD>-<short-slug>` format. Example:
```
pc-2026-04-28-refund-amount-enum
pc-2026-04-28-orders-api-v2
```

### Step 4 — After creating a plan

Guide the user through the next step:

1. Register the old signature (what's being replaced):
   ```
   pc.py set-old <id> --symbol "Refund.amount" --pattern 'Refund\.amount\b'
   ```

2. Implement the new signature alongside the old, then register:
   ```
   pc.py set-new <id> --symbol "Refund.amount_type" --pattern 'Refund\.amount_type\b'
   ```

3. When ready to transition: `/migrate-traffic` (will validate expand criteria)

### Step 5 — Caller pattern guidance

The `caller_pattern` is a regex passed to ripgrep/grep. Common examples:

| Target type | Pattern example |
|------------|----------------|
| Property access | `Refund\.amount\b` |
| Function call | `\boldFunction\s*\(` |
| API endpoint | `POST\s+/api/v1/refunds` |
| DB column | `\brefunds\.amount\b` |
| Type/Class name | `\bOldType\b` |

Make patterns specific enough to avoid false positives but flexible enough to catch all callers. Test with:
```
pc.py callers <id>
```

## Constraints

- Multiple plans can be active at once (different changes in parallel)
- Plans in `phase=done` are kept for audit (not auto-deleted)
- Never advance two phases at once (`expand → contract` directly is rejected)
- Patterns in plans should not match within the plan files themselves (gates exclude `.harness/`)

## Output location

```
.harness/parallel-change/plans/<plan-id>.yaml
```
