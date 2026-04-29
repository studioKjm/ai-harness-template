---
description: Switch the active reasoning persona (analyst | ux-designer | pm-strict). Provided by the BMAD-lite methodology.
---

# /persona — Switch Active Reasoning Persona

> "Same brain, different lens." — temporarily shift how you reason about the spec.

## When to use

- Drafting a new story → start with `analyst`
- Story has UI surface → switch to `ux-designer` to design the flow
- Story looks sloppy → switch to `pm-strict` to validate format
- Returning to general engineering → `/persona clear`

## Usage

```
/persona <name>           # Activate persona
/persona                  # Show current persona
/persona clear            # Return to default reasoning
/persona list             # List available personas
```

## Available personas (BMAD-lite)

| Name | Role | Use when |
|------|------|----------|
| `analyst` | Domain analyst | Mapping fuzzy goals to entities/behaviors |
| `ux-designer` | UX flow designer | Designing minimal user flows and states |
| `pm-strict` | PM validator | Enforcing AC quality, blocking vague stories |

## Instructions

### Step 1 — Resolve the persona file

```
.harness/methodologies/bmad-lite/personas/<name>.md
```

If file missing → list available personas and abort.

### Step 2 — Load persona context

Read the persona file completely. Persona files contain:
- Voice (how to speak)
- Inputs (what to read)
- Outputs (what shape to produce)
- Constraints (what NOT to do)

### Step 3 — Update state

Write to `.harness/state/bmad-lite.yaml`:

```yaml
active_persona: "<name>"
activated_at: "<ISO-8601>"
methodology: bmad-lite
previous_persona: "<previous | null>"
```

### Step 4 — Acknowledge the shift

> "Persona shifted: **{name}**. {one-line voice summary from persona file}.
>  I will produce output in the format defined by `personas/{name}.md`."

### Step 5 — Apply persona until cleared

All subsequent reasoning in this session follows the persona's:
- Voice / questions / refusal patterns
- Output schema (the `Outputs` section of the persona file)
- Constraints

Until the user runs `/persona clear` or switches to another persona.

## Constraints

- Only ONE persona active at a time (no compositions — that's anti-BMAD)
- Persona does NOT change available tools, only reasoning style
- pm-strict cannot self-override its block verdicts — user must explicitly override
- Personas only change reasoning shape, never bypass gates

## Failure modes

| Symptom | Cause | Fix |
|---------|------|-----|
| Persona file not found | Methodology not installed | `/methodology compose ouroboros bmad-lite` |
| Output drifts back to default voice | Long context, persona context fading | Re-run `/persona <name>` to reload |
| pm-strict keeps blocking | Story is genuinely vague | Run `/persona analyst` first to surface entities |
