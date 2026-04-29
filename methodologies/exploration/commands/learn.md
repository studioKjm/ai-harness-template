---
description: Capture learnings from a closed spike and optionally promote them to ADR or seed evolution. Provided by the Exploration methodology.
---

# /learn — Record and Promote Spike Findings

> A spike without a learning record is just lost time. Make the knowledge durable.

## When to use

- Right before closing a spike (`/spike close`) — capture findings while context is fresh
- After reviewing a learning to promote it to a permanent artifact (ADR, seed, code)

## Usage

```
/learn record <spike-id>          # Create learning.yaml from spike findings
/learn show <learning-id>          # Print learning
/learn list [--spike <spike-id>]   # List all learnings (optionally filtered)
/learn promote <learning-id> --to <adr|seed|code> --target <id>
                                   # Mark learning as applied to a specific artifact
```

## Prerequisites

- `record`: spike must exist in `spiking` or `learned` state
- `promote`: learning must exist; target artifact must exist (ADR file, seed-vN, or code path)

## Instructions

### Step 1 — `/learn record`

For a recording invocation, the agent (you) does most of the work, not a script:

1. Load the spike: `.harness/exploration/spikes/<spike-id>/spike.yaml`
2. Read the sandbox: `.harness/exploration/spikes/<spike-id>/sandbox/` — note files, measurements, code patterns
3. Generate a learning ID: `ln-<date>-<slug>` (slug derived from spike question)
4. Bootstrap from template: `.harness/methodologies/exploration/templates/learning.yaml`
5. Fill in:
   - `id`, `created_at`, `spike_id`, `question` (copy from spike)
   - `finding.summary` — your 2-3 sentence answer
   - `finding.confidence` — high/medium/low (be honest)
   - `hypothesis_check` — compare spike's hypothesis to actual finding (the most valuable field)
   - `evidence` — at least one concrete artifact (file path, measurement, error message)
   - `recommendation.action` — adopt | reject | defer | further_spike
   - `applies_to` — where in the project this finding applies
6. Save to `.harness/exploration/learnings/<learning-id>.yaml`
7. Update spike's `links.learning_id` to point at the new learning

### Step 2 — Reporting after `/learn record`

> "Learning `{id}` recorded. Confidence: {confidence}.
>  Recommendation: **{action}**.
>  Promotion targets identified: {applies_to summary}.
>
>  Next:
>   - To close the spike: `/spike close {spike-id} --learning-id {id}`
>   - To make this knowledge durable: `/learn promote {id} --to <adr|seed|code> --target <id>`"

### Step 3 — `/learn promote`

Promotion makes the learning **citable** — future engineers (or future-you) can find it.

Three promotion paths:

#### a) Promote to ADR (architectural decisions)

Use when finding answers a "should we use X?" question.

1. Open `docs/adr.yaml`
2. Append a new ADR entry referencing the learning:
   ```yaml
   - id: ADR-NNN
     title: "<short title from learning.finding.summary>"
     status: accepted
     context: "<learning.question>"
     decision: "<learning.recommendation.action> — <rationale>"
     consequences: "<learning.recommendation.caveats>"
     evidence:
       learning_id: "<learning-id>"
       spike_id: "<spike-id>"
   ```
3. Update learning: `promotion.to_adr = "ADR-NNN"`, `promotion.promoted_at = <now>`

#### b) Promote to seed (informs new spec)

Use when finding changes what should be built.

1. Note the learning id in seed-vN draft: `evidence_sources: [<learning-id>]`
2. Run `/seed` flow with this learning as input
3. Update learning: `promotion.to_seed = "seed-vN"`

#### c) Promote to code (production implementation)

Use when finding directly enabled production code.

1. In the production code, add a comment referencing the learning (only if non-obvious — usually not needed)
2. Update learning: `promotion.to_code = true`

### Step 4 — `/learn list`

Iterate `.harness/exploration/learnings/*.yaml`. Print:

```
  ln-2026-04-29-llm-streaming    [adopt]    high     → ADR-014
  ln-2026-04-22-redis-cluster    [reject]   medium   (not promoted)
  ln-2026-04-15-edge-functions   [defer]    low      (further_spike: sp-2026-04-25-...)
```

Format: `<id>  [<action>]  <confidence>  → <promotion or status>`

## Constraints

- Cannot promote a learning whose spike is `abandoned` (abandoned ≠ learned)
- Promotion is one-way — un-promoting requires manual yaml edit and an audit log entry
- A learning without evidence is not allowed to be promoted (script blocks promotion if `evidence: []`)

## Anti-patterns

- ❌ Recording a learning with `confidence: high` for a 30-minute spike — be honest about evidence depth
- ❌ Skipping `hypothesis_check` — this is where the real intuition-building happens
- ❌ Promoting every learning to ADR — ADRs are for *decisions*, not *findings*. Findings without a decision are fine to leave un-promoted

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| `learning has no evidence` blocks promotion | Recorded too quickly | Add at least one `evidence[]` entry with file/URL |
| Promotion target doesn't exist | ADR-NNN or seed-vN not created yet | Create target first, then promote |
| Spike still `spiking` | Forgot to close | `/spike close <id> --learning-id <id>` after `/learn record` |
