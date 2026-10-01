#!/usr/bin/env bash
# PreToolUse guard for Supabase projects (Bash|Edit|Write|MultiEdit). Input: JSON on stdin.
# Deterministically blocks what must never happen, regardless of what the prompt says:
#   - writes to a remote (linked) Supabase project
#   - editing an already-created migration file
#   - reading/moving production env files
#   - bypassing git hooks
# Note: regex-based, so it cannot stop every shell trick. Pair it with /sandbox for hard guarantees.
set -uo pipefail
command -v jq >/dev/null 2>&1 || exit 0   # without jq the guard is a no-op; the git hook still runs

INPUT="$(cat)"
TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')"
PROJECT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

decide() { # $1=deny|ask  $2=reason
  jq -n --arg d "$1" --arg r "$2" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:$d,permissionDecisionReason:$r}}'
  exit 0
}

case "$TOOL" in
  Edit|Write|MultiEdit)
    FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"
    REL="${FILE#"$PROJECT"/}"
    if [[ "$REL" == supabase/migrations/*.sql && -e "$FILE" ]]; then
      decide deny "Existing migrations are immutable. Add a new one (supabase migration new <name>)."
    fi
    if [[ "$REL" == .env.production* || "$REL" == .env.remote ]]; then
      decide deny "Production/remote env files must not be modified by the agent."
    fi
    ;;
  Bash)
    CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')"
    if printf '%s' "$CMD" | grep -qE 'supabase[[:space:]]+(db[[:space:]]+push|migration[[:space:]]+repair|link|unlink|db[[:space:]]+reset[^|;&]*--linked|projects[[:space:]]+(delete|create)|branches[[:space:]]+delete)'; then
      decide deny "This writes to (or re-targets) a remote Supabase project. Run it yourself after agreeing on the rollout."
    fi
    if printf '%s' "$CMD" | grep -qE 'supabase[^|;&]*--linked'; then
      decide ask "Targets the linked remote project. Confirm it is read-only (advisors, gen types)."
    fi
    # Only when the file is the command's first non-option argument (heredoc bodies are not matched)
    if printf '%s' "$CMD" | grep -qE '(^|[;&|][[:space:]]*)(cat|source|\.|less|more|head|tail|grep|cp|mv|sed|awk)[[:space:]]+(-[A-Za-z0-9-]+[[:space:]]+)*[^[:space:]|;&<>]*\.env\.(remote|production)'; then
      decide deny "Production/remote env files must not be read or moved by the agent."
    fi
    if printf '%s' "$CMD" | grep -qE 'git[[:space:]]+(commit|push)[^|;&]*--no-verify'; then
      decide deny "Bypassing git hooks is not allowed. Fix the failing gate."
    fi
    ;;
esac
exit 0
