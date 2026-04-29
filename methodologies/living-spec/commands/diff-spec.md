---
description: Semantic diff between two seed versions (entities, AC, actions, constraints, architecture). Provided by the Living Spec methodology. Use after /seed creates seed-vN+1 to understand what changed since seed-vN.
---

# /diff-spec — Seed Version Diff

> seed-vN ↔ seed-v(N+1) 의 의미 단위 diff

## When to use

- After `/seed` creates a new version on top of an existing one
- Before running `/migrate-tasks` (this report informs that classification)
- When reviewing a colleague's `seed-evolve` PR

## Prerequisites

- Living Spec methodology must be active (`/methodology use living-spec` or `/methodology compose ouroboros living-spec`)
- At least two seed versions must exist in `.harness/ouroboros/seeds/`

## Usage

```
/diff-spec                       # auto: latest two seeds
/diff-spec 1 2                   # explicit version numbers
/diff-spec <pathA> <pathB>       # explicit file paths
```

## Instructions

You are running the **diff-spec** tool. Delegate to the Python script — do not attempt to compute the diff yourself; the script's structural comparison is far more reliable than LLM judgment for this.

### Step 1 — Locate the script

Try in order:
1. `.harness/methodologies/living-spec/scripts/diff-spec.py`
2. `methodologies/living-spec/scripts/diff-spec.py` (if running from harness source)

If neither exists, instruct the user to activate the Living Spec methodology first.

### Step 2 — Resolve arguments

If the user gave no args, find the two latest seeds in `.harness/ouroboros/seeds/seed-v*.yaml` and pass their version numbers:

```shell
ls .harness/ouroboros/seeds/seed-v*.yaml | sort -V | tail -2
```

### Step 3 — Run

```shell
python3 .harness/methodologies/living-spec/scripts/diff-spec.py <from> <to>
```

The script:
- Compares: `acceptance_criteria` (by id), `ontology.entities` (by name), `ontology.actions` (by name), `constraints.must` / `must_not` (by string), `architecture.pattern`, `goal.summary`
- Saves report to `.harness/ouroboros/seeds/.diffs/diff-v{a}-to-v{b}.md`
- Prints the markdown report to stdout
- Heuristic flags **breaking-change indicators** (removed AC/entities/actions, new must_not, architecture shift)

### Step 4 — Report

Relay the script's stdout. If the report contains a 🔴 breaking-change section, add a one-line suggestion:

> "Breaking changes detected. Consider activating Parallel Change methodology before implementing: `/methodology compose ouroboros living-spec parallel-change`"

## Constraints

- Do not edit seed files based on the diff. Seeds are immutable; create a new version with `/seed` (which automatically picks up the prior version).
- Do not skip running the script and "summarize from memory" — structural diff requires line-level comparison.
- Reports are saved with version-derived filenames; do not rename or move them — `/migrate-tasks` may read them.

## Output location

```
.harness/ouroboros/seeds/.diffs/diff-v{from}-to-v{to}.md
```
