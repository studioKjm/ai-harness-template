#!/usr/bin/env python3
"""
obs.py — Observability spec + SLO state machine.

Spec subcommands:
    define <slug> --target-kind story|feature|endpoint|module --target-ref REF [--description "..."]
    list-specs [--status STATUS]
    show-spec <spec-id>
    instrument <spec-id>             # defined → instrumented (code verified)
    measure <spec-id>                # instrumented → measuring (data flowing)
    coverage <spec-id> --files F1 [F2 ...] [--symbols S1 [S2 ...]]
    add-metric <spec-id> --name N --type counter|gauge|histogram|summary --question "..." [--labels L1 ...]
    add-log <spec-id> --event E --level info|warn|error [--field F1 ...]

SLO subcommands:
    slo-new <slug> --service S --sli-good "QUERY" --sli-valid "QUERY" --target PCT --window "30d"
    slo-list [--status STATUS]
    slo-show <slo-id>
    slo-activate <slo-id>             # proposed → active
    slo-retire <slo-id>                # active → retired
    slo-record-violation <slo-id> --duration MIN --burn-rate RATE [--incident-id ID]

Storage:
    .harness/observability-first/specs/<spec-id>.yaml
    .harness/observability-first/slos/<slo-id>.yaml
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


SPECS_DIR = Path(".harness/observability-first/specs")
SLOS_DIR = Path(".harness/observability-first/slos")
SPEC_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "observability-spec.yaml"
SLO_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "slo.yaml"

SPEC_TRANSITIONS = {
    "draft": ["defined"],
    "defined": ["instrumented"],
    "instrumented": ["measuring"],
    "measuring": ["review-due"],
    "review-due": ["measuring"],
}

SLO_TRANSITIONS = {
    "proposed": ["active"],
    "active": ["retired"],
    "retired": [],
}


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", s.lower())
    return re.sub(r"-+", "-", s).strip("-")


def _load(path: Path):
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _save(path: Path, data: dict):
    data["updated_at"] = now_iso()
    with path.open("w") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)


# ─── SPEC commands ───────────────────────────────────────────────────────

def cmd_define(args):
    today = datetime.date.today().isoformat()
    spec_id = f"obs-{today}-{slugify(args.slug)}"
    path = SPECS_DIR / f"{spec_id}.yaml"
    if path.exists():
        print(f"ERROR: spec already exists: {spec_id}", file=sys.stderr)
        sys.exit(1)
    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    if not SPEC_TEMPLATE.exists():
        print(f"ERROR: template not found at {SPEC_TEMPLATE}", file=sys.stderr)
        sys.exit(2)

    with SPEC_TEMPLATE.open() as f:
        spec = yaml.safe_load(f)

    now = now_iso()
    spec["id"] = spec_id
    spec["created_at"] = now
    spec["updated_at"] = now
    spec["target"] = {
        "kind": args.target_kind,
        "ref": args.target_ref,
        "description": args.description or "",
    }
    spec["status"] = "draft"
    spec["history"] = [{
        "timestamp": now, "from": None, "to": "draft",
        "note": "spec created",
    }]
    spec["metrics"] = []
    spec["logs"] = []
    spec["traces"] = []
    spec["slos"] = []
    spec["coverage"] = {"files": [], "symbols": [], "last_verified_at": None}
    spec["high_cardinality_warnings"] = []
    spec["links"] = {
        "story": args.target_ref if args.target_kind == "story" else None,
        "related_incidents": [],
        "related_adrs": [],
    }

    _save(path, spec)
    print(f"Created observability spec: {spec_id}")
    print(f"  Target: {args.target_kind} → {args.target_ref}")
    print(f"  Status: draft")
    print()
    print(f"Next:")
    print(f"  - Add metrics: /observe add-metric {spec_id} --name N --type T --question \"...\"")
    print(f"  - Add log events: /observe add-log {spec_id} --event E --level L")
    print(f"  - When done: status auto-advances when first metric/log/trace added")


def cmd_list_specs(args):
    if not SPECS_DIR.exists():
        print("(no specs)")
        return
    rows = []
    for f in sorted(SPECS_DIR.glob("*.yaml")):
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if args.status and data.get("status") != args.status:
            continue
        m = len(data.get("metrics") or [])
        l = len(data.get("logs") or [])
        t = len(data.get("traces") or [])
        s = len(data.get("slos") or [])
        target = data.get("target", {}) or {}
        rows.append((data.get("id", "?"), data.get("status", "?"),
                     f"M{m}/L{l}/T{t}/S{s}",
                     f"{target.get('kind','?')}:{target.get('ref','?')}"))

    if not rows:
        print("(no matching specs)")
        return
    width = max(len(r[0]) for r in rows)
    for sid, status, counts, target in rows:
        print(f"  {sid:<{width}}  [{status:<13}]  {counts:<14}  {target}")


def cmd_show_spec(args):
    print(yaml.dump(_load(SPECS_DIR / f"{args.spec_id}.yaml"),
                    sort_keys=False, allow_unicode=True))


def _spec_transition(spec_id: str, target: str, **updates):
    path = SPECS_DIR / f"{spec_id}.yaml"
    data = _load(path)
    current = data.get("status", "draft")
    if target not in SPEC_TRANSITIONS.get(current, []):
        print(f"ERROR: invalid spec transition {current} → {target}", file=sys.stderr)
        sys.exit(1)
    now = now_iso()
    data.setdefault("history", []).append({
        "timestamp": now, "from": current, "to": target,
        "note": updates.pop("note", ""),
    })
    data["status"] = target
    for k, v in updates.items():
        data[k] = v
    _save(path, data)
    print(f"{spec_id}: {current} → {target}")


def cmd_instrument(args):
    path = SPECS_DIR / f"{args.spec_id}.yaml"
    data = _load(path)
    if data.get("status") != "defined":
        print(f"ERROR: can only instrument from 'defined' (current: {data.get('status')})",
              file=sys.stderr)
        sys.exit(1)
    cov = data.get("coverage", {})
    if not (cov.get("files") or cov.get("symbols")):
        print("ERROR: coverage.files or coverage.symbols must be populated.",
              file=sys.stderr)
        print(f"  Run: /observe coverage {args.spec_id} --files F1 [F2 ...] --symbols S1 [...]",
              file=sys.stderr)
        sys.exit(1)
    cov["last_verified_at"] = now_iso()
    _spec_transition(args.spec_id, "instrumented",
                     note="code instrumentation verified")


def cmd_measure(args):
    _spec_transition(args.spec_id, "measuring",
                     note="production data flowing")


def cmd_coverage(args):
    path = SPECS_DIR / f"{args.spec_id}.yaml"
    data = _load(path)
    cov = data.setdefault("coverage", {})
    if args.files:
        cov["files"] = sorted(set((cov.get("files") or []) + args.files))
    if args.symbols:
        cov["symbols"] = sorted(set((cov.get("symbols") or []) + args.symbols))
    cov["last_verified_at"] = now_iso()
    _save(path, data)
    print(f"Coverage updated: {len(cov.get('files') or [])} files, "
          f"{len(cov.get('symbols') or [])} symbols")


def _maybe_advance_to_defined(data: dict) -> bool:
    """If spec has metrics/logs/traces and is in draft, advance."""
    if data.get("status") != "draft":
        return False
    has_content = bool(data.get("metrics") or data.get("logs") or data.get("traces"))
    return has_content


def cmd_add_metric(args):
    path = SPECS_DIR / f"{args.spec_id}.yaml"
    data = _load(path)
    metrics = data.setdefault("metrics", [])
    metrics.append({
        "name": args.name,
        "type": args.type,
        "labels": args.labels or [],
        "question": args.question,
        "unit": args.unit or "",
    })
    advanced = _maybe_advance_to_defined(data)
    if advanced:
        data["status"] = "defined"
        data.setdefault("history", []).append({
            "timestamp": now_iso(), "from": "draft", "to": "defined",
            "note": "first metric/log/trace added",
        })
    _save(path, data)
    print(f"Added metric: {args.name} ({args.type})")
    if advanced:
        print(f"  Status auto-advanced: draft → defined")


def cmd_add_log(args):
    path = SPECS_DIR / f"{args.spec_id}.yaml"
    data = _load(path)
    logs = data.setdefault("logs", [])
    fields = []
    for f in (args.field or []):
        if ":" in f:
            name, attrs = f.split(":", 1)
            entry = {"name": name}
            if "pii" in attrs.lower():
                entry["pii"] = True
            fields.append(entry)
        else:
            fields.append({"name": f})
    logs.append({
        "event": args.event,
        "level": args.level,
        "fields": fields,
        "when_to_log": args.when or "",
    })
    advanced = _maybe_advance_to_defined(data)
    if advanced:
        data["status"] = "defined"
        data.setdefault("history", []).append({
            "timestamp": now_iso(), "from": "draft", "to": "defined",
            "note": "first metric/log/trace added",
        })
    _save(path, data)
    print(f"Added log event: {args.event} ({args.level})")
    if advanced:
        print(f"  Status auto-advanced: draft → defined")


# ─── SLO commands ────────────────────────────────────────────────────────

def cmd_slo_new(args):
    today = datetime.date.today().isoformat()
    slo_id = f"slo-{slugify(args.slug)}"  # SLOs are time-independent typically
    path = SLOS_DIR / f"{slo_id}.yaml"
    if path.exists():
        print(f"ERROR: SLO already exists: {slo_id}", file=sys.stderr)
        sys.exit(1)
    SLOS_DIR.mkdir(parents=True, exist_ok=True)

    if not SLO_TEMPLATE.exists():
        print(f"ERROR: template not found at {SLO_TEMPLATE}", file=sys.stderr)
        sys.exit(2)

    with SLO_TEMPLATE.open() as f:
        slo = yaml.safe_load(f)

    now = now_iso()
    slo["id"] = slo_id
    slo["created_at"] = now
    slo["updated_at"] = now
    slo["title"] = args.title or args.slug
    slo["service"] = args.service
    slo["sli"] = {
        "description": args.description or "",
        "good_events": args.sli_good,
        "valid_events": args.sli_valid,
        "metric_source": args.metric_source,
    }
    slo["target"] = {
        "percentage": args.target,
        "window": args.window,
        "unit": "ratio",
    }
    slo["status"] = "proposed"
    slo["history"] = [{
        "timestamp": now, "from": None, "to": "proposed",
        "note": "SLO drafted",
    }]
    slo["violations"] = []

    _save(path, slo)
    print(f"Created SLO: {slo_id}")
    print(f"  Service: {args.service}")
    print(f"  Target:  {args.target}% over {args.window}")


def cmd_slo_list(args):
    if not SLOS_DIR.exists():
        print("(no SLOs)")
        return
    rows = []
    for f in sorted(SLOS_DIR.glob("*.yaml")):
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if args.status and data.get("status") != args.status:
            continue
        target = data.get("target", {}) or {}
        recent = data.get("recent", {}) or {}
        achieved = recent.get("achieved_pct")
        ach_str = f"{achieved}%" if achieved else "(no data)"
        violations = len(data.get("violations") or [])
        rows.append((data.get("id", "?"), data.get("status", "?"),
                     data.get("service", "?"),
                     f"{target.get('percentage', '?')}%",
                     ach_str, str(violations)))

    if not rows:
        print("(no matching SLOs)")
        return
    width = max(len(r[0]) for r in rows)
    print(f"  {'ID':<{width}}  STATUS    SERVICE        TARGET  ACHIEVED  VIOL")
    for sid, status, svc, tgt, ach, v in rows:
        print(f"  {sid:<{width}}  [{status:<8}] {svc:<14} {tgt:<7} {ach:<10} {v}")


def cmd_slo_show(args):
    print(yaml.dump(_load(SLOS_DIR / f"{args.slo_id}.yaml"),
                    sort_keys=False, allow_unicode=True))


def _slo_transition(slo_id: str, target: str, note: str = ""):
    path = SLOS_DIR / f"{slo_id}.yaml"
    data = _load(path)
    current = data.get("status", "proposed")
    if target not in SLO_TRANSITIONS.get(current, []):
        print(f"ERROR: invalid SLO transition {current} → {target}", file=sys.stderr)
        sys.exit(1)
    data.setdefault("history", []).append({
        "timestamp": now_iso(), "from": current, "to": target, "note": note,
    })
    data["status"] = target
    _save(path, data)
    print(f"{slo_id}: {current} → {target}")


def cmd_slo_activate(args):
    _slo_transition(args.slo_id, "active",
                    note="SLO active — alerts enabled")


def cmd_slo_retire(args):
    _slo_transition(args.slo_id, "retired",
                    note=args.note or "retired")


def cmd_slo_record_violation(args):
    path = SLOS_DIR / f"{args.slo_id}.yaml"
    data = _load(path)
    violations = data.setdefault("violations", [])
    violations.append({
        "date": datetime.date.today().isoformat(),
        "duration_minutes": args.duration,
        "burn_rate": args.burn_rate,
        "incident_id": args.incident_id,
        "resolved": False,
    })
    _save(path, data)
    print(f"Recorded violation on {args.slo_id}: {args.duration}min, burn rate {args.burn_rate}x")


def main():
    p = argparse.ArgumentParser(prog="obs.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Spec commands
    s = sub.add_parser("define"); s.set_defaults(fn=cmd_define)
    s.add_argument("slug")
    s.add_argument("--target-kind", required=True,
                   choices=["story", "feature", "endpoint", "module"])
    s.add_argument("--target-ref", required=True)
    s.add_argument("--description", default="")

    s = sub.add_parser("list-specs"); s.set_defaults(fn=cmd_list_specs)
    s.add_argument("--status", default=None)

    s = sub.add_parser("show-spec"); s.set_defaults(fn=cmd_show_spec)
    s.add_argument("spec_id")

    for cmd, fn in [("instrument", cmd_instrument), ("measure", cmd_measure)]:
        s = sub.add_parser(cmd); s.set_defaults(fn=fn)
        s.add_argument("spec_id")

    s = sub.add_parser("coverage"); s.set_defaults(fn=cmd_coverage)
    s.add_argument("spec_id")
    s.add_argument("--files", nargs="*", default=[])
    s.add_argument("--symbols", nargs="*", default=[])

    s = sub.add_parser("add-metric"); s.set_defaults(fn=cmd_add_metric)
    s.add_argument("spec_id")
    s.add_argument("--name", required=True)
    s.add_argument("--type", required=True,
                   choices=["counter", "gauge", "histogram", "summary"])
    s.add_argument("--question", required=True)
    s.add_argument("--labels", nargs="*", default=[])
    s.add_argument("--unit", default="")

    s = sub.add_parser("add-log"); s.set_defaults(fn=cmd_add_log)
    s.add_argument("spec_id")
    s.add_argument("--event", required=True)
    s.add_argument("--level", required=True,
                   choices=["debug", "info", "warn", "error", "fatal"])
    s.add_argument("--field", action="append")
    s.add_argument("--when", default="")

    # SLO commands
    s = sub.add_parser("slo-new"); s.set_defaults(fn=cmd_slo_new)
    s.add_argument("slug")
    s.add_argument("--service", required=True)
    s.add_argument("--sli-good", required=True)
    s.add_argument("--sli-valid", required=True)
    s.add_argument("--target", type=float, required=True)
    s.add_argument("--window", default="30d")
    s.add_argument("--metric-source", default="prometheus")
    s.add_argument("--description", default="")
    s.add_argument("--title", default=None)

    s = sub.add_parser("slo-list"); s.set_defaults(fn=cmd_slo_list)
    s.add_argument("--status", default=None)

    s = sub.add_parser("slo-show"); s.set_defaults(fn=cmd_slo_show)
    s.add_argument("slo_id")

    s = sub.add_parser("slo-activate"); s.set_defaults(fn=cmd_slo_activate)
    s.add_argument("slo_id")

    s = sub.add_parser("slo-retire"); s.set_defaults(fn=cmd_slo_retire)
    s.add_argument("slo_id")
    s.add_argument("--note", default="")

    s = sub.add_parser("slo-record-violation"); s.set_defaults(fn=cmd_slo_record_violation)
    s.add_argument("slo_id")
    s.add_argument("--duration", type=int, required=True)
    s.add_argument("--burn-rate", type=float, required=True)
    s.add_argument("--incident-id", default=None)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
