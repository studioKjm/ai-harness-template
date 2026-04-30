#!/usr/bin/env python3
"""tdd-strict CLI — manage TDD cycles (Red → Green → Refactor → Done)."""
import argparse
import sys
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import yaml

HARNESS_DIR = Path(os.environ.get("HARNESS_DIR", ".harness"))
CYCLES_DIR = HARNESS_DIR / "tdd-strict" / "cycles"
CONFIG_FILE = HARNESS_DIR / "tdd-strict" / "config.yaml"
STATE_FILE = HARNESS_DIR / "state" / "tdd-strict.yaml"

# ── State machine ──────────────────────────────────────────────────────────────

TRANSITIONS = {
    "red":      {"pass": "green", "abandon": "abandoned"},
    "green":    {"refactor": "refactor", "done": "done", "abandon": "abandoned"},
    "refactor": {"done": "done", "abandon": "abandoned"},
}

TERMINAL = {"done", "abandoned"}

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def cycle_path(cycle_id: str) -> Path:
    return CYCLES_DIR / f"{cycle_id}.yaml"

def load_cycle(cycle_id: str) -> dict:
    p = cycle_path(cycle_id)
    if not p.exists():
        print(f"Error: cycle '{cycle_id}' not found at {p}", file=sys.stderr)
        sys.exit(1)
    return yaml.safe_load(p.read_text())

def save_cycle(path: Path, data: dict):
    data["updated_at"] = now_iso()
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))

def transition(cycle_id: str, action: str, updates: dict | None = None) -> dict:
    p = cycle_path(cycle_id)
    data = load_cycle(cycle_id)
    current = data["state"]

    if current in TERMINAL:
        print(f"Error: cycle '{cycle_id}' is already in terminal state '{current}'", file=sys.stderr)
        sys.exit(1)

    allowed = TRANSITIONS.get(current, {})
    if action not in allowed:
        valid = list(allowed.keys())
        print(f"Error: cannot '{action}' from state '{current}'. Valid: {valid}", file=sys.stderr)
        sys.exit(1)

    data["state"] = allowed[action]
    if updates:
        for k, v in updates.items():
            if "." in k:
                parts = k.split(".", 1)
                data.setdefault(parts[0], {})[parts[1]] = v
            else:
                data[k] = v
    save_cycle(p, data)
    return data

def gen_cycle_id() -> str:
    ts = datetime.now().strftime("%Y%m%d")
    existing = sorted(CYCLES_DIR.glob(f"tdd-{ts}-*.yaml")) if CYCLES_DIR.exists() else []
    idx = len(existing) + 1
    return f"tdd-{ts}-{idx:03d}"

def current_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return ""

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_new(args):
    """Create a new TDD cycle in 'red' state."""
    CYCLES_DIR.mkdir(parents=True, exist_ok=True)
    cycle_id = gen_cycle_id()
    p = cycle_path(cycle_id)

    data = {
        "cycle_id": cycle_id,
        "target": " ".join(args.target),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "state": "red",
        "files": {"test": args.test or "", "source": args.source or ""},
        "git": {"test_commit": "", "green_commit": "", "refactor_commit": ""},
        "notes": {
            "hypothesis": args.hypothesis or "",
            "red_criteria": "",
            "green_criteria": "",
            "refactor_notes": "",
        },
        "links": {"story_id": args.story or "", "spike_id": ""},
    }
    p.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))
    print(f"✓ TDD cycle created: {cycle_id}")
    print(f"  State: 🔴 red")
    print(f"  Target: {data['target']}")
    print(f"  Next: Write the failing test first, then commit.")
    print(f"        When tests pass → /tdd pass {cycle_id}")


def cmd_pass(args):
    """Advance red → green (tests now passing)."""
    sha = current_sha()
    updates = {"git.green_commit": sha}
    if args.criteria:
        updates["notes.green_criteria"] = args.criteria
    data = transition(args.cycle_id, "pass", updates)
    print(f"✓ {args.cycle_id}: 🔴 red → 🟢 green")
    print(f"  Green commit: {sha[:8] if sha else 'n/a'}")
    print(f"  Next: Clean up implementation → /tdd refactor {args.cycle_id}")


def cmd_refactor(args):
    """Advance green → refactor."""
    sha = current_sha()
    updates = {"git.refactor_commit": sha}
    if args.notes:
        updates["notes.refactor_notes"] = args.notes
    data = transition(args.cycle_id, "refactor", updates)
    print(f"✓ {args.cycle_id}: 🟢 green → 🔵 refactor")
    print(f"  Next: When cleanup done → /tdd done {args.cycle_id}")


def cmd_done(args):
    """Advance to done — cycle complete."""
    data = transition(args.cycle_id, "done")
    print(f"✓ {args.cycle_id}: → ✅ done")
    print(f"  TDD cycle complete. Target: {data['target']}")


def cmd_abandon(args):
    """Mark cycle as abandoned."""
    data = transition(args.cycle_id, "abandon")
    print(f"✓ {args.cycle_id}: → ❌ abandoned")
    if args.reason:
        p = cycle_path(args.cycle_id)
        d = load_cycle(args.cycle_id)
        d.setdefault("notes", {})["abandon_reason"] = args.reason
        save_cycle(p, d)


def cmd_status(args):
    """Show status of a cycle."""
    data = load_cycle(args.cycle_id)
    icons = {"red": "🔴", "green": "🟢", "refactor": "🔵", "done": "✅", "abandoned": "❌"}
    state = data["state"]
    print(f"Cycle: {data['cycle_id']}  {icons.get(state, '?')} {state.upper()}")
    print(f"  Target : {data.get('target', '')}")
    print(f"  Test   : {data.get('files', {}).get('test', '—')}")
    print(f"  Source : {data.get('files', {}).get('source', '—')}")
    print(f"  Created: {data.get('created_at', '')}")
    print(f"  Updated: {data.get('updated_at', '')}")
    hyp = data.get("notes", {}).get("hypothesis", "")
    if hyp:
        print(f"  Hypothesis: {hyp}")
    sha = data.get("git", {})
    if sha.get("green_commit"):
        print(f"  Green@: {sha['green_commit'][:8]}")


def cmd_list(args):
    """List all cycles (optionally filter by state)."""
    if not CYCLES_DIR.exists():
        print("No TDD cycles found.")
        return
    icons = {"red": "🔴", "green": "🟢", "refactor": "🔵", "done": "✅", "abandoned": "❌"}
    cycles = sorted(CYCLES_DIR.glob("tdd-*.yaml"))
    if not cycles:
        print("No TDD cycles found.")
        return
    for p in cycles:
        data = yaml.safe_load(p.read_text())
        state = data.get("state", "?")
        if args.state and state != args.state:
            continue
        icon = icons.get(state, "?")
        target = data.get("target", "")[:50]
        print(f"{icon} {data['cycle_id']:25s} {state:10s} {target}")


def cmd_link(args):
    """Link a cycle to a story or spike."""
    p = cycle_path(args.cycle_id)
    data = load_cycle(args.cycle_id)
    data.setdefault("links", {})
    if args.story:
        data["links"]["story_id"] = args.story
    if args.spike:
        data["links"]["spike_id"] = args.spike
    if args.test_file:
        data.setdefault("files", {})["test"] = args.test_file
    if args.source_file:
        data.setdefault("files", {})["source"] = args.source_file
    save_cycle(p, data)
    print(f"✓ {args.cycle_id}: links updated")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="tdd",
        description="TDD Strict — Red → Green → Refactor cycle manager"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # new
    p_new = sub.add_parser("new", help="Start a new TDD cycle")
    p_new.add_argument("target", nargs="+", help="What behavior is being driven")
    p_new.add_argument("--test", help="Test file path")
    p_new.add_argument("--source", help="Source file path (will be created after test)")
    p_new.add_argument("--hypothesis", help="Expected behavior hypothesis")
    p_new.add_argument("--story", help="Story ID to link")

    # pass
    p_pass = sub.add_parser("pass", help="Mark tests as passing (red → green)")
    p_pass.add_argument("cycle_id")
    p_pass.add_argument("--criteria", help="Green criteria description")

    # refactor
    p_refactor = sub.add_parser("refactor", help="Enter refactor phase (green → refactor)")
    p_refactor.add_argument("cycle_id")
    p_refactor.add_argument("--notes", help="What was refactored")

    # done
    p_done = sub.add_parser("done", help="Complete the cycle")
    p_done.add_argument("cycle_id")

    # abandon
    p_abandon = sub.add_parser("abandon", help="Abandon a cycle")
    p_abandon.add_argument("cycle_id")
    p_abandon.add_argument("--reason", help="Reason for abandoning")

    # status
    p_status = sub.add_parser("status", help="Show cycle status")
    p_status.add_argument("cycle_id")

    # list
    p_list = sub.add_parser("list", help="List cycles")
    p_list.add_argument("--state", choices=["red", "green", "refactor", "done", "abandoned"],
                        help="Filter by state")

    # link
    p_link = sub.add_parser("link", help="Link cycle to story/spike/files")
    p_link.add_argument("cycle_id")
    p_link.add_argument("--story", help="Story ID")
    p_link.add_argument("--spike", help="Spike ID")
    p_link.add_argument("--test-file", dest="test_file")
    p_link.add_argument("--source-file", dest="source_file")

    args = parser.parse_args()
    dispatch = {
        "new": cmd_new, "pass": cmd_pass, "refactor": cmd_refactor,
        "done": cmd_done, "abandon": cmd_abandon, "status": cmd_status,
        "list": cmd_list, "link": cmd_link,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
