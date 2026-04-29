#!/usr/bin/env bash
# check-parallel-state.sh — Enforce parallel-change phase state machine.
#
# Blocking gate. Runs at pre-commit. For each active plan:
#   - phase=expand  : both old.caller_pattern and new.caller_pattern must match in code
#   - phase=migrate : both still match (transition out happens via /contract)
#   - phase=contract: new must match; old must NOT match (zero callers)
#   - phase=done    : skip
#
# Exit:
#   0 — all plans consistent
#   1 — at least one plan in inconsistent state

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PLANS_DIR="$PROJECT_ROOT/.harness/parallel-change/plans"

if [ ! -d "$PLANS_DIR" ]; then
  exit 0  # no plans → no enforcement
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[check-parallel-state] python3 not found — skipping" >&2
  exit 0
fi

VIOLATIONS=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PC_SCRIPT="$SCRIPT_DIR/../scripts/pc.py"
[ -f "$PC_SCRIPT" ] || PC_SCRIPT="$PROJECT_ROOT/.harness/methodologies/parallel-change/scripts/pc.py"

if [ ! -f "$PC_SCRIPT" ]; then
  echo "[check-parallel-state] pc.py not found — skipping" >&2
  exit 0
fi

shopt -s nullglob
for plan_file in "$PLANS_DIR"/*.yaml; do
  [ -f "$plan_file" ] || continue
  pid="$(basename "$plan_file" .yaml)"

  result="$(python3 - "$plan_file" "$PROJECT_ROOT" <<'PY'
import sys, yaml, subprocess, os, re

plan_file, root = sys.argv[1], sys.argv[2]
with open(plan_file) as f:
    plan = yaml.safe_load(f) or {}

phase = (plan.get("phases") or {}).get("current", "expand")
old_pat = (plan.get("old") or {}).get("caller_pattern", "")
new_pat = (plan.get("new") or {}).get("caller_pattern", "")

if phase == "done":
    print("OK"); sys.exit(0)

cs = plan.get("caller_scan") or {}
scan_dirs = cs.get("scan_dirs") or ["src", "app", "lib", "api", "server", "frontend", "backend"]
exclude_dirs = cs.get("exclude_dirs") or [".git", "node_modules", "dist", "build", ".harness"]

targets = [os.path.join(root, d) for d in scan_dirs if os.path.isdir(os.path.join(root, d))]
if not targets:
    print("OK"); sys.exit(0)

def count(pattern):
    if not pattern: return 0
    have_rg = subprocess.run(["which", "rg"], capture_output=True).returncode == 0
    if have_rg:
        cmd = ["rg", "-l", "-e", pattern]
        for d in exclude_dirs: cmd += ["--glob", f"!{d}/**"]
        cmd += targets
    else:
        cmd = ["grep", "-rlE"]
        for d in exclude_dirs: cmd += [f"--exclude-dir={d}"]
        cmd += ["-e", pattern] + targets
    r = subprocess.run(cmd, capture_output=True, text=True)
    return len([f for f in r.stdout.strip().split("\n") if f])

old_n = count(old_pat)
new_n = count(new_pat)

errors = []
if phase == "expand":
    if old_n == 0:
        errors.append(f"expand: OLD pattern '{old_pat}' has 0 matches — was old removed already?")
    if new_n == 0:
        errors.append(f"expand: NEW pattern '{new_pat}' has 0 matches — implement new alongside old")
elif phase == "migrate":
    if old_n == 0 and new_n > 0:
        errors.append(f"migrate: OLD has 0 callers — advance to /contract instead of staying in migrate")
    if new_n == 0:
        errors.append(f"migrate: NEW pattern '{new_pat}' has 0 matches — should still exist")
elif phase == "contract":
    if old_n > 0:
        errors.append(f"contract: OLD pattern '{old_pat}' still has {old_n} caller(s) — cannot remove yet")
    if new_n == 0:
        errors.append(f"contract: NEW pattern '{new_pat}' has 0 matches — new disappeared?")

if errors:
    print("FAIL")
    for e in errors: print(e)
else:
    print("OK")
PY
  )"

  status="$(echo "$result" | head -1)"
  if [ "$status" != "OK" ]; then
    echo ""
    echo "[parallel-change] Plan '$pid' in inconsistent state:"
    echo "$result" | tail -n +2 | sed 's/^/  ✗ /'
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
done

if [ "$VIOLATIONS" -gt 0 ]; then
  echo ""
  echo "[BLOCKED] $VIOLATIONS parallel-change plan(s) in inconsistent state."
  echo "         Fix the plan or advance phase via:"
  echo "         python3 .harness/methodologies/parallel-change/scripts/pc.py advance <id> <next-phase>"
  exit 1
fi

exit 0
