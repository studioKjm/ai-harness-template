# /tdd-config — TDD Configuration

**Methodology**: tdd-strict  
**Purpose**: Configure test pairing conventions and gate behavior for this project.

---

## Setup

Copy the template and customize:

```bash
mkdir -p .harness/tdd-strict
cp methodologies/tdd-strict/templates/tdd-config.yaml .harness/tdd-strict/config.yaml
```

---

## Key Settings

### Test Pairing Conventions

Tell the gate how to find the test file for a given source file:

```yaml
pairing:
  conventions:
    - source: "src/**/*.ts"
      test: "src/**/*.test.ts"
    - source: "src/**/*.ts"
      test: "src/**/*.spec.ts"
```

The gate resolves pairs at commit time using `git log` to verify history order.

### Exempt Directories

```yaml
pairing:
  exempt_dirs:
    - "migrations/"
    - "scripts/"
    - "config/"
```

Source files in these directories skip the test-first check entirely.

### Exempt Patterns

```yaml
pairing:
  exempt_patterns:
    - "index.ts"      # Re-export barrels
    - "types.ts"      # Pure type definitions
    - "constants.ts"  # Constants only
```

### Allow Same-Commit

```yaml
gate:
  allow_same_commit: false   # true: test and source may appear in same commit
```

Default is `false` (test must appear in an earlier commit). Set to `true` for teams
that prefer atomic test+source commits.

### Gate Severity

```yaml
gate:
  severity: "blocking"   # or "warning"
```

Switch to `warning` during ramp-up to measure violations without blocking.

---

## Verifying Configuration

```bash
# Run gate manually
HARNESS_DIR=.harness bash methodologies/tdd-strict/gates/check-test-first.sh

# Check cycle list
python3 methodologies/tdd-strict/scripts/tdd.py list
```
