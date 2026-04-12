#!/usr/bin/env bash
# Pre-commit gate for Claude Code PreCommit hook.
# Runs DEFAULT harness gates before allowing commit.
#
# Gates split into two tiers:
#   DEFAULT (blocking, fast)  : secrets, boundaries, structure, spec, layers, security, deps
#   OPT-IN  (warning, slow)   : complexity, mutation, performance, ai-antipatterns
#
# To enable opt-in gates, set env vars:
#   HARNESS_ENABLE_COMPLEXITY=1
#   HARNESS_ENABLE_MUTATION=1
#   HARNESS_ENABLE_PERFORMANCE=1
#   HARNESS_ENABLE_AI_ANTIPATTERNS=1

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HARNESS_DIR="$PROJECT_ROOT/.harness"
GATE_FAILED=0

echo "=== Harness Pre-Commit Gates ==="
echo ""

run_gate() {
  local name="$1"
  local script="$HARNESS_DIR/gates/$name"
  shift
  if [ -f "$script" ]; then
    if ! "$script" "$PROJECT_ROOT" "$@"; then
      GATE_FAILED=1
    fi
  fi
}

# ─── DEFAULT GATES (always blocking) ─────────────────────────────
run_gate "check-secrets.sh" --staged
run_gate "check-boundaries.sh"
run_gate "check-structure.sh"
run_gate "check-spec.sh"
run_gate "check-layers.sh"
run_gate "check-security.sh"
run_gate "check-deps.sh"

# ─── OPT-IN GATES (enabled via env var) ──────────────────────────
[ "${HARNESS_ENABLE_COMPLEXITY:-0}" = "1" ]      && run_gate "check-complexity.sh"
[ "${HARNESS_ENABLE_MUTATION:-0}" = "1" ]        && run_gate "check-mutation.sh"
[ "${HARNESS_ENABLE_PERFORMANCE:-0}" = "1" ]     && run_gate "check-performance.sh"
[ "${HARNESS_ENABLE_AI_ANTIPATTERNS:-0}" = "1" ] && run_gate "check-ai-antipatterns.sh"

echo ""
if [ $GATE_FAILED -ne 0 ]; then
  echo "[HARNESS] Commit blocked. Fix the violations above."
  exit 1
else
  echo "[HARNESS] All gates passed."
fi
