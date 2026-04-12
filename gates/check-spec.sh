#!/usr/bin/env bash
# Check that a seed spec exists and has required fields.
# Usage: ./check-spec.sh [project-root]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(dirname "$SCRIPT_DIR")}"

# Colors
if [ -f "$SCRIPT_DIR/../lib/colors.sh" ]; then
  source "$SCRIPT_DIR/../lib/colors.sh"
elif [ -f "$PROJECT_ROOT/.harness/../lib/colors.sh" ]; then
  source "$PROJECT_ROOT/.harness/../lib/colors.sh"
else
  info() { echo "[INFO] $*"; }
  success() { echo "[OK] $*"; }
  warn() { echo "[WARN] $*"; }
  error() { echo "[ERROR] $*"; }
  header() { echo "=== $* ==="; }
fi

header "Spec Completeness Check"

SEEDS_DIR="$PROJECT_ROOT/.ouroboros/seeds"
VIOLATIONS=0

# Check if seeds directory exists
if [ ! -d "$SEEDS_DIR" ]; then
  warn "No .ouroboros/seeds/ directory found"
  warn "Run /interview then /seed to create a specification"
  exit 0  # Not a hard failure — spec is optional
fi

# Find latest seed
LATEST_SEED=$(ls -t "$SEEDS_DIR"/seed-v*.yaml 2>/dev/null | head -1)

if [ -z "$LATEST_SEED" ]; then
  warn "No seed spec files found in $SEEDS_DIR"
  exit 0
fi

info "Checking: $(basename "$LATEST_SEED")"

# Required fields check (grep-based, no YAML parser needed)
check_field() {
  local field="$1"
  local label="$2"
  if grep -q "^${field}:" "$LATEST_SEED" 2>/dev/null || \
     grep -q "^  ${field}:" "$LATEST_SEED" 2>/dev/null || \
     grep -q "^    ${field}:" "$LATEST_SEED" 2>/dev/null; then
    # Check if it's not empty (has content after colon)
    local value
    value=$(grep -m1 "${field}:" "$LATEST_SEED" | sed "s/.*${field}:\s*//" | tr -d '"' | tr -d "'" | xargs)
    if [ -n "$value" ] && [ "$value" != '""' ] && [ "$value" != "''" ]; then
      success "$label: present"
      return 0
    fi
  fi
  error "$label: MISSING or EMPTY"
  VIOLATIONS=$((VIOLATIONS + 1))
  return 1
}

check_section() {
  local section="$1"
  local label="$2"
  if grep -q "^${section}:" "$LATEST_SEED" 2>/dev/null; then
    success "$label: present"
    return 0
  fi
  error "$label: MISSING"
  VIOLATIONS=$((VIOLATIONS + 1))
  return 1
}

# Check TODO/TBD placeholders
TODO_COUNT=$(grep -ci "TODO\|TBD\|FIXME\|XXX" "$LATEST_SEED" 2>/dev/null || true)
TODO_COUNT="${TODO_COUNT:-0}"
if [ "$TODO_COUNT" -gt 0 ]; then
  error "Found $TODO_COUNT TODO/TBD placeholders in seed spec"
  VIOLATIONS=$((VIOLATIONS + 1))
fi

# Detect minimal vs full mode
# Minimal mode: no top-level `ontology:` section
if grep -q "^ontology:" "$LATEST_SEED" 2>/dev/null; then
  SPEC_MODE="full"
else
  SPEC_MODE="minimal"
fi
info "Spec mode: $SPEC_MODE"

# Check required sections
echo ""
check_section "goal" "Goal section" || true
check_section "constraints" "Constraints section" || true
check_section "acceptance_criteria" "Acceptance Criteria" || true
if [ "$SPEC_MODE" = "full" ]; then
  check_section "ontology" "Ontology" || true
  check_section "scope" "Scope" || true
fi

# Check acceptance_criteria count
AC_COUNT=$(grep -c "id: \"AC-" "$LATEST_SEED" 2>/dev/null || true)
AC_COUNT="${AC_COUNT:-0}"
if [ "$AC_COUNT" -lt 2 ]; then
  error "Need at least 2 acceptance criteria (found: $AC_COUNT)"
  VIOLATIONS=$((VIOLATIONS + 1))
else
  success "Acceptance criteria count: $AC_COUNT"
fi

# Check ontology entities (full mode only)
if [ "$SPEC_MODE" = "full" ]; then
  ENTITY_COUNT=$(grep -c "^    - name:" "$LATEST_SEED" 2>/dev/null || true)
  ENTITY_COUNT="${ENTITY_COUNT:-0}"
  if [ "$ENTITY_COUNT" -lt 1 ]; then
    warn "No ontology entities defined"
  fi
fi

echo ""

# Summary
if [ $VIOLATIONS -eq 0 ]; then
  success "Seed spec is complete: $(basename "$LATEST_SEED")"
  exit 0
else
  error "$VIOLATIONS issue(s) found in seed spec"
  echo ""
  echo "  Fix the spec or re-run /seed to regenerate."
  exit 1
fi
