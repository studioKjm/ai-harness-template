#!/usr/bin/env python3
"""
rfc.py — RFC state machine + change-link manager.

Subcommands:
    new <slug> --title "..." [--authors A1 A2 ...]
    list [--status STATUS]
    show <rfc-id>
    propose <rfc-id>                 # draft → proposed
    accept <rfc-id> --decided-by NAME --rationale "..."
    reject <rfc-id> --decided-by NAME --rationale "..."
    supersede <rfc-id> --by NEW_RFC_ID
    link <rfc-id> --files F1 [F2 ...] [--modules M1 [M2 ...]]
    declare-pr --rfc-id RID --pr-files F1 [F2 ...]   # link a working set to RFC

State machine:
    draft → proposed → accepted | rejected
    accepted → superseded

Storage:
    .harness/rfc-driven/rfcs/<rfc-id>.yaml
    .harness/rfc-driven/.rfc-links.yaml   (file→rfc-id mapping for gate)
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


RFCS_DIR = Path(".harness/rfc-driven/rfcs")
LINKS_FILE = Path(".harness/rfc-driven/.rfc-links.yaml")
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "rfc.yaml"

VALID_TRANSITIONS = {
    "draft": ["proposed"],
    "proposed": ["accepted", "rejected", "draft"],
    "accepted": ["superseded"],
    "rejected": [],
    "superseded": [],
}


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", s.lower())
    return re.sub(r"-+", "-", s).strip("-")


def load_rfc(rfc_id: str) -> tuple[Path, dict]:
    path = RFCS_DIR / f"{rfc_id}.yaml"
    if not path.exists():
        print(f"ERROR: RFC not found: {rfc_id}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return path, yaml.safe_load(f) or {}


def save_rfc(path: Path, data: dict) -> None:
    data["updated_at"] = now_iso()
    with path.open("w") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)


def cmd_new(args):
    today = datetime.date.today().isoformat()
    rfc_id = f"rfc-{today}-{slugify(args.slug)}"
    path = RFCS_DIR / f"{rfc_id}.yaml"
    if path.exists():
        print(f"ERROR: RFC already exists: {rfc_id}", file=sys.stderr)
        sys.exit(1)
    RFCS_DIR.mkdir(parents=True, exist_ok=True)

    if not TEMPLATE.exists():
        print(f"ERROR: template not found at {TEMPLATE}", file=sys.stderr)
        sys.exit(2)

    with TEMPLATE.open() as f:
        rfc = yaml.safe_load(f)

    now = now_iso()
    rfc["id"] = rfc_id
    rfc["created_at"] = now
    rfc["updated_at"] = now
    rfc["title"] = args.title
    rfc["authors"] = args.authors or []
    rfc["status"] = "draft"
    rfc["history"] = [{
        "timestamp": now, "from": None, "to": "draft",
        "note": "RFC created",
    }]
    rfc["alternatives"] = []
    rfc["drawbacks"] = []
    rfc["open_questions"] = []
    rfc["decision"] = {"date": None, "decided_by": "",
                       "rationale": "", "conditions": []}
    rfc["links"] = {
        "related_rfcs": [], "supersedes": None, "superseded_by": None,
        "related_adrs": [], "related_incidents": [], "related_seeds": [],
        "governs_files": [], "governs_modules": [],
    }
    rfc["required_approvals"] = []

    save_rfc(path, rfc)
    print(f"Created RFC: {rfc_id}")
    print(f"  Title:   {args.title}")
    print(f"  Authors: {', '.join(args.authors or []) or '(none)'}")
    print(f"  Status:  draft")
    print()
    print(f"Next:")
    print(f"  - Edit yaml: fill summary, motivation, design, alternatives, drawbacks")
    print(f"  - When ready for review: /rfc propose {rfc_id}")


def cmd_list(args):
    if not RFCS_DIR.exists():
        print("(no RFCs)")
        return
    rows = []
    for f in sorted(RFCS_DIR.glob("*.yaml")):
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if args.status and data.get("status") != args.status:
            continue
        title = data.get("title", "")[:50]
        authors = ", ".join(data.get("authors") or [])[:20]
        rows.append((data.get("id", "?"), data.get("status", "?"),
                     authors, title))

    if not rows:
        print("(no matching RFCs)")
        return
    width = max(len(r[0]) for r in rows)
    for rid, status, authors, title in rows:
        print(f"  {rid:<{width}}  [{status:<11}]  {authors:<20}  {title}")


def cmd_show(args):
    print(yaml.dump(load_rfc(args.rfc_id)[1], sort_keys=False, allow_unicode=True))


def _validate_proposable(data: dict) -> list[str]:
    """Return list of unmet criteria for moving to 'proposed'."""
    issues = []
    if not (data.get("summary") or "").strip():
        issues.append("summary must be filled")
    if not (data.get("motivation") or "").strip():
        issues.append("motivation must be filled")
    if not (data.get("design") or "").strip():
        issues.append("design must be filled")
    alts = data.get("alternatives") or []
    if len(alts) < 2:
        issues.append(f"alternatives must have ≥2 entries (current: {len(alts)})")
    drawbacks = data.get("drawbacks") or []
    if len(drawbacks) < 1:
        issues.append("drawbacks must have ≥1 entry (be honest about tradeoffs)")
    return issues


def cmd_propose(args):
    path, data = load_rfc(args.rfc_id)
    current = data.get("status", "draft")
    if current != "draft":
        print(f"ERROR: can only propose from 'draft' (current: {current})",
              file=sys.stderr)
        sys.exit(1)

    issues = _validate_proposable(data)
    if issues and not args.force:
        print(f"ERROR: RFC not ready for proposal:", file=sys.stderr)
        for iss in issues:
            print(f"  - {iss}", file=sys.stderr)
        print(f"\nFix and re-run, or use --force (recorded in history).",
              file=sys.stderr)
        sys.exit(1)

    now = now_iso()
    history_entry = {
        "timestamp": now, "from": "draft", "to": "proposed",
        "note": "submitted for review",
    }
    if issues and args.force:
        history_entry["forced"] = True
        history_entry["unmet_criteria"] = issues
    data.setdefault("history", []).append(history_entry)
    data["status"] = "proposed"
    save_rfc(path, data)
    print(f"{args.rfc_id}: draft → proposed"
          + (" (forced)" if issues and args.force else ""))


def _decision_transition(rfc_id: str, target: str, decided_by: str,
                          rationale: str, conditions: list = None):
    path, data = load_rfc(rfc_id)
    current = data.get("status", "draft")
    if current != "proposed":
        print(f"ERROR: can only {target} from 'proposed' (current: {current})",
              file=sys.stderr)
        sys.exit(1)

    if not decided_by.strip():
        print("ERROR: --decided-by is required", file=sys.stderr)
        sys.exit(2)
    if not rationale.strip():
        print("ERROR: --rationale is required", file=sys.stderr)
        sys.exit(2)

    now = now_iso()
    data.setdefault("history", []).append({
        "timestamp": now, "from": "proposed", "to": target,
        "note": f"{target} by {decided_by}: {rationale[:80]}",
    })
    data["decision"] = {
        "date": datetime.date.today().isoformat(),
        "decided_by": decided_by,
        "rationale": rationale,
        "conditions": conditions or [],
    }
    data["status"] = target
    save_rfc(path, data)
    print(f"{rfc_id}: proposed → {target}")
    print(f"  Decided by: {decided_by}")
    print(f"  Rationale:  {rationale[:120]}")


def cmd_accept(args):
    _decision_transition(args.rfc_id, "accepted",
                          args.decided_by, args.rationale, args.conditions)


def cmd_reject(args):
    _decision_transition(args.rfc_id, "rejected",
                          args.decided_by, args.rationale)


def cmd_supersede(args):
    path, data = load_rfc(args.rfc_id)
    current = data.get("status", "draft")
    if current != "accepted":
        print(f"ERROR: can only supersede from 'accepted' (current: {current})",
              file=sys.stderr)
        sys.exit(1)
    new_path = RFCS_DIR / f"{args.by}.yaml"
    if not new_path.exists():
        print(f"ERROR: superseding RFC not found: {args.by}", file=sys.stderr)
        sys.exit(1)
    with new_path.open() as f:
        new_data = yaml.safe_load(f) or {}
    if new_data.get("status") != "accepted":
        print(f"ERROR: superseding RFC must be 'accepted' (current: {new_data.get('status')})",
              file=sys.stderr)
        sys.exit(1)

    now = now_iso()
    data.setdefault("history", []).append({
        "timestamp": now, "from": "accepted", "to": "superseded",
        "note": f"superseded by {args.by}",
    })
    data["status"] = "superseded"
    data.setdefault("links", {})["superseded_by"] = args.by
    save_rfc(path, data)

    # Update the new RFC to point back
    new_data.setdefault("links", {})["supersedes"] = args.rfc_id
    save_rfc(new_path, new_data)
    print(f"{args.rfc_id}: accepted → superseded (by {args.by})")


def cmd_link(args):
    path, data = load_rfc(args.rfc_id)
    if data.get("status") != "accepted":
        print(f"ERROR: can only link files to 'accepted' RFCs (current: {data.get('status')})",
              file=sys.stderr)
        sys.exit(1)
    links = data.setdefault("links", {})
    if args.files:
        existing = set(links.get("governs_files") or [])
        existing.update(args.files)
        links["governs_files"] = sorted(existing)
    if args.modules:
        existing = set(links.get("governs_modules") or [])
        existing.update(args.modules)
        links["governs_modules"] = sorted(existing)
    save_rfc(path, data)

    # Update reverse-lookup file
    _update_links_file()
    print(f"Linked {args.rfc_id}: "
          f"+{len(args.files or [])} files, +{len(args.modules or [])} modules")


def _update_links_file():
    """Regenerate .rfc-links.yaml from all accepted RFCs."""
    if not RFCS_DIR.exists():
        return
    file_to_rfc: dict[str, list[str]] = {}
    module_to_rfc: dict[str, list[str]] = {}
    for f in RFCS_DIR.glob("*.yaml"):
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if data.get("status") != "accepted":
            continue
        rfc_id = data.get("id", "?")
        links = data.get("links") or {}
        for path in links.get("governs_files") or []:
            file_to_rfc.setdefault(path, []).append(rfc_id)
        for mod in links.get("governs_modules") or []:
            module_to_rfc.setdefault(mod, []).append(rfc_id)

    out = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "files": file_to_rfc,
        "modules": module_to_rfc,
    }
    LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LINKS_FILE.open("w") as f:
        yaml.dump(out, f, sort_keys=False, allow_unicode=True)


def cmd_declare_pr(args):
    """Declare that a working set of files is governed by a specific RFC.
    The gate uses this for warning suppression."""
    path, data = load_rfc(args.rfc_id)
    if data.get("status") != "accepted":
        print(f"ERROR: --rfc-id must be 'accepted' (current: {data.get('status')})",
              file=sys.stderr)
        sys.exit(1)
    cmd_link(argparse.Namespace(
        rfc_id=args.rfc_id, files=args.pr_files, modules=[]))
    print(f"Declared {len(args.pr_files)} files governed by {args.rfc_id}")


def main():
    p = argparse.ArgumentParser(prog="rfc.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new"); s.set_defaults(fn=cmd_new)
    s.add_argument("slug")
    s.add_argument("--title", required=True)
    s.add_argument("--authors", nargs="*", default=[])

    s = sub.add_parser("list"); s.set_defaults(fn=cmd_list)
    s.add_argument("--status", default=None)

    s = sub.add_parser("show"); s.set_defaults(fn=cmd_show)
    s.add_argument("rfc_id")

    s = sub.add_parser("propose"); s.set_defaults(fn=cmd_propose)
    s.add_argument("rfc_id")
    s.add_argument("--force", action="store_true")

    s = sub.add_parser("accept"); s.set_defaults(fn=cmd_accept)
    s.add_argument("rfc_id")
    s.add_argument("--decided-by", required=True)
    s.add_argument("--rationale", required=True)
    s.add_argument("--conditions", nargs="*", default=[])

    s = sub.add_parser("reject"); s.set_defaults(fn=cmd_reject)
    s.add_argument("rfc_id")
    s.add_argument("--decided-by", required=True)
    s.add_argument("--rationale", required=True)

    s = sub.add_parser("supersede"); s.set_defaults(fn=cmd_supersede)
    s.add_argument("rfc_id")
    s.add_argument("--by", required=True, dest="by")

    s = sub.add_parser("link"); s.set_defaults(fn=cmd_link)
    s.add_argument("rfc_id")
    s.add_argument("--files", nargs="*", default=[])
    s.add_argument("--modules", nargs="*", default=[])

    s = sub.add_parser("declare-pr"); s.set_defaults(fn=cmd_declare_pr)
    s.add_argument("--rfc-id", required=True)
    s.add_argument("--pr-files", nargs="+", required=True)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
