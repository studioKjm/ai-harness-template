# CLAUDE.md — My Python Project

## CRITICAL: Read ARCHITECTURE_INVARIANTS First

| Item | Detail |
|------|--------|
| Stacks | python, fastapi/django, alembic, docker |
| Package Manager | pip |
| Entry Point | main.py or src/api/main.py |

## Absolute Rules
1. No secrets in code — environment variables only
2. Type hints on all functions
3. No raw SQL — use ORM
4. Async and sync don't mix in the same module
5. Tests must pass before commit

## Python Rules
- Type hints on all parameters and return values
- f-strings only (no `.format()`, no `%`)
- Config in config module, not module-level globals
- One execution model per module (async or sync, not both)

## Harness Commands
```bash
.harness/gates/check-secrets.sh       # Secret leaks
.harness/gates/check-boundaries.sh    # Import violations
.harness/detect-violations.sh         # Full scan
```
