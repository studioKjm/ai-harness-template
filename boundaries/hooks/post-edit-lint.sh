#!/usr/bin/env bash
# Auto-lint after file edit. Called by Claude Code PostToolUse hook.
# Usage: ./post-edit-lint.sh <file-path>

set -euo pipefail

FILE_PATH="${1:-}"

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

EXT="${FILE_PATH##*.}"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

case "$EXT" in
  ts|tsx|js|jsx|mjs|cjs)
    # Try ESLint
    if command -v npx &>/dev/null; then
      if [ -f "$PROJECT_ROOT/eslint.config.js" ] || \
         [ -f "$PROJECT_ROOT/eslint.config.mjs" ] || \
         [ -f "$PROJECT_ROOT/.eslintrc.js" ] || \
         [ -f "$PROJECT_ROOT/.eslintrc.json" ] || \
         [ -f "$PROJECT_ROOT/.eslintrc.yml" ]; then
        npx eslint --fix "$FILE_PATH" 2>/dev/null || true
      fi
    fi

    # Try Prettier
    if command -v npx &>/dev/null; then
      if [ -f "$PROJECT_ROOT/.prettierrc" ] || \
         [ -f "$PROJECT_ROOT/.prettierrc.json" ] || \
         [ -f "$PROJECT_ROOT/prettier.config.js" ]; then
        npx prettier --write "$FILE_PATH" 2>/dev/null || true
      fi
    fi
    ;;

  py)
    # Try ruff (fast Python linter)
    if command -v ruff &>/dev/null; then
      ruff check --fix "$FILE_PATH" 2>/dev/null || true
      ruff format "$FILE_PATH" 2>/dev/null || true
    elif command -v black &>/dev/null; then
      black --quiet "$FILE_PATH" 2>/dev/null || true
    fi

    # Try isort
    if command -v isort &>/dev/null; then
      isort --quiet "$FILE_PATH" 2>/dev/null || true
    fi
    ;;

  json)
    # Format JSON with Python (always available on macOS/Linux)
    if command -v python3 &>/dev/null; then
      python3 -c "
import json, sys
try:
    with open('$FILE_PATH', 'r') as f:
        data = json.load(f)
    with open('$FILE_PATH', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
except:
    pass
" 2>/dev/null || true
    fi
    ;;

  *)
    # No linter for this extension
    ;;
esac
