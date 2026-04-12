#!/usr/bin/env bash
# Harness v1 → v2 migration script
# Moves .ouroboros/* into .harness/ouroboros/* to unify the dotfolder layout.
# Usage: ./scripts/migrate-v2.sh [project-root]

set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"

OLD_DIR="$PROJECT_ROOT/.ouroboros"
NEW_PARENT="$PROJECT_ROOT/.harness"
NEW_DIR="$NEW_PARENT/ouroboros"

echo "=== Harness v2 Migration ==="
echo "Project: $PROJECT_ROOT"
echo ""

# ─── Preflight ───────────────────────────────────────────────────
if [ ! -d "$OLD_DIR" ]; then
  echo "[OK] No legacy .ouroboros/ found — nothing to migrate."
  exit 0
fi

if [ ! -d "$NEW_PARENT" ]; then
  echo "[ERROR] .harness/ directory missing."
  echo "       Re-run the installer first: <harness-repo>/init.sh $PROJECT_ROOT"
  exit 1
fi

if [ -d "$NEW_DIR" ]; then
  echo "[ERROR] $NEW_DIR already exists."
  echo "       Merge manually or remove one side before retrying."
  exit 1
fi

# ─── Preview ─────────────────────────────────────────────────────
echo "Plan:"
echo "  $OLD_DIR"
echo "    → $NEW_DIR"
echo ""

if [ -t 0 ]; then
  read -p "Proceed? [y/N] " -n 1 -r CONFIRM
  echo ""
  if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
fi

# ─── Move (prefer git mv when tracked) ──────────────────────────
USE_GIT_MV=0
if [ -d "$PROJECT_ROOT/.git" ] && git -C "$PROJECT_ROOT" ls-files --error-unmatch ".ouroboros" >/dev/null 2>&1; then
  USE_GIT_MV=1
fi

if [ "$USE_GIT_MV" -eq 1 ]; then
  echo "[INFO] Using 'git mv' to preserve history."
  git -C "$PROJECT_ROOT" mv ".ouroboros" ".harness/ouroboros"
else
  echo "[INFO] Using 'mv' (not tracked in git or no git repo)."
  mv "$OLD_DIR" "$NEW_DIR"
fi

echo "[OK] Moved directory."

# ─── Update .gitignore ──────────────────────────────────────────
GITIGNORE="$PROJECT_ROOT/.gitignore"
if [ -f "$GITIGNORE" ]; then
  CHANGED=0
  # Replace common v1 entries in-place
  TMP="$(mktemp)"
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ".ouroboros/session.db")   echo ".harness/ouroboros/session.db"   >> "$TMP"; CHANGED=1 ;;
      ".ouroboros/interviews/")  echo ".harness/ouroboros/interviews/"  >> "$TMP"; CHANGED=1 ;;
      ".ouroboros/evaluations/") echo ".harness/ouroboros/evaluations/" >> "$TMP"; CHANGED=1 ;;
      ".ouroboros/"|".ouroboros")echo ".harness/ouroboros/"             >> "$TMP"; CHANGED=1 ;;
      *)                         echo "$line"                           >> "$TMP" ;;
    esac
  done < "$GITIGNORE"
  if [ "$CHANGED" -eq 1 ]; then
    mv "$TMP" "$GITIGNORE"
    echo "[OK] Updated .gitignore"
  else
    rm -f "$TMP"
  fi
fi

echo ""
echo "=== Migration complete ==="
echo ""
echo "Next steps:"
echo "  1. Review changes:    git status"
echo "  2. Re-install harness: <harness-repo>/init.sh $PROJECT_ROOT --yes"
echo "     (refreshes commands/agents with v2 paths)"
echo "  3. Commit the move:   git commit -am 'chore: migrate to harness v2 layout'"
