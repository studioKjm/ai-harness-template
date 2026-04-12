# CLAUDE.md — My NestJS + Next.js Project

## CRITICAL: Read ARCHITECTURE_INVARIANTS First

| Item | Detail |
|------|--------|
| Stacks | nextjs, nestjs, typescript, prisma, docker |
| Package Manager | pnpm |
| Frontend | frontend/ (Next.js + React) |
| Backend | backend/ (NestJS + Prisma) |

## Absolute Rules
1. No direct DB access from frontend
2. No secrets in code
3. No new dependencies without approval
4. Controllers = HTTP only, Services = business logic
5. All DTOs must have class-validator decorators

## NestJS Rules
- Controller: request/response transformation only
- Service: all business logic
- DI for all dependencies — never `new Service()` directly
- Guard separation: AuthGuard (JWT) vs RolesGuard (RBAC)
- API response format: `{ data, error, meta }`

## Next.js Rules
- Server Components by default
- No client-side API calls — use Server Actions
- No business logic in pages

## Prisma Rules
- Migrations via `prisma migrate` only
- Always commit migration files
- Use `$transaction()` for multi-table ops
