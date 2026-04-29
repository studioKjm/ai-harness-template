#!/usr/bin/env python3
"""Semantic diff between two seed versions.

Compares structural sections (constraints, AC, ontology, architecture) and
emits a markdown report. Saved to:
    .harness/ouroboros/seeds/.diffs/diff-v{a}-to-v{b}.md

Usage:
    diff-spec.py <seed-vA.yaml> <seed-vB.yaml> [--out <path>]
    diff-spec.py 1 2                    # shorthand: vN ↔ v(N) using project default location

Exit:
    0 — diff completed successfully (regardless of differences found)
    1 — file or argument error
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def find_project_root() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists() or (parent / ".harness").exists():
            return parent
    return cwd


def resolve_seed(arg: str, root: Path) -> Path:
    """Accept either a path or a version number (1, 2, ...)."""
    p = Path(arg)
    if p.exists():
        return p
    if arg.isdigit():
        candidate = root / ".harness/ouroboros/seeds" / f"seed-v{arg}.yaml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Seed not found: {arg}")


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def diff_lists_by_id(a: list, b: list, key: str) -> tuple[list, list, list]:
    """Returns (added, removed, modified) lists."""
    a_map = {x.get(key): x for x in (a or []) if isinstance(x, dict) and x.get(key)}
    b_map = {x.get(key): x for x in (b or []) if isinstance(x, dict) and x.get(key)}
    added = [b_map[k] for k in b_map if k not in a_map]
    removed = [a_map[k] for k in a_map if k not in b_map]
    modified = []
    for k in a_map:
        if k in b_map and a_map[k] != b_map[k]:
            modified.append({"id": k, "before": a_map[k], "after": b_map[k]})
    return added, removed, modified


def diff_string_lists(a: list, b: list) -> tuple[list, list]:
    sa = set(a or [])
    sb = set(b or [])
    return list(sb - sa), list(sa - sb)  # added, removed


def render_section(title: str, added: list, removed: list, modified: list = None) -> str:
    lines = [f"### {title}"]
    if not (added or removed or modified):
        lines.append("_no changes_\n")
        return "\n".join(lines)
    if added:
        lines.append("\n**Added:**")
        for x in added:
            label = x.get("id") or x.get("name") or str(x)[:80]
            desc = x.get("description", "")
            lines.append(f"- `{label}` — {desc}" if desc else f"- `{label}`")
    if removed:
        lines.append("\n**Removed:**")
        for x in removed:
            label = x.get("id") or x.get("name") or str(x)[:80]
            lines.append(f"- `{label}`")
    if modified:
        lines.append("\n**Modified:**")
        for m in modified:
            lines.append(f"- `{m['id']}`")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("from_seed")
    ap.add_argument("to_seed")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    root = find_project_root()
    a_path = resolve_seed(args.from_seed, root)
    b_path = resolve_seed(args.to_seed, root)

    a = load(a_path)
    b = load(b_path)

    # AC diff
    ac_added, ac_removed, ac_modified = diff_lists_by_id(
        a.get("acceptance_criteria", []), b.get("acceptance_criteria", []), "id"
    )

    # Entities diff (by name)
    a_ent = (a.get("ontology") or {}).get("entities") or []
    b_ent = (b.get("ontology") or {}).get("entities") or []
    ent_added, ent_removed, ent_modified = diff_lists_by_id(a_ent, b_ent, "name")

    # Actions diff (by name)
    a_act = (a.get("ontology") or {}).get("actions") or []
    b_act = (b.get("ontology") or {}).get("actions") or []
    act_added, act_removed, act_modified = diff_lists_by_id(a_act, b_act, "name")

    # Constraints diff (string lists)
    a_must = (a.get("constraints") or {}).get("must") or []
    b_must = (b.get("constraints") or {}).get("must") or []
    must_added, must_removed = diff_string_lists(a_must, b_must)

    a_mustnot = (a.get("constraints") or {}).get("must_not") or []
    b_mustnot = (b.get("constraints") or {}).get("must_not") or []
    mustnot_added, mustnot_removed = diff_string_lists(a_mustnot, b_mustnot)

    # Architecture pattern change
    a_pattern = (a.get("architecture") or {}).get("pattern", "")
    b_pattern = (b.get("architecture") or {}).get("pattern", "")
    arch_changed = a_pattern != b_pattern

    # Goal change
    a_goal = (a.get("goal") or {}).get("summary", "")
    b_goal = (b.get("goal") or {}).get("summary", "")
    goal_changed = a_goal != b_goal

    # Render markdown report
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    report = []
    report.append(f"# Seed Diff: v{a.get('version', '?')} → v{b.get('version', '?')}")
    report.append("")
    report.append(f"**From**: `{a_path}`  ")
    report.append(f"**To**: `{b_path}`  ")
    report.append(f"**Generated**: {now}")
    report.append("")
    report.append("## Summary")
    report.append("")
    report.append(f"| Section | Added | Removed | Modified |")
    report.append(f"|---------|------:|--------:|---------:|")
    report.append(f"| Acceptance Criteria | {len(ac_added)} | {len(ac_removed)} | {len(ac_modified)} |")
    report.append(f"| Entities | {len(ent_added)} | {len(ent_removed)} | {len(ent_modified)} |")
    report.append(f"| Actions | {len(act_added)} | {len(act_removed)} | {len(act_modified)} |")
    report.append(f"| Constraints (must) | {len(must_added)} | {len(must_removed)} | — |")
    report.append(f"| Constraints (must_not) | {len(mustnot_added)} | {len(mustnot_removed)} | — |")
    report.append("")

    if goal_changed:
        report.append("## ⚠️  Goal changed")
        report.append(f"- Before: {a_goal}")
        report.append(f"- After: {b_goal}")
        report.append("")
    if arch_changed:
        report.append("## ⚠️  Architecture pattern changed")
        report.append(f"- Before: `{a_pattern}` → After: `{b_pattern}`")
        report.append("")

    report.append("## Details")
    report.append("")
    report.append(render_section("Acceptance Criteria", ac_added, ac_removed, ac_modified))
    report.append(render_section("Entities", ent_added, ent_removed, ent_modified))
    report.append(render_section("Actions", act_added, act_removed, act_modified))
    report.append(render_section("Constraints (must)",
                                  [{"id": x} for x in must_added],
                                  [{"id": x} for x in must_removed]))
    report.append(render_section("Constraints (must_not)",
                                  [{"id": x} for x in mustnot_added],
                                  [{"id": x} for x in mustnot_removed]))

    # Breaking-change heuristic
    is_breaking = bool(ac_removed or ent_removed or act_removed or mustnot_added or arch_changed)
    if is_breaking:
        report.append("## 🔴 Breaking-change indicators")
        report.append("")
        report.append("This diff likely contains breaking changes (removed AC/entities/actions, "
                      "added must_not constraints, or architecture pattern shift). "
                      "Review with care and consider a Parallel Change methodology rollout.")
        report.append("")

    out_text = "\n".join(report)

    # Save
    if args.out:
        out_path = Path(args.out)
    else:
        diffs_dir = root / ".harness/ouroboros/seeds/.diffs"
        diffs_dir.mkdir(parents=True, exist_ok=True)
        out_path = diffs_dir / f"diff-v{a.get('version', 'a')}-to-v{b.get('version', 'b')}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text, encoding="utf-8")

    # Print to stdout too
    print(out_text)
    print(f"\n[saved] {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
