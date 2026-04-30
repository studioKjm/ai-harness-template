#!/usr/bin/env python3
"""Shape Up CLI — Pitch, Bet, Cycle, Hill Chart management."""

import argparse
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path


HARNESS_DIR = Path(".harness/shape-up")
PITCHES_DIR = HARNESS_DIR / "pitches"
BETS_DIR = HARNESS_DIR / "bets"
CYCLES_DIR = HARNESS_DIR / "cycles"
TEMPLATE_DIR = Path("methodologies/shape-up/templates")

PITCH_STATES = ["shaping", "ready", "bet", "building", "done", "not-bet", "abandoned"]
PITCH_TERMINAL = {"done", "not-bet", "abandoned"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _next_id(prefix: str, directory: Path) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    existing = list(directory.glob(f"{prefix.lower()}-*.yaml"))
    seq = len(existing) + 1
    return f"{prefix}-{_today()}-{seq:03d}"


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _load_template(name: str) -> dict:
    path = TEMPLATE_DIR / name
    if path.exists():
        return _load_yaml(path)
    return {}


def _find_pitch(pitch_id: str) -> Path:
    hits = list(PITCHES_DIR.glob(f"{pitch_id}*.yaml"))
    if not hits:
        print(f"Error: pitch '{pitch_id}' not found", file=sys.stderr)
        sys.exit(1)
    return hits[0]


# ── pitch ─────────────────────────────────────────────────────────────────────

def cmd_pitch_new(args):
    pch_id = _next_id("PCH", PITCHES_DIR)
    data = _load_template("pitch.yaml")
    data["pitch_id"] = pch_id
    data["title"] = args.title
    data["state"] = "shaping"
    data["appetite"] = {
        "size": args.appetite or "big-batch",
        "weeks": 6 if (args.appetite or "big-batch") == "big-batch" else 2,
        "rationale": "",
    }
    data["problem"] = {"description": "", "customer_pain": "", "current_workaround": ""}
    data["solution"] = {"description": "", "breadboard": "", "fat_marker_sketch": ""}
    data["rabbit_holes"] = []
    data["no_gos"] = []
    data["bet"] = {"decided_at": "", "decided_by": "", "cycle_id": "", "rationale": ""}
    data["created_at"] = _now()
    data["updated_at"] = _now()

    slug = args.title.lower().replace(" ", "-")[:40]
    out_path = PITCHES_DIR / f"{pch_id}-{slug}.yaml"
    _save_yaml(out_path, data)
    print(f"Created pitch: {pch_id}")
    print(f"  Title:    {args.title}")
    print(f"  Appetite: {data['appetite']['size']} ({data['appetite']['weeks']} weeks)")
    print(f"  File:     {out_path}")
    print(f"\nNext: edit {out_path} to fill in Problem, Solution, Rabbit Holes, No-Gos")


def cmd_pitch_list(args):
    PITCHES_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(PITCHES_DIR.glob("PCH-*.yaml"))
    if not files:
        print("No pitches found. Create one with: shapeup.py pitch new <title>")
        return

    state_filter = args.state if hasattr(args, "state") and args.state else None
    icon_map = {
        "shaping": "✏️ ", "ready": "🔵", "bet": "🎯", "building": "🔨",
        "done": "✅", "not-bet": "❌", "abandoned": "⬛"
    }

    print(f"{'ID':<18} {'St':<3} {'Appetite':<12} Title")
    print("-" * 70)
    for f in files:
        d = _load_yaml(f)
        state = d.get("state", "")
        if state_filter and state != state_filter:
            continue
        appetite = d.get("appetite", {}).get("size", "")
        icon = icon_map.get(state, "❓")
        print(f"{d.get('pitch_id',''):<18} {icon} {appetite:<12} {d.get('title','')}")


def cmd_pitch_show(args):
    path = _find_pitch(args.id)
    data = _load_yaml(path)

    icon_map = {
        "shaping": "✏️", "ready": "🔵", "bet": "🎯", "building": "🔨",
        "done": "✅", "not-bet": "❌", "abandoned": "⬛"
    }
    icon = icon_map.get(data.get("state", ""), "❓")
    appetite = data.get("appetite", {})

    print(f"{icon} [{data['pitch_id']}] {data['title']}")
    print(f"   State:    {data.get('state')}")
    print(f"   Appetite: {appetite.get('size')} ({appetite.get('weeks')} weeks)")
    print()

    problem = data.get("problem") or {}
    if problem.get("description"):
        print(f"Problem: {problem['description']}")
    if problem.get("customer_pain"):
        print(f"  Pain:     {problem['customer_pain']}")

    solution = data.get("solution") or {}
    if solution.get("description"):
        print(f"Solution: {solution['description']}")

    rh = data.get("rabbit_holes") or []
    if rh:
        print(f"Rabbit Holes: {len(rh)} identified")

    ng = data.get("no_gos") or []
    if ng:
        print(f"No-Gos: {len(ng)} items")


def cmd_pitch_ready(args):
    path = _find_pitch(args.id)
    data = _load_yaml(path)
    current = data.get("state")
    if current not in ("shaping",):
        print(f"Error: can only mark ready from 'shaping', current state is '{current}'", file=sys.stderr)
        sys.exit(1)
    data["state"] = "ready"
    data["updated_at"] = _now()
    _save_yaml(path, data)
    print(f"Pitch {args.id}: shaping → ready (available for betting table)")


# ── bet ───────────────────────────────────────────────────────────────────────

def cmd_bet(args):
    pitch_path = _find_pitch(args.pitch_id)
    pitch = _load_yaml(pitch_path)

    if pitch.get("state") not in ("ready",):
        print(f"Error: pitch must be in 'ready' state to bet. Current: '{pitch.get('state')}'", file=sys.stderr)
        sys.exit(1)

    bet_id = _next_id("BET", BETS_DIR)
    bet_data = _load_template("bet.yaml")
    bet_data["bet_id"] = bet_id
    bet_data["pitch_id"] = args.pitch_id
    bet_data["cycle_id"] = args.cycle or ""
    bet_data["title"] = pitch["title"]
    bet_data["appetite_weeks"] = pitch.get("appetite", {}).get("weeks", 6)
    bet_data["decision"] = {
        "decided_at": _now(),
        "decided_by": args.by or "",
        "rationale": args.rationale or "",
        "competing_pitches": [],
    }
    bet_data["state"] = "active"
    bet_data["created_at"] = _now()

    slug = pitch["title"].lower().replace(" ", "-")[:40]
    out_path = BETS_DIR / f"{bet_id}-{slug}.yaml"
    _save_yaml(out_path, bet_data)

    pitch["state"] = "bet"
    pitch["bet"]["decided_at"] = _now()
    pitch["bet"]["decided_by"] = args.by or ""
    pitch["bet"]["cycle_id"] = args.cycle or ""
    pitch["bet"]["rationale"] = args.rationale or ""
    pitch["updated_at"] = _now()
    _save_yaml(pitch_path, pitch)

    print(f"Bet placed: {bet_id}")
    print(f"  Pitch: {args.pitch_id} — {pitch['title']}")
    if args.cycle:
        print(f"  Cycle: {args.cycle}")
    print(f"  File:  {out_path}")


def cmd_not_bet(args):
    path = _find_pitch(args.id)
    data = _load_yaml(path)
    if data.get("state") not in ("ready", "shaping"):
        print(f"Error: pitch '{args.id}' is in state '{data.get('state')}', cannot mark not-bet", file=sys.stderr)
        sys.exit(1)
    data["state"] = "not-bet"
    data["updated_at"] = _now()
    _save_yaml(path, data)
    print(f"Pitch {args.id} marked as not-bet (can be re-shaped and re-pitched next cycle)")


# ── hill ──────────────────────────────────────────────────────────────────────

def cmd_hill(args):
    """Print hill chart visualization for a cycle."""
    snap_id = _next_id("HLC", CYCLES_DIR)
    data = _load_template("hill-chart.yaml")
    data["snapshot_id"] = snap_id
    data["cycle_id"] = args.cycle or ""
    data["captured_at"] = _now()
    data["items"] = []

    out_path = CYCLES_DIR / f"{snap_id}.yaml"
    _save_yaml(out_path, data)
    print(f"Created hill chart snapshot: {snap_id}")
    print(f"  File: {out_path}")
    print(f"\nEdit the file to record scope positions (0=start, 50=hilltop, 100=done)")
    print("\nHill Chart Reference:")
    print("  0% ──── Uphill (figuring it out) ──── 50% ──── Downhill (executing) ──── 100%")


def cmd_hill_show(args):
    """Render a hill chart snapshot as ASCII."""
    hits = list(CYCLES_DIR.glob(f"{args.id}*.yaml"))
    if not hits:
        print(f"Error: hill chart '{args.id}' not found", file=sys.stderr)
        sys.exit(1)
    data = _load_yaml(hits[0])
    items = data.get("items") or []

    print(f"Hill Chart — Cycle: {data.get('cycle_id', '-')} | {data.get('captured_at', '')}")
    print()
    print("  Uphill          [HILL TOP]      Downhill")
    print("  0%      25%       50%      75%      100%")
    print("  |---------|---------|---------|---------|")

    for item in items:
        pos = item.get("position", 0)
        bar_pos = int(pos * 40 / 100)
        line = [" "] * 41
        line[bar_pos] = "●"
        phase_icon = {"uphill": "↗", "hilltop": "🏔", "downhill": "↘", "done": "✅"}.get(item.get("phase", ""), " ")
        scope = (item.get("scope") or "")[:20]
        print(f"  {''.join(line)}  {phase_icon} {scope}")

    print()
    summary = data.get("summary") or {}
    on_track = "✅ On track" if summary.get("on_track") else "⚠️  Off track"
    print(f"  {on_track}")
    if summary.get("concerns"):
        print(f"  Concerns: {summary['concerns']}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Shape Up CLI")
    sub = parser.add_subparsers(dest="cmd")

    # pitch
    pitch_p = sub.add_parser("pitch")
    pitch_sub = pitch_p.add_subparsers(dest="action")

    pitch_new = pitch_sub.add_parser("new")
    pitch_new.add_argument("title")
    pitch_new.add_argument("--appetite", "-a", choices=["small-batch", "big-batch"], default="big-batch")

    pitch_sub.add_parser("list").add_argument("--state", "-s", default="")
    pitch_show = pitch_sub.add_parser("show")
    pitch_show.add_argument("id")

    pitch_ready = pitch_sub.add_parser("ready")
    pitch_ready.add_argument("id")

    pitch_not_bet = pitch_sub.add_parser("not-bet")
    pitch_not_bet.add_argument("id")

    # bet
    bet_p = sub.add_parser("bet")
    bet_p.add_argument("pitch_id")
    bet_p.add_argument("--cycle", "-c", default="")
    bet_p.add_argument("--by", "-b", default="")
    bet_p.add_argument("--rationale", "-r", default="")

    # not-bet (shortcut at top level)
    not_bet_p = sub.add_parser("not-bet")
    not_bet_p.add_argument("id")

    # hill
    hill_p = sub.add_parser("hill")
    hill_sub = hill_p.add_subparsers(dest="action")

    hill_new = hill_sub.add_parser("new")
    hill_new.add_argument("--cycle", "-c", default="")

    hill_show = hill_sub.add_parser("show")
    hill_show.add_argument("id")

    args = parser.parse_args()

    if args.cmd == "pitch":
        action = getattr(args, "action", None)
        if action == "new":
            cmd_pitch_new(args)
        elif action == "list":
            cmd_pitch_list(args)
        elif action == "show":
            cmd_pitch_show(args)
        elif action == "ready":
            cmd_pitch_ready(args)
        elif action == "not-bet":
            cmd_not_bet(args)
        else:
            pitch_p.print_help()
    elif args.cmd == "bet":
        cmd_bet(args)
    elif args.cmd == "not-bet":
        cmd_not_bet(args)
    elif args.cmd == "hill":
        action = getattr(args, "action", None)
        if action == "new":
            cmd_hill(args)
        elif action == "show":
            cmd_hill_show(args)
        else:
            hill_p.print_help()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
