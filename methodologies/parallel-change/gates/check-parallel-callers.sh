#!/usr/bin/env bash
# check-parallel-callers.sh — Block contract→done if old still has callers.
#
# Blocking gate. Runs at pre-commit. For plans in phase=contract:
#   - count callers of old.caller_pattern
#   - if > 0, block commit unless commit only modifies the plan itself
#
# This is the "last gate" before old disappears. The companion gate
# check-parallel-state.sh handles state consistency for all phases.
# This one is laser-focused on the contract→done transition specifically.

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PLANS_DIR="$PROJECT_ROOT/.harness/parallel-change/plans"

if [ ! -d "$PLANS_DIR" ]; then
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

VIOLATIONS=0
shopt -s nullglob
for plan_file in "$PLANS_DIR"/*.yaml; do
  [ -f "$plan_file" ] || continue
  pid="$(basename "$plan_file" .yaml)"

  python3 - "$plan_file" "$PROJECT_ROOT" "$pid" <<'PY'
import sys, yaml, os, subprocess

plan_file, root, pid = sys.argv[1], sys.argv[2], sys.argv[3]
with open(plan_file) as f:
    plan = yaml.safe_load(f) or {}

phase = (plan.get("phases") or {}).get("current", "")
if phase != "contract":
    sys.exit(0)

old_pat = (plan.get("old") or {}).get("caller_pattern", "")
if not old_pat:
    sys.exit(0)

cs = plan.get("caller_scan") or {}
scan_dirs = cs.get("scan_dirs") or ["src", "app", "lib", "api", "server", "frontend", "backend"]
exclude_dirs = cs.get("exclude_dirs") or [".git", "node_modules", "dist", "build", ".harness"]
targets = [os.path.join(root, d) for d in scan_dirs if os.path.isdir(os.path.join(root, d))]
if not targets:
    sys.exit(0)

have_rg = subprocess.run(["which", "rg"], capture_output=True).returncode == 0
if have_rg:
    cmd = ["rg", "-l", "-e", old_pat]
    for d in exclude_dirs: cmd += ["--glob", f"!{d}/**"]
    cmd += targets
else:
    cmd = ["grep", "-rlE"]
    for d in exclude_dirs: cmd += [f"--exclude-dir={d}"]
    cmd += ["-e", old_pat] + targets

r = subprocess.run(cmd, capture_output=True, text=True)
files = [f for f in r.stdout.strip().split("\n") if f]
if not files:
    sys.exit(0)

print(f"[parallel-change/{pid}] CONTRACT BLOCKED: old signature '{old_pat}' still has {len(files)} caller(s):")
for f in files[:10]:
    print(f"  ✗ {f}")
if len(files) > 10:
    print(f"  ... and {len(files) - 10} more")
sys.exit(1)
PY
  rc=$?
  if [ "$rc" -ne 0 ]; then
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
done

if [ "$VIOLATIONS" -gt 0 ]; then
  echo ""
  echo "[BLOCKED] $VIOLATIONS plan(s) in contract phase still have old-signature callers."
  echo "         Either migrate the remaining callers, or revert phase via:"
  echo "         (intentionally not provided — contract regression should require manual yaml edit)"
  exit 1
fi

exit 0
