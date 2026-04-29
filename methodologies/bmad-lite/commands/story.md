---
description: Decompose a feature into BMAD-style user stories with acceptance criteria. Provided by the BMAD-lite methodology.
---

# /story — Create or Refine a User Story

> Convert a fuzzy feature ask into a structured, testable story.

## When to use

- After `/seed` exists and you're about to implement a new feature
- When a backlog item is too vague to start coding
- Before `/decompose` — story output feeds into task decomposition

## Usage

```
/story new <slug>             # Create new story (interactive)
/story refine <story-id>      # Run pm-strict against existing story
/story show <story-id>        # Print story
/story list [epic-id]         # List stories (filter by epic)
/story link <story-id> <epic-id>  # Attach to epic
```

## Prerequisites

- Seed exists at `.harness/ouroboros/seeds/seed-vN.yaml`
- (Optional) Active persona for richer output. Recommend running:
  ```
  /persona analyst    # to populate analyst_notes
  /persona ux-designer  # if story has UI surface
  /persona pm-strict   # to validate before marking refined
  ```

## Instructions

### Step 1 — Generate story ID

`st-YYYY-MM-DD-<slug>`. Path: `.harness/bmad-lite/stories/<id>.yaml`.

### Step 2 — Bootstrap from template

Copy `templates/story.yaml` to the new path. Fill in:
- `id`, `created_at`, `seed_version`
- `narrative` (required — ask user if missing)
- At least one `acceptance_criteria` entry

### Step 3 — Run analyst pass (if persona active)

If active persona == `analyst`:
- Read seed, identify entities the story touches
- Populate `analyst_notes`
- Flag ambiguities — if > 3, advise: "Run /interview before continuing"

### Step 4 — Run ux-designer pass (if persona active)

If active persona == `ux-designer` AND story has UI surface:
- Populate `ux_notes` with flow summary, states, primitives
- Default to existing components in the codebase

### Step 5 — Run pm-strict validation

ALWAYS run pm-strict at the end of `/story new` or `/story refine`:

Check each gate:
- `narrative.persona`, `.capability`, `.outcome` — all present, no nulls
- `acceptance_criteria` count ≥ 1
- Each AC has `given`, `when`, `then` filled
- No weasel words (fast / easy / intuitive / robust / secure / scalable / user-friendly)
  unless paired with a metric or behavior
- Story scope is single deployable increment (no "and also" in narrative)

Append to `pm_strict_log`:

```yaml
- timestamp: "<now>"
  verdict: "pass | block"
  issues: [...]
  overrides: []
```

### Step 6 — State transition

| Result | New `status` |
|--------|-------------|
| pm-strict pass on first draft | `refined` |
| pm-strict block | `draft` (stays) |
| User runs `/decompose` referencing this story | `ready` |

### Step 7 — Report

On pass:
> "Story `{id}` refined. {N} AC, {M} entities touched.
>  Next: `/decompose {id}` to break into tasks."

On block:
> "Story `{id}` BLOCKED by pm-strict. Issues:
>  - {field}: {issue} → {fix}
>  Fix and re-run `/story refine {id}`."

## Override (escape hatch)

If pm-strict blocks but the story is intentional (rare):

```
/story refine <id> --override "<reason>"
```

This appends to `pm_strict_log[].overrides` with reason, allowing status to advance to `refined`. Override is permanent in the audit log.

## Constraints

- Stories without a parent seed are rejected (BMAD-lite extends ouroboros, not replaces)
- One story = one deployable increment. Multi-feature stories must be split.
- No time/effort estimates in stories — only `estimated_size: S|M|L`
- AC count > 8 is a smell — story is probably an epic in disguise

## Failure modes

| Symptom | Likely cause | Fix |
|---------|------------|-----|
| pm-strict blocks every story | User writing too generic ACs | Run `/persona analyst` first to surface entities |
| Story keeps growing during refinement | Scope creep — pm-strict should have caught | Split into multiple stories under one epic |
| `analyst_notes` empty | Persona not active during `/story new` | Run `/persona analyst` then `/story refine <id>` |
