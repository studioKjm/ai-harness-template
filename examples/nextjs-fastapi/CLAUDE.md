# CLAUDE.md — My FastAPI + Next.js Project

This file provides guidance to Claude Code when working with this repository.

## CRITICAL: Read ARCHITECTURE_INVARIANTS First

**BEFORE starting ANY work**, read `ARCHITECTURE_INVARIANTS.md`.

### Document Priority
1. **ARCHITECTURE_INVARIANTS.md** (Supreme)
2. **docs/adr.yaml** (ADR)
3. **CLAUDE.md** (This file)
4. **docs/code-convention.yaml** (Conventions)

---

## Project Overview

| Item | Detail |
|------|--------|
| Stacks | nextjs, fastapi, python, typescript, docker, alembic |
| Package Manager | pnpm |
| Frontend | dashboard/ (Next.js 16 + React 19) |
| Backend | src/ (FastAPI + SQLAlchemy) |

---

## Absolute Rules

1. **No direct DB access from frontend** — All data through API routes
2. **No secrets in code** — Environment variables only
3. **No new dependencies without approval**
4. **Follow existing patterns**
5. **Run tests before committing**

---

## FastAPI Rules

- Routes are thin — business logic in service modules
- Use Pydantic models for all I/O
- Dependency injection for DB sessions via `Depends()`
- Async by default — `async def` for all handlers

## Next.js Rules

- Server Components by default
- No direct API calls from client components
- No business logic in page components
- Use `next/image` for images

## TypeScript Rules

- No `any` — use `unknown` with type guards
- No `I` prefix on interfaces
- `as const` over enums
- Path aliases (`@/`) over deep relative imports

---

## Harness Gate Commands

```bash
.harness/gates/check-boundaries.sh    # Dependency violations
.harness/gates/check-secrets.sh       # Secret leaks
.harness/gates/check-structure.sh     # Structure rules
.harness/detect-violations.sh         # Full scan
```
