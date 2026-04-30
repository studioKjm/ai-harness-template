#!/usr/bin/env bash
# check-test-first.sh — Block commits where source precedes test in git history
# Severity: blocking | runs_on: pre-commit
set -euo pipefail

HARNESS_DIR="${HARNESS_DIR:-.harness}"
CONFIG_FILE="$HARNESS_DIR/tdd-strict/config.yaml"
ERRORS=()
WARNINGS=()

# ── helpers ────────────────────────────────────────────────────────────────────

red()    { echo -e "\033[0;31m$*\033[0m" >&2; }
yellow() { echo -e "\033[0;33m$*\033[0m" >&2; }
green()  { echo -e "\033[0;32m$*\033[0m" >&2; }

# Read yaml field (simple single-value extraction)
yaml_field() { grep -m1 "^${1}:" "$2" 2>/dev/null | sed 's/^[^:]*:[[:space:]]*//' | tr -d '"'; }

# ── commit message exemption check ─────────────────────────────────────────────

COMMIT_MSG=""
if [[ -f ".git/COMMIT_EDITMSG" ]]; then
  COMMIT_MSG=$(head -1 .git/COMMIT_EDITMSG)
fi

EXEMPT_PREFIXES=("[refactor]" "[chore]" "[docs]" "[style]" "[ci]" "[infra]")

# Load custom prefixes from config if available
if [[ -f "$CONFIG_FILE" ]]; then
  while IFS= read -r line; do
    prefix=$(echo "$line" | sed 's/^[[:space:]]*-[[:space:]]*//' | tr -d '"')
    [[ -n "$prefix" ]] && EXEMPT_PREFIXES+=("$prefix")
  done < <(grep -A20 "^  prefixes:" "$CONFIG_FILE" 2>/dev/null | grep "^    -" || true)
fi

for prefix in "${EXEMPT_PREFIXES[@]}"; do
  if [[ "$COMMIT_MSG" == "$prefix"* ]]; then
    green "[tdd-strict] Commit exempt (prefix: $prefix). Skipping test-first check."
    exit 0
  fi
done

# ── staged files ────────────────────────────────────────────────────────────────

STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
if [[ -z "$STAGED" ]]; then
  exit 0
fi

# ── exempt directories / patterns ──────────────────────────────────────────────

EXEMPT_DIRS=(
  "migrations/" "scripts/" "config/" "docs/"
  "__generated__/" "vendor/" "node_modules/" ".harness/"
)

EXEMPT_PATTERNS=(
  "*.d.ts" "*.min.js" "index.ts" "index.js"
  "types.ts" "constants.ts"
)

# Load from config if available
if [[ -f "$CONFIG_FILE" ]]; then
  while IFS= read -r line; do
    dir=$(echo "$line" | sed 's/^[[:space:]]*-[[:space:]]*//' | tr -d '"')
    [[ -n "$dir" ]] && EXEMPT_DIRS+=("$dir")
  done < <(grep -A30 "^  exempt_dirs:" "$CONFIG_FILE" 2>/dev/null | grep "^    -" || true)

  while IFS= read -r line; do
    pat=$(echo "$line" | sed 's/^[[:space:]]*-[[:space:]]*//' | tr -d '"')
    [[ -n "$pat" ]] && EXEMPT_PATTERNS+=("$pat")
  done < <(grep -A30 "^  exempt_patterns:" "$CONFIG_FILE" 2>/dev/null | grep "^    -" || true)
fi

is_exempt() {
  local file="$1"
  for dir in "${EXEMPT_DIRS[@]}"; do
    [[ "$file" == "$dir"* ]] && return 0
  done
  local basename; basename=$(basename "$file")
  for pat in "${EXEMPT_PATTERNS[@]}"; do
    # shellcheck disable=SC2053
    [[ "$basename" == $pat ]] && return 0
  done
  return 1
}

# ── test file detection ─────────────────────────────────────────────────────────

is_test_file() {
  local file="$1"
  [[ "$file" =~ \.(test|spec)\.(ts|js|py|go|rb|java|kt|swift|rs|cpp|c)$ ]] && return 0
  [[ "$file" =~ /(test|spec|tests|__tests__|__spec__)/ ]] && return 0
  [[ "$file" =~ _test\.(go|py|rb)$ ]] && return 0
  [[ "$file" =~ Test\.(java|kt)$ ]] && return 0
  [[ "$file" =~ _spec\.rb$ ]] && return 0
  return 1
}

# ── source → test file mapping ──────────────────────────────────────────────────

find_test_file() {
  local src="$1"
  local dir; dir=$(dirname "$src")
  local base; base=$(basename "$src")
  local ext="${base##*.}"
  local stem="${base%.*}"

  # Language-specific conventions
  case "$ext" in
    ts|js|tsx|jsx)
      # Same dir: foo.test.ts, foo.spec.ts
      for test_path in \
        "$dir/$stem.test.$ext" \
        "$dir/$stem.spec.$ext" \
        "$dir/__tests__/$stem.test.$ext" \
        "$dir/__tests__/$stem.spec.$ext"; do
        git log --oneline -- "$test_path" 2>/dev/null | head -1 | grep -q . && echo "$test_path" && return 0
      done
      ;;
    py)
      # tests/test_foo.py or tests/foo_test.py
      for test_path in \
        "tests/test_$stem.py" \
        "tests/${stem}_test.py" \
        "$(echo "$dir" | sed 's|^src|tests|')/test_$stem.py"; do
        git log --oneline -- "$test_path" 2>/dev/null | head -1 | grep -q . && echo "$test_path" && return 0
      done
      ;;
    go)
      echo "${src%.go}_test.go" && return 0
      ;;
    rb)
      local spec_path; spec_path=$(echo "$src" | sed 's|^lib/|spec/|; s|\.rb$|_spec.rb|')
      echo "$spec_path" && return 0
      ;;
    java|kt)
      local test_path; test_path=$(echo "$src" | sed 's|src/main|src/test|; s|\.java$|Test.java|; s|\.kt$|Test.kt|')
      echo "$test_path" && return 0
      ;;
  esac
  return 1
}

# ── git history commit order check ─────────────────────────────────────────────

ALLOW_SAME_COMMIT=false
if [[ -f "$CONFIG_FILE" ]]; then
  val=$(yaml_field "allow_same_commit" "$CONFIG_FILE")
  [[ "$val" == "true" ]] && ALLOW_SAME_COMMIT=true
fi

HISTORY_DEPTH=100
if [[ -f "$CONFIG_FILE" ]]; then
  depth=$(yaml_field "history_depth" "$CONFIG_FILE")
  [[ "$depth" =~ ^[0-9]+$ ]] && HISTORY_DEPTH="$depth"
fi

source_before_test() {
  local src="$1"
  local test_file="$2"

  # Commit introducing source file
  local src_sha; src_sha=$(git log --diff-filter=A --format="%H" -1 -- "$src" 2>/dev/null || true)
  # Commit introducing test file
  local test_sha; test_sha=$(git log --diff-filter=A --format="%H" -1 -- "$test_file" 2>/dev/null || true)

  # Test file doesn't exist in git yet — violation (test must come first)
  if [[ -z "$test_sha" ]]; then
    return 0  # source before test
  fi

  # Source file not yet committed (staged new) — check test exists
  if [[ -z "$src_sha" ]]; then
    return 1  # new file being committed, test already in history — OK
  fi

  # Both exist — compare commit timestamps
  local src_ts; src_ts=$(git show -s --format="%ct" "$src_sha" 2>/dev/null || echo 0)
  local test_ts; test_ts=$(git show -s --format="%ct" "$test_sha" 2>/dev/null || echo 0)

  if [[ "$ALLOW_SAME_COMMIT" == "true" ]]; then
    (( src_ts < test_ts )) && return 0
  else
    (( src_ts <= test_ts )) && return 0
  fi
  return 1
}

# ── main loop ──────────────────────────────────────────────────────────────────

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  is_exempt "$file" && continue
  is_test_file "$file" && continue  # test files themselves are always OK

  test_file=$(find_test_file "$file" 2>/dev/null || true)
  if [[ -z "$test_file" ]]; then
    # Cannot determine test pairing — warn but don't block
    WARNINGS+=("$file: no test file mapping found (add convention to tdd-config.yaml)")
    continue
  fi

  if source_before_test "$file" "$test_file"; then
    ERRORS+=("$file: source committed before test ($test_file). Write the test first.")
  fi
done <<< "$STAGED"

# ── output ────────────────────────────────────────────────────────────────────

if [[ ${#WARNINGS[@]} -gt 0 ]]; then
  yellow "[tdd-strict] WARNINGS:"
  for w in "${WARNINGS[@]}"; do yellow "  ⚠ $w"; done
fi

if [[ ${#ERRORS[@]} -gt 0 ]]; then
  red ""
  red "[tdd-strict] BLOCKED — Test-first violations:"
  for e in "${ERRORS[@]}"; do red "  ✗ $e"; done
  red ""
  red "  Red → Green → Refactor: write the failing test BEFORE the source."
  red "  Exempt commit? Prefix message with [refactor] / [chore] / [docs] / [ci]."
  red "  Configure exemptions: .harness/tdd-strict/config.yaml"
  exit 1
fi

green "[tdd-strict] OK — test-first order verified."
exit 0
