#!/usr/bin/env bash
# Gate: check-scenario-coverage.sh (warning — non-blocking)
# Warns when a new feature-like file is committed without a corresponding BDD scenario.
#
# Heuristic: if a staged file creates/modifies a "feature" module (src/features/*, app/features/*)
# and no scenario YAML references it, print a warning.

set -euo pipefail

SCENARIOS_DIR=".harness/bdd/scenarios"

# If no scenarios directory yet, skip
if [[ ! -d "${SCENARIOS_DIR}" ]]; then
    exit 0
fi

# Only check staged files
if ! git rev-parse --git-dir &>/dev/null; then
    exit 0
fi

STAGED=$(git diff --cached --name-only --diff-filter=A 2>/dev/null || true)
if [[ -z "${STAGED}" ]]; then
    exit 0
fi

WARNINGS=0

for file in ${STAGED}; do
    # Only flag new feature-like files (heuristic: contains "feature" or "use-case" in path)
    if echo "${file}" | grep -qiE '(features?|use.?cases?|handlers?)/[^/]+\.(ts|tsx|js|py|rb|go)$'; then
        # Check if any scenario references this file
        if [[ -d "${SCENARIOS_DIR}" ]]; then
            if ! grep -r "${file}" "${SCENARIOS_DIR}"/*.yaml &>/dev/null 2>&1; then
                echo "⚠️  [bdd] No scenario covers new feature file: ${file}"
                WARNINGS=$((WARNINGS + 1))
            fi
        fi
    fi
done

if [[ ${WARNINGS} -gt 0 ]]; then
    echo ""
    echo "  Consider adding BDD scenarios with: /bdd new '<title>' --feature <feature-id>"
    echo "  This is a warning — commit is not blocked."
fi

exit 0
