#!/usr/bin/env python3
"""DDD Lite CLI — Bounded Context, Aggregate, Domain Event, Glossary management."""

import argparse
import sys
import os
import yaml
from datetime import datetime, timezone
from pathlib import Path


HARNESS_DIR = Path(".harness/ddd-lite")
CONTEXTS_DIR = HARNESS_DIR / "contexts"
AGGREGATES_DIR = HARNESS_DIR / "aggregates"
EVENTS_DIR = HARNESS_DIR / "events"
GLOSSARY_FILE = HARNESS_DIR / "glossary.yaml"

TEMPLATE_DIR = Path("methodologies/ddd-lite/templates")


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


# ── context ──────────────────────────────────────────────────────────────────

def cmd_context_new(args):
    ctx_id = _next_id("BC", CONTEXTS_DIR)
    data = _load_template("bounded-context.yaml")
    data["context_id"] = ctx_id
    data["name"] = args.name
    data["description"] = args.description or ""
    data["owner"] = args.owner or ""
    data["state"] = "draft"
    data["created_at"] = _now()
    data["updated_at"] = _now()

    slug = args.name.lower().replace(" ", "-")
    out_path = CONTEXTS_DIR / f"{ctx_id}-{slug}.yaml"
    _save_yaml(out_path, data)
    print(f"Created Bounded Context: {ctx_id} ({args.name})")
    print(f"  File: {out_path}")


def cmd_context_list(args):
    CONTEXTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(CONTEXTS_DIR.glob("BC-*.yaml"))
    if not files:
        print("No bounded contexts found. Create one with: ddd.py context new <name>")
        return
    print(f"{'ID':<22} {'Name':<25} {'State':<12} {'Owner'}")
    print("-" * 70)
    for f in files:
        d = _load_yaml(f)
        print(f"{d.get('context_id',''):<22} {d.get('name',''):<25} {d.get('state',''):<12} {d.get('owner','')}")


def cmd_context_show(args):
    hits = list(CONTEXTS_DIR.glob(f"{args.id}*.yaml"))
    if not hits:
        print(f"Error: context '{args.id}' not found", file=sys.stderr)
        sys.exit(1)
    d = _load_yaml(hits[0])
    print(yaml.dump(d, allow_unicode=True, default_flow_style=False, sort_keys=False))


# ── aggregate ─────────────────────────────────────────────────────────────────

def cmd_aggregate_new(args):
    agg_id = _next_id("AGG", AGGREGATES_DIR)
    data = _load_template("aggregate.yaml")
    data["aggregate_id"] = agg_id
    data["context_id"] = args.context or ""
    data["name"] = args.name
    data["description"] = args.description or ""
    data["state"] = "draft"
    data["created_at"] = _now()
    data["updated_at"] = _now()

    slug = args.name.lower().replace(" ", "-")
    out_path = AGGREGATES_DIR / f"{agg_id}-{slug}.yaml"
    _save_yaml(out_path, data)
    print(f"Created Aggregate: {agg_id} ({args.name})")
    print(f"  File: {out_path}")


def cmd_aggregate_list(args):
    AGGREGATES_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(AGGREGATES_DIR.glob("AGG-*.yaml"))
    if not files:
        print("No aggregates found. Create one with: ddd.py aggregate new <name>")
        return
    print(f"{'ID':<22} {'Name':<25} {'Context':<22} {'State'}")
    print("-" * 80)
    for f in files:
        d = _load_yaml(f)
        print(f"{d.get('aggregate_id',''):<22} {d.get('name',''):<25} {d.get('context_id',''):<22} {d.get('state','')}")


# ── event ─────────────────────────────────────────────────────────────────────

def cmd_event_new(args):
    evt_id = _next_id("EVT", EVENTS_DIR)
    data = _load_template("domain-event.yaml")
    data["event_id"] = evt_id
    data["name"] = args.name
    data["context_id"] = args.context or ""
    data["aggregate_id"] = args.aggregate or ""
    data["description"] = args.description or ""
    data["created_at"] = _now()
    data["updated_at"] = _now()

    slug = args.name.lower().replace(" ", "-")
    out_path = EVENTS_DIR / f"{evt_id}-{slug}.yaml"
    _save_yaml(out_path, data)
    print(f"Created Domain Event: {evt_id} ({args.name})")
    print(f"  File: {out_path}")


# ── glossary ──────────────────────────────────────────────────────────────────

def _load_glossary() -> dict:
    GLOSSARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if GLOSSARY_FILE.exists():
        return _load_yaml(GLOSSARY_FILE) or {"terms": []}
    return {"terms": []}


def _save_glossary(data: dict) -> None:
    _save_yaml(GLOSSARY_FILE, data)


def cmd_glossary_add(args):
    glossary = _load_glossary()
    existing = [t for t in glossary["terms"] if t["term"] == args.term and t.get("context_id") == (args.context or "")]
    if existing:
        print(f"Warning: term '{args.term}' already exists in this context. Use 'glossary update' to modify.")
        return

    entry = {
        "term": args.term,
        "context_id": args.context or "",
        "definition": args.definition or "",
        "code_references": [],
        "synonyms": [],
        "cross_context": [],
        "status": "active",
        "disputed_reason": "",
        "created_at": _now(),
        "updated_at": _now(),
    }
    glossary["terms"].append(entry)
    _save_glossary(glossary)
    print(f"Added term '{args.term}' to glossary.")


def cmd_glossary_list(args):
    glossary = _load_glossary()
    terms = glossary.get("terms", [])
    if not terms:
        print("Glossary is empty. Add terms with: ddd.py glossary add <term>")
        return

    context_filter = args.context if hasattr(args, "context") else None
    filtered = [t for t in terms if not context_filter or t.get("context_id") == context_filter]

    print(f"{'Term':<30} {'Context':<22} {'Status':<10} Definition")
    print("-" * 90)
    for t in sorted(filtered, key=lambda x: x["term"]):
        defn = (t.get("definition") or "")[:40]
        print(f"{t['term']:<30} {t.get('context_id',''):<22} {t.get('status',''):<10} {defn}")


# ── tree ──────────────────────────────────────────────────────────────────────

def cmd_tree(args):
    """Print a context map showing all bounded contexts and their relationships."""
    CONTEXTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(CONTEXTS_DIR.glob("BC-*.yaml"))
    if not files:
        print("No bounded contexts defined yet.")
        return

    contexts = {_load_yaml(f)["context_id"]: _load_yaml(f) for f in files}

    print("Context Map")
    print("=" * 50)
    for ctx_id, ctx in contexts.items():
        state_icon = {"draft": "⚪", "active": "🟢", "deprecated": "🔴"}.get(ctx.get("state", ""), "❓")
        print(f"\n{state_icon} [{ctx_id}] {ctx['name']}")
        if ctx.get("description"):
            print(f"   {ctx['description']}")
        if ctx.get("upstream_contexts"):
            print(f"   ← upstream: {', '.join(ctx['upstream_contexts'])}")
        if ctx.get("downstream_contexts"):
            print(f"   → downstream: {', '.join(ctx['downstream_contexts'])}")
        if ctx.get("integration", {}).get("pattern"):
            print(f"   pattern: {ctx['integration']['pattern']}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DDD Lite CLI")
    sub = parser.add_subparsers(dest="cmd")

    # context
    ctx_p = sub.add_parser("context")
    ctx_sub = ctx_p.add_subparsers(dest="action")

    ctx_new = ctx_sub.add_parser("new")
    ctx_new.add_argument("name")
    ctx_new.add_argument("--description", "-d", default="")
    ctx_new.add_argument("--owner", "-o", default="")

    ctx_sub.add_parser("list")

    ctx_show = ctx_sub.add_parser("show")
    ctx_show.add_argument("id")

    # aggregate
    agg_p = sub.add_parser("aggregate")
    agg_sub = agg_p.add_subparsers(dest="action")

    agg_new = agg_sub.add_parser("new")
    agg_new.add_argument("name")
    agg_new.add_argument("--context", "-c", default="")
    agg_new.add_argument("--description", "-d", default="")

    agg_sub.add_parser("list")

    # event
    evt_p = sub.add_parser("event")
    evt_sub = evt_p.add_subparsers(dest="action")

    evt_new = evt_sub.add_parser("new")
    evt_new.add_argument("name")
    evt_new.add_argument("--context", "-c", default="")
    evt_new.add_argument("--aggregate", "-a", default="")
    evt_new.add_argument("--description", "-d", default="")

    # glossary
    gls_p = sub.add_parser("glossary")
    gls_sub = gls_p.add_subparsers(dest="action")

    gls_add = gls_sub.add_parser("add")
    gls_add.add_argument("term")
    gls_add.add_argument("--context", "-c", default="")
    gls_add.add_argument("--definition", "-d", default="")

    gls_list = gls_sub.add_parser("list")
    gls_list.add_argument("--context", "-c", default="")

    # tree
    sub.add_parser("tree")

    args = parser.parse_args()

    dispatch = {
        ("context", "new"): cmd_context_new,
        ("context", "list"): lambda a: cmd_context_list(a),
        ("context", "show"): cmd_context_show,
        ("aggregate", "new"): cmd_aggregate_new,
        ("aggregate", "list"): lambda a: cmd_aggregate_list(a),
        ("event", "new"): cmd_event_new,
        ("glossary", "add"): cmd_glossary_add,
        ("glossary", "list"): cmd_glossary_list,
        ("tree", None): cmd_tree,
    }

    action = getattr(args, "action", None)
    fn = dispatch.get((args.cmd, action))
    if fn:
        fn(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
