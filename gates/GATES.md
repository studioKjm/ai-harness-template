# Harness Gates — Default vs Opt-in

Gates enforce structural quality. To lower the barrier to adoption, they split into two tiers:

## Default Gates (7) — Blocking

Run on every pre-commit and every CI build. These are the minimum safety net.

| Gate | Purpose | Typical runtime |
|---|---|---|
| `check-secrets.sh` | Leaked API keys, tokens, credentials | <1s |
| `check-boundaries.sh` | Import/dependency boundary rules | ~1s |
| `check-structure.sh` | File placement rules (.env, migrations) | <1s |
| `check-spec.sh` | Seed spec completeness (no TODO/TBD) | <1s |
| `check-layers.sh` | 3-tier architecture separation | ~1s |
| `check-security.sh` | SAST (Semgrep / Bandit / built-in patterns) | 5-30s |
| `check-deps.sh` | Dependency vulnerability audit | 5-15s |

## Opt-in Gates (4) — Warning

Disabled by default. Enable when the project matures or when noise-to-signal ratio justifies them.

| Gate | Purpose | Why opt-in |
|---|---|---|
| `check-complexity.sh` | Function length, nesting, file size | Overlaps with linters; thresholds vary per team |
| `check-mutation.sh` | Mutation testing score | Slow (minutes); requires mutmut/Stryker setup |
| `check-performance.sh` | File size, dep count, import depth | Subjective budgets; better measured in prod |
| `check-ai-antipatterns.sh` | Hallucinated APIs, naming drift, dead code | Heuristic-based; can false-positive |

## Enabling Opt-in Gates

### Pre-commit

```shell
# Enable per-gate via env var
export HARNESS_ENABLE_COMPLEXITY=1
export HARNESS_ENABLE_MUTATION=1
export HARNESS_ENABLE_PERFORMANCE=1
export HARNESS_ENABLE_AI_ANTIPATTERNS=1
```

Or add to `.envrc` / `.env.local`.

### GitHub Actions

Uncomment the `opt-in-gates` job in `.github/workflows/harness-gates.yaml`.

### Manual invocation

Any gate can be run manually at any time:

```shell
bash .harness/gates/check-ai-antipatterns.sh .
```

## Philosophy

Default gates prioritize **correctness & security**. Opt-in gates prioritize **code quality & discipline**.

Start with defaults. Add opt-in gates once the team agrees on thresholds.
