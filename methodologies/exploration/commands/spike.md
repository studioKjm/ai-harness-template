---
description: Create or manage time-boxed spikes (research investigations) with sandbox exempt from spec/boundary gates. Provided by the Exploration methodology.
---

# /spike — Time-boxed Investigation

> "I don't know yet, and that's the question." — bound the unknown before writing real code.

## When to use

- You don't know what to build yet — ouroboros / BMAD-lite require knowing
- You're stuck on a story because of a technical unknown
- You're evaluating a library, API, or architecture choice
- You need real measurements (latency, payload size, behavior)

**Not for**: implementing known features. Use `/decompose` (ouroboros) or `/story` (BMAD-lite) for that.

## Usage

```
/spike new <slug> --question "..." [--timebox 4] [--hypothesis "..."]
/spike list [--status questioning|spiking|learned|applied|abandoned]
/spike show <spike-id>
/spike start <spike-id>             # questioning → spiking (timebox starts)
/spike close <spike-id> [--learning-id LN-...]   # spiking → learned
/spike abandon <spike-id> --reason "..."
/spike apply <spike-id>              # learned → applied (after promotion)
```

## Prerequisites

None. `exploration` is a base methodology — usable at any point including before `/interview`.

## Instructions

### Step 1 — Locate the script

```
.harness/methodologies/exploration/scripts/spike.py
```

### Step 2 — Run the requested subcommand

Pass through all arguments. Examples:

```shell
python3 .harness/methodologies/exploration/scripts/spike.py \
  new llm-streaming-vercel \
  --question "Can I stream OpenAI tokens through Vercel Edge with TTFT < 300ms?" \
  --timebox 4 \
  --hypothesis "Yes, using AI SDK + Edge runtime"
```

### Step 3 — Communicate state changes back to the user

The script prints next-step hints. Surface them. Examples:

- After `new`:
  > "Spike `{id}` created. Sandbox: `{path}`.
  >  Code in this directory is exempt from layer/spec/structure gates.
  >  When you start working, run `/spike start {id}` to begin the timebox."

- After `start`:
  > "Timebox running. Expires at `{expires_at}`.
  >  At expiry: stop, capture findings via `/learn record {id}`, then `/spike close {id}`."

- After `close`:
  > "Spike `{id}` closed (learned). Findings in `{learning_id}.yaml`.
  >  When ready to apply (ADR / seed update / production code), run `/spike apply {id}`."

### Step 4 — Sandbox semantics

The directory `.harness/exploration/spikes/<id>/sandbox/` is special:
- **Exempt from**: boundaries, spec, structure gates (via `relaxes_gates` in manifest)
- **Not exempt from**: secrets, security gates (these always run)
- **Not commitable to production**: sandbox code is throwaway by definition

If user wants to keep code from sandbox: explicitly copy out, refactor to layered structure, then commit to the real project tree.

### Step 5 — Timebox enforcement

The script does NOT auto-kill at timebox expiry — softness by design (real spikes sometimes run over by 30 min). But:
- `/spike show` displays `expires_at` so user can self-monitor
- If timebox exceeds 2× duration, suggest:
  > "Spike has run 2× past timebox. Either:
  >   1. /spike abandon (the question is bigger than expected — restart with bigger timebox)
  >   2. /spike close --learning-id ... (capture what you learned, even if incomplete)"

## Constraints

- Question must end with `?` (script enforces)
- Cannot skip states — must go questioning → spiking → learned → applied
- Cannot reopen abandoned/applied spikes — start a new spike
- One spike = one question. If question morphs, close + start new one.

## State machine

```
[questioning] → [spiking] → [learned] → [applied]
       │           │           │
       └───────────┴───────────┴──────→ [abandoned]
```

| From | To | Trigger |
|------|-----|---------|
| questioning | spiking | `/spike start <id>` (timebox starts) |
| spiking | learned | `/spike close <id>` (with linked learning) |
| learned | applied | `/spike apply <id>` (after promotion fields set) |
| any active | abandoned | `/spike abandon <id> --reason "..."` |

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| `cannot transition X → Y` | Skipped state | Run intermediate transitions in order |
| `learning not found` on close | `/learn record` not yet run | Run `/learn record <spike-id>` first |
| `learning has no promotion target` on apply | Learning never reviewed | Edit learning.yaml's `promotion.to_adr` / `to_seed` / `to_code` field |
| Sandbox code accidentally committed to prod tree | Forgot sandbox is throwaway | Move to proper tree + ensure it passes all gates |

## Composition with other methodologies

- **+ ouroboros**: spike findings can drive a new `/seed` (status: applied → linked to seed-v2)
- **+ living-spec**: spike abandons answer to "should we evolve the seed?" — `/diff-spec` consumes the learning
- **+ BMAD-lite**: spike findings can resolve `analyst.ambiguities` so a story can be refined
- **+ parallel-change**: spikes can validate that a planned breaking change actually achieves the desired outcome before commit
