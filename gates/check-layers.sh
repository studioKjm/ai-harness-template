#!/usr/bin/env bash
# Check 3-tier layer separation violations.
# Verifies that Presentation, Logic, and Data layers respect their boundaries.
# Usage: ./check-layers.sh [project-root]
#
# Checks:
#   1. Presentation → Data layer skipping (direct DB access from UI/routes)
#   2. Logic → Presentation reverse dependency (services importing UI frameworks)
#   3. Data → Logic/Presentation reverse dependency
#   4. Business logic in Presentation layer (complex logic in controllers/routes)

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

header "3-Tier Layer Separation Check"

VIOLATIONS=0
WARNINGS=0
CHECKED=0

# ─── Layer directory detection ──────────────────────────────────────
# Auto-detect which directories belong to which layer

# Presentation layer directories
PRESENTATION_DIRS=(
  "src/components" "src/pages" "src/app" "components" "pages" "app"
  "src/controllers" "controllers"
  "src/routes" "routes" "src/api/routes"
  "src/views" "views" "templates"
)

# Logic layer directories
LOGIC_DIRS=(
  "src/services" "services" "src/domain" "domain"
  "src/lib" "lib" "src/core" "core"
  "src/usecases" "usecases" "src/use-cases" "use-cases"
  "src/business" "business"
)

# Data layer directories
DATA_DIRS=(
  "src/repositories" "repositories" "src/repo" "repo"
  "src/models" "models" "src/entities" "entities"
  "src/db" "db" "src/database" "database"
  "src/persistence" "persistence" "src/infrastructure" "infrastructure"
  "prisma"
)

# ─── Presentation framework patterns (should not appear in Logic/Data) ──
PRESENTATION_IMPORTS=(
  "from react"
  "import React"
  "from 'react'"
  "from \"react\""
  "from 'next/"
  "from \"next/"
  "from 'vue'"
  "from '@angular"
  "from 'svelte'"
  "express.Request"
  "express.Response"
  "flask.request"
  "django.http.HttpRequest"
  "starlette.requests"
  "fastapi.Request"
)

# ─── DB/Data patterns (should not appear in Presentation) ──────────
DATA_IMPORTS=(
  "PrismaClient"
  "@prisma/client"
  "drizzle-orm"
  "typeorm"
  "sequelize"
  "mongoose"
  "create_engine"
  "sessionmaker"
  "AsyncSession"
  "cursor.execute"
  "raw("
  "better-sqlite3"
  "pg "
  "mysql2"
)

# ─── Check function ────────────────────────────────────────────────
check_layer_violation() {
  local dir="$1"
  local layer_name="$2"
  local patterns_var="$3"
  local violation_type="$4"

  local search_dir="$PROJECT_ROOT/$dir"
  [ ! -d "$search_dir" ] && return

  # bash 3.2 compatible: use eval to expand array variable by name
  eval "local patterns_list=(\"\${${patterns_var}[@]}\")"

  for pattern in "${patterns_list[@]}"; do
    local matches
    matches=$(grep -rn "$pattern" "$search_dir" \
      --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" \
      2>/dev/null | grep -v "node_modules" | grep -v "__pycache__" | grep -v ".test." | grep -v ".spec." | head -5 || true)
    [ -z "$matches" ] && continue

    while IFS= read -r match; do
      local file_line=$(echo "$match" | cut -d: -f1-2)
      local rel_path="${file_line#$PROJECT_ROOT/}"
      error "LAYER VIOLATION [$violation_type]: $rel_path"
      echo "  Pattern: $pattern"
      echo "  Layer: $layer_name should not reference this"
      echo ""
      VIOLATIONS=$((VIOLATIONS + 1))
    done <<< "$matches"
  done
}

# ─── Run checks ────────────────────────────────────────────────────

info "Checking Presentation → Data layer skipping..."
for dir in "${PRESENTATION_DIRS[@]}"; do
  check_layer_violation "$dir" "Presentation" DATA_IMPORTS "P→D SKIP"
  CHECKED=$((CHECKED + 1))
done

info "Checking Logic → Presentation reverse dependency..."
for dir in "${LOGIC_DIRS[@]}"; do
  check_layer_violation "$dir" "Logic" PRESENTATION_IMPORTS "L→P REVERSE"
  CHECKED=$((CHECKED + 1))
done

info "Checking Data → Presentation reverse dependency..."
for dir in "${DATA_DIRS[@]}"; do
  check_layer_violation "$dir" "Data" PRESENTATION_IMPORTS "D→P REVERSE"
  CHECKED=$((CHECKED + 1))
done

# ─── Check for business logic in Presentation ──────────────────────
info "Checking for business logic in Presentation layer..."

check_presentation_size() {
  local dir="$1"
  local search_dir="$PROJECT_ROOT/$dir"
  [ ! -d "$search_dir" ] && return

  # Find suspiciously long controller/route functions (potential business logic leak)
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    local lines
    lines=$(wc -l < "$file" 2>/dev/null | tr -d ' ')
    local rel_path="${file#$PROJECT_ROOT/}"

    # Skip test files
    [[ "$rel_path" =~ (test|spec|__test__) ]] && continue

    if [ "$lines" -gt 200 ]; then
      warn "LARGE PRESENTATION FILE: $rel_path ($lines lines)"
      echo "  Presentation 레이어 파일이 200줄을 초과합니다. 비즈니스 로직이 포함되었을 수 있습니다."
      echo "  Logic 레이어(services/)로 분리를 검토하세요."
      echo ""
      WARNINGS=$((WARNINGS + 1))
    fi
  done < <(find "$search_dir" -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.py" \) 2>/dev/null)
}

for dir in "${PRESENTATION_DIRS[@]}"; do
  check_presentation_size "$dir"
done

# ─── Report ────────────────────────────────────────────────────────
echo ""
info "Checked $CHECKED directory patterns"

if [ $VIOLATIONS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  success "No layer separation issues found."
  exit 0
elif [ $VIOLATIONS -eq 0 ]; then
  warn "$WARNINGS warning(s) found. Review recommended."
  exit 0
else
  error "$VIOLATIONS layer violation(s) found. $WARNINGS warning(s)."
  info "Fix violations before committing. Layer rules:"
  info "  Presentation → Logic → Data (downward only, no skipping)"
  exit 1
fi
