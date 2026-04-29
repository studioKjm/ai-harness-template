---
description: Methodology plugin manager. List, activate, compose, deactivate development methodologies (Ouroboros, Living Spec, Parallel Change, BMAD-lite, Exploration). Harness gates remain enforced regardless of methodology.
---

# /methodology — Methodology Plugin Manager

> 하네스(고정 게이트) 위에 사용자가 상황별로 골라 쓰는 개발 방법론 시스템

## Concept

```
┌─────────────────────────────────────────┐
│  HARNESS CORE (always enforced)         │
│  • 11 gates (security, layers, spec)    │
│  • Hooks (post-edit, pre-commit)        │
└─────────────────────────────────────────┘
                   ▲
                   │  methodology can ADD gates,
                   │  cannot REMOVE core ones
                   │
┌─────────────────────────────────────────┐
│  METHODOLOGY LAYER (user-selected)      │
│  ouroboros (default) | living-spec |    │
│  parallel-change | bmad-lite |          │
│  exploration | <custom>                 │
└─────────────────────────────────────────┘
```

## Usage

```
/methodology                          # alias for `list`
/methodology list                     # show all installed methodologies + active state
/methodology current                  # show currently active methodology(ies)
/methodology info <name>              # show one methodology in detail
/methodology use <name>               # activate (replaces previous unless composing)
/methodology compose <a> <b> [...]    # activate multiple methodologies together
/methodology deactivate <name>        # turn off one methodology (other actives stay)
```

## Instructions

You are the **Methodology Dispatcher**. Your job is to delegate to the shell library at `.harness/lib/methodology.sh` (or `lib/methodology.sh` if running from harness source) and report results clearly.

### Step 1 — Locate the dispatcher script

Try in order:
1. `.harness/lib/methodology.sh` (installed in user project)
2. `lib/methodology.sh` (running from harness source)

If neither exists, instruct the user to run `init.sh` (or re-run with `--force`) to install the methodology system, then stop.

### Step 2 — Parse the user's subcommand

Map natural language to subcommands when needed:
- "show methodologies" / "what's available" / blank → `list`
- "what's active" / "current setup" → `current`
- "tell me about <name>" / "details on <name>" → `info <name>`
- "switch to <name>" / "use <name>" → `use <name>`
- "combine <a> and <b>" → `compose <a> <b>`
- "turn off <name>" / "stop using <name>" → `deactivate <name>`

### Step 3 — Invoke the dispatcher

Call via Bash:

```shell
bash <path-to-methodology.sh> <subcommand> [args...]
```

The script handles all state mutation, prerequisite checking, and YAML editing. Do NOT hand-edit `.harness/methodology/_state.yaml` — that file is owned by the dispatcher.

### Step 4 — Report

After the script returns:
- On success: relay the script's output verbatim, then add a one-line next-step suggestion if relevant
- On error: relay the error and suggest the most likely fix (missing yq/python3, missing manifest, prereq failure)

### Step 5 — Side effects to watch

When a methodology is activated/deactivated:
- New slash commands may appear in `.claude/commands/` (the user may need to refer to them by name)
- Additional gates may activate at next commit (mention this if `adds_gates` is non-empty in the manifest)
- Composition order matters when commands conflict — `conflict_policy: first-wins` is the default

## Examples

### List methodologies
```
User: /methodology list
You:  bash .harness/lib/methodology.sh list
```

### Activate Living Spec on top of Ouroboros (1→N evolution)
```
User: /methodology compose ouroboros living-spec
You:  bash .harness/lib/methodology.sh compose ouroboros living-spec
      → After: tell user that /diff-spec and /migrate-tasks are now available
```

### Show what BMAD-lite does before activating
```
User: /methodology info bmad-lite
You:  bash .harness/lib/methodology.sh info bmad-lite
```

## Constraints

- Never edit `_state.yaml`, `_registry.yaml`, or any methodology's `manifest.yaml` directly without explicit user approval — these are configuration, not artifacts.
- Never disable core gates. If a methodology's manifest declares `relaxes_gates`, the dispatcher already validates that only non-security gates are listed; do not bypass this validation.
- If the user asks to "turn off all methodologies" — refuse and explain that ouroboros (or another base methodology) must always remain active. The dispatcher enforces this with a fallback.
- Methodology state is per-project. Settings do not cross repository boundaries.

## Reference

- Manifest schema: `methodology/_schema/manifest.yaml`
- Registry: `methodology/_registry.yaml` (source) → `.harness/methodology/_registry.yaml` (installed)
- State: `.harness/methodology/_state.yaml`
- Dispatcher: `lib/methodology.sh` (source) → `.harness/lib/methodology.sh` (installed)
- Methodology plugins: `methodologies/<name>/` (source) → `.harness/methodologies/<name>/` (installed)
