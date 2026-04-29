#!/usr/bin/env bash
# check-spec-drift.sh — Warn when code references entities not present in current seed.
#
# Living Spec gate (severity: warning, not blocking).
# Scans source files for entity names and flags any that don't appear in
# the latest seed-v*.yaml.
#
# Heuristic: looks for camelcase identifiers in code matching entity names
# from seed.ontology.entities[].name. False-positive prone — that's why
# severity is warning, not blocking.

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SEEDS_DIR="$PROJECT_ROOT/.harness/ouroboros/seeds"

# No seeds → nothing to check
if [ ! -d "$SEEDS_DIR" ]; then
  exit 0
fi

# Find latest seed
LATEST_SEED="$(ls "$SEEDS_DIR"/seed-v*.yaml 2>/dev/null | sort -V | tail -1)"
if [ -z "$LATEST_SEED" ]; then
  exit 0
fi

# Need python3 to parse YAML
if ! command -v python3 >/dev/null 2>&1; then
  echo "[check-spec-drift] python3 not found — skipping" >&2
  exit 0
fi

# Extract entity names from latest seed
ENTITY_NAMES="$(python3 -c "
import yaml, sys
with open('$LATEST_SEED') as f:
    data = yaml.safe_load(f) or {}
ents = (data.get('ontology') or {}).get('entities') or []
for e in ents:
    n = e.get('name')
    if n: print(n)
" 2>/dev/null || echo "")"

if [ -z "$ENTITY_NAMES" ]; then
  exit 0  # no entities defined → nothing to drift from
fi

# Scan source files for entity-like usage that doesn't match any seed entity
# Limit scope to common source dirs and small extensions for speed
SCAN_DIRS=()
for d in src app lib api server frontend backend; do
  [ -d "$PROJECT_ROOT/$d" ] && SCAN_DIRS+=("$PROJECT_ROOT/$d")
done

if [ "${#SCAN_DIRS[@]}" -eq 0 ]; then
  exit 0
fi

# Collect identifiers that LOOK LIKE entities (PascalCase, 4+ chars, used as types/classes)
# This is heuristic — meant to flag obvious cases like new model names
SUSPECTS=$(grep -rhEo --include='*.ts' --include='*.tsx' --include='*.py' --include='*.js' \
  '\b[A-Z][a-zA-Z0-9]{3,}\b' "${SCAN_DIRS[@]}" 2>/dev/null \
  | sort -u || echo "")

if [ -z "$SUSPECTS" ]; then
  exit 0
fi

# Filter — known seed entities are OK; everything else MIGHT be drift
DRIFT_FOUND=0
WARN_LIMIT=10
warned=0

while IFS= read -r ident; do
  [ -z "$ident" ] && continue
  if echo "$ENTITY_NAMES" | grep -qx "$ident"; then
    continue  # known entity — OK
  fi
  # Skip very common non-entity PascalCase (frameworks, types)
  case "$ident" in
    React|Component|Props|State|String|Number|Boolean|Array|Object|Promise|Error|Math|Date|JSON|Map|Set|HTMLElement|Event|Request|Response|App|Component|Module|Class|Function|Type|Interface|Enum|TypeScript|JavaScript|Python|Test|Tests|Setup|Config|Logger|Utils)
      continue
      ;;
  esac
done <<< "$SUSPECTS"

# v0.1: best-effort scan only. Don't actually emit warnings yet — too noisy.
# Once stable, this gate will warn on truly novel PascalCase identifiers
# that appear in code but not in seed.
#
# To enable verbose output: HARNESS_SPEC_DRIFT_VERBOSE=1 ./check-spec-drift.sh
if [ "${HARNESS_SPEC_DRIFT_VERBOSE:-0}" = "1" ]; then
  echo "[check-spec-drift] scanned ${#SCAN_DIRS[@]} dirs against $LATEST_SEED"
  echo "[check-spec-drift] entities tracked: $(echo "$ENTITY_NAMES" | wc -l | tr -d ' ')"
fi

exit 0
