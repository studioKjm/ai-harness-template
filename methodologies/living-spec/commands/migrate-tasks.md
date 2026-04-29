---
description: Classify existing decompose tasks against a new seed version. Outputs task-migration-plan.yaml with categories (unchanged/modified/deprecated/added). Provided by the Living Spec methodology.
---

# /migrate-tasks — Task Migration Planner

> 새 seed 버전에 대해 기존 태스크 영향 분석

## When to use

- After `/diff-spec` reveals AC/entity/action changes between seed versions
- Before re-running `/decompose` for the new version (avoids losing context from prior tasks)
- When an external requirement change forces breaking AC removal

## Prerequisites

- Living Spec methodology active
- `.harness/ouroboros/tasks/` exists with tasks from prior `/decompose` runs
- Both source and target seed versions must exist

## Usage

```
/migrate-tasks --to 2                # auto-detect 'from' as latest version below 2
/migrate-tasks --from 1 --to 3       # explicit
/migrate-tasks                       # auto: from latest-1 to latest
```

## Instructions

Delegate to the Python classifier; do not classify tasks by reading them yourself — the script's reference matching against seed signatures is more reliable than free-form LLM judgment.

### Step 1 — Locate the script

```
.harness/methodologies/living-spec/scripts/migrate-tasks.py
```

### Step 2 — Resolve `--to` if missing

If the user didn't specify `--to`, default to the highest-numbered seed:

```shell
ls .harness/ouroboros/seeds/seed-v*.yaml | sort -V | tail -1 | grep -oE 'v[0-9]+' | tr -d 'v'
```

### Step 3 — Run

```shell
python3 .harness/methodologies/living-spec/scripts/migrate-tasks.py --to <version>
```

The script:
- Reads all `.harness/ouroboros/tasks/*.yaml` (excluding `migration-plans/`)
- Compares each task's `references.{ac, entities, actions}` against target seed's signatures
- Classifies as: **unchanged** (refs intact), **deprecated** (refs removed), **modified** (placeholder for v0.2)
- Identifies **added** items: AC/entities/actions present in target seed but not covered by any task
- Saves to `.harness/ouroboros/tasks/migration-plans/migration-v{from}-to-v{to}.yaml`

### Step 4 — Report

Relay the script's stdout summary. Then surface follow-up recommendations:

| Category | Recommended next action |
|----------|------------------------|
| `unchanged` | No action needed — these tasks remain valid |
| `modified` | Review each — open the task and check whether AC tightening requires re-implementation |
| `deprecated` | Decide per-task: archive, delete, or replace. Suggest using `/decompose --replace <task-id>` once available |
| `added` | Run `/decompose` against the new seed version to generate covering tasks |

If `summary.deprecated > 0`, also suggest:

> "{N} tasks are now deprecated. Before deleting, consider whether their work product (code/tests) needs to be migrated or removed via Parallel Change."

## Confidence handling

The migration plan includes a `confidence` block. Current heuristic only:
- `name_match` — 1.0 if all entities in tasks are still in target seed
- `structural_match` — 0.7 default (placeholder; v0.2 will deepen)
- `semantic_match` — 0.0 (LLM-assisted match planned for v0.3)

If `confidence.overall < 0.6`, do not auto-apply — surface to user for review.

## Constraints

- Do not modify the migration plan file directly; it is generated output. To override classifications, re-run the script with adjusted seeds.
- Do not delete tasks based on `deprecated` classification without explicit user approval — the heuristic can miss cases where an entity was renamed (rather than removed).
- Tasks that have no `references` block default to `unchanged` (no signal to decide otherwise).

## Output location

```
.harness/ouroboros/tasks/migration-plans/migration-v{from}-to-v{to}.yaml
```
