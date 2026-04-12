#!/usr/bin/env bash
# Check mutation testing score for AI-generated code.
# Delegates to native mutation testing tools: mutmut (Python), Stryker (JS/TS).
# Usage: ./check-mutation.sh [project-root] [--threshold=60] [--changed-only]
#
# AI-generated code passes traditional tests but has 75% more logic bugs.
# Mutation testing catches these by modifying code and checking if tests fail.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"

# Colors
if [ -f "$SCRIPT_DIR/../lib/colors.sh" ]; then
  source "$SCRIPT_DIR/../lib/colors.sh"
elif [ -f "$PROJECT_ROOT/.harness/lib/colors.sh" ]; then
  source "$PROJECT_ROOT/.harness/lib/colors.sh"
else
  info() { echo "[INFO] $*"; }
  success() { echo "[OK] $*"; }
  warn() { echo "[WARN] $*"; }
  error() { echo "[ERROR] $*"; }
  header() { echo "=== $* ==="; }
fi

# ─── Configuration ──────────────────────────────────────────────────
THRESHOLD=60  # Minimum mutation score (percentage)
CHANGED_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --threshold=*) THRESHOLD="${arg#*=}" ;;
    --changed-only) CHANGED_ONLY=true ;;
  esac
done

header "Mutation Testing Gate"
info "Threshold: ${THRESHOLD}% mutation score"
echo ""

VIOLATIONS=0
SCANNED=false

# ─── Get changed files (for --changed-only mode) ───────────────────
get_changed_files() {
  if $CHANGED_ONLY; then
    cd "$PROJECT_ROOT" && git diff --name-only HEAD~1 2>/dev/null | grep -E '\.(py|ts|tsx|js|jsx)$' || true
  fi
}

# ─── Python: mutmut ────────────────────────────────────────────────
check_python_mutation() {
  if [ ! -f "$PROJECT_ROOT/requirements.txt" ] && \
     [ ! -f "$PROJECT_ROOT/pyproject.toml" ] && \
     [ ! -f "$PROJECT_ROOT/setup.py" ]; then
    return
  fi

  # Check if tests exist
  local test_count
  test_count=$(find "$PROJECT_ROOT" -name "test_*.py" -o -name "*_test.py" 2>/dev/null | grep -c . || true)
  if [ "$test_count" -eq 0 ]; then
    info "Python: No test files found, skipping mutation testing"
    return
  fi

  SCANNED=true

  if command -v mutmut &>/dev/null; then
    info "Running: mutmut (Python mutation testing)"

    local mutmut_args="run --no-progress"

    if $CHANGED_ONLY; then
      local changed
      changed=$(get_changed_files | grep '\.py$' || true)
      if [ -z "$changed" ]; then
        info "No changed Python files, skipping"
        return
      fi
      # mutmut can target specific files
      for f in $changed; do
        mutmut_args="$mutmut_args --paths-to-mutate=$f"
      done
    fi

    local output exit_code
    output=$(cd "$PROJECT_ROOT" && mutmut $mutmut_args 2>&1) && exit_code=0 || exit_code=$?

    # Parse results
    local killed survived total score
    killed=$(echo "$output" | sed -n 's/.*Killed: \([0-9]*\).*/\1/p' | head -1)
    killed="${killed:-0}"
    survived=$(echo "$output" | sed -n 's/.*Survived: \([0-9]*\).*/\1/p' | head -1)
    survived="${survived:-0}"
    total=$((killed + survived))

    if [ "$total" -gt 0 ]; then
      score=$((killed * 100 / total))
      if [ "$score" -ge "$THRESHOLD" ]; then
        success "Python mutation score: ${score}% ($killed/$total killed) >= ${THRESHOLD}%"
      else
        error "Python mutation score: ${score}% ($killed/$total killed) < ${THRESHOLD}%"
        echo "  $survived mutant(s) survived — tests don't catch these logic changes"
        echo "  Run 'mutmut results' to see surviving mutants"
        echo ""
        VIOLATIONS=$((VIOLATIONS + 1))
      fi
    else
      info "Python: No mutations generated (code may be too simple)"
    fi
  else
    warn "Python: mutmut not found. Install: pip install mutmut"
    info "  Mutation testing verifies your tests catch real logic bugs"
  fi
}

# ─── JavaScript/TypeScript: Stryker ────────────────────────────────
check_js_mutation() {
  if [ ! -f "$PROJECT_ROOT/package.json" ]; then
    return
  fi

  # Check if tests exist
  local test_count
  test_count=$(find "$PROJECT_ROOT" -name "*.test.*" -o -name "*.spec.*" 2>/dev/null | \
    grep -v node_modules | grep -c . || true)
  if [ "$test_count" -eq 0 ]; then
    info "JS/TS: No test files found, skipping mutation testing"
    return
  fi

  SCANNED=true

  # Check for Stryker config
  if [ -f "$PROJECT_ROOT/stryker.conf.js" ] || \
     [ -f "$PROJECT_ROOT/stryker.conf.mjs" ] || \
     [ -f "$PROJECT_ROOT/stryker.config.mjs" ] || \
     grep -q '"@stryker-mutator"' "$PROJECT_ROOT/package.json" 2>/dev/null; then

    info "Running: Stryker (JS/TS mutation testing)"

    local output exit_code
    output=$(cd "$PROJECT_ROOT" && npx stryker run --reporters=clear-text 2>&1) && exit_code=0 || exit_code=$?

    # Parse score from Stryker output
    local score
    score=$(echo "$output" | sed -n 's/.*Mutation score: \([0-9.]*\).*/\1/p' | head -1)

    if [ -n "$score" ]; then
      local int_score=${score%.*}
      if [ "$int_score" -ge "$THRESHOLD" ]; then
        success "JS/TS mutation score: ${score}% >= ${THRESHOLD}%"
      else
        error "JS/TS mutation score: ${score}% < ${THRESHOLD}%"
        echo "  Run 'npx stryker run' for full report"
        echo ""
        VIOLATIONS=$((VIOLATIONS + 1))
      fi
    else
      warn "Could not parse Stryker output"
      echo "$output" | tail -5
    fi
  else
    # Stryker not configured — provide setup guidance
    warn "JS/TS: Stryker not configured"
    info "  Setup: npx stryker init"
    info "  Mutation testing verifies your tests catch real logic bugs"
  fi
}

# ─── Run checks ────────────────────────────────────────────────────
check_python_mutation
check_js_mutation

# ─── Report ────────────────────────────────────────────────────────
echo ""
if ! $SCANNED; then
  info "No testable code found for mutation testing."
  exit 0
fi

if [ $VIOLATIONS -eq 0 ]; then
  success "Mutation testing passed."
  exit 0
else
  error "$VIOLATIONS mutation testing failure(s)."
  info "Surviving mutants indicate tests that pass but don't verify logic."
  info "Add assertions that would fail if the mutated logic were deployed."
  exit 1
fi
