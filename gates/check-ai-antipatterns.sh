#!/usr/bin/env bash
# Check for common AI-generated code anti-patterns.
# Usage: ./check-ai-antipatterns.sh [project-root]
#
# AI agents produce specific categories of mistakes:
# - Hallucinated APIs (methods/functions that don't exist)
# - Over-abstraction (unnecessary wrappers, premature generalization)
# - Naming drift (inconsistent naming across files)
# - Dead code (generated but never called)
# - Copy-paste artifacts (duplicate blocks with minor variations)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"

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

header "AI Anti-pattern Detection"
echo ""

WARNINGS=0
CHECKED=0

# ─── Collect source files ──────────────────────────────────────────
get_source_files() {
  find "$PROJECT_ROOT" -type f \
    \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" \) \
    -not -path "*/node_modules/*" -not -path "*/.next/*" \
    -not -path "*/dist/*" -not -path "*/build/*" \
    -not -path "*/__pycache__/*" -not -path "*/.harness/*" \
    -not -path "*/.ouroboros/*" -not -name "*.min.*" \
    2>/dev/null
}

# ─── 1. Hallucinated API patterns ──────────────────────────────────
check_hallucinated_apis() {
  info "Checking for hallucinated API patterns..."

  # Common hallucinated methods/patterns AI agents produce
  local patterns=(
    '\.toArray().*\.toArray()'      # Double toArray (common AI hallucination)
    'Array\.from.*Array\.from'       # Redundant Array.from
    'JSON\.parse.*JSON\.parse'       # Double parse
    '\.toString()\.toString()'       # Chained toString
    '\.trim()\.trim()'              # Redundant trim
    'await await '                   # Double await
    'return return '                 # Double return
    'async async '                   # Double async
  )

  local found=0
  for pattern in "${patterns[@]}"; do
    local matches
    matches=$(grep -rn "$pattern" "$PROJECT_ROOT" \
      --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" \
      2>/dev/null | grep -v "node_modules" | grep -v ".harness" | head -3 || true)
    [ -z "$matches" ] && continue

    while IFS= read -r match; do
      local rel="${match#$PROJECT_ROOT/}"
      warn "HALLUCINATION: $rel"
      echo "  Pattern: $pattern"
      echo ""
      found=$((found + 1))
    done <<< "$matches"
  done

  if [ "$found" -eq 0 ]; then
    success "No hallucinated API patterns found"
  fi
  WARNINGS=$((WARNINGS + found))
  CHECKED=$((CHECKED + 1))
}

# ─── 2. Over-abstraction ──────────────────────────────────────────
check_over_abstraction() {
  info "Checking for over-abstraction..."

  local found=0

  # Single-method wrapper classes/interfaces (useless abstraction)
  # TypeScript/JavaScript: class with only one method
  while IFS= read -r file; do
    [ -z "$file" ] && continue

    # Check for files that are just thin wrappers
    local total_lines
    total_lines=$(wc -l < "$file" 2>/dev/null | tr -d ' ')
    [ "$total_lines" -lt 5 ] && continue

    # Detect classes/functions that just call another function (passthrough)
    local passthrough_count
    passthrough_count=$(grep -cE '^\s*return\s+(this\.|super\.|self\.)\w+\(' "$file" 2>/dev/null || true)
    local method_count
    method_count=$(grep -cE '^\s*(def |async def |function |const \w+ = |static |public |private )' "$file" 2>/dev/null || true)

    if [ "$method_count" -gt 0 ] && [ "$passthrough_count" -gt 0 ]; then
      local ratio=$((passthrough_count * 100 / method_count))
      if [ "$ratio" -gt 80 ] && [ "$method_count" -gt 2 ]; then
        local rel="${file#$PROJECT_ROOT/}"
        warn "OVER-ABSTRACTION: $rel"
        echo "  $passthrough_count/$method_count methods are passthrough wrappers ($ratio%)"
        echo "  Consider removing the wrapper and calling the target directly"
        echo ""
        found=$((found + 1))
      fi
    fi
  done < <(get_source_files)

  if [ "$found" -eq 0 ]; then
    success "No over-abstraction detected"
  fi
  WARNINGS=$((WARNINGS + found))
  CHECKED=$((CHECKED + 1))
}

# ─── 3. Copy-paste artifacts ──────────────────────────────────────
check_copy_paste() {
  info "Checking for copy-paste artifacts..."

  local found=0

  # Detect TODO/FIXME that reference wrong file/function names
  # (common when AI copies a template and forgets to update)
  local matches
  matches=$(grep -rn "TODO.*CHANGEME\|FIXME.*CHANGEME\|XXX.*CHANGEME\|PLACEHOLDER" "$PROJECT_ROOT" \
    --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" \
    2>/dev/null | grep -v "node_modules" | grep -v ".harness" | head -10 || true)

  if [ -n "$matches" ]; then
    while IFS= read -r match; do
      local rel="${match#$PROJECT_ROOT/}"
      warn "COPY-PASTE ARTIFACT: $rel"
      found=$((found + 1))
    done <<< "$matches"
  fi

  # Detect commented-out code blocks (AI often leaves old attempts)
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    local commented_lines
    commented_lines=$(grep -cE '^\s*(//|#)\s*(const|let|var|function|class|def |async def |import |from |if |for |while |return )' "$file" 2>/dev/null || true)
    local total_lines
    total_lines=$(wc -l < "$file" 2>/dev/null | tr -d ' ')

    if [ "$total_lines" -gt 20 ] && [ "$commented_lines" -gt 10 ]; then
      local ratio=$((commented_lines * 100 / total_lines))
      if [ "$ratio" -gt 15 ]; then
        local rel="${file#$PROJECT_ROOT/}"
        warn "COMMENTED CODE: $rel"
        echo "  $commented_lines/$total_lines lines are commented-out code ($ratio%)"
        echo "  Remove dead code — version control preserves history"
        echo ""
        found=$((found + 1))
      fi
    fi
  done < <(get_source_files)

  if [ "$found" -eq 0 ]; then
    success "No copy-paste artifacts found"
  fi
  WARNINGS=$((WARNINGS + found))
  CHECKED=$((CHECKED + 1))
}

# ─── 4. Inconsistent naming ──────────────────────────────────────
check_naming_drift() {
  info "Checking for naming inconsistencies..."

  local found=0

  # Detect mixed naming conventions in the same file
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    local rel="${file#$PROJECT_ROOT/}"

    case "$file" in
      *.py)
        # Python: check for camelCase functions (should be snake_case)
        local camel_funcs
        camel_funcs=$(grep -cE '^\s*def [a-z]+[A-Z]' "$file" 2>/dev/null || true)
        if [ "$camel_funcs" -gt 2 ]; then
          warn "NAMING DRIFT: $rel — $camel_funcs camelCase function(s) in Python (use snake_case)"
          found=$((found + 1))
        fi
        ;;
      *.ts|*.tsx|*.js|*.jsx)
        # JS/TS: check for snake_case functions (should be camelCase)
        local snake_funcs
        snake_funcs=$(grep -cE '(function|const|let|var)\s+[a-z]+_[a-z]' "$file" 2>/dev/null || true)
        if [ "$snake_funcs" -gt 3 ]; then
          warn "NAMING DRIFT: $rel — $snake_funcs snake_case identifier(s) in JS/TS (use camelCase)"
          found=$((found + 1))
        fi
        ;;
    esac
  done < <(get_source_files)

  if [ "$found" -eq 0 ]; then
    success "No naming drift detected"
  fi
  WARNINGS=$((WARNINGS + found))
  CHECKED=$((CHECKED + 1))
}

# ─── 5. Unused imports ────────────────────────────────────────────
check_unused_imports() {
  info "Checking for potential unused imports..."

  local found=0

  while IFS= read -r file; do
    [ -z "$file" ] && continue
    local rel="${file#$PROJECT_ROOT/}"

    # Skip test files
    [[ "$rel" =~ (test|spec|__test__) ]] && continue

    case "$file" in
      *.py)
        local imports
        imports=$(grep -E '^\s*(import |from .+ import )' "$file" 2>/dev/null || true)
        [ -z "$imports" ] && continue

        local content
        content=$(grep -v '^\s*#' "$file" | grep -v '^\s*import ' | grep -v '^\s*from ' 2>/dev/null || true)

        while IFS= read -r imp_line; do
          [ -z "$imp_line" ] && continue
          # Extract imported name
          local name
          name=$(echo "$imp_line" | sed -n 's/.*import[[:space:]]\{1,\}\([a-zA-Z_][a-zA-Z0-9_]*\).*/\1/p' | tail -1)
          [ -z "$name" ] && continue
          [ ${#name} -lt 3 ] && continue

          if ! echo "$content" | grep -q "$name" 2>/dev/null; then
            warn "UNUSED IMPORT: $rel — '$name' imported but not used"
            found=$((found + 1))
          fi
        done <<< "$imports"
        ;;
    esac
  done < <(get_source_files)

  if [ "$found" -eq 0 ]; then
    success "No obviously unused imports found"
  fi
  WARNINGS=$((WARNINGS + found))
  CHECKED=$((CHECKED + 1))
}

# ─── Run all checks ────────────────────────────────────────────────
check_hallucinated_apis
check_over_abstraction
check_copy_paste
check_naming_drift
check_unused_imports

# ─── Report ────────────────────────────────────────────────────────
echo ""
if [ $WARNINGS -eq 0 ]; then
  success "No AI anti-patterns detected. ($CHECKED checks run)"
  exit 0
else
  warn "$WARNINGS AI anti-pattern warning(s) found. ($CHECKED checks run)"
  info "These are warnings from heuristic checks. Review and fix as needed."
  exit 0  # Warnings don't block
fi
