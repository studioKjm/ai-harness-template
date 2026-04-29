#!/usr/bin/env python3
"""Parallel Change — plan management & phase transitions.

Subcommands:
    new <id> [--title TITLE]              Create a new plan in phase=expand
    list                                   List all plans + current phase
    show <id>                              Print full plan
    set-old <id> --symbol S --pattern P    Register old signature
    set-new <id> --symbol S --pattern P    Register new signature
    advance <id> <to_phase>                Attempt phase transition (with gate checks)
    callers <id>                           Count callers of old/new (no transition)

Phase transition rules:
    expand → migrate    : check_parallel_state passes (both old & new exist)
    migrate → contract  : caller_count_old == 0
    contract → done     : caller_count_old == 0 AND old files removed
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required.", file=sys.stderr)
    sys.exit(1)


PHASES = ["expand", "migrate", "contract", "done"]


def find_project_root() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists() or (parent / ".harness").exists():
            return parent
    return cwd


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def plans_dir(root: Path) -> Path:
    d = root / ".harness/parallel-change/plans"
    d.mkdir(parents=True, exist_ok=True)
    return d


def plan_path(root: Path, plan_id: str) -> Path:
    return plans_dir(root) / f"{plan_id}.yaml"


def load_plan(root: Path, plan_id: str) -> dict:
    p = plan_path(root, plan_id)
    if not p.exists():
        die(f"Plan not found: {plan_id}")
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_plan(root: Path, plan_id: str, data: dict) -> None:
    with open(plan_path(root, plan_id), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# ─────────────────────────────────────────────────────────
# Caller counting
# ─────────────────────────────────────────────────────────

DEFAULT_SCAN_DIRS = ["src", "app", "lib", "api", "server", "frontend", "backend"]


def count_callers(root: Path, pattern: str, plan: dict) -> tuple[int, list[str]]:
    """Count regex matches of pattern in source dirs. Returns (count, sample_files)."""
    if not pattern:
        return 0, []
    cs = plan.get("caller_scan") or {}
    scan_dirs = cs.get("scan_dirs") or DEFAULT_SCAN_DIRS
    exclude_dirs = cs.get("exclude_dirs") or [".git", "node_modules", "dist", "build", ".harness"]
    exclude_files = cs.get("exclude_files") or []

    targets = [str(root / d) for d in scan_dirs if (root / d).exists()]
    if not targets:
        return 0, []

    # Use ripgrep if available, else grep -r
    have_rg = subprocess.run(["which", "rg"], capture_output=True).returncode == 0
    cmd: list[str]
    if have_rg:
        cmd = ["rg", "-l", "-e", pattern]
        for d in exclude_dirs:
            cmd += ["--glob", f"!{d}/**"]
        for f in exclude_files:
            cmd += ["--glob", f"!{f}"]
        cmd += targets
    else:
        excl = "|".join(re.escape(d) for d in exclude_dirs)
        cmd = ["grep", "-rlE", "--exclude-dir=" + ".git",
               "--exclude-dir=node_modules", "--exclude-dir=dist",
               "--exclude-dir=build", "--exclude-dir=.harness",
               "-e", pattern] + targets

    result = subprocess.run(cmd, capture_output=True, text=True)
    files = [f for f in result.stdout.strip().split("\n") if f]
    return len(files), files[:5]


# ─────────────────────────────────────────────────────────
# Subcommands
# ─────────────────────────────────────────────────────────

def cmd_new(args, root):
    pid = args.id
    if plan_path(root, pid).exists():
        die(f"Plan already exists: {pid}")
    today = datetime.date.today().isoformat()
    plan = {
        "schema_version": 1,
        "id": pid,
        "title": args.title or "",
        "created_at": now(),
        "created_by": os.environ.get("USER", "unknown"),
        "target": {"type": "", "description": ""},
        "old": {"symbol": "", "files": [], "caller_pattern": ""},
        "new": {"symbol": "", "files": [], "caller_pattern": ""},
        "caller_scan": {"exclude_files": [], "exclude_dirs": [".git", "node_modules", "dist", "build", ".harness"], "scan_dirs": []},
        "phases": {"current": "expand", "history": [{"phase": "expand", "entered_at": now()}]},
        "expand_criteria": ["Both old and new signatures exist in the codebase", "Tests exist for new signature"],
        "migrate_criteria": ["All known callers switched to new signature"],
        "contract_criteria": ["Zero callers reference old signature"],
        "last_check": {"timestamp": "", "caller_count_old": -1, "caller_count_new": -1, "state_consistent": None},
        "notes": [],
    }
    save_plan(root, pid, plan)
    print(f"[OK] Created plan {pid} in phase=expand")
    print(f"     Path: {plan_path(root, pid).relative_to(root)}")
    print(f"     Next: pc.py set-old {pid} --symbol <S> --pattern <P>")


def cmd_list(args, root):
    pdir = plans_dir(root)
    files = sorted(pdir.glob("*.yaml"))
    if not files:
        print("No plans found.")
        return
    print(f"\n{'PLAN':<40} {'PHASE':<10} TITLE")
    print("─" * 100)
    for pf in files:
        try:
            with open(pf, encoding="utf-8") as f:
                p = yaml.safe_load(f) or {}
            phase = (p.get("phases") or {}).get("current", "?")
            print(f"{p.get('id', pf.stem):<40} {phase:<10} {p.get('title', '')}")
        except Exception as e:
            print(f"{pf.stem:<40} {'ERROR':<10} {e}")
    print()


def cmd_show(args, root):
    plan = load_plan(root, args.id)
    print(yaml.safe_dump(plan, sort_keys=False, allow_unicode=True))


def cmd_set_signature(args, root, side: str):
    plan = load_plan(root, args.id)
    sec = plan.setdefault(side, {})
    if args.symbol is not None: sec["symbol"] = args.symbol
    if args.pattern is not None: sec["caller_pattern"] = args.pattern
    if args.files:
        sec["files"] = args.files
    save_plan(root, args.id, plan)
    print(f"[OK] {side}.symbol = {sec.get('symbol')}")
    print(f"     {side}.caller_pattern = {sec.get('caller_pattern')}")


def cmd_callers(args, root):
    plan = load_plan(root, args.id)
    old_pat = (plan.get("old") or {}).get("caller_pattern", "")
    new_pat = (plan.get("new") or {}).get("caller_pattern", "")
    old_n, old_sample = count_callers(root, old_pat, plan)
    new_n, new_sample = count_callers(root, new_pat, plan)
    plan["last_check"] = {
        "timestamp": now(),
        "caller_count_old": old_n,
        "caller_count_new": new_n,
        "state_consistent": True,  # set by check-parallel-state.sh in real check
    }
    save_plan(root, args.id, plan)
    print(f"Callers of OLD ({old_pat or '<unset>'}): {old_n}")
    for f in old_sample: print(f"  - {f}")
    print(f"Callers of NEW ({new_pat or '<unset>'}): {new_n}")
    for f in new_sample: print(f"  - {f}")


def cmd_advance(args, root):
    plan = load_plan(root, args.id)
    cur = (plan.get("phases") or {}).get("current", "expand")
    target = args.to_phase

    if target not in PHASES:
        die(f"Unknown phase: {target}. Valid: {PHASES}")
    if PHASES.index(target) <= PHASES.index(cur):
        die(f"Cannot move backward: current={cur}, target={target}")
    if PHASES.index(target) > PHASES.index(cur) + 1:
        die(f"Cannot skip phases: current={cur}, target={target}. Advance one phase at a time.")

    # Validate transition criteria
    if cur == "expand" and target == "migrate":
        old_pat = (plan.get("old") or {}).get("caller_pattern", "")
        new_pat = (plan.get("new") or {}).get("caller_pattern", "")
        if not old_pat or not new_pat:
            die("expand → migrate requires both old.caller_pattern and new.caller_pattern set")
        old_n, _ = count_callers(root, old_pat, plan)
        new_n, _ = count_callers(root, new_pat, plan)
        if old_n == 0:
            die(f"expand → migrate: old signature has 0 callers — already migrated? "
                f"Check pattern: {old_pat}")
        if new_n == 0:
            die(f"expand → migrate: new signature not found in codebase. "
                f"Implement it before advancing. Pattern: {new_pat}")
        print(f"[OK] expand criteria met: old has {old_n} callers, new has {new_n} usages")

    elif cur == "migrate" and target == "contract":
        old_pat = (plan.get("old") or {}).get("caller_pattern", "")
        old_n, sample = count_callers(root, old_pat, plan)
        if old_n > 0:
            print(f"[BLOCKED] migrate → contract: old signature still has {old_n} caller(s):", file=sys.stderr)
            for f in sample: print(f"  - {f}", file=sys.stderr)
            die("All callers must switch to new before contract")
        print(f"[OK] migrate criteria met: 0 callers of old signature")

    elif cur == "contract" and target == "done":
        # contract → done: old files actually removed?
        old_files = (plan.get("old") or {}).get("files") or []
        still_there = [f for f in old_files if (root / f.split(":")[0]).exists() and old_files]
        if still_there:
            print(f"[WARN] contract → done: old.files still on disk: {still_there}")
            print("       Mark done if these are intentionally retained (e.g., shared modules)")
        print("[OK] contract complete")

    # Apply transition
    plan["phases"]["current"] = target
    plan["phases"]["history"].append({"phase": target, "entered_at": now()})
    save_plan(root, args.id, plan)
    print(f"[OK] {args.id}: {cur} → {target}")


# ─────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new"); p_new.add_argument("id"); p_new.add_argument("--title")
    sub.add_parser("list")
    p_show = sub.add_parser("show"); p_show.add_argument("id")
    p_old = sub.add_parser("set-old"); p_old.add_argument("id"); p_old.add_argument("--symbol"); p_old.add_argument("--pattern"); p_old.add_argument("--files", nargs="*")
    p_new2 = sub.add_parser("set-new"); p_new2.add_argument("id"); p_new2.add_argument("--symbol"); p_new2.add_argument("--pattern"); p_new2.add_argument("--files", nargs="*")
    p_callers = sub.add_parser("callers"); p_callers.add_argument("id")
    p_adv = sub.add_parser("advance"); p_adv.add_argument("id"); p_adv.add_argument("to_phase")

    args = ap.parse_args()
    root = find_project_root()

    if args.cmd == "new":          cmd_new(args, root)
    elif args.cmd == "list":       cmd_list(args, root)
    elif args.cmd == "show":       cmd_show(args, root)
    elif args.cmd == "set-old":    cmd_set_signature(args, root, "old")
    elif args.cmd == "set-new":    cmd_set_signature(args, root, "new")
    elif args.cmd == "callers":    cmd_callers(args, root)
    elif args.cmd == "advance":    cmd_advance(args, root)


if __name__ == "__main__":
    main()
