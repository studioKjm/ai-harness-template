#!/usr/bin/env python3
"""
inc.py — Incident Review state machine + action item manager.

Subcommands:
    new <slug> --title "..." --severity sev1|sev2|sev3|sev4 [--reporter NAME]
    list [--status STATUS] [--severity SEV]
    show <incident-id>
    timeline add <incident-id> --time TIME --event "..." [--source SRC]
    analyze <incident-id>             # recording → analyzing
    publish <incident-id>             # analyzing → published (requires blameless_review_passed)
    close <incident-id>                # published → acted-on (requires all action items resolved)
    archive <incident-id>              # acted-on → archived (manual or auto via age)
    action add <incident-id> --description "..." --owner NAME --due DATE [--priority high|medium|low]
    action resolve <incident-id> --action-id ID --status done|dropped|converted [--converted-to ID]
    patterns [--days N]                # Analyze recurring root causes

State machine:
    recording → analyzing → published → acted-on → archived

Storage:
    .harness/incident-review/incidents/<incident-id>.yaml

Exit codes:
    0  success
    1  not found / invalid state / criteria not met
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


INCIDENTS_DIR = Path(".harness/incident-review/incidents")
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "incident.yaml"

VALID_TRANSITIONS = {
    "recording": ["analyzing"],
    "analyzing": ["published"],
    "published": ["acted-on"],
    "acted-on": ["archived"],
    "archived": [],
}

VALID_SEVERITIES = ("sev1", "sev2", "sev3", "sev4")
VALID_AI_STATUS = ("open", "in-progress", "done", "dropped", "converted")


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", s.lower())
    return re.sub(r"-+", "-", s).strip("-")


def load_incident(inc_id: str) -> tuple[Path, dict]:
    path = INCIDENTS_DIR / f"{inc_id}.yaml"
    if not path.exists():
        print(f"ERROR: incident not found: {inc_id}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return path, yaml.safe_load(f) or {}


def save_incident(path: Path, data: dict) -> None:
    data["updated_at"] = now_iso()
    with path.open("w") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)


def cmd_new(args):
    if args.severity not in VALID_SEVERITIES:
        print(f"ERROR: --severity must be one of {VALID_SEVERITIES}", file=sys.stderr)
        sys.exit(2)

    today = datetime.date.today().isoformat()
    inc_id = f"inc-{today}-{slugify(args.slug)}"
    path = INCIDENTS_DIR / f"{inc_id}.yaml"
    if path.exists():
        print(f"ERROR: incident already exists: {inc_id}", file=sys.stderr)
        sys.exit(1)
    INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)

    if not TEMPLATE.exists():
        print(f"ERROR: template not found at {TEMPLATE}", file=sys.stderr)
        sys.exit(2)

    with TEMPLATE.open() as f:
        inc = yaml.safe_load(f)

    now = now_iso()
    inc["id"] = inc_id
    inc["created_at"] = now
    inc["updated_at"] = now
    inc["title"] = args.title
    inc["severity"] = args.severity
    inc["reporter"] = args.reporter or ""
    inc["status"] = "recording"
    inc["history"] = [{
        "timestamp": now, "from": None, "to": "recording",
        "note": "incident opened",
    }]
    inc["timeline"] = []
    inc["action_items"] = []
    inc["blameless_review_passed"] = False

    save_incident(path, inc)
    print(f"Opened incident: {inc_id}")
    print(f"  Title:    {args.title}")
    print(f"  Severity: {args.severity}")
    print()
    print(f"Next:")
    print(f"  - Add timeline entries: /incident timeline add {inc_id} --time T --event \"...\"")
    print(f"  - When response is over: /incident analyze {inc_id}")


def cmd_list(args):
    if not INCIDENTS_DIR.exists():
        print("(no incidents)")
        return
    rows = []
    for f in sorted(INCIDENTS_DIR.glob("*.yaml")):
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if args.status and data.get("status") != args.status:
            continue
        if args.severity and data.get("severity") != args.severity:
            continue
        ai_count = len(data.get("action_items", []) or [])
        ai_open = sum(1 for ai in (data.get("action_items") or [])
                      if ai.get("status") in ("open", "in-progress"))
        rows.append((data.get("id", "?"), data.get("severity", "?"),
                     data.get("status", "?"), f"{ai_open}/{ai_count}",
                     data.get("title", "")[:50]))

    if not rows:
        print("(no matching incidents)")
        return

    width = max(len(r[0]) for r in rows)
    print(f"  {'ID':<{width}}  SEV   STATUS        OPEN/TOTAL  TITLE")
    for iid, sev, status, ai, title in rows:
        print(f"  {iid:<{width}}  {sev:<5} [{status:<11}] {ai:<10}  {title}")


def cmd_show(args):
    _, data = load_incident(args.incident_id)
    print(yaml.dump(data, sort_keys=False, allow_unicode=True))


def cmd_timeline_add(args):
    path, data = load_incident(args.incident_id)
    timeline = data.setdefault("timeline", [])
    timeline.append({
        "time": args.time,
        "event": args.event,
        "source": args.source or "manual",
    })
    timeline.sort(key=lambda x: x.get("time", ""))
    save_incident(path, data)
    print(f"Added timeline entry: {args.time} — {args.event[:60]}")


def transition(inc_id: str, target: str, note: str = ""):
    path, data = load_incident(inc_id)
    current = data.get("status", "recording")
    if target not in VALID_TRANSITIONS.get(current, []):
        print(f"ERROR: invalid transition {current} → {target}", file=sys.stderr)
        print(f"  valid from {current}: {VALID_TRANSITIONS.get(current, [])}",
              file=sys.stderr)
        sys.exit(1)
    now = now_iso()
    data.setdefault("history", []).append({
        "timestamp": now, "from": current, "to": target, "note": note,
    })
    data["status"] = target
    save_incident(path, data)
    print(f"{inc_id}: {current} → {target}")


def cmd_analyze(args):
    transition(args.incident_id, "analyzing",
               note="response complete — entering RCA phase")


def cmd_publish(args):
    path, data = load_incident(args.incident_id)
    current = data.get("status", "recording")
    if current != "analyzing":
        print(f"ERROR: can only publish from 'analyzing' state (current: {current})",
              file=sys.stderr)
        if current == "recording":
            print(f"  Run /incident analyze {args.incident_id} first.",
                  file=sys.stderr)
        sys.exit(1)
    if not (data.get("five_whys") or {}).get("root_cause"):
        print("ERROR: five_whys.root_cause must be filled before publishing.",
              file=sys.stderr)
        print("  Drill down 5 whys in the yaml until you reach a system-level cause.",
              file=sys.stderr)
        sys.exit(1)
    if not data.get("blameless_review_passed", False):
        print("ERROR: blameless_review_passed must be true before publishing.",
              file=sys.stderr)
        print("  Review the incident yaml — remove blame language, focus on systems.",
              file=sys.stderr)
        print("  Then set 'blameless_review_passed: true' and re-run publish.",
              file=sys.stderr)
        sys.exit(1)
    transition(args.incident_id, "published",
               note="postmortem published")


def cmd_close(args):
    path, data = load_incident(args.incident_id)
    items = data.get("action_items", []) or []
    unresolved = [
        ai for ai in items
        if ai.get("status") in ("open", "in-progress")
    ]
    if unresolved and not args.force:
        print(f"ERROR: {len(unresolved)} action item(s) still open/in-progress:",
              file=sys.stderr)
        for ai in unresolved[:5]:
            print(f"  - {ai.get('id')}: {ai.get('description', '')[:60]} "
                  f"(owner: {ai.get('owner', '?')}, status: {ai.get('status')})",
                  file=sys.stderr)
        if len(unresolved) > 5:
            print(f"  ... +{len(unresolved) - 5} more", file=sys.stderr)
        print(f"\nResolve via: /incident-action resolve {args.incident_id} --action-id ID --status done|dropped|converted",
              file=sys.stderr)
        sys.exit(1)
    transition(args.incident_id, "acted-on",
               note=f"all {len(items)} action items resolved"
                    + (" (forced)" if unresolved and args.force else ""))


def cmd_archive(args):
    transition(args.incident_id, "archived", note=args.note or "archived")


def cmd_action_add(args):
    path, data = load_incident(args.incident_id)
    items = data.setdefault("action_items", [])
    aid = args.action_id or f"ai-{len(items) + 1}"
    if any(ai.get("id") == aid for ai in items):
        print(f"ERROR: action_id '{aid}' already exists", file=sys.stderr)
        sys.exit(1)
    items.append({
        "id": aid,
        "description": args.description,
        "owner": args.owner,
        "due_date": args.due,
        "status": "open",
        "priority": args.priority,
        "converted_to": None,
        "notes": "",
        "created_at": now_iso(),
    })
    save_incident(path, data)
    print(f"Added action item {aid}: {args.description[:60]}")
    print(f"  Owner: {args.owner}, Due: {args.due}, Priority: {args.priority}")


def cmd_action_resolve(args):
    path, data = load_incident(args.incident_id)
    items = data.get("action_items", []) or []
    target = next((ai for ai in items if ai.get("id") == args.action_id), None)
    if not target:
        print(f"ERROR: action_id '{args.action_id}' not found", file=sys.stderr)
        sys.exit(1)
    if args.status not in VALID_AI_STATUS:
        print(f"ERROR: --status must be one of {VALID_AI_STATUS}", file=sys.stderr)
        sys.exit(2)
    if args.status == "converted" and not args.converted_to:
        print("ERROR: --converted-to required when status=converted", file=sys.stderr)
        sys.exit(2)
    target["status"] = args.status
    target["resolved_at"] = now_iso()
    if args.converted_to:
        target["converted_to"] = args.converted_to
    save_incident(path, data)
    print(f"Resolved {args.action_id}: {args.status}"
          + (f" → {args.converted_to}" if args.converted_to else ""))


def cmd_patterns(args):
    """Aggregate root causes and contributing factors across recent incidents."""
    if not INCIDENTS_DIR.exists():
        print("(no incidents)")
        return
    cutoff = datetime.datetime.now(datetime.timezone.utc) - \
             datetime.timedelta(days=args.days)

    root_causes = {}
    factor_categories = {}
    severity_counts = {s: 0 for s in VALID_SEVERITIES}
    total = 0

    for f in INCIDENTS_DIR.glob("*.yaml"):
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        created = data.get("created_at", "")
        if created:
            try:
                dt = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
                if dt < cutoff:
                    continue
            except Exception:
                pass

        total += 1
        sev = data.get("severity", "sev3")
        if sev in severity_counts:
            severity_counts[sev] += 1

        rc = (data.get("five_whys") or {}).get("root_cause", "").strip().lower()
        if rc:
            root_causes[rc] = root_causes.get(rc, 0) + 1

        for cf in data.get("contributing_factors") or []:
            cat = (cf.get("category") if isinstance(cf, dict) else "uncategorized") or "uncategorized"
            factor_categories[cat] = factor_categories.get(cat, 0) + 1

    print(f"Incident pattern analysis (last {args.days} days)")
    print("─" * 50)
    print(f"Total incidents: {total}")
    if total == 0:
        return
    print(f"By severity:")
    for sev, count in severity_counts.items():
        print(f"  {sev}: {count}")
    print()
    print(f"Top root causes (recurring):")
    for rc, count in sorted(root_causes.items(), key=lambda x: -x[1])[:5]:
        if count > 1:
            print(f"  [{count}x] {rc[:70]}")
    if not any(c > 1 for c in root_causes.values()):
        print("  (no recurring root causes — every incident had unique root cause)")
    print()
    print(f"Contributing factor categories:")
    for cat, count in sorted(factor_categories.items(), key=lambda x: -x[1]):
        print(f"  {count:>3}x  {cat}")


def main():
    p = argparse.ArgumentParser(prog="inc.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new"); s.set_defaults(fn=cmd_new)
    s.add_argument("slug")
    s.add_argument("--title", required=True)
    s.add_argument("--severity", required=True)
    s.add_argument("--reporter", default=None)

    s = sub.add_parser("list"); s.set_defaults(fn=cmd_list)
    s.add_argument("--status", default=None)
    s.add_argument("--severity", default=None)

    s = sub.add_parser("show"); s.set_defaults(fn=cmd_show)
    s.add_argument("incident_id")

    tl = sub.add_parser("timeline"); tl_sub = tl.add_subparsers(dest="tl_cmd", required=True)
    s = tl_sub.add_parser("add"); s.set_defaults(fn=cmd_timeline_add)
    s.add_argument("incident_id")
    s.add_argument("--time", required=True)
    s.add_argument("--event", required=True)
    s.add_argument("--source", default="manual")

    for cmd_name, fn in [("analyze", cmd_analyze), ("publish", cmd_publish)]:
        s = sub.add_parser(cmd_name); s.set_defaults(fn=fn)
        s.add_argument("incident_id")

    s = sub.add_parser("close"); s.set_defaults(fn=cmd_close)
    s.add_argument("incident_id")
    s.add_argument("--force", action="store_true")

    s = sub.add_parser("archive"); s.set_defaults(fn=cmd_archive)
    s.add_argument("incident_id")
    s.add_argument("--note", default="")

    act = sub.add_parser("action"); act_sub = act.add_subparsers(dest="act_cmd", required=True)

    s = act_sub.add_parser("add"); s.set_defaults(fn=cmd_action_add)
    s.add_argument("incident_id")
    s.add_argument("--description", required=True)
    s.add_argument("--owner", required=True)
    s.add_argument("--due", required=True)
    s.add_argument("--priority", default="medium", choices=["high", "medium", "low"])
    s.add_argument("--action-id", default=None)

    s = act_sub.add_parser("resolve"); s.set_defaults(fn=cmd_action_resolve)
    s.add_argument("incident_id")
    s.add_argument("--action-id", required=True)
    s.add_argument("--status", required=True)
    s.add_argument("--converted-to", default=None)

    s = sub.add_parser("patterns"); s.set_defaults(fn=cmd_patterns)
    s.add_argument("--days", type=int, default=90)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
