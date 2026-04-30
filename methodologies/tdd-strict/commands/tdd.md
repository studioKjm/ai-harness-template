# /tdd — TDD Cycle Manager

**Methodology**: tdd-strict  
**Purpose**: Manage Red→Green→Refactor cycles. Gate enforces test-first order in git history.

---

## Usage

```
/tdd new <description> [--test <path>] [--source <path>] [--hypothesis <text>] [--story <id>]
/tdd pass <cycle-id> [--criteria <text>]
/tdd refactor <cycle-id> [--notes <text>]
/tdd done <cycle-id>
/tdd abandon <cycle-id> [--reason <text>]
/tdd status <cycle-id>
/tdd list [--state red|green|refactor|done|abandoned]
/tdd link <cycle-id> [--story <id>] [--spike <id>] [--test-file <path>] [--source-file <path>]
```

---

## State Machine

```
     new
      ↓
   🔴 red  ──pass──→  🟢 green  ──refactor──→  🔵 refactor  ──done──→  ✅ done
      │                  │                          │
      └──abandon──→  ❌ abandoned  ←─────────────────┘
```

**Invariant enforced by gate**: `check-test-first.sh` blocks commits where a source file
was introduced into git before its corresponding test file.

---

## Workflow

### 1. Start a cycle

```bash
python3 methodologies/tdd-strict/scripts/tdd.py new "user can reset password" \
  --test src/auth/reset.test.ts \
  --source src/auth/reset.ts \
  --hypothesis "POST /auth/reset sends email and returns 202"
```

### 2. Write the failing test → commit → the gate verifies test exists

```bash
# Write test file first
git add src/auth/reset.test.ts
git commit -m "test: reset password sends email (RED)"
# Gate passes: test file committed before source
```

### 3. Implement to pass the test

```bash
# Now write source
git add src/auth/reset.ts
git commit -m "feat: implement password reset"
# Gate passes: test was committed first
python3 methodologies/tdd-strict/scripts/tdd.py pass tdd-20260430-001
```

### 4. Refactor (optional cleanup)

```bash
git add .
git commit -m "[refactor] extract sendResetEmail helper"
# [refactor] prefix exempts this commit from gate
python3 methodologies/tdd-strict/scripts/tdd.py refactor tdd-20260430-001 \
  --notes "extracted sendResetEmail, removed duplication"
```

### 5. Close cycle

```bash
python3 methodologies/tdd-strict/scripts/tdd.py done tdd-20260430-001
```

---

## Gate Exemptions

Commit message prefixes that bypass the test-first gate:

| Prefix | Use case |
|--------|---------|
| `[refactor]` | Structural cleanup without behavior change |
| `[chore]` | Build, tooling, dependency updates |
| `[docs]` | Documentation only |
| `[style]` | Formatting, whitespace |
| `[ci]` | CI configuration |
| `[infra]` | Infrastructure changes |

---

## Agent Notes

When executing `/tdd`:

1. **Always verify RED first** — the test must fail before you write source. Run the test runner and confirm failure.
2. **Commit test before source** — staged files order matters for the gate.
3. **Minimal green** — write the simplest code that makes the test pass. Refactor separately.
4. **Gate block?** — check `git log --diff-filter=A --format="%H %ai %s" -- <test-file>` to verify test history.
5. **Hypothesis drives design** — record what you expect BEFORE writing code.
