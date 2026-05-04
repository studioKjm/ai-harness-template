#!/usr/bin/env bash
# Opt-in gate: warns when a diff touches too many files, suggesting scope creep.
# Surgical Changes principle derived from Andrej Karpathy's LLM coding observations.
# Ref: https://github.com/forrestchang/andrej-karpathy-skills
#
# Enable: export HARNESS_ENABLE_SURGICAL_CHANGES=1
# Tune:   export SURGICAL_CHANGES_MAX_FILES=20  (default: 15)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/../lib/colors.sh" ]; then
  source "$SCRIPT_DIR/../lib/colors.sh"
elif [ -f "$SCRIPT_DIR/../../.harness/lib/colors.sh" ]; then
  source "$SCRIPT_DIR/../../.harness/lib/colors.sh"
else
  success() { echo "[OK] $*"; }
  warn()    { echo "[WARN] $*"; }
  error()   { echo "[ERROR] $*"; }
  header()  { echo "=== $* ==="; }
fi

header "Surgical Changes Check"
echo ""

if [[ "${HARNESS_ENABLE_SURGICAL_CHANGES:-0}" != "1" ]]; then
  echo "  (skipped — set HARNESS_ENABLE_SURGICAL_CHANGES=1 to enable)"
  exit 0
fi

MAX_FILES="${SURGICAL_CHANGES_MAX_FILES:-15}"

# Prefer staged diff; fall back to last commit vs HEAD~1
if ! git diff --cached --quiet 2>/dev/null; then
  CHANGED_FILES=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
  SCOPE="staged"
else
  CHANGED_FILES=$(git diff HEAD~1..HEAD --name-only 2>/dev/null | wc -l | tr -d ' ')
  SCOPE="last commit"
fi

echo "  Changed files (${SCOPE}): ${CHANGED_FILES} / ${MAX_FILES} limit"
echo ""

if [[ "$CHANGED_FILES" -gt "$MAX_FILES" ]]; then
  warn "Surgical Changes: ${CHANGED_FILES} files changed (threshold: ${MAX_FILES})"
  echo ""
  echo "  Review that every changed file traces directly to the request."
  echo "  Common causes:"
  echo "    - Drive-by refactoring of unrelated code"
  echo "    - Auto-formatting applied to untouched files"
  echo "    - Dead code cleanup beyond the task scope"
  echo ""
  echo "  Adjust threshold: export SURGICAL_CHANGES_MAX_FILES=N"
  exit 1
fi

success "Surgical Changes: ${CHANGED_FILES} files changed (within limit of ${MAX_FILES})"
exit 0
