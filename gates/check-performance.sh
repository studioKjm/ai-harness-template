#!/usr/bin/env bash
# Performance budget gate.
# Checks bundle size, file size, dependency count, and import depth.
# Usage: ./check-performance.sh [project-root] [--max-bundle=500] [--max-deps=50]
#
# AI tends to generate verbose, unoptimized code with excessive dependencies.

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

# ─── Configurable budgets ───────────────────────────────────────────
MAX_BUNDLE_KB=500       # Max bundle/build output size (KB)
MAX_SINGLE_FILE_KB=100  # Max single source file size (KB)
MAX_DEPS=50             # Max production dependencies
MAX_IMPORT_DEPTH=5      # Max directory nesting for imports

for arg in "$@"; do
  case "$arg" in
    --max-bundle=*) MAX_BUNDLE_KB="${arg#*=}" ;;
    --max-deps=*) MAX_DEPS="${arg#*=}" ;;
    --max-file=*) MAX_SINGLE_FILE_KB="${arg#*=}" ;;
  esac
done

header "Performance Budget Check"
info "Budgets: bundle=${MAX_BUNDLE_KB}KB, file=${MAX_SINGLE_FILE_KB}KB, deps=${MAX_DEPS}"
echo ""

WARNINGS=0

# ─── Large source files ────────────────────────────────────────────
check_file_sizes() {
  info "Checking source file sizes..."
  local large_count=0

  while IFS= read -r file; do
    [ -z "$file" ] && continue
    local size_kb
    size_kb=$(( $(wc -c < "$file" 2>/dev/null | tr -d ' ') / 1024 ))
    if [ "$size_kb" -gt "$MAX_SINGLE_FILE_KB" ]; then
      local rel="${file#$PROJECT_ROOT/}"
      warn "LARGE FILE: $rel (${size_kb}KB > ${MAX_SINGLE_FILE_KB}KB)"
      large_count=$((large_count + 1))
    fi
  done < <(find "$PROJECT_ROOT" -type f \
    \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \
       -o -name "*.py" -o -name "*.go" -o -name "*.rs" \) \
    -not -path "*/node_modules/*" -not -path "*/.next/*" \
    -not -path "*/dist/*" -not -path "*/build/*" \
    -not -path "*/__pycache__/*" -not -path "*/.harness/*" \
    -not -name "*.min.*" -not -name "*.lock" \
    2>/dev/null)

  if [ "$large_count" -eq 0 ]; then
    success "All source files within budget"
  else
    WARNINGS=$((WARNINGS + large_count))
  fi
}

# ─── Dependency count ──────────────────────────────────────────────
check_dep_count() {
  info "Checking dependency count..."

  # Node.js
  if [ -f "$PROJECT_ROOT/package.json" ]; then
    local prod_deps
    prod_deps=$(python3 -c "
import json, sys
try:
    with open('$PROJECT_ROOT/package.json') as f:
        d = json.load(f)
    print(len(d.get('dependencies', {})))
except:
    print(0)
" 2>/dev/null || echo "0")

    if [ "$prod_deps" -gt "$MAX_DEPS" ]; then
      warn "NPM: $prod_deps production dependencies (budget: $MAX_DEPS)"
      echo "  Review package.json for unnecessary or duplicate dependencies"
      WARNINGS=$((WARNINGS + 1))
    else
      success "NPM: $prod_deps production dependencies (budget: $MAX_DEPS)"
    fi
  fi

  # Python
  if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    local py_deps
    py_deps=$(grep -cE '^[a-zA-Z]' "$PROJECT_ROOT/requirements.txt" 2>/dev/null || echo "0")
    if [ "$py_deps" -gt "$MAX_DEPS" ]; then
      warn "Python: $py_deps dependencies (budget: $MAX_DEPS)"
      WARNINGS=$((WARNINGS + 1))
    else
      success "Python: $py_deps dependencies (budget: $MAX_DEPS)"
    fi
  fi
}

# ─── Build output size ─────────────────────────────────────────────
check_build_size() {
  info "Checking build output size..."

  local build_dirs=("dist" "build" ".next/static" "out")
  for dir in "${build_dirs[@]}"; do
    local full_path="$PROJECT_ROOT/$dir"
    [ ! -d "$full_path" ] && continue

    local size_kb
    size_kb=$(du -sk "$full_path" 2>/dev/null | cut -f1)
    if [ "$size_kb" -gt "$MAX_BUNDLE_KB" ]; then
      warn "BUILD: $dir is ${size_kb}KB (budget: ${MAX_BUNDLE_KB}KB)"
      echo "  Consider code splitting, tree shaking, or removing unused code"
      WARNINGS=$((WARNINGS + 1))
    else
      success "BUILD: $dir is ${size_kb}KB (budget: ${MAX_BUNDLE_KB}KB)"
    fi
  done
}

# ─── Deep import paths ─────────────────────────────────────────────
check_import_depth() {
  info "Checking import depth..."
  local deep_count=0

  local matches
  matches=$(grep -rn "from ['\"].*/" "$PROJECT_ROOT" \
    --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" \
    2>/dev/null | \
    grep -v "node_modules" | grep -v ".next" | grep -v "dist" || true)

  while IFS= read -r line; do
    [ -z "$line" ] && continue
    local import_path
    import_path=$(echo "$line" | sed -n "s/.*from ['\"]\.\\{0,1\\}\([^'\"]*\).*/\\1/p")
    [ -z "$import_path" ] && continue

    local depth
    depth=$(echo "$import_path" | tr '/' '\n' | grep -c '\.\.' || true)
    if [ "$depth" -gt "$MAX_IMPORT_DEPTH" ]; then
      local file_ref=$(echo "$line" | cut -d: -f1-2)
      local rel="${file_ref#$PROJECT_ROOT/}"
      warn "DEEP IMPORT: $rel — $depth levels up"
      deep_count=$((deep_count + 1))
    fi
  done <<< "$matches"

  if [ "$deep_count" -eq 0 ]; then
    success "No excessively deep imports"
  else
    echo "  Consider using path aliases (@/lib, @/components) instead of ../../../"
    WARNINGS=$((WARNINGS + deep_count))
  fi
}

# ─── Run checks ────────────────────────────────────────────────────
check_file_sizes
check_dep_count
check_build_size
check_import_depth

# ─── Report ────────────────────────────────────────────────────────
echo ""
if [ $WARNINGS -eq 0 ]; then
  success "All performance budgets within limits."
  exit 0
else
  warn "$WARNINGS performance budget warning(s)."
  info "These are warnings, not blocking. Review and optimize as needed."
  exit 0
fi
