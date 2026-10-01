#!/usr/bin/env bash
# Supabase / SQL migration safety gate.
# Usage: ./check-migrations.sh [project-root]
#
# Checks (only when supabase/migrations exists, otherwise no-op):
#   1. Applied migrations are immutable: modified / deleted / renamed files are rejected
#   2. File name format: <14-digit timestamp>_<snake_case>.sql
#   3. New tables must enable row level security in the same migration
#   4. Blanket policies: using (true) / with check (true) are rejected
#
# Scope of comparison:
#   - Staged changes (pre-commit), or
#   - HARNESS_BASE_REF (default: origin/main) ... HEAD when nothing is staged (CI)
# Escape hatch for a legitimate squash/baseline rewrite: HARNESS_ALLOW_MIGRATION_REWRITE=1

set -uo pipefail

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

MIG_DIR="supabase/migrations"
cd "$PROJECT_ROOT" || exit 0
[ -d "$MIG_DIR" ] || exit 0

header "Migration Safety Check"
VIOLATIONS=0
fail() { error "$*"; VIOLATIONS=$((VIOLATIONS + 1)); }

# Resolve what changed
if git rev-parse --git-dir >/dev/null 2>&1; then
  if ! git diff --cached --quiet -- "$MIG_DIR" 2>/dev/null; then
    NAME_STATUS="$(git diff --cached --name-status -- "$MIG_DIR")"
    ADDED="$(git diff --cached --name-only --diff-filter=A -- "$MIG_DIR")"
  else
    BASE="${HARNESS_BASE_REF:-origin/main}"
    if git rev-parse --verify -q "$BASE" >/dev/null 2>&1; then
      NAME_STATUS="$(git diff --name-status "$BASE"...HEAD -- "$MIG_DIR" 2>/dev/null || true)"
      ADDED="$(git diff --name-only --diff-filter=A "$BASE"...HEAD -- "$MIG_DIR" 2>/dev/null || true)"
    else
      NAME_STATUS=""; ADDED=""
    fi
  fi
else
  exit 0
fi

# 1. Immutability
if [ "${HARNESS_ALLOW_MIGRATION_REWRITE:-0}" != "1" ]; then
  BAD="$(printf '%s\n' "$NAME_STATUS" | awk '$1 ~ /^[MDR]/ {print}' | grep -E '\.sql' || true)"
  [ -n "$BAD" ] && fail "Applied migrations are immutable. Add a new migration instead:
$BAD"
fi

# 2-4. New files
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in *.sql) ;; *) continue ;; esac
  base="$(basename "$f")"
  [[ "$base" =~ ^[0-9]{14}_[a-z0-9_]+\.sql$ ]] || fail "$f: file name must match <timestamp>_<snake_case>.sql"
  [ -f "$f" ] || continue
  if grep -qiE 'create[[:space:]]+table' "$f" && ! grep -qiE 'enable[[:space:]]+row[[:space:]]+level[[:space:]]+security' "$f"; then
    fail "$f: new table without 'enable row level security' in the same migration"
  fi
  if grep -qiE '(using|with[[:space:]]+check)[[:space:]]*\([[:space:]]*true[[:space:]]*\)' "$f"; then
    fail "$f: blanket policy using (true) / with check (true) is not allowed"
  fi
done <<< "$ADDED"

if [ "$VIOLATIONS" -gt 0 ]; then
  error "Migration gate failed ($VIOLATIONS violation(s))"
  exit 1
fi
success "Migration gate passed"
exit 0
