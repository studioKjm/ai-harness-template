#!/usr/bin/env bash
# Gate: check-context-boundary.sh
# Detects imports that cross Bounded Context boundaries.
# A file inside context A must not directly import from context B's internals.
# Only public_api paths are allowed for cross-context references.
#
# Requires: .harness/ddd-lite/contexts/*.yaml to define path mappings.

set -euo pipefail

HARNESS_DIR=".harness/ddd-lite"
CONTEXTS_DIR="${HARNESS_DIR}/contexts"
ERRORS=0

# If no contexts are defined yet, skip (gate is opt-in until contexts are defined)
if [[ ! -d "${CONTEXTS_DIR}" ]] || [[ -z "$(ls "${CONTEXTS_DIR}"/*.yaml 2>/dev/null)" ]]; then
    exit 0
fi

# Load staged files (or all files if run manually)
if git rev-parse --git-dir &>/dev/null; then
    STAGED=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)
else
    STAGED=$(find . -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.py" \) | sed 's|^\./||')
fi

if [[ -z "${STAGED}" ]]; then
    exit 0
fi

# Build context path map from YAML files
declare -A CTX_PATHS  # context_id -> space-separated path globs
declare -A CTX_NAMES

if command -v python3 &>/dev/null; then
    # Use Python to parse YAML context files
    CTX_MAP=$(python3 - "${CONTEXTS_DIR}" <<'PYEOF'
import sys, os, yaml, json

ctx_dir = sys.argv[1]
result = {}
for fname in os.listdir(ctx_dir):
    if not fname.endswith('.yaml'):
        continue
    with open(os.path.join(ctx_dir, fname)) as f:
        d = yaml.safe_load(f) or {}
    ctx_id = d.get('context_id', '')
    paths = d.get('paths') or []
    if ctx_id and paths:
        result[ctx_id] = paths
print(json.dumps(result))
PYEOF
)
    if [[ -z "${CTX_MAP}" ]] || [[ "${CTX_MAP}" == "{}" ]]; then
        # No paths configured yet — gate is advisory until paths are set
        exit 0
    fi
else
    # No Python — skip gate
    exit 0
fi

# For each staged file, determine which context it belongs to
# Then check if any imports reference paths inside other contexts (non-public paths)
VIOLATIONS=$(python3 - "${CTX_MAP}" ${STAGED} <<'PYEOF'
import sys, json, re

ctx_map = json.loads(sys.argv[1])
files = sys.argv[2:]

def match_glob(path, glob_pattern):
    """Simple glob matching (supports ** and *)"""
    import fnmatch
    pattern = glob_pattern.rstrip('/').rstrip('*')
    return path.startswith(pattern.replace('**', '').replace('*', ''))

def find_context(filepath, ctx_map):
    for ctx_id, paths in ctx_map.items():
        for p in paths:
            if match_glob(filepath, p):
                return ctx_id
    return None

violations = []
import_patterns = [
    re.compile(r'''(?:import|from)\s+['"]([^'"]+)['"]'''),  # JS/TS
    re.compile(r'''(?:^|\s)from\s+(\S+)\s+import'''),        # Python
    re.compile(r'''(?:^|\s)import\s+(\S+)'''),               # Python
]

for filepath in files:
    if not filepath.endswith(('.ts', '.tsx', '.js', '.py')):
        continue
    src_ctx = find_context(filepath, ctx_map)
    if not src_ctx:
        continue  # file not in any known context

    try:
        with open(filepath, 'r', errors='replace') as f:
            content = f.read()
    except FileNotFoundError:
        continue

    for line_num, line in enumerate(content.splitlines(), 1):
        for pat in import_patterns:
            m = pat.search(line)
            if not m:
                continue
            imported_path = m.group(1)
            # Normalize relative imports — skip external packages
            if imported_path.startswith('.'):
                # Resolve relative path
                import os
                base = os.path.dirname(filepath)
                resolved = os.path.normpath(os.path.join(base, imported_path))
            else:
                continue  # external package, skip

            # Check if resolved path belongs to a different context
            tgt_ctx = find_context(resolved, ctx_map)
            if tgt_ctx and tgt_ctx != src_ctx:
                violations.append(f"{filepath}:{line_num}: [{src_ctx}] imports from [{tgt_ctx}]: {imported_path}")

for v in violations:
    print(v)
PYEOF
)

if [[ -n "${VIOLATIONS}" ]]; then
    echo "❌ [ddd-lite] Bounded Context boundary violation detected:"
    echo ""
    echo "${VIOLATIONS}" | while IFS= read -r line; do
        echo "  ${line}"
    done
    echo ""
    echo "  Cross-context access must go through the public_api defined in the context manifest."
    echo "  See .harness/ddd-lite/contexts/ for boundary definitions."
    exit 1
fi

exit 0
