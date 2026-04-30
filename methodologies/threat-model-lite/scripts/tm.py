#!/usr/bin/env python3
"""
tm.py — Threat Model (Lite) state machine + STRIDE entry manager.

Subcommands:
    new <slug> --target-kind story|spike|feature|endpoint|module --target-ref REF [--description "..."]
    list [--status STATUS]
    show <model-id>
    add <model-id> --category S|T|R|I|D|E --threat "..." --mitigation "..." [--likelihood ...] [--impact ...]
    review <model-id>                 # draft → reviewed (validates STRIDE coverage)
    approve <model-id>                # reviewed → approved
    apply <model-id>                  # approved → applied
    link <model-id> --to story-id|spike-id|adr-id
    scan [--path GLOB]                # scan codebase against triggers, suggest models

State machine:
    draft → reviewed → approved → applied

Storage:
    .harness/threat-model-lite/models/<model-id>.yaml

Exit codes:
    0  success
    1  not found / invalid state / coverage incomplete
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


MODELS_DIR = Path(".harness/threat-model-lite/models")
TRIGGERS_FILE = Path(".harness/threat-model-lite/triggers.yaml")
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "threat-model.yaml"

VALID_TRANSITIONS = {
    "draft": ["reviewed"],
    "reviewed": ["approved", "draft"],
    "approved": ["applied", "reviewed"],
    "applied": [],
}

CATEGORY_MAP = {
    "S": "spoofing",
    "T": "tampering",
    "R": "repudiation",
    "I": "information_disclosure",
    "D": "denial_of_service",
    "E": "elevation_of_privilege",
}

STRIDE_CATS = list(CATEGORY_MAP.values())


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", s.lower())
    return re.sub(r"-+", "-", s).strip("-")


def load_model(model_id: str) -> tuple[Path, dict]:
    path = MODELS_DIR / f"{model_id}.yaml"
    if not path.exists():
        print(f"ERROR: threat model not found: {model_id}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return path, yaml.safe_load(f) or {}


def save_model(path: Path, data: dict) -> None:
    data["updated_at"] = now_iso()
    with path.open("w") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)


def cmd_new(args):
    today = datetime.date.today().isoformat()
    model_id = f"tm-{today}-{slugify(args.slug)}"
    path = MODELS_DIR / f"{model_id}.yaml"
    if path.exists():
        print(f"ERROR: threat model already exists: {model_id}", file=sys.stderr)
        sys.exit(1)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if not TEMPLATE.exists():
        print(f"ERROR: template not found at {TEMPLATE}", file=sys.stderr)
        sys.exit(2)

    with TEMPLATE.open() as f:
        m = yaml.safe_load(f)

    now = now_iso()
    m["id"] = model_id
    m["created_at"] = now
    m["updated_at"] = now
    m["target"] = {
        "kind": args.target_kind,
        "ref": args.target_ref,
        "description": args.description or "",
    }
    m["status"] = "draft"
    m["history"] = [{
        "timestamp": now, "from": None, "to": "draft",
        "note": "model created",
    }]
    # Initialize STRIDE structure with empty arrays
    m["stride"] = {cat: {"threats": []} for cat in STRIDE_CATS}
    m["assets"] = []
    m["trust_boundaries"] = []
    m["residual_risks"] = []
    m["links"] = {
        "story": args.target_ref if args.target_kind == "story" else None,
        "spike": args.target_ref if args.target_kind == "spike" else None,
        "related_adrs": [],
        "related_incidents": [],
        "related_models": [],
    }

    save_model(path, m)
    print(f"Created threat model: {model_id}")
    print(f"  Target: {args.target_kind} → {args.target_ref}")
    print(f"  Status: draft")
    print()
    print(f"Next:")
    print(f"  - Add assets and trust_boundaries (edit yaml)")
    print(f"  - Add threats per STRIDE category:")
    print(f"      /threat add {model_id} --category S --threat \"...\" --mitigation \"...\"")
    print(f"  - When all categories covered: /threat review {model_id}")


def cmd_list(args):
    if not MODELS_DIR.exists():
        print("(no threat models)")
        return
    rows = []
    for f in sorted(MODELS_DIR.glob("*.yaml")):
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if args.status and data.get("status") != args.status:
            continue
        target = data.get("target", {}) or {}
        threat_count = sum(
            len((data.get("stride", {}) or {}).get(c, {}).get("threats", []) or [])
            for c in STRIDE_CATS
        )
        rows.append((data.get("id", "?"), data.get("status", "?"),
                     f"{target.get('kind', '?')}:{target.get('ref', '?')}",
                     f"{threat_count} threats",
                     (target.get("description", "") or "")[:40]))

    if not rows:
        print("(no matching threat models)")
        return

    width = max(len(r[0]) for r in rows)
    for mid, status, target, count, desc in rows:
        print(f"  {mid:<{width}}  [{status:<10}]  {target:<28}  {count:<12}  {desc}")


def cmd_show(args):
    _, data = load_model(args.model_id)
    print(yaml.dump(data, sort_keys=False, allow_unicode=True))


def cmd_add(args):
    path, data = load_model(args.model_id)
    if args.category not in CATEGORY_MAP:
        print(f"ERROR: --category must be one of {list(CATEGORY_MAP.keys())}",
              file=sys.stderr)
        sys.exit(2)

    cat_full = CATEGORY_MAP[args.category]
    stride = data.setdefault("stride", {})
    cat_block = stride.setdefault(cat_full, {"threats": []})
    threats = cat_block.setdefault("threats", [])

    threat_id = args.threat_id or f"{args.category}-{len(threats) + 1}"
    if any(t.get("id") == threat_id for t in threats):
        print(f"ERROR: threat_id '{threat_id}' already exists", file=sys.stderr)
        sys.exit(1)

    mitigations = args.mitigation if isinstance(args.mitigation, list) else [args.mitigation]
    threats.append({
        "id": threat_id,
        "description": args.threat,
        "likelihood": args.likelihood,
        "impact": args.impact,
        "mitigations": mitigations,
        "mitigation_status": args.mitigation_status,
    })
    save_model(path, data)
    print(f"Added threat {threat_id} ({cat_full}): {args.threat[:60]}")


def _coverage_check(data: dict) -> dict:
    """Return per-category coverage status."""
    stride = data.get("stride", {}) or {}
    out = {}
    for cat in STRIDE_CATS:
        block = stride.get(cat, {}) or {}
        threats = block.get("threats") or []
        na_reason = block.get("not_applicable_reason")
        if threats:
            out[cat] = "covered"
        elif na_reason:
            out[cat] = "n/a"
        else:
            out[cat] = "missing"
    return out


def cmd_review(args):
    path, data = load_model(args.model_id)
    coverage = _coverage_check(data)
    missing = [c for c, s in coverage.items() if s == "missing"]
    if missing and not args.override:
        print(f"ERROR: STRIDE coverage incomplete:", file=sys.stderr)
        for c in missing:
            print(f"  - {c}: missing (no threats and no 'not_applicable_reason')",
                  file=sys.stderr)
        print("\nFix: add threats via /threat add, OR mark category N/A:", file=sys.stderr)
        print("  edit yaml: stride.<category>.not_applicable_reason: \"...\"",
              file=sys.stderr)
        print("\nOverride: /threat review <id> --override \"<reason>\"", file=sys.stderr)
        sys.exit(1)

    current = data.get("status", "draft")
    if current != "draft":
        print(f"ERROR: can only review from 'draft' (current: {current})",
              file=sys.stderr)
        sys.exit(1)

    note = "STRIDE coverage validated"
    if missing and args.override:
        note = f"reviewed with override: {args.override}"

    now = now_iso()
    data["history"].append({
        "timestamp": now, "from": "draft", "to": "reviewed",
        "note": note, "coverage": coverage,
    })
    if missing and args.override:
        data["history"][-1]["overridden_categories"] = missing
        data["history"][-1]["override_reason"] = args.override
    data["status"] = "reviewed"
    save_model(path, data)
    print(f"{args.model_id}: draft → reviewed"
          + (" (override)" if missing and args.override else ""))


def cmd_approve(args):
    path, data = load_model(args.model_id)
    current = data.get("status", "draft")
    if current != "reviewed":
        print(f"ERROR: can only approve from 'reviewed' (current: {current})",
              file=sys.stderr)
        sys.exit(1)
    now = now_iso()
    data["history"].append({
        "timestamp": now, "from": "reviewed", "to": "approved",
        "note": "approved for implementation",
    })
    data["status"] = "approved"
    save_model(path, data)
    print(f"{args.model_id}: reviewed → approved")


def cmd_apply(args):
    path, data = load_model(args.model_id)
    current = data.get("status", "draft")
    if current != "approved":
        print(f"ERROR: can only apply from 'approved' (current: {current})",
              file=sys.stderr)
        sys.exit(1)
    # Check that all 'planned' mitigations are now 'implemented' or 'deferred'
    stride = data.get("stride", {}) or {}
    pending = []
    for cat in STRIDE_CATS:
        for t in (stride.get(cat, {}) or {}).get("threats", []) or []:
            if t.get("mitigation_status") == "planned":
                pending.append((cat, t.get("id"), t.get("description", "")[:40]))
    if pending and not args.force:
        print(f"ERROR: {len(pending)} mitigation(s) still 'planned':", file=sys.stderr)
        for cat, tid, desc in pending[:5]:
            print(f"  - [{cat}] {tid}: {desc}", file=sys.stderr)
        print("\nUpdate mitigation_status to 'implemented'/'deferred'/'accepted', "
              "or use --force.", file=sys.stderr)
        sys.exit(1)
    now = now_iso()
    data["history"].append({
        "timestamp": now, "from": "approved", "to": "applied",
        "note": "mitigations implemented" + (" (forced)" if pending and args.force else ""),
    })
    data["status"] = "applied"
    save_model(path, data)
    print(f"{args.model_id}: approved → applied")


def cmd_link(args):
    path, data = load_model(args.model_id)
    links = data.setdefault("links", {})
    target = args.to
    # Detect target type by prefix
    if target.startswith("st-"):
        links["story"] = target
    elif target.startswith("sp-"):
        links["spike"] = target
    elif target.startswith("ADR-") or target.startswith("adr-"):
        links.setdefault("related_adrs", []).append(target)
    elif target.startswith("inc-"):
        links.setdefault("related_incidents", []).append(target)
    elif target.startswith("tm-"):
        links.setdefault("related_models", []).append(target)
    else:
        print(f"ERROR: unrecognized target prefix: {target}", file=sys.stderr)
        print(f"  Recognized: st-* | sp-* | ADR-* | inc-* | tm-*", file=sys.stderr)
        sys.exit(2)
    save_model(path, data)
    print(f"Linked {args.model_id} → {target}")


def cmd_scan(args):
    """Scan codebase for files matching trigger patterns, list those without
    a threat model."""
    if not TRIGGERS_FILE.exists():
        print(f"ERROR: triggers file not found at {TRIGGERS_FILE}", file=sys.stderr)
        print("  Initialize with: /threat-triggers init", file=sys.stderr)
        sys.exit(1)
    with TRIGGERS_FILE.open() as f:
        triggers = yaml.safe_load(f) or {}

    sensitive_paths = triggers.get("sensitive_paths") or []
    if not sensitive_paths:
        print("(no sensitive paths configured)")
        return

    # Find existing models' targets
    existing_targets = set()
    if MODELS_DIR.exists():
        for f in MODELS_DIR.glob("*.yaml"):
            with f.open() as fh:
                data = yaml.safe_load(fh) or {}
            target = data.get("target", {}).get("ref", "")
            if target:
                existing_targets.add(target)

    # Glob match (simplified — uses Path.glob)
    matches = []
    base = Path(args.path or ".")
    for pattern in sensitive_paths:
        # Strip ** prefix, use rglob
        clean = pattern.replace("**/", "").replace("/**", "")
        for p in base.rglob(clean):
            if p.is_dir() and not any(p.iterdir()):
                continue
            matches.append(str(p))

    matches = sorted(set(matches))
    print(f"Sensitive paths matched: {len(matches)}")
    uncovered = [m for m in matches if m not in existing_targets]
    if uncovered:
        print(f"Without threat model:")
        for m in uncovered[:20]:
            print(f"  - {m}")
        if len(uncovered) > 20:
            print(f"  ... +{len(uncovered) - 20} more")
        print(f"\nCreate model: /threat new <slug> --target-kind module --target-ref <path>")


def main():
    p = argparse.ArgumentParser(prog="tm.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new"); s.set_defaults(fn=cmd_new)
    s.add_argument("slug")
    s.add_argument("--target-kind", required=True,
                   choices=["story", "spike", "feature", "endpoint", "module"])
    s.add_argument("--target-ref", required=True)
    s.add_argument("--description", default="")

    s = sub.add_parser("list"); s.set_defaults(fn=cmd_list)
    s.add_argument("--status", default=None)

    s = sub.add_parser("show"); s.set_defaults(fn=cmd_show)
    s.add_argument("model_id")

    s = sub.add_parser("add"); s.set_defaults(fn=cmd_add)
    s.add_argument("model_id")
    s.add_argument("--category", required=True, choices=list(CATEGORY_MAP.keys()))
    s.add_argument("--threat", required=True)
    s.add_argument("--mitigation", required=True, action="append",
                   help="May be repeated for multiple mitigations")
    s.add_argument("--likelihood", default="medium",
                   choices=["low", "medium", "high"])
    s.add_argument("--impact", default="medium",
                   choices=["low", "medium", "high"])
    s.add_argument("--mitigation-status", default="planned",
                   choices=["planned", "implemented", "deferred", "accepted"])
    s.add_argument("--threat-id", default=None)

    s = sub.add_parser("review"); s.set_defaults(fn=cmd_review)
    s.add_argument("model_id")
    s.add_argument("--override", default=None,
                   help="Override missing-coverage block with reason")

    for cmd_name, fn in [("approve", cmd_approve)]:
        s = sub.add_parser(cmd_name); s.set_defaults(fn=fn)
        s.add_argument("model_id")

    s = sub.add_parser("apply"); s.set_defaults(fn=cmd_apply)
    s.add_argument("model_id")
    s.add_argument("--force", action="store_true")

    s = sub.add_parser("link"); s.set_defaults(fn=cmd_link)
    s.add_argument("model_id")
    s.add_argument("--to", required=True)

    s = sub.add_parser("scan"); s.set_defaults(fn=cmd_scan)
    s.add_argument("--path", default=None)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
