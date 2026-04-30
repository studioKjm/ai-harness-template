#!/usr/bin/env python3
"""lean-mvp CLI — Build → Measure → Learn hypothesis manager."""
import argparse
import sys
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yaml

HARNESS_DIR = Path(os.environ.get("HARNESS_DIR", ".harness"))
HYPS_DIR = HARNESS_DIR / "lean-mvp" / "hypotheses"
CONFIG_FILE = HARNESS_DIR / "lean-mvp" / "config.yaml"
STATE_FILE = HARNESS_DIR / "state" / "lean-mvp.yaml"

# ── State machine ──────────────────────────────────────────────────────────────

TRANSITIONS = {
    "proposed":  {"build": "testing"},
    "testing":   {"measure": "measuring"},
    "measuring": {"decide": "decided"},
}

TERMINAL = {"decided"}

ICONS = {
    "proposed":  "💡",
    "testing":   "🔨",
    "measuring": "📏",
    "decided":   "✅",
}

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def hyp_path(hyp_id: str) -> Path:
    return HYPS_DIR / f"{hyp_id}.yaml"

def load_hyp(hyp_id: str) -> dict:
    p = hyp_path(hyp_id)
    if not p.exists():
        print(f"Error: hypothesis '{hyp_id}' not found at {p}", file=sys.stderr)
        sys.exit(1)
    return yaml.safe_load(p.read_text())

def save_hyp(path: Path, data: dict):
    data["updated_at"] = now_iso()
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))

def gen_hyp_id() -> str:
    ts = datetime.now().strftime("%Y%m%d")
    existing = sorted(HYPS_DIR.glob(f"hyp-{ts}-*.yaml")) if HYPS_DIR.exists() else []
    idx = len(existing) + 1
    return f"hyp-{ts}-{idx:03d}"

def load_config() -> dict:
    if CONFIG_FILE.exists():
        return yaml.safe_load(CONFIG_FILE.read_text()) or {}
    return {}

def current_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return ""

def transition(hyp_id: str, action: str, updates: dict | None = None) -> dict:
    p = hyp_path(hyp_id)
    data = load_hyp(hyp_id)
    current = data["state"]

    if current in TERMINAL:
        print(f"Error: hypothesis '{hyp_id}' already decided.", file=sys.stderr)
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
    save_hyp(p, data)
    return data

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_new(args):
    """Create a new hypothesis in 'proposed' state."""
    HYPS_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    hyp_id = gen_hyp_id()
    p = hyp_path(hyp_id)

    window = args.window or cfg.get("default_measurement_window_days", 14)
    deadline = ""
    if window:
        deadline = (datetime.now(timezone.utc) + timedelta(days=int(window))).strftime("%Y-%m-%d")

    data = {
        "hypothesis_id": hyp_id,
        "title": args.title or "",
        "statement": args.statement or "",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "deadline": deadline,
        "state": "proposed",
        "build": {"mvp_description": "", "shipped_at": "", "ship_commit": ""},
        "measure": {
            "metric_name": args.metric or "",
            "metric_target": args.target or "",
            "metric_actual": "",
            "measurement_window_days": window,
            "data_source": args.data_source or "",
            "measured_at": "",
        },
        "learn": {
            "outcome": "",
            "rationale": "",
            "next_hypothesis_id": "",
            "decided_by": "",
            "decided_at": "",
        },
        "links": {
            "story_id": args.story or "",
            "rfc_id": "",
            "tdd_cycle_id": "",
            "parent_hypothesis_id": "",
        },
        "tags": args.tags.split(",") if args.tags else [],
    }
    p.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))

    print(f"✓ Hypothesis created: {hyp_id}")
    print(f"  State: 💡 proposed")
    print(f"  Title: {data['title'] or '(set title)'}")
    if data["statement"]:
        print(f"  Statement: {data['statement']}")
    if data["measure"]["metric_name"]:
        print(f"  Metric: {data['measure']['metric_name']} (target: {data['measure']['metric_target']})")
    print(f"  Deadline: {deadline or '(not set)'}")
    print(f"  Next: Build MVP → /lean build {hyp_id} --mvp <description>")


def cmd_build(args):
    """Transition proposed → testing: MVP shipped."""
    cfg = load_config()
    data = load_hyp(args.hyp_id)

    # Validation
    if cfg.get("require_metric_before_build", True):
        metric = data.get("measure", {}).get("metric_name", "")
        if not metric and not args.metric:
            print("Error: set a metric before building. Use --metric or set in hypothesis.", file=sys.stderr)
            print("  /lean build <id> --metric <metric-name> --target <threshold>", file=sys.stderr)
            sys.exit(1)

    sha = current_sha()
    updates: dict = {
        "build.shipped_at": now_iso(),
        "build.ship_commit": sha,
        "build.mvp_description": args.mvp or "",
    }
    if args.metric:
        updates["measure.metric_name"] = args.metric
    if args.target:
        updates["measure.metric_target"] = args.target

    data = transition(args.hyp_id, "build", updates)
    print(f"✓ {args.hyp_id}: 💡 proposed → 🔨 testing")
    print(f"  MVP shipped: {data['build']['mvp_description'] or '(described in commit)'}")
    print(f"  Metric: {data['measure']['metric_name']} (target: {data['measure']['metric_target']})")
    print(f"  Measurement window: {data['measure']['measurement_window_days']} days")
    print(f"  Next: Collect data → /lean measure {args.hyp_id} --actual <value>")


def cmd_measure(args):
    """Transition testing → measuring: data collected."""
    data = load_hyp(args.hyp_id)

    if not args.actual and not args.source:
        print("Error: provide --actual <observed-value> to record measurement.", file=sys.stderr)
        sys.exit(1)

    updates = {
        "measure.measured_at": now_iso(),
        "measure.metric_actual": args.actual or "",
    }
    if args.source:
        updates["measure.data_source"] = args.source

    data = transition(args.hyp_id, "measure", updates)
    target = data["measure"]["metric_target"]
    actual = data["measure"]["metric_actual"]
    print(f"✓ {args.hyp_id}: 🔨 testing → 📏 measuring")
    print(f"  Metric: {data['measure']['metric_name']}")
    print(f"  Target: {target}")
    print(f"  Actual: {actual}")
    print(f"  Next: Decide outcome → /lean decide {args.hyp_id} persist|pivot|abandon --rationale <text>")


def cmd_decide(args):
    """Transition measuring → decided: pivot, persist, or abandon."""
    cfg = load_config()
    data = load_hyp(args.hyp_id)
    outcome = args.outcome

    if outcome not in ("persist", "pivot", "abandon"):
        print(f"Error: outcome must be 'persist', 'pivot', or 'abandon'.", file=sys.stderr)
        sys.exit(1)

    # Validation
    if not data.get("measure", {}).get("metric_actual"):
        print("Error: no measurement recorded. Run /lean measure first.", file=sys.stderr)
        sys.exit(1)

    if cfg.get("require_rationale_for_pivot", True) and outcome in ("pivot", "abandon"):
        if not args.rationale:
            print(f"Error: --rationale required for '{outcome}' decision.", file=sys.stderr)
            sys.exit(1)

    updates = {
        "learn.outcome": outcome,
        "learn.rationale": args.rationale or "",
        "learn.decided_by": args.decided_by or os.environ.get("GIT_AUTHOR_NAME", ""),
        "learn.decided_at": now_iso(),
    }
    if args.next_hyp:
        updates["learn.next_hypothesis_id"] = args.next_hyp

    data = transition(args.hyp_id, "decide", updates)
    outcome_icons = {"persist": "✅ PERSIST", "pivot": "🔄 PIVOT", "abandon": "🗑️ ABANDON"}
    print(f"✓ {args.hyp_id}: 📏 measuring → decided")
    print(f"  Outcome: {outcome_icons[outcome]}")
    print(f"  Rationale: {data['learn']['rationale'] or '(none)'}")
    if outcome == "pivot" and data["learn"]["next_hypothesis_id"]:
        print(f"  Next hypothesis: {data['learn']['next_hypothesis_id']}")
    elif outcome == "persist":
        print(f"  Ship it. Link to story: /lean link {args.hyp_id} --story <id>")
    elif outcome == "abandon":
        print(f"  Hypothesis closed. Document learnings for future reference.")


def cmd_status(args):
    """Show hypothesis status."""
    data = load_hyp(args.hyp_id)
    state = data["state"]
    icon = ICONS.get(state, "?")
    print(f"Hypothesis: {data['hypothesis_id']}  {icon} {state.upper()}")
    print(f"  Title   : {data.get('title', '')}")
    stmt = data.get("statement", "")
    if stmt:
        print(f"  Statement: {stmt}")
    m = data.get("measure", {})
    if m.get("metric_name"):
        print(f"  Metric  : {m['metric_name']}")
        print(f"  Target  : {m.get('metric_target', '—')}")
        print(f"  Actual  : {m.get('metric_actual', '—')}")
    b = data.get("build", {})
    if b.get("shipped_at"):
        print(f"  Shipped : {b['shipped_at']}")
    deadline = data.get("deadline", "")
    if deadline:
        print(f"  Deadline: {deadline}")
    l = data.get("learn", {})
    if l.get("outcome"):
        print(f"  Outcome : {l['outcome'].upper()} — {l.get('rationale', '')}")


def cmd_list(args):
    """List all hypotheses."""
    if not HYPS_DIR.exists():
        print("No hypotheses found.")
        return
    hyps = sorted(HYPS_DIR.glob("hyp-*.yaml"))
    if not hyps:
        print("No hypotheses found.")
        return
    for p in hyps:
        data = yaml.safe_load(p.read_text())
        state = data.get("state", "?")
        if args.state and state != args.state:
            continue
        icon = ICONS.get(state, "?")
        title = data.get("title", "")[:40]
        outcome = data.get("learn", {}).get("outcome", "")
        suffix = f" [{outcome}]" if outcome else ""
        print(f"{icon} {data['hypothesis_id']:25s} {state:10s} {title}{suffix}")


def cmd_link(args):
    """Link hypothesis to story/rfc/tdd."""
    p = hyp_path(args.hyp_id)
    data = load_hyp(args.hyp_id)
    data.setdefault("links", {})
    if args.story:
        data["links"]["story_id"] = args.story
    if args.rfc:
        data["links"]["rfc_id"] = args.rfc
    if args.tdd:
        data["links"]["tdd_cycle_id"] = args.tdd
    if args.parent:
        data["links"]["parent_hypothesis_id"] = args.parent
    save_hyp(p, data)
    print(f"✓ {args.hyp_id}: links updated")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="lean",
        description="Lean MVP — Build → Measure → Learn hypothesis manager"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # new
    p_new = sub.add_parser("new", help="Create a new hypothesis")
    p_new.add_argument("--title", required=True, help="Short title")
    p_new.add_argument("--statement", help="Full hypothesis statement")
    p_new.add_argument("--metric", help="Success metric name")
    p_new.add_argument("--target", help="Success threshold")
    p_new.add_argument("--data-source", dest="data_source", help="Where to measure")
    p_new.add_argument("--window", type=int, help="Measurement window (days)")
    p_new.add_argument("--story", help="Story ID to link")
    p_new.add_argument("--tags", help="Comma-separated tags")

    # build
    p_build = sub.add_parser("build", help="Ship MVP (proposed → testing)")
    p_build.add_argument("hyp_id")
    p_build.add_argument("--mvp", help="MVP description")
    p_build.add_argument("--metric", help="Override metric name")
    p_build.add_argument("--target", help="Override metric target")

    # measure
    p_measure = sub.add_parser("measure", help="Record measurement (testing → measuring)")
    p_measure.add_argument("hyp_id")
    p_measure.add_argument("--actual", help="Observed metric value")
    p_measure.add_argument("--source", help="Data source used")

    # decide
    p_decide = sub.add_parser("decide", help="Make pivot/persist/abandon decision (measuring → decided)")
    p_decide.add_argument("hyp_id")
    p_decide.add_argument("outcome", choices=["persist", "pivot", "abandon"])
    p_decide.add_argument("--rationale", help="Reason for decision")
    p_decide.add_argument("--decided-by", dest="decided_by", help="Decision maker")
    p_decide.add_argument("--next-hyp", dest="next_hyp", help="If pivot: next hypothesis ID")

    # status
    p_status = sub.add_parser("status", help="Show hypothesis status")
    p_status.add_argument("hyp_id")

    # list
    p_list = sub.add_parser("list", help="List hypotheses")
    p_list.add_argument("--state", choices=["proposed", "testing", "measuring", "decided"],
                        help="Filter by state")

    # link
    p_link = sub.add_parser("link", help="Link to story/rfc/tdd")
    p_link.add_argument("hyp_id")
    p_link.add_argument("--story")
    p_link.add_argument("--rfc")
    p_link.add_argument("--tdd")
    p_link.add_argument("--parent", help="Parent hypothesis ID (pivot chain)")

    args = parser.parse_args()
    dispatch = {
        "new": cmd_new, "build": cmd_build, "measure": cmd_measure,
        "decide": cmd_decide, "status": cmd_status,
        "list": cmd_list, "link": cmd_link,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
