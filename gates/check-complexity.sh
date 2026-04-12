#!/usr/bin/env bash
# Check code complexity metrics.
# Flags functions/methods that exceed configurable thresholds.
# Usage: ./check-complexity.sh [project-root] [--max-lines=80] [--max-params=5]
#
# Checks:
#   - Function length (lines)
#   - Parameter count
#   - File length
#   - Nesting depth (approximation)

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

# ─── Configurable thresholds ────────────────────────────────────────
MAX_FUNC_LINES=80
MAX_PARAMS=5
MAX_FILE_LINES=500
MAX_NESTING=5

# Parse optional arguments
for arg in "$@"; do
  case "$arg" in
    --max-lines=*) MAX_FUNC_LINES="${arg#*=}" ;;
    --max-params=*) MAX_PARAMS="${arg#*=}" ;;
    --max-file-lines=*) MAX_FILE_LINES="${arg#*=}" ;;
  esac
done

header "Code Complexity Check"
info "Thresholds: func=${MAX_FUNC_LINES}L, params=${MAX_PARAMS}, file=${MAX_FILE_LINES}L, nesting=${MAX_NESTING}"
echo ""

WARNINGS=0
VIOLATIONS=0

# ─── File length check ──────────────────────────────────────────────
check_file_length() {
  local file="$1"
  local lines
  lines=$(wc -l < "$file" 2>/dev/null | tr -d ' ')

  if [ "$lines" -gt "$MAX_FILE_LINES" ]; then
    local rel_path="${file#$PROJECT_ROOT/}"
    warn "LONG FILE: $rel_path ($lines lines, threshold: $MAX_FILE_LINES)"
    WARNINGS=$((WARNINGS + 1))
  fi
}

# ─── Function length check (Python) ────────────────────────────────
check_python_complexity() {
  local file="$1"
  local rel_path="${file#$PROJECT_ROOT/}"
  local in_func=false
  local func_name=""
  local func_start=0
  local line_num=0
  local indent_level=0

  while IFS= read -r line; do
    line_num=$((line_num + 1))

    # Detect function/method definition
    if echo "$line" | grep -qE '^\s*(def|async def)\s+\w+'; then
      # Check previous function
      if $in_func && [ $func_start -gt 0 ]; then
        local func_lines=$((line_num - func_start))
        if [ "$func_lines" -gt "$MAX_FUNC_LINES" ]; then
          warn "LONG FUNCTION: $rel_path:$func_start — $func_name ($func_lines lines)"
          WARNINGS=$((WARNINGS + 1))
        fi
      fi

      func_name=$(echo "$line" | sed 's/.*def \(async \)\?\([a-zA-Z_][a-zA-Z0-9_]*\).*/\2/')
      func_start=$line_num
      in_func=true

      # Check parameter count
      local params
      params=$(echo "$line" | sed 's/.*(\(.*\)).*/\1/' | tr ',' '\n' | grep -c '\w' || true)
      # Subtract 'self' and 'cls'
      if echo "$line" | grep -q 'self'; then
        params=$((params - 1))
      fi
      if [ "$params" -gt "$MAX_PARAMS" ]; then
        warn "TOO MANY PARAMS: $rel_path:$line_num — $func_name ($params params)"
        WARNINGS=$((WARNINGS + 1))
      fi
    fi
  done < "$file"

  # Check last function
  if $in_func && [ $func_start -gt 0 ]; then
    local func_lines=$((line_num - func_start))
    if [ "$func_lines" -gt "$MAX_FUNC_LINES" ]; then
      warn "LONG FUNCTION: $rel_path:$func_start — $func_name ($func_lines lines)"
      WARNINGS=$((WARNINGS + 1))
    fi
  fi
}

# ─── Function length check (JS/TS) ─────────────────────────────────
check_js_complexity() {
  local file="$1"
  local rel_path="${file#$PROJECT_ROOT/}"
  local line_num=0
  local brace_depth=0
  local func_name=""
  local func_start=0
  local in_func=false

  while IFS= read -r line; do
    line_num=$((line_num + 1))

    # Detect function/method definition
    if echo "$line" | grep -qE '(function\s+\w+|const\s+\w+\s*=\s*(async\s+)?\(|^\s*(async\s+)?\w+\s*\()'; then
      if ! $in_func; then
        func_name=$(echo "$line" | grep -oE '\b[a-zA-Z_]\w*\s*[=(]' | head -1 | tr -d '(= ')
        func_start=$line_num
        in_func=true
        brace_depth=0
      fi

      # Check parameter count (rough)
      local params
      params=$(echo "$line" | sed 's/.*(\(.*\)).*/\1/' | tr ',' '\n' | grep -c '\w' || true)
      if [ "$params" -gt "$MAX_PARAMS" ]; then
        warn "TOO MANY PARAMS: $rel_path:$line_num — ${func_name:-anonymous} ($params params)"
        WARNINGS=$((WARNINGS + 1))
      fi
    fi

    # Track brace depth for function end detection
    if $in_func; then
      local opens closes
      opens=$(echo "$line" | tr -cd '{' | wc -c | tr -d ' ')
      closes=$(echo "$line" | tr -cd '}' | wc -c | tr -d ' ')
      brace_depth=$((brace_depth + opens - closes))

      if [ "$brace_depth" -le 0 ] && [ "$func_start" -gt 0 ]; then
        local func_lines=$((line_num - func_start))
        if [ "$func_lines" -gt "$MAX_FUNC_LINES" ]; then
          warn "LONG FUNCTION: $rel_path:$func_start — ${func_name:-anonymous} ($func_lines lines)"
          WARNINGS=$((WARNINGS + 1))
        fi
        in_func=false
        func_start=0
      fi

      # Check nesting depth
      if [ "$brace_depth" -gt "$MAX_NESTING" ]; then
        warn "DEEP NESTING: $rel_path:$line_num — depth $brace_depth (max: $MAX_NESTING)"
        WARNINGS=$((WARNINGS + 1))
        # Only warn once per excessive nesting block
        brace_depth=$MAX_NESTING
      fi
    fi
  done < "$file"
}

# ─── Find and check files ──────────────────────────────────────────
file_count=0

while IFS= read -r file; do
  [ -z "$file" ] && continue
  [ ! -f "$file" ] && continue

  check_file_length "$file"

  case "$file" in
    *.py)
      check_python_complexity "$file"
      ;;
    *.ts|*.tsx|*.js|*.jsx)
      check_js_complexity "$file"
      ;;
  esac

  file_count=$((file_count + 1))
done < <(find "$PROJECT_ROOT" -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
  -not -path '*/.git/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/.next/*' \
  -not -path '*/dist/*' \
  -not -path '*/build/*' \
  -not -path '*/*.min.js' \
  -not -path '*/.harness/*' \
  2>/dev/null)

# ─── Report ────────────────────────────────────────────────────────
echo ""
if [ $WARNINGS -eq 0 ]; then
  success "No complexity issues found. ($file_count files checked)"
  exit 0
else
  warn "$WARNINGS complexity warning(s) found across $file_count files."
  info "These are warnings, not blocking violations. Review and refactor as needed."
  exit 0  # Warnings don't block by default
fi
