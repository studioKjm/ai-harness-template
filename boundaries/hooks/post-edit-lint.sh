#!/usr/bin/env bash
# Auto-lint after file edit. Called by Claude Code PostToolUse hook.
# Input: Claude Code passes hook input as JSON on stdin (tool_input.file_path).
#        The legacy $CLAUDE_FILE_PATH variable is not documented anymore.
# Usage: echo '{"tool_input":{"file_path":"..."}}' | ./post-edit-lint.sh
#        ./post-edit-lint.sh <file-path>            (manual / backward compatible)

set -euo pipefail

FILE_PATH="${1:-}"
if [ -z "$FILE_PATH" ] && [ ! -t 0 ]; then
  STDIN_JSON="$(cat || true)"
  if command -v jq &>/dev/null; then
    FILE_PATH="$(printf '%s' "$STDIN_JSON" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"
  elif command -v python3 &>/dev/null; then
    FILE_PATH="$(printf '%s' "$STDIN_JSON" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))
except Exception: pass' 2>/dev/null || true)"
  fi
fi

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
    # Pass path via argv to avoid string-interpolation injection on special chars
    if command -v python3 &>/dev/null; then
      python3 -c '
import json, sys
path = sys.argv[1]
try:
    with open(path, "r") as f:
        data = json.load(f)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
except Exception:
    pass
' "$FILE_PATH" 2>/dev/null || true
    fi
    ;;

  *)
    # No linter for this extension
    ;;
esac
