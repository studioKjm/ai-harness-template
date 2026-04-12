#!/usr/bin/env python3
"""Session start hook — initializes or resumes session tracking.

Runs on SessionStart to:
1. Check for existing active session
2. Resume if found, create new if not
3. Display session status
"""

import sys
from pathlib import Path


def main():
    # Find project root
    cwd = Path.cwd()
    project_root = cwd
    for _ in range(10):
        if (project_root / ".ouroboros").is_dir():
            break
        parent = project_root.parent
        if parent == project_root:
            return
        project_root = parent
    else:
        return

    try:
        from harness_pro.persistence.store import EventStore
        store = EventStore(project_root=project_root)
        session = store.get_current_session()

        if session:
            print(f"[Harness] Resuming session {session.id} | Phase: {session.phase} | Gen: {session.generation}")
            if session.seed_ref:
                print(f"[Harness] Seed: {session.seed_ref}")
        else:
            # Don't auto-create — let the user start explicitly
            print("[Harness] No active session. Run /interview to start.")

    except ImportError:
        # harness_pro not installed
        ouroboros_dir = project_root / ".ouroboros"
        if ouroboros_dir.exists():
            seeds = list((ouroboros_dir / "seeds").glob("seed-v*.yaml")) if (ouroboros_dir / "seeds").exists() else []
            if seeds:
                print(f"[Harness] Found {len(seeds)} seed spec(s). Run /evaluate to verify.")


if __name__ == "__main__":
    main()
