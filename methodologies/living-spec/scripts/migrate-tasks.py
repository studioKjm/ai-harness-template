#!/usr/bin/env python3
"""Classify existing tasks against a target seed version.

Reads tasks from .harness/ouroboros/tasks/*.yaml (decompose output) and
maps each to: unchanged | modified | deprecated. Also reports new
AC/entities in target seed without covering tasks (added).

Usage:
    migrate-tasks.py --to <version> [--from <version>]
    migrate-tasks.py --to 2

Output:
    .harness/ouroboros/tasks/migration-plans/migration-v{from}-to-v{to}.yaml
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
    sys.exit(1)


def find_project_root() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists() or (parent / ".harness").exists():
            return parent
    return cwd


def list_seeds(root: Path) -> list[Path]:
    seeds_dir = root / ".harness/ouroboros/seeds"
    if not seeds_dir.exists():
        return []
    return sorted(seeds_dir.glob("seed-v*.yaml"),
                  key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def collect_refs(seed: dict) -> dict:
    """Pull AC ids and entity/action names referenced in seed."""
    ac_ids = {a.get("id") for a in (seed.get("acceptance_criteria") or []) if a.get("id")}
    ent_names = {e.get("name") for e in (seed.get("ontology") or {}).get("entities") or [] if e.get("name")}
    act_names = {a.get("name") for a in (seed.get("ontology") or {}).get("actions") or [] if a.get("name")}
    return {"ac": ac_ids, "entities": ent_names, "actions": act_names}


def task_signature(task: dict) -> dict:
    """Extract refs a task points at."""
    refs = task.get("references") or {}
    return {
        "ac": set(refs.get("ac") or []),
        "entities": set(refs.get("entities") or []),
        "actions": set(refs.get("actions") or []),
    }


def classify(task: dict, before: dict, after: dict) -> tuple[str, str]:
    """Returns (status, reason)."""
    sig = task_signature(task)
    # Anything in task signature missing from `after`?
    missing_ac = sig["ac"] - after["ac"]
    missing_ent = sig["entities"] - after["entities"]
    missing_act = sig["actions"] - after["actions"]

    if missing_ac or missing_ent or missing_act:
        bits = []
        if missing_ac: bits.append(f"AC removed: {sorted(missing_ac)}")
        if missing_ent: bits.append(f"entities removed: {sorted(missing_ent)}")
        if missing_act: bits.append(f"actions removed: {sorted(missing_act)}")
        return "deprecated", "; ".join(bits)

    # Modified — present in both, but check if structure changed (heuristic: AC description / entity fields)
    # For v0.1 we keep it conservative: only flag deprecated; modification detection added in v0.2
    return "unchanged", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, type=int)
    ap.add_argument("--from", dest="from_v", type=int, default=None)
    args = ap.parse_args()

    root = find_project_root()
    seeds = list_seeds(root)
    if not seeds:
        print("ERROR: no seeds found in .harness/ouroboros/seeds/", file=sys.stderr)
        sys.exit(1)

    by_v = {int(re.search(r"v(\d+)", p.name).group(1)): p for p in seeds}

    if args.to not in by_v:
        print(f"ERROR: seed-v{args.to}.yaml not found", file=sys.stderr)
        sys.exit(1)

    if args.from_v is None:
        # Pick the most recent version below `to`
        prior = [v for v in by_v if v < args.to]
        if not prior:
            print(f"ERROR: no seed version prior to v{args.to}", file=sys.stderr)
            sys.exit(1)
        args.from_v = max(prior)

    if args.from_v not in by_v:
        print(f"ERROR: seed-v{args.from_v}.yaml not found", file=sys.stderr)
        sys.exit(1)

    before = collect_refs(load(by_v[args.from_v]))
    after = collect_refs(load(by_v[args.to]))

    # Read tasks
    tasks_dir = root / ".harness/ouroboros/tasks"
    tasks = []
    if tasks_dir.exists():
        for tf in sorted(tasks_dir.glob("*.yaml")):
            if tf.parent.name == "migration-plans":
                continue
            t = load(tf)
            t["_source_file"] = str(tf.relative_to(root))
            tasks.append(t)

    # Classify
    plan = {
        "schema_version": 1,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "from_version": args.from_v,
        "to_version": args.to,
        "summary": {"total_tasks": len(tasks), "unchanged": 0, "modified": 0, "deprecated": 0, "added": 0},
        "classifications": {"unchanged": [], "modified": [], "deprecated": [], "added": []},
        "confidence": {"overall": 0.7, "details": {"name_match": 1.0, "structural_match": 0.7, "semantic_match": 0.0}},
        "review_queue": [],
    }

    for t in tasks:
        tid = t.get("id") or t.get("_source_file")
        status, reason = classify(t, before, after)
        if status == "unchanged":
            plan["classifications"]["unchanged"].append(tid)
            plan["summary"]["unchanged"] += 1
        elif status == "deprecated":
            plan["classifications"]["deprecated"].append(
                {"task_id": tid, "reason": reason, "disposition": "review"}
            )
            plan["summary"]["deprecated"] += 1
        else:
            plan["classifications"]["modified"].append({"task_id": tid, "reason": reason, "action_required": "review"})
            plan["summary"]["modified"] += 1

    # Added — refs in `after` not in `before`
    for ac in sorted(after["ac"] - before["ac"]):
        plan["classifications"]["added"].append({
            "source": ac, "proposed_task": f"Cover new AC {ac}", "priority": "should",
        })
        plan["summary"]["added"] += 1
    for e in sorted(after["entities"] - before["entities"]):
        plan["classifications"]["added"].append({
            "source": f"entity:{e}", "proposed_task": f"Add support for entity {e}", "priority": "should",
        })
        plan["summary"]["added"] += 1
    for a in sorted(after["actions"] - before["actions"]):
        plan["classifications"]["added"].append({
            "source": f"action:{a}", "proposed_task": f"Implement action {a}", "priority": "should",
        })
        plan["summary"]["added"] += 1

    # Save
    out_dir = tasks_dir / "migration-plans"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"migration-v{args.from_v}-to-v{args.to}.yaml"
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(plan, f, sort_keys=False, allow_unicode=True)

    # Print summary
    s = plan["summary"]
    print(f"Migration plan v{args.from_v} → v{args.to}")
    print(f"  Total tasks    : {s['total_tasks']}")
    print(f"  Unchanged      : {s['unchanged']}")
    print(f"  Modified       : {s['modified']}")
    print(f"  Deprecated     : {s['deprecated']}")
    print(f"  New (uncovered): {s['added']}")
    print(f"\n[saved] {out_path}")


if __name__ == "__main__":
    main()
