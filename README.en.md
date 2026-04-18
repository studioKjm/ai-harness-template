# AI Harness Engineering Template

> [한국어 README](./README.md) · English

A template that lets AI agents work autonomously — safely and within structural boundaries.
Combines **Harness (structural guardrails) + Ouroboros (spec-first development) + 3-Tier Layered Architecture**.

> "Prompts are requests. Harnesses are enforcement."
> "Stop prompting. Start specifying."

## Releases

| Version | Date | Highlights |
|---------|------|-----------|
| [**v2.1.0**](https://github.com/studioKjm/ai-harness-template/releases/tag/v2.1.0) | 2026-04-18 | **Pair Mode** — Navigator-Driver pair programming + independent Test Designer + `/review` lightweight mid-run verification. Opt-in via `HARNESS_ENABLE_PAIR_MODE=1`. Based on PairCoder (ASE 2024) + AgentCoder. |
| [**v2.0.0**](https://github.com/studioKjm/ai-harness-template/releases/tag/v2.0.0) | 2026-04-12 | **Unified layout** — `.ouroboros/` merged under `.harness/ouroboros/`. Opt-in gates separated. (BREAKING) |
| [**v1.0.0**](https://github.com/studioKjm/ai-harness-template/releases/tag/v1.0.0) | 2026-04-12 | Initial release — 11 gates, 10 commands, 9 agents, 3-tier architecture enforcement. |

---

## Why This Exists

AI coding agents are fast but undisciplined. They hallucinate APIs, skip layers, leak secrets, drift from specs, and over-engineer trivial features. This template inverts the loop:

1. **Specify first** — force clarity before code (Socratic interview, immutable seed spec)
2. **Enforce structurally** — gates block commits, not just warn (11 gates: boundaries, layers, secrets, security, …)
3. **Evolve on failure** — every violation becomes a new rule (self-strengthening system)

---

## Quick Start

### Option A — Claude Code Plugin (simplest)

```
/plugin marketplace add studioKjm/ai-harness-template
/plugin install harness@studioKjm-harness
```

Installs 10 commands + 9 agents. For the full toolkit (gates, hooks, templates), use Option B.

### Option B — Full install

```shell
git clone https://github.com/studioKjm/ai-harness-template.git

# Lite (bash only, zero dependencies)
./ai-harness-template/init.sh /path/to/your-project

# Non-interactive install with defaults
./ai-harness-template/init.sh /path/to/your-project --yes

# Pro (Python 3.11+, adds scoring/persistence/MCP/observability)
./ai-harness-template/pro/install.sh /path/to/your-project
```

---

## Core Components

### Ouroboros Workflow (10 commands)

```
/interview → /seed → /trd → /decompose → /run → /evaluate
     ↑                                              │
     └────────── /evolve (until convergence) ───────┘
```

Plus `/rollback`, `/unstuck`, `/pm` for edge cases.

| Command | Purpose |
|---|---|
| `/interview` | Socratic interview measuring 4D ambiguity (goal/constraints/success/context) |
| `/seed` | Crystallize interview into **immutable** seed spec (versioned) |
| `/trd` | Layer-aware technical design document |
| `/decompose` | Break AC into atomic layer-aware tasks |
| `/run` | Execute via Double Diamond (Discover/Define/Design/Deliver) |
| `/evaluate` | 3-stage verification (Mechanical → Semantic → Judgment) |
| `/evolve` | Wonder/Reflect/Re-seed loop until ontology similarity ≥ 0.95 |
| `/rollback` | Saga-pattern safe rollback (stash/checkout/branch) |
| `/unstuck` | 5-agent multi-perspective deadlock breaker |
| `/pm` | Generate PRD for non-engineering stakeholders |

### 11 Gates (7 default + 4 opt-in)

**Default (blocking on pre-commit + CI):**
- `check-secrets` — 35+ secret patterns (AWS, GitHub, Stripe, OpenAI, …)
- `check-boundaries` — import/dependency rules
- `check-structure` — file placement
- `check-spec` — seed completeness (no TODO/TBD)
- `check-layers` — 3-tier separation (P→L→D only, no skip)
- `check-security` — SAST (Semgrep / Bandit / built-in)
- `check-deps` — dependency vulnerability audit

**Opt-in (enable via `HARNESS_ENABLE_*` env vars):**
- `check-complexity`, `check-mutation`, `check-performance`, `check-ai-antipatterns`

See [`gates/GATES.md`](./gates/GATES.md) for details.

### 9 Agent Personas

`interviewer`, `ontologist`, `seed-architect`, `evaluator`, `contrarian`, `simplifier`, `researcher`, `architect`, `hacker`

Orchestration patterns (see `agents/topology.yaml`): Pipeline · Fan-out · Expert Pool · Producer-Reviewer.

### 3-Tier Architecture (enforced)

```
Presentation ──→ Logic ──→ Data
```

- **No layer skipping** (P→D direct access = gate violation)
- **No reverse deps** (L→P reverse import = violation)
- **DTO at boundaries**, repository interface at L↔D
- Stack-specific mapping auto-generated per framework (Next.js, NestJS, FastAPI, Django, …)

---

## Lite vs Pro

**Start with Lite. It delivers 80% of the value.**

Upgrade to Pro when 2+ apply:
- Team of 3+, long collaboration sessions
- Project lasting 3+ months
- Need audit logs for gate runs
- Want to expose gates to other AI tools via MCP
- Need numeric ambiguity/drift scores in CI

| Feature | Lite | Pro |
|---|:---:|:---:|
| Zero deps (bash only) | ✓ | - |
| 11 gates, 10 commands, 9 agents | ✓ | ✓ |
| Ambiguity score engine | - | ✓ |
| Ontology similarity tracking | - | ✓ |
| SQLite session persistence | - | ✓ |
| Drift monitoring hooks | - | ✓ |
| Test scaffold generation | - | ✓ |
| Audit log | - | ✓ |
| Agent observability tracer | - | ✓ |
| MCP server | - | ✓ |
| `harness` CLI | - | ✓ |

---

## Stack Auto-detection

30+ frameworks auto-detected from lock files and config:

- **Frontend**: Next.js, React, Vue, Nuxt, Svelte, SvelteKit, Remix, Astro
- **Backend**: NestJS, Express, Fastify, Hono, FastAPI, Django, Flask, Gin, Chi, Actix, Axum, Spring
- **ORM**: Prisma, TypeORM, SQLAlchemy, Alembic, Django ORM
- **Package managers**: npm, yarn, pnpm, bun, pip, poetry, uv, pipenv, go, cargo, maven, gradle
- **Monorepo**: pnpm workspace, Turborepo, Lerna
- **Infra**: Docker, GitHub Actions

---

## Directory Structure

```
harness/
├── .claude-plugin/     # Plugin manifest (for /plugin install)
├── init.sh             # Lite installer
├── commands/           # 10 Ouroboros slash commands
├── agents/             # 9 agent personas + topology.yaml
├── gates/              # 11 gate scripts + rules + GATES.md
├── boundaries/         # Permission presets + hooks
├── ouroboros/          # Seed spec templates (full + minimal)
├── templates/          # CLAUDE.md, ARCHITECTURE_INVARIANTS, CI workflow
├── lib/                # Stack detection, template rendering
└── pro/                # Python engine (CLI + MCP + persistence + observability)
```

---

## Philosophy

| Principle | Meaning |
|---|---|
| Spec-first | No code before an interview + immutable seed |
| Structural enforcement | Gates block, not warn |
| Immutable specs | Seeds never mutate — changes mean new versions |
| Self-reinforcement | Every violation → new rule → stronger gates |
| Architecture mandatory | 3-tier Presentation/Logic/Data separation |
| Progressive adoption | Pick components — no all-or-nothing |

---

## License

MIT — see [LICENSE](./LICENSE)

## Acknowledgments

Built on foundations from the broader AI-agent engineering community. See main [README](./README.md#acknowledgments--inspirations) for detailed attributions.

---

**Full documentation (Korean):** [README.md](./README.md)
