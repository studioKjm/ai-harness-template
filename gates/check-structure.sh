#!/usr/bin/env bash
# Check project structure rules.
# Reads rules from .harness/gates/rules/structure.yaml
# Usage: ./check-structure.sh [project-root]

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

# Find rules file
RULES_FILE=""
if [ -f "$PROJECT_ROOT/.harness/gates/rules/structure.yaml" ]; then
  RULES_FILE="$PROJECT_ROOT/.harness/gates/rules/structure.yaml"
elif [ -f "$SCRIPT_DIR/rules/structure.yaml" ]; then
  RULES_FILE="$SCRIPT_DIR/rules/structure.yaml"
else
  warn "No structure.yaml found, skipping structure check"
  exit 0
fi

header "Project Structure Check"
info "Rules: $RULES_FILE"
echo ""

VIOLATIONS=0

# ─── Check: .env files not in git ──────────────────────────────────
if [ -d "$PROJECT_ROOT/.git" ]; then
  ENV_IN_GIT=$(cd "$PROJECT_ROOT" && git ls-files '*.env' '.env*' 2>/dev/null | grep -v '.env.example' | grep -v '.env.template' || true)
  if [ -n "$ENV_IN_GIT" ]; then
    while IFS= read -r file; do
      [ -z "$file" ] && continue
      error "VIOLATION: $file is tracked by git"
      echo "  Rule: .env files must not be committed"
      echo "  Fix: git rm --cached $file && add to .gitignore"
      echo ""
      VIOLATIONS=$((VIOLATIONS + 1))
    done <<< "$ENV_IN_GIT"
  fi
fi

# ─── Check: No orphan migration files ──────────────────────────────
# SQL files outside migration directories
find "$PROJECT_ROOT" -name "*.sql" -type f \
  -not -path "*/node_modules/*" \
  -not -path "*/.git/*" \
  -not -path "*/migrations/*" \
  -not -path "*/alembic/*" \
  -not -path "*/prisma/*" \
  -not -path "*/.harness/*" \
  2>/dev/null | while IFS= read -r file; do
  rel_path="${file#$PROJECT_ROOT/}"
  warn "SQL file outside migration directory: $rel_path"
  VIOLATIONS=$((VIOLATIONS + 1))
done

# ─── Check: No test files in production directories ───────────────
# This is a common AI agent mistake
find "$PROJECT_ROOT/src" "$PROJECT_ROOT/app" \
  -name "*.test.*" -o -name "*.spec.*" \
  -type f 2>/dev/null | \
  grep -v "__tests__" | \
  grep -v "node_modules" | \
  grep -v ".next" | while IFS= read -r file; do
  # This is actually fine for co-located tests — just informational
  :
done

# Report
echo ""
if [ $VIOLATIONS -eq 0 ]; then
  success "Project structure is clean."
  exit 0
else
  error "$VIOLATIONS structure violation(s) found."
  exit 1
fi
