#!/usr/bin/env python3
"""
sf.py — Strangler Fig state machine + routing rule manager.

Subcommands:
    new <slug> --legacy <path> --new <path> --facade <path> [--title "..."]
    list [--state STATE]
    show <plan-id>
    route add <plan-id> --pattern PAT --target legacy|new --reason "..."
    route remove <plan-id> --rule-id RID
    coverage <plan-id> [--scan-endpoints PATTERN]
    advance <plan-id> <state>           # explicit state transition
    retire <plan-id>                    # final state (alias for `advance retired`)

State machine:
    legacy-only → coexist → new-primary → retired

Storage:
    .harness/strangler-fig/plans/<plan-id>.yaml

Exit codes:
    0  success
    1  not found / wrong state / cutover criteria not met
    2  validation error
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required.", file=sys.stderr)
    sys.exit(2)


PLANS_DIR = Path(".harness/strangler-fig/plans")
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "strangler-plan.yaml"

VALID_TRANSITIONS = {
    "legacy-only": ["coexist"],
    "coexist": ["new-primary", "legacy-only"],   # rollback to legacy-only allowed
    "new-primary": ["retired", "coexist"],        # rollback to coexist allowed
    "retired": [],
}


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", s.lower())
    return re.sub(r"-+", "-", s).strip("-")


def load_plan(plan_id: str) -> tuple[Path, dict]:
    path = PLANS_DIR / f"{plan_id}.yaml"
    if not path.exists():
        print(f"ERROR: plan not found: {plan_id}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return path, yaml.safe_load(f) or {}


def save_plan(path: Path, data: dict) -> None:
    data["updated_at"] = now_iso()
    with path.open("w") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)


def cmd_new(args):
    today = datetime.date.today().isoformat()
    plan_id = f"sf-{today}-{slugify(args.slug)}"
    path = PLANS_DIR / f"{plan_id}.yaml"
    if path.exists():
        print(f"ERROR: plan already exists: {plan_id}", file=sys.stderr)
        sys.exit(1)
    PLANS_DIR.mkdir(parents=True, exist_ok=True)

    if not TEMPLATE.exists():
        print(f"ERROR: template not found at {TEMPLATE}", file=sys.stderr)
        sys.exit(2)

    with TEMPLATE.open() as f:
        plan = yaml.safe_load(f)

    now = now_iso()
    plan["id"] = plan_id
    plan["created_at"] = now
    plan["updated_at"] = now
    plan["title"] = args.title or f"Strangle {args.slug}"
    plan["description"] = ""
    plan["legacy_module"]["path"] = args.legacy
    plan["new_module"]["path"] = args.new
    plan["new_module"]["exists_yet"] = False
    plan["facade"]["path"] = args.facade
    plan["facade"]["exists_yet"] = False
    plan["routing_rules"] = []
    plan["coverage"] = {
        "legacy_endpoints": [],
        "routed_count": 0,
        "total_count": 0,
        "percent": 0,
        "unrouted": [],
    }
    plan["state"] = "legacy-only"
    plan["history"] = [{
        "timestamp": now, "from": None, "to": "legacy-only",
        "note": "plan created", "routing_count": 0,
    }]
    plan["risks"] = []
    plan["links"] = {
        "parallel_changes": [], "parent_seed": None, "related_adrs": [],
    }

    save_plan(path, plan)
    print(f"Created strangler plan: {plan_id}")
    print(f"  Legacy:  {args.legacy}")
    print(f"  New:     {args.new}")
    print(f"  Facade:  {args.facade}")
    print(f"  State:   legacy-only")
    print()
    print(f"Next:")
    print(f"  1. Build the facade and at least one routed pattern in '{args.new}'")
    print(f"  2. Add routing rules: /strangler-route add {plan_id} --pattern '...' --target new")
    print(f"  3. When facade routes ≥ 1 pattern: /strangler advance {plan_id} coexist")


def cmd_list(args):
    if not PLANS_DIR.exists():
        print("(no strangler plans)")
        return
    rows = []
    for f in sorted(PLANS_DIR.glob("*.yaml")):
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if args.state and data.get("state") != args.state:
            continue
        cov = data.get("coverage", {})
        pct = cov.get("percent", 0) or 0
        rules = len(data.get("routing_rules", []) or [])
        rows.append((data.get("id", "?"), data.get("state", "?"),
                     f"{pct}% ({rules} rules)",
                     data.get("title", "")[:50]))

    if not rows:
        print("(no matching plans)")
        return

    width = max(len(r[0]) for r in rows)
    for pid, state, cov, title in rows:
        print(f"  {pid:<{width}}  [{state:<12}]  {cov:<18}  {title}")


def cmd_show(args):
    _, data = load_plan(args.plan_id)
    print(yaml.dump(data, sort_keys=False, allow_unicode=True))


def cmd_route_add(args):
    path, data = load_plan(args.plan_id)
    rules = data.setdefault("routing_rules", [])
    rule_id = args.rule_id or f"rule-{len(rules) + 1}"
    if any(r.get("id") == rule_id for r in rules):
        print(f"ERROR: rule_id '{rule_id}' already exists", file=sys.stderr)
        sys.exit(1)
    if args.target not in ("legacy", "new"):
        print("ERROR: --target must be 'legacy' or 'new'", file=sys.stderr)
        sys.exit(2)
    rules.append({
        "id": rule_id,
        "pattern": args.pattern,
        "target": args.target,
        "reason": args.reason or "",
        "added_at": now_iso(),
    })
    _recompute_coverage(data)
    save_plan(path, data)
    print(f"Added rule {rule_id}: {args.pattern} → {args.target}")


def cmd_route_remove(args):
    path, data = load_plan(args.plan_id)
    rules = data.get("routing_rules", []) or []
    new_rules = [r for r in rules if r.get("id") != args.rule_id]
    if len(new_rules) == len(rules):
        print(f"ERROR: rule '{args.rule_id}' not found", file=sys.stderr)
        sys.exit(1)
    data["routing_rules"] = new_rules
    _recompute_coverage(data)
    save_plan(path, data)
    print(f"Removed rule {args.rule_id}")


def _recompute_coverage(data: dict) -> None:
    """Recompute coverage stats from routing rules + declared endpoints."""
    rules = data.get("routing_rules", []) or []
    endpoints = (data.get("coverage", {}) or {}).get("legacy_endpoints", []) or []

    routed_patterns = {r.get("pattern") for r in rules}
    routed = [ep for ep in endpoints if ep in routed_patterns]
    unrouted = [ep for ep in endpoints if ep not in routed_patterns]

    coverage = data.setdefault("coverage", {})
    coverage["routed_count"] = len(routed)
    coverage["total_count"] = len(endpoints)
    coverage["percent"] = (
        round(100 * len(routed) / len(endpoints)) if endpoints else 0
    )
    coverage["unrouted"] = unrouted


def cmd_coverage(args):
    """Update declared legacy endpoints, optionally scanning a glob pattern."""
    path, data = load_plan(args.plan_id)
    coverage = data.setdefault("coverage", {})

    if args.scan_endpoints:
        # Simple grep-based scan for HTTP route declarations
        eps = []
        try:
            import subprocess
            res = subprocess.run(
                ["grep", "-rEho",
                 r"(GET|POST|PUT|PATCH|DELETE)\s+['\"][^'\"]+['\"]",
                 args.scan_endpoints],
                capture_output=True, text=True, check=False)
            for line in res.stdout.splitlines():
                m = re.search(
                    r"(GET|POST|PUT|PATCH|DELETE)\s+['\"]([^'\"]+)['\"]", line)
                if m:
                    ep = f"{m.group(1)} {m.group(2)}"
                    if ep not in eps:
                        eps.append(ep)
        except Exception as e:
            print(f"WARN: scan failed: {e}", file=sys.stderr)
        coverage["legacy_endpoints"] = sorted(eps)
        print(f"Scanned {args.scan_endpoints}: found {len(eps)} endpoints")

    _recompute_coverage(data)
    save_plan(path, data)

    print(f"Coverage: {coverage['routed_count']}/{coverage['total_count']} "
          f"({coverage['percent']}%)")
    if coverage["unrouted"]:
        print(f"  Unrouted ({len(coverage['unrouted'])}):")
        for ep in coverage["unrouted"][:10]:
            print(f"    - {ep}")
        if len(coverage["unrouted"]) > 10:
            print(f"    ... +{len(coverage['unrouted']) - 10} more")


def _check_cutover_criteria(data: dict, target: str) -> list[str]:
    """Return list of unmet criteria (auto-checkable subset)."""
    unmet = []
    coverage = data.get("coverage", {}) or {}
    rules = data.get("routing_rules", []) or []
    pct = coverage.get("percent", 0) or 0

    if target == "coexist":
        if not data.get("facade", {}).get("exists_yet", False):
            unmet.append("facade.exists_yet must be true")
        if len(rules) < 1:
            unmet.append("routing_rules must have ≥ 1 rule")
        if not data.get("new_module", {}).get("exists_yet", False):
            unmet.append("new_module.exists_yet must be true")
    elif target == "new-primary":
        new_routed = [r for r in rules if r.get("target") == "new"]
        if rules and len(new_routed) / len(rules) < 0.8:
            unmet.append(
                f"≥80% rules must target new (current: "
                f"{round(100*len(new_routed)/len(rules))}%)")
    elif target == "retired":
        legacy_routed = [r for r in rules if r.get("target") == "legacy"]
        if legacy_routed:
            unmet.append(
                f"all rules must target new — {len(legacy_routed)} still "
                f"target legacy")
        if pct < 100:
            unmet.append(f"coverage must be 100% (current: {pct}%)")
    return unmet


def cmd_advance(args):
    path, data = load_plan(args.plan_id)
    current = data.get("state", "legacy-only")
    target = args.state

    if target not in VALID_TRANSITIONS.get(current, []):
        print(f"ERROR: invalid transition {current} → {target}", file=sys.stderr)
        print(f"  valid from {current}: {VALID_TRANSITIONS.get(current, [])}",
              file=sys.stderr)
        sys.exit(1)

    unmet = _check_cutover_criteria(data, target)
    if unmet and not args.force:
        print(f"ERROR: cutover criteria not met for {target}:", file=sys.stderr)
        for u in unmet:
            print(f"  - {u}", file=sys.stderr)
        print(f"\n(use --force to override; recorded in history)", file=sys.stderr)
        sys.exit(1)

    now = now_iso()
    rules_count = len(data.get("routing_rules", []) or [])
    history_entry = {
        "timestamp": now, "from": current, "to": target,
        "note": args.note or "", "routing_count": rules_count,
    }
    if unmet and args.force:
        history_entry["forced"] = True
        history_entry["unmet_criteria"] = unmet
    data["history"].append(history_entry)
    data["state"] = target
    save_plan(path, data)
    print(f"{args.plan_id}: {current} → {target}"
          + (" (forced)" if unmet and args.force else ""))


def cmd_retire(args):
    args.state = "retired"
    args.note = args.note or "final retirement"
    cmd_advance(args)


def main():
    p = argparse.ArgumentParser(prog="sf.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new"); s.set_defaults(fn=cmd_new)
    s.add_argument("slug")
    s.add_argument("--legacy", required=True)
    s.add_argument("--new", required=True)
    s.add_argument("--facade", required=True)
    s.add_argument("--title", default=None)

    s = sub.add_parser("list"); s.set_defaults(fn=cmd_list)
    s.add_argument("--state", default=None)

    s = sub.add_parser("show"); s.set_defaults(fn=cmd_show)
    s.add_argument("plan_id")

    route = sub.add_parser("route"); route_sub = route.add_subparsers(
        dest="route_cmd", required=True)

    s = route_sub.add_parser("add"); s.set_defaults(fn=cmd_route_add)
    s.add_argument("plan_id")
    s.add_argument("--pattern", required=True)
    s.add_argument("--target", required=True, choices=["legacy", "new"])
    s.add_argument("--reason", default="")
    s.add_argument("--rule-id", default=None)

    s = route_sub.add_parser("remove"); s.set_defaults(fn=cmd_route_remove)
    s.add_argument("plan_id")
    s.add_argument("--rule-id", required=True)

    s = sub.add_parser("coverage"); s.set_defaults(fn=cmd_coverage)
    s.add_argument("plan_id")
    s.add_argument("--scan-endpoints", default=None,
                   help="Glob pattern to grep for HTTP routes (e.g., 'src/legacy/**/*.ts')")

    s = sub.add_parser("advance"); s.set_defaults(fn=cmd_advance)
    s.add_argument("plan_id")
    s.add_argument("state", choices=["legacy-only", "coexist", "new-primary", "retired"])
    s.add_argument("--note", default="")
    s.add_argument("--force", action="store_true",
                   help="Override unmet cutover criteria (recorded in history)")

    s = sub.add_parser("retire"); s.set_defaults(fn=cmd_retire)
    s.add_argument("plan_id")
    s.add_argument("--note", default="")
    s.add_argument("--force", action="store_true")

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
