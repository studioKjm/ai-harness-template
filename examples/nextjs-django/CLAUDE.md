# CLAUDE.md — My Django + Next.js Project

## CRITICAL: Read ARCHITECTURE_INVARIANTS First

| Item | Detail |
|------|--------|
| Stacks | nextjs, django, python, typescript, docker |
| Package Manager | npm (frontend), pip (backend) |
| Frontend | frontend/ (Next.js) |
| Backend | backend/ (Django REST Framework) |

## Absolute Rules
1. No direct DB access from frontend
2. No secrets in code
3. Fat models, thin views
4. Never edit existing migration files
5. Use Django ORM — no raw SQL

## Django Rules
- Business logic in models/managers, not views
- Use class-based views unless trivially simple
- Migrations: `python manage.py makemigrations` only
- Never modify existing migration files — create new ones

## Next.js Rules
- Server Components by default
- No Django imports from frontend code (ever!)
- No business logic in pages
