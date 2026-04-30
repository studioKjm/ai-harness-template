#!/usr/bin/env python3
"""mikado-method CLI — Goal→try→revert→prerequisites tree-based refactoring."""
import argparse
import sys
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import yaml

HARNESS_DIR = Path(os.environ.get("HARNESS_DIR", ".harness"))
GRAPHS_DIR = HARNESS_DIR / "mikado-method" / "graphs"
STATE_FILE = HARNESS_DIR / "state" / "mikado-method.yaml"

# ── Node state machine ─────────────────────────────────────────────────────────

# pending → attempted: /mikado try
# attempted → done: /mikado done (all prerequisites done)
# attempted → blocked: /mikado block (discovered prerequisites)
# blocked → attempted: /mikado try (prerequisites now done)
# any → reverted: /mikado revert

NODE_ICONS = {
    "pending":   "⬜",
    "attempted": "🟡",
    "blocked":   "🔴",
    "done":      "✅",
    "reverted":  "↩️",
}

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def graph_path(graph_id: str) -> Path:
    return GRAPHS_DIR / f"{graph_id}.yaml"

def load_graph(graph_id: str) -> dict:
    p = graph_path(graph_id)
    if not p.exists():
        print(f"Error: graph '{graph_id}' not found at {p}", file=sys.stderr)
        sys.exit(1)
    return yaml.safe_load(p.read_text())

def save_graph(path: Path, data: dict):
    data["updated_at"] = now_iso()
    # Recompute metadata
    nodes = data.get("nodes", [])
    data["metadata"] = {
        "total_nodes": len(nodes),
        "done_nodes": sum(1 for n in nodes if n["state"] == "done"),
        "blocked_nodes": sum(1 for n in nodes if n["state"] == "blocked"),
        "pending_nodes": sum(1 for n in nodes if n["state"] == "pending"),
    }
    # Recompute graph_state
    root = next((n for n in nodes if n["id"] == "root"), None)
    if root and root["state"] == "done":
        data["graph_state"] = "done"
    elif data.get("graph_state") != "abandoned":
        data["graph_state"] = "in-progress"
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))

def find_node(data: dict, node_id: str) -> dict | None:
    return next((n for n in data.get("nodes", []) if n["id"] == node_id), None)

def gen_graph_id() -> str:
    ts = datetime.now().strftime("%Y%m%d")
    existing = sorted(GRAPHS_DIR.glob(f"mik-{ts}-*.yaml")) if GRAPHS_DIR.exists() else []
    idx = len(existing) + 1
    return f"mik-{ts}-{idx:03d}"

def gen_node_id(data: dict) -> str:
    existing = [n["id"] for n in data.get("nodes", [])]
    for i in range(1, 1000):
        nid = f"node-{i:03d}"
        if nid not in existing:
            return nid
    return f"node-{len(existing)+1:03d}"

def current_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return ""

def prerequisites_done(data: dict, node: dict) -> tuple[bool, list[str]]:
    """Returns (all_done, not_done_ids)."""
    not_done = []
    for prereq_id in node.get("prerequisites", []):
        prereq = find_node(data, prereq_id)
        if not prereq or prereq["state"] != "done":
            not_done.append(prereq_id)
    return len(not_done) == 0, not_done

# ── Tree rendering ─────────────────────────────────────────────────────────────

def render_tree(data: dict) -> str:
    nodes = {n["id"]: n for n in data.get("nodes", [])}
    children: dict[str | None, list] = {}
    for n in data["nodes"]:
        parent = n.get("parent_id")
        children.setdefault(parent, []).append(n["id"])

    lines = [f"🎯 Graph: {data['graph_id']}  [{data['graph_state']}]"]
    lines.append(f"   Goal: {data['goal']}")
    lines.append("")

    def render_node(node_id: str, prefix: str, is_last: bool):
        node = nodes[node_id]
        connector = "└── " if is_last else "├── "
        icon = NODE_ICONS.get(node["state"], "?")
        prereqs = node.get("prerequisites", [])
        prereq_str = f" (needs: {', '.join(prereqs)})" if prereqs else ""
        lines.append(f"{prefix}{connector}{icon} {node_id} [{node['state']}] {node.get('label', '')}{prereq_str}")
        child_list = children.get(node_id, [])
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child_id in enumerate(child_list):
            render_node(child_id, child_prefix, i == len(child_list) - 1)

    root_children = children.get(None, [])
    for i, root_id in enumerate(root_children):
        render_node(root_id, "", i == len(root_children) - 1)

    meta = data.get("metadata", {})
    lines.append("")
    lines.append(f"Progress: ✅ {meta.get('done_nodes', 0)} done  "
                 f"🔴 {meta.get('blocked_nodes', 0)} blocked  "
                 f"⬜ {meta.get('pending_nodes', 0)} pending  "
                 f"/ {meta.get('total_nodes', 0)} total")
    return "\n".join(lines)

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_new(args):
    """Create a new Mikado graph with a root goal node."""
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    graph_id = gen_graph_id()
    p = graph_path(graph_id)

    goal = " ".join(args.goal)
    root_node = {
        "id": "root",
        "label": goal,
        "state": "pending",
        "prerequisites": [],
        "parent_id": None,
        "notes": {
            "hypothesis": args.hypothesis or "",
            "attempt_notes": "",
            "blocker_description": "",
            "done_commit": "",
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    data = {
        "graph_id": graph_id,
        "goal": goal,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "graph_state": "in-progress",
        "nodes": [root_node],
        "metadata": {"total_nodes": 1, "done_nodes": 0, "blocked_nodes": 0, "pending_nodes": 1},
    }
    p.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))

    print(f"✓ Mikado graph created: {graph_id}")
    print(f"  Goal: {goal}")
    print(f"  Next: Try the change → /mikado try {graph_id} root")


def cmd_try(args):
    """Mark a node as attempted (start trying the change)."""
    p = graph_path(args.graph_id)
    data = load_graph(args.graph_id)
    node = find_node(data, args.node_id)
    if not node:
        print(f"Error: node '{args.node_id}' not found.", file=sys.stderr)
        sys.exit(1)

    if node["state"] == "done":
        print(f"Node '{args.node_id}' is already done.", file=sys.stderr)
        sys.exit(1)

    # Check prerequisites for both blocked and pending states (pending after revert may still have prereqs)
    if node.get("prerequisites"):
        all_done, not_done = prerequisites_done(data, node)
        if not all_done:
            print(f"Error: prerequisites not done yet: {not_done}", file=sys.stderr)
            print(f"  Complete those nodes first, then retry.", file=sys.stderr)
            sys.exit(1)

    node["state"] = "attempted"
    node["notes"]["attempt_notes"] = args.notes or node["notes"].get("attempt_notes", "")
    node["updated_at"] = now_iso()
    save_graph(p, data)

    icon = "⬜" if node["state"] == "pending" else "🔴"
    print(f"✓ {args.graph_id} / {args.node_id}: {icon} → 🟡 attempted")
    print(f"  Make the change. If it builds clean → /mikado done {args.graph_id} {args.node_id}")
    print(f"  If you hit blockers → /mikado block {args.graph_id} {args.node_id} --prereq <desc>")
    print(f"  To undo all changes → /mikado revert {args.graph_id} {args.node_id}")


def cmd_block(args):
    """Mark node as blocked — discovered prerequisites."""
    p = graph_path(args.graph_id)
    data = load_graph(args.graph_id)
    node = find_node(data, args.node_id)
    if not node:
        print(f"Error: node '{args.node_id}' not found.", file=sys.stderr)
        sys.exit(1)

    if node["state"] != "attempted":
        print(f"Error: can only block an 'attempted' node (current: '{node['state']}').", file=sys.stderr)
        sys.exit(1)

    # Add prerequisite nodes
    new_node_ids = []
    for prereq_label in args.prereq:
        new_id = gen_node_id(data)
        new_node = {
            "id": new_id,
            "label": prereq_label,
            "state": "pending",
            "prerequisites": [],
            "parent_id": args.node_id,
            "notes": {
                "hypothesis": "",
                "attempt_notes": "",
                "blocker_description": "",
                "done_commit": "",
            },
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        data["nodes"].append(new_node)
        new_node_ids.append(new_id)

    # Register prereqs on the blocked node
    node["prerequisites"].extend(new_node_ids)
    node["state"] = "blocked"
    node["notes"]["blocker_description"] = args.desc or "; ".join(args.prereq)
    node["updated_at"] = now_iso()
    save_graph(p, data)

    print(f"✓ {args.graph_id} / {args.node_id}: 🟡 attempted → 🔴 blocked")
    print(f"  Prerequisites discovered:")
    for nid in new_node_ids:
        n = find_node(data, nid)
        print(f"    {nid}: {n['label']}")
    print(f"  Complete prerequisites first:")
    for nid in new_node_ids:
        print(f"    /mikado try {args.graph_id} {nid}")
    print(f"\n  View tree: /mikado tree {args.graph_id}")


def cmd_done(args):
    """Mark node as done — change committed, no blockers."""
    p = graph_path(args.graph_id)
    data = load_graph(args.graph_id)
    node = find_node(data, args.node_id)
    if not node:
        print(f"Error: node '{args.node_id}' not found.", file=sys.stderr)
        sys.exit(1)

    if node["state"] != "attempted":
        print(f"Error: can only complete an 'attempted' node (current: '{node['state']}').", file=sys.stderr)
        sys.exit(1)

    # Verify prerequisites
    all_done, not_done = prerequisites_done(data, node)
    if not all_done:
        print(f"Error: prerequisites not done: {not_done}", file=sys.stderr)
        sys.exit(1)

    sha = current_sha()
    node["state"] = "done"
    node["notes"]["done_commit"] = sha
    node["updated_at"] = now_iso()
    save_graph(p, data)

    print(f"✓ {args.graph_id} / {args.node_id}: 🟡 attempted → ✅ done")
    print(f"  Commit: {sha[:8] if sha else 'n/a'}")

    # Check if any parent is now unblocked
    for n in data["nodes"]:
        if args.node_id in n.get("prerequisites", []) and n["state"] == "blocked":
            all_done_2, _ = prerequisites_done(data, n)
            if all_done_2:
                print(f"  🎯 Node '{n['id']}' prerequisites all done — ready to try again!")
                print(f"     /mikado try {args.graph_id} {n['id']}")

    if args.node_id == "root":
        print(f"\n  🎊 Graph complete! Goal achieved: {data['goal']}")


def cmd_revert(args):
    """Revert node — undo attempted change, go back to pending."""
    p = graph_path(args.graph_id)
    data = load_graph(args.graph_id)
    node = find_node(data, args.node_id)
    if not node:
        print(f"Error: node '{args.node_id}' not found.", file=sys.stderr)
        sys.exit(1)

    if node["state"] not in ("attempted", "blocked"):
        print(f"Error: can only revert 'attempted' or 'blocked' node (current: '{node['state']}').", file=sys.stderr)
        sys.exit(1)

    prev_state = node["state"]
    node["state"] = "pending"
    node["notes"]["attempt_notes"] += f" [reverted from {prev_state}]"
    node["updated_at"] = now_iso()
    save_graph(p, data)

    print(f"✓ {args.graph_id} / {args.node_id}: {prev_state} → ⬜ pending (reverted)")
    print(f"  Revert the code: git checkout HEAD -- . (or git stash)")
    print(f"  Then complete prerequisites before retrying.")


def cmd_tree(args):
    """Print the Mikado tree visualization."""
    data = load_graph(args.graph_id)
    print(render_tree(data))


def cmd_show(args):
    """Show details of a specific node."""
    data = load_graph(args.graph_id)
    node = find_node(data, args.node_id)
    if not node:
        print(f"Error: node '{args.node_id}' not found.", file=sys.stderr)
        sys.exit(1)
    icon = NODE_ICONS.get(node["state"], "?")
    print(f"{icon} {node['id']} [{node['state']}] {node.get('label', '')}")
    if node.get("prerequisites"):
        prereq_states = []
        for pid in node["prerequisites"]:
            pn = find_node(data, pid)
            pstate = pn["state"] if pn else "?"
            prereq_states.append(f"{pid}[{pstate}]")
        print(f"  Prerequisites: {', '.join(prereq_states)}")
    notes = node.get("notes", {})
    if notes.get("hypothesis"):
        print(f"  Hypothesis: {notes['hypothesis']}")
    if notes.get("blocker_description"):
        print(f"  Blockers: {notes['blocker_description']}")
    if notes.get("done_commit"):
        print(f"  Done commit: {notes['done_commit'][:8]}")


def cmd_list(args):
    """List all Mikado graphs."""
    if not GRAPHS_DIR.exists():
        print("No Mikado graphs found.")
        return
    graphs = sorted(GRAPHS_DIR.glob("mik-*.yaml"))
    if not graphs:
        print("No Mikado graphs found.")
        return
    for gp in graphs:
        data = yaml.safe_load(gp.read_text())
        state = data.get("graph_state", "?")
        if args.state and state != args.state:
            continue
        meta = data.get("metadata", {})
        goal = data.get("goal", "")[:45]
        print(f"🎋 {data['graph_id']:25s} [{state:12s}] {goal}  "
              f"({meta.get('done_nodes', 0)}/{meta.get('total_nodes', 0)} done)")


def cmd_abandon(args):
    """Abandon a Mikado graph."""
    p = graph_path(args.graph_id)
    data = load_graph(args.graph_id)
    data["graph_state"] = "abandoned"
    save_graph(p, data)
    print(f"✓ {args.graph_id}: abandoned")
    if args.reason:
        data["abandon_reason"] = args.reason
        save_graph(p, data)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="mikado",
        description="Mikado Method — Goal→try→revert→prerequisites tree-based refactoring"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # new
    p_new = sub.add_parser("new", help="Create a new Mikado graph")
    p_new.add_argument("goal", nargs="+", help="Refactoring goal")
    p_new.add_argument("--hypothesis", help="Why we believe this is achievable")

    # try
    p_try = sub.add_parser("try", help="Attempt a node change (pending/blocked → attempted)")
    p_try.add_argument("graph_id")
    p_try.add_argument("node_id")
    p_try.add_argument("--notes", help="What you're attempting")

    # block
    p_block = sub.add_parser("block", help="Mark node as blocked, discover prerequisites")
    p_block.add_argument("graph_id")
    p_block.add_argument("node_id")
    p_block.add_argument("--prereq", nargs="+", required=True,
                         help="Prerequisite(s) discovered (label text, can be multiple)")
    p_block.add_argument("--desc", help="Description of what blocked you")

    # done
    p_done = sub.add_parser("done", help="Mark node as done (attempted → done)")
    p_done.add_argument("graph_id")
    p_done.add_argument("node_id")

    # revert
    p_revert = sub.add_parser("revert", help="Revert node change (back to pending)")
    p_revert.add_argument("graph_id")
    p_revert.add_argument("node_id")

    # tree
    p_tree = sub.add_parser("tree", help="Print Mikado tree visualization")
    p_tree.add_argument("graph_id")

    # show
    p_show = sub.add_parser("show", help="Show node details")
    p_show.add_argument("graph_id")
    p_show.add_argument("node_id")

    # list
    p_list = sub.add_parser("list", help="List all graphs")
    p_list.add_argument("--state", choices=["in-progress", "done", "abandoned"],
                        help="Filter by state")

    # abandon
    p_abandon = sub.add_parser("abandon", help="Abandon a graph")
    p_abandon.add_argument("graph_id")
    p_abandon.add_argument("--reason", help="Why abandoned")

    args = parser.parse_args()
    dispatch = {
        "new": cmd_new, "try": cmd_try, "block": cmd_block,
        "done": cmd_done, "revert": cmd_revert, "tree": cmd_tree,
        "show": cmd_show, "list": cmd_list, "abandon": cmd_abandon,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
