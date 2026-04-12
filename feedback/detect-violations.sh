#!/usr/bin/env bash
# Run all harness violation checks and produce a summary report.
# Usage: ./detect-violations.sh [project-root]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# If run from .harness/, infer PROJECT_ROOT as parent
if [ -n "${1:-}" ]; then
  PROJECT_ROOT="$1"
elif [ "$(basename "$SCRIPT_DIR")" = ".harness" ]; then
  PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
  PROJECT_ROOT="$(pwd)"
fi

HARNESS_DIR="$PROJECT_ROOT/.harness"

# Colors
if [ -f "$SCRIPT_DIR/../lib/colors.sh" ]; then
  source "$SCRIPT_DIR/../lib/colors.sh"
elif [ -f "$HARNESS_DIR/lib/colors.sh" ]; then
  source "$HARNESS_DIR/lib/colors.sh"
else
  info() { echo "[INFO] $*"; }
  success() { echo "[OK] $*"; }
  warn() { echo "[WARN] $*"; }
  error() { echo "[ERROR] $*"; }
  header() { echo "=== $* ==="; }
fi

header "Harness Violation Report"
info "Project: $PROJECT_ROOT"
info "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

TOTAL_VIOLATIONS=0

# Find gate scripts
if [ -d "$HARNESS_DIR/gates" ]; then
  GATES_DIR="$HARNESS_DIR/gates"
elif [ -d "$SCRIPT_DIR/gates" ]; then
  GATES_DIR="$SCRIPT_DIR/gates"
elif [ -d "$SCRIPT_DIR/../gates" ]; then
  GATES_DIR="$SCRIPT_DIR/../gates"
else
  GATES_DIR="$HARNESS_DIR/gates"
fi

# ─── Run each gate ────────────────────────────────────────────────

echo "────────────────────────────────────────"
echo ""

# 1. Secrets
if [ -f "$GATES_DIR/check-secrets.sh" ]; then
  if ! "$GATES_DIR/check-secrets.sh" "$PROJECT_ROOT" 2>&1; then
    TOTAL_VIOLATIONS=$((TOTAL_VIOLATIONS + 1))
  fi
else
  warn "check-secrets.sh not found"
fi

echo ""
echo "────────────────────────────────────────"
echo ""

# 2. Boundaries
if [ -f "$GATES_DIR/check-boundaries.sh" ]; then
  if ! "$GATES_DIR/check-boundaries.sh" "$PROJECT_ROOT" 2>&1; then
    TOTAL_VIOLATIONS=$((TOTAL_VIOLATIONS + 1))
  fi
else
  warn "check-boundaries.sh not found"
fi

echo ""
echo "────────────────────────────────────────"
echo ""

# 3. Structure
if [ -f "$GATES_DIR/check-structure.sh" ]; then
  if ! "$GATES_DIR/check-structure.sh" "$PROJECT_ROOT" 2>&1; then
    TOTAL_VIOLATIONS=$((TOTAL_VIOLATIONS + 1))
  fi
else
  warn "check-structure.sh not found"
fi

echo ""
echo "────────────────────────────────────────"

# ─── Summary ──────────────────────────────────────────────────────
echo ""
header "Summary"

if [ $TOTAL_VIOLATIONS -eq 0 ]; then
  success "All checks passed. No violations found."
else
  error "$TOTAL_VIOLATIONS check(s) failed."
  echo ""
  echo "  Next steps:"
  echo "    1. Fix the violations reported above"
  echo "    2. If a rule is too strict, edit .harness/gates/rules/*.yaml"
  echo "    3. If a new pattern emerged, add a rule to prevent recurrence"
  echo "    4. Re-run this script to verify: .harness/detect-violations.sh"
  echo ""
  echo "  Rule evolution guide: See feedback/evolve-rules.md"
fi
