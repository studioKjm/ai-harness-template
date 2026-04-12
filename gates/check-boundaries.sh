#!/usr/bin/env bash
# Check dependency boundary violations.
# Reads rules from .harness/gates/rules/boundaries.yaml (or fallback to harness/gates/rules/)
# Usage: ./check-boundaries.sh [project-root]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"

# Try to find colors.sh
if [ -f "$SCRIPT_DIR/../lib/colors.sh" ]; then
  source "$SCRIPT_DIR/../lib/colors.sh"
elif [ -f "$PROJECT_ROOT/.harness/lib/colors.sh" ]; then
  source "$PROJECT_ROOT/.harness/lib/colors.sh"
else
  # Inline fallback
  info() { echo "[INFO] $*"; }
  success() { echo "[OK] $*"; }
  warn() { echo "[WARN] $*"; }
  error() { echo "[ERROR] $*"; }
  header() { echo "=== $* ==="; }
fi

# Find rules file
RULES_FILE=""
if [ -f "$PROJECT_ROOT/.harness/gates/rules/boundaries.yaml" ]; then
  RULES_FILE="$PROJECT_ROOT/.harness/gates/rules/boundaries.yaml"
elif [ -f "$SCRIPT_DIR/rules/boundaries.yaml" ]; then
  RULES_FILE="$SCRIPT_DIR/rules/boundaries.yaml"
else
  error "No boundaries.yaml found"
  exit 1
fi

header "Dependency Boundary Check"
info "Rules: $RULES_FILE"
info "Project: $PROJECT_ROOT"
echo ""

VIOLATIONS=0
CHECKED=0

# Parse YAML rules (simple line-by-line parser — no external deps)
current_from=""
current_reason=""
current_stacks=""
declare -a current_imports=()
declare -a current_patterns=()

check_rule() {
  if [ -z "$current_from" ] || [ ${#current_imports[@]} -eq 0 ]; then
    return
  fi

  local search_dir="$PROJECT_ROOT/$current_from"
  if [ ! -d "$search_dir" ]; then
    return
  fi

  # Build file pattern args for find
  local find_args=()
  if [ ${#current_patterns[@]} -gt 0 ]; then
    local first=true
    for pat in "${current_patterns[@]}"; do
      if $first; then
        find_args+=(-name "$pat")
        first=false
      else
        find_args+=(-o -name "$pat")
      fi
    done
  else
    find_args+=(-name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py")
  fi

  # Search for violations
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    for imp in "${current_imports[@]}"; do
      local matches
      matches=$(grep -n "$imp" "$file" 2>/dev/null | grep -v "^[[:space:]]*#" | grep -v "^[[:space:]]*//" | head -5 || true)
      [ -z "$matches" ] && continue
      while IFS= read -r match; do
        local line_num=$(echo "$match" | cut -d: -f1)
        local line_content=$(echo "$match" | cut -d: -f2-)
        local rel_path="${file#$PROJECT_ROOT/}"
        error "VIOLATION: $rel_path:$line_num"
        echo "  Import: $imp"
        echo "  Line: $(echo "$line_content" | sed 's/^[[:space:]]*//')"
        echo "  Rule: $current_reason"
        echo ""
        VIOLATIONS=$((VIOLATIONS + 1))
      done <<< "$matches"
    done
    CHECKED=$((CHECKED + 1))
  done < <(find "$search_dir" \( "${find_args[@]}" \) -type f 2>/dev/null | grep -v node_modules | grep -v __pycache__ | grep -v .next | grep -v dist | grep -v build)
}

# Parse the YAML file
in_rule=false
while IFS= read -r line; do
  # Skip comments and empty lines
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ "$line" =~ ^[[:space:]]*$ ]] && continue

  # Section headers (nextjs:, fastapi:, etc.)
  if [[ "$line" =~ ^[a-z]+:$ ]]; then
    # Check previous rule
    check_rule
    current_from=""
    current_imports=()
    current_patterns=()
    current_reason=""
    continue
  fi

  # New rule item
  if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*from: ]]; then
    # Check previous rule first
    check_rule
    current_from=$(echo "$line" | sed 's/.*from:[[:space:]]*"\(.*\)"/\1/' | tr -d '"')
    current_imports=()
    current_patterns=()
    current_reason=""
    in_rule=true
    continue
  fi

  if $in_rule; then
    # Parse cannot_import array
    if [[ "$line" =~ cannot_import: ]]; then
      imports_str=$(echo "$line" | sed 's/.*\[//;s/\].*//' | tr -d '"')
      IFS=',' read -ra imports_arr <<< "$imports_str"
      for imp in "${imports_arr[@]}"; do
        current_imports+=("$(echo "$imp" | tr -d ' ')")
      done
      continue
    fi

    # Parse file_patterns
    if [[ "$line" =~ file_patterns: ]]; then
      patterns_str=$(echo "$line" | sed 's/.*\[//;s/\].*//' | tr -d '"')
      IFS=',' read -ra patterns_arr <<< "$patterns_str"
      for pat in "${patterns_arr[@]}"; do
        current_patterns+=("$(echo "$pat" | tr -d ' ')")
      done
      continue
    fi

    # Parse reason
    if [[ "$line" =~ reason: ]]; then
      current_reason=$(echo "$line" | sed 's/.*reason:[[:space:]]*"\(.*\)"/\1/' | tr -d '"')
      continue
    fi
  fi
done < "$RULES_FILE"

# Check last rule
check_rule

# Report
echo ""
if [ $VIOLATIONS -eq 0 ]; then
  success "No boundary violations found. ($CHECKED files checked)"
  exit 0
else
  error "$VIOLATIONS boundary violation(s) found."
  exit 1
fi
