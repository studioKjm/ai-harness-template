#!/usr/bin/env python3
"""
spike.py — Spike state machine for the Exploration methodology.

Subcommands:
    new <slug> --question "..." [--timebox 4] [--hypothesis "..."]
    list [--status STATUS]
    show <spike-id>
    start <spike-id>             # questioning → spiking (sets started_at)
    close <spike-id>              # spiking → learned (requires learning_id linked)
    abandon <spike-id> --reason "..."
    apply <spike-id>              # learned → applied (requires promotion fields set)

Storage:
    .harness/exploration/spikes/<spike-id>/spike.yaml

Exit codes:
    0  success
    1  not found / wrong state
    2  validation error (missing required fields)
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. Install with: pip3 install pyyaml", file=sys.stderr)
    sys.exit(2)


SPIKES_DIR = Path(".harness/exploration/spikes")
LEARNINGS_DIR = Path(".harness/exploration/learnings")
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "spike.yaml"

VALID_TRANSITIONS = {
    "questioning": ["spiking", "abandoned"],
    "spiking": ["learned", "abandoned"],
    "learned": ["applied", "abandoned"],
    "applied": [],
    "abandoned": [],
}


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", s.lower())
    return re.sub(r"-+", "-", s).strip("-")


def load_spike(spike_id: str) -> tuple[Path, dict]:
    path = SPIKES_DIR / spike_id / "spike.yaml"
    if not path.exists():
        print(f"ERROR: spike not found: {spike_id}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return path, yaml.safe_load(f) or {}


def save_spike(path: Path, data: dict) -> None:
    data["updated_at"] = now_iso()
    with path.open("w") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)


def cmd_new(args):
    if not args.question.strip().endswith("?"):
        print("ERROR: --question must end with '?'", file=sys.stderr)
        sys.exit(2)

    today = datetime.date.today().isoformat()
    spike_id = f"sp-{today}-{slugify(args.slug)}"
    spike_dir = SPIKES_DIR / spike_id
    if spike_dir.exists():
        print(f"ERROR: spike already exists: {spike_id}", file=sys.stderr)
        sys.exit(1)

    spike_dir.mkdir(parents=True)
    (spike_dir / "sandbox").mkdir()

    if not TEMPLATE.exists():
        print(f"ERROR: template not found at {TEMPLATE}", file=sys.stderr)
        sys.exit(2)

    with TEMPLATE.open() as f:
        spike = yaml.safe_load(f)

    now = now_iso()
    spike["id"] = spike_id
    spike["created_at"] = now
    spike["updated_at"] = now
    spike["question"] = args.question.strip()
    spike["timebox"] = {
        "duration_hours": args.timebox,
        "started_at": None,
        "expires_at": None,
    }
    spike["hypothesis"] = args.hypothesis or ""
    spike["answered_when"] = []
    spike["sandbox"] = {"path": f".harness/exploration/spikes/{spike_id}/sandbox/"}
    spike["status"] = "questioning"
    spike["history"] = [
        {"timestamp": now, "from": None, "to": "questioning", "note": "spike created"}
    ]
    spike["links"] = {
        "learning_id": None,
        "parent_seed": None,
        "parent_story": None,
        "related_spikes": [],
    }
    spike["abandoned_reason"] = None

    save_spike(spike_dir / "spike.yaml", spike)
    print(f"Created spike: {spike_id}")
    print(f"  Question: {spike['question']}")
    print(f"  Timebox:  {args.timebox}h")
    print(f"  Sandbox:  {spike['sandbox']['path']}")
    print(f"\nNext: when you start working, run `spike.py start {spike_id}`")


def cmd_list(args):
    if not SPIKES_DIR.exists():
        print("(no spikes)")
        return
    rows = []
    for d in sorted(SPIKES_DIR.iterdir()):
        if not d.is_dir():
            continue
        f = d / "spike.yaml"
        if not f.exists():
            continue
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if args.status and data.get("status") != args.status:
            continue
        rows.append((data.get("id", "?"), data.get("status", "?"),
                     data.get("question", "")[:60]))

    if not rows:
        print("(no matching spikes)")
        return

    width = max(len(r[0]) for r in rows)
    for sid, status, q in rows:
        print(f"  {sid:<{width}}  [{status:<11}]  {q}")


def cmd_show(args):
    _, data = load_spike(args.spike_id)
    print(yaml.dump(data, sort_keys=False, allow_unicode=True))


def transition(spike_id: str, target: str, **updates):
    path, data = load_spike(spike_id)
    current = data.get("status", "questioning")
    if target not in VALID_TRANSITIONS.get(current, []):
        print(f"ERROR: cannot transition {current} → {target}", file=sys.stderr)
        print(f"  valid from {current}: {VALID_TRANSITIONS.get(current, [])}",
              file=sys.stderr)
        sys.exit(1)
    now = now_iso()
    data["history"].append({
        "timestamp": now,
        "from": current,
        "to": target,
        "note": updates.pop("note", ""),
    })
    data["status"] = target
    for k, v in updates.items():
        data[k] = v
    save_spike(path, data)
    print(f"{spike_id}: {current} → {target}")


def cmd_start(args):
    path, data = load_spike(args.spike_id)
    if data.get("status") != "questioning":
        print(f"ERROR: can only start a 'questioning' spike (current: {data.get('status')})",
              file=sys.stderr)
        sys.exit(1)
    now = now_iso()
    duration = data.get("timebox", {}).get("duration_hours", 4)
    expires = (datetime.datetime.now(datetime.timezone.utc)
               + datetime.timedelta(hours=duration)).isoformat(timespec="seconds")
    data["timebox"]["started_at"] = now
    data["timebox"]["expires_at"] = expires
    data["status"] = "spiking"
    data["history"].append({
        "timestamp": now, "from": "questioning", "to": "spiking",
        "note": f"timebox started ({duration}h, expires {expires})",
    })
    save_spike(path, data)
    print(f"{args.spike_id}: questioning → spiking")
    print(f"  Timebox expires at: {expires}")


def cmd_close(args):
    path, data = load_spike(args.spike_id)
    if data.get("status") != "spiking":
        print(f"ERROR: can only close a 'spiking' spike (current: {data.get('status')})",
              file=sys.stderr)
        sys.exit(1)
    learning_id = args.learning_id
    if learning_id:
        learning_path = LEARNINGS_DIR / f"{learning_id}.yaml"
        if not learning_path.exists():
            print(f"ERROR: learning not found: {learning_path}", file=sys.stderr)
            sys.exit(1)
        data.setdefault("links", {})["learning_id"] = learning_id
        save_spike(path, data)
    transition(args.spike_id, "learned",
               note=f"closed with learning={learning_id or 'none'}")


def cmd_abandon(args):
    path, data = load_spike(args.spike_id)
    if data.get("status") not in ("questioning", "spiking", "learned"):
        print(f"ERROR: cannot abandon from status: {data.get('status')}", file=sys.stderr)
        sys.exit(1)
    transition(args.spike_id, "abandoned", abandoned_reason=args.reason,
               note=f"abandoned: {args.reason}")


def cmd_apply(args):
    path, data = load_spike(args.spike_id)
    if data.get("status") != "learned":
        print(f"ERROR: can only apply a 'learned' spike (current: {data.get('status')})",
              file=sys.stderr)
        sys.exit(1)
    learning_id = data.get("links", {}).get("learning_id")
    if not learning_id:
        print("ERROR: spike has no linked learning. Run /learn record first.",
              file=sys.stderr)
        sys.exit(1)
    learning_path = LEARNINGS_DIR / f"{learning_id}.yaml"
    if not learning_path.exists():
        print(f"ERROR: linked learning file missing: {learning_path}", file=sys.stderr)
        sys.exit(1)
    with learning_path.open() as f:
        learning = yaml.safe_load(f) or {}
    promotion = learning.get("promotion", {}) or {}
    if not (promotion.get("to_adr") or promotion.get("to_seed")
            or promotion.get("to_code")):
        print("ERROR: learning has no promotion target. Set promotion.to_adr, "
              "to_seed, or to_code first.", file=sys.stderr)
        sys.exit(1)
    transition(args.spike_id, "applied",
               note=f"promoted via learning {learning_id}")


def main():
    p = argparse.ArgumentParser(prog="spike.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new"); s.set_defaults(fn=cmd_new)
    s.add_argument("slug")
    s.add_argument("--question", required=True)
    s.add_argument("--timebox", type=int, default=4)
    s.add_argument("--hypothesis", default="")

    s = sub.add_parser("list"); s.set_defaults(fn=cmd_list)
    s.add_argument("--status", default=None)

    s = sub.add_parser("show"); s.set_defaults(fn=cmd_show)
    s.add_argument("spike_id")

    s = sub.add_parser("start"); s.set_defaults(fn=cmd_start)
    s.add_argument("spike_id")

    s = sub.add_parser("close"); s.set_defaults(fn=cmd_close)
    s.add_argument("spike_id")
    s.add_argument("--learning-id", default=None)

    s = sub.add_parser("abandon"); s.set_defaults(fn=cmd_abandon)
    s.add_argument("spike_id")
    s.add_argument("--reason", required=True)

    s = sub.add_parser("apply"); s.set_defaults(fn=cmd_apply)
    s.add_argument("spike_id")

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
