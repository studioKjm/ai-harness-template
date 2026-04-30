#!/usr/bin/env python3
"""BDD CLI — Given/When/Then scenario and feature management."""

import argparse
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path


HARNESS_DIR = Path(".harness/bdd")
SCENARIOS_DIR = HARNESS_DIR / "scenarios"
FEATURES_DIR = HARNESS_DIR / "features"
TEMPLATE_DIR = Path("methodologies/bdd/templates")

VALID_STATES = ["draft", "ready", "implementing", "passing", "skipped"]
TERMINAL_STATES = {"passing", "skipped"}


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


def _find_scenario(scenario_id: str) -> Path:
    hits = list(SCENARIOS_DIR.glob(f"{scenario_id}*.yaml"))
    if not hits:
        print(f"Error: scenario '{scenario_id}' not found", file=sys.stderr)
        sys.exit(1)
    return hits[0]


# ── scenario ──────────────────────────────────────────────────────────────────

def cmd_new(args):
    scn_id = _next_id("SCN", SCENARIOS_DIR)
    data = _load_template("scenario.yaml")
    data["scenario_id"] = scn_id
    data["title"] = args.title
    data["feature_id"] = args.feature or ""
    data["state"] = "draft"
    data["given"] = []
    data["when"] = []
    data["then"] = []
    data["created_at"] = _now()
    data["updated_at"] = _now()

    slug = args.title.lower().replace(" ", "-")[:40]
    out_path = SCENARIOS_DIR / f"{scn_id}-{slug}.yaml"
    _save_yaml(out_path, data)
    print(f"Created scenario: {scn_id}")
    print(f"  Title: {args.title}")
    print(f"  File:  {out_path}")
    print(f"\nNext: edit {out_path} to fill in Given/When/Then")


def cmd_status(args):
    path = _find_scenario(args.id)
    data = _load_yaml(path)
    current = data.get("state", "draft")

    if current in TERMINAL_STATES:
        print(f"Error: scenario is already in terminal state '{current}'", file=sys.stderr)
        sys.exit(1)

    if args.state not in VALID_STATES:
        print(f"Error: invalid state '{args.state}'. Valid: {', '.join(VALID_STATES)}", file=sys.stderr)
        sys.exit(1)

    data["state"] = args.state
    data["updated_at"] = _now()
    if args.state == "passing" and not data.get("implementation", {}).get("file"):
        print("Warning: marking as passing but no implementation.file set")

    _save_yaml(path, data)
    print(f"Scenario {args.id}: {current} → {args.state}")


def cmd_list(args):
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(SCENARIOS_DIR.glob("SCN-*.yaml"))
    if not files:
        print("No scenarios found. Create one with: bdd.py new <title>")
        return

    state_filter = args.state if hasattr(args, "state") and args.state else None
    feature_filter = args.feature if hasattr(args, "feature") and args.feature else None

    icon_map = {
        "draft": "⚪", "ready": "🔵", "implementing": "🟡",
        "passing": "🟢", "skipped": "⬛"
    }

    print(f"{'ID':<18} {'St':<3} {'Feature':<20} Title")
    print("-" * 80)
    for f in files:
        d = _load_yaml(f)
        state = d.get("state", "")
        if state_filter and state != state_filter:
            continue
        feat = d.get("feature_id", "")
        if feature_filter and feat != feature_filter:
            continue
        icon = icon_map.get(state, "❓")
        print(f"{d.get('scenario_id',''):<18} {icon}  {feat:<20} {d.get('title','')}")


def cmd_show(args):
    path = _find_scenario(args.id)
    data = _load_yaml(path)

    icon_map = {"draft": "⚪", "ready": "🔵", "implementing": "🟡", "passing": "🟢", "skipped": "⬛"}
    icon = icon_map.get(data.get("state", ""), "❓")

    print(f"{icon} [{data['scenario_id']}] {data['title']}")
    print(f"   State:   {data.get('state')}")
    print(f"   Feature: {data.get('feature_id') or '-'}")
    print()

    given = data.get("given") or []
    when = data.get("when") or []
    then = data.get("then") or []

    if given:
        print("Given:")
        for g in given:
            print(f"  - {g}")
    if when:
        print("When:")
        for w in when:
            print(f"  - {w}")
    if then:
        print("Then:")
        for t in then:
            print(f"  - {t}")

    links = data.get("links") or {}
    impl = data.get("implementation") or {}
    if any(links.values()) or impl.get("file"):
        print()
        if links.get("story_id"):
            print(f"  Story:    {links['story_id']}")
        if links.get("tdd_cycle_id"):
            print(f"  TDD:      {links['tdd_cycle_id']}")
        if impl.get("file"):
            print(f"  Impl:     {impl['file']} [{impl.get('status', '')}]")


def cmd_link(args):
    path = _find_scenario(args.id)
    data = _load_yaml(path)

    links = data.get("links") or {}
    if args.tdd:
        links["tdd_cycle_id"] = args.tdd
        print(f"Linked {args.id} → TDD cycle {args.tdd}")
    if args.story:
        links["story_id"] = args.story
        print(f"Linked {args.id} → story {args.story}")
    if args.rfc:
        links["rfc_id"] = args.rfc
        print(f"Linked {args.id} → RFC {args.rfc}")

    data["links"] = links
    data["updated_at"] = _now()
    _save_yaml(path, data)


# ── feature ───────────────────────────────────────────────────────────────────

def cmd_feature_new(args):
    ftr_id = _next_id("FTR", FEATURES_DIR)
    data = _load_template("feature.yaml")
    data["feature_id"] = ftr_id
    data["name"] = args.name
    data["description"] = args.description or ""
    data["state"] = "draft"
    data["scenarios"] = []
    data["created_at"] = _now()
    data["updated_at"] = _now()

    slug = args.name.lower().replace(" ", "-")[:40]
    out_path = FEATURES_DIR / f"{ftr_id}-{slug}.yaml"
    _save_yaml(out_path, data)
    print(f"Created feature: {ftr_id} ({args.name})")
    print(f"  File: {out_path}")


def cmd_feature_list(args):
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(FEATURES_DIR.glob("FTR-*.yaml"))
    if not files:
        print("No features found.")
        return
    print(f"{'ID':<18} {'State':<12} Name")
    print("-" * 60)
    for f in files:
        d = _load_yaml(f)
        print(f"{d.get('feature_id',''):<18} {d.get('state',''):<12} {d.get('name','')}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BDD CLI")
    sub = parser.add_subparsers(dest="cmd")

    new_p = sub.add_parser("new")
    new_p.add_argument("title")
    new_p.add_argument("--feature", "-f", default="")

    status_p = sub.add_parser("status")
    status_p.add_argument("id")
    status_p.add_argument("state", choices=VALID_STATES)

    list_p = sub.add_parser("list")
    list_p.add_argument("--state", "-s", default="")
    list_p.add_argument("--feature", "-f", default="")

    show_p = sub.add_parser("show")
    show_p.add_argument("id")

    link_p = sub.add_parser("link")
    link_p.add_argument("id")
    link_p.add_argument("--tdd", default="")
    link_p.add_argument("--story", default="")
    link_p.add_argument("--rfc", default="")

    feat_p = sub.add_parser("feature")
    feat_sub = feat_p.add_subparsers(dest="action")

    feat_new = feat_sub.add_parser("new")
    feat_new.add_argument("name")
    feat_new.add_argument("--description", "-d", default="")

    feat_sub.add_parser("list")

    args = parser.parse_args()

    dispatch = {
        "new": cmd_new,
        "status": cmd_status,
        "list": cmd_list,
        "show": cmd_show,
        "link": cmd_link,
    }

    if args.cmd == "feature":
        action = getattr(args, "action", None)
        if action == "new":
            cmd_feature_new(args)
        elif action == "list":
            cmd_feature_list(args)
        else:
            feat_p.print_help()
    elif args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
