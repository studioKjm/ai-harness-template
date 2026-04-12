#!/usr/bin/env python3
"""Drift monitor hook for PostToolUse (Edit/Write).

Measures how far the changed file deviates from the seed spec.
Outputs a warning if drift exceeds threshold.
"""

import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        return

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        return

    # Skip non-code files
    code_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs"}
    if file_path.suffix not in code_extensions:
        return

    # Find project root (walk up looking for .harness/)
    project_root = file_path.parent
    for _ in range(10):
        if (project_root / ".harness").is_dir():
            break
        parent = project_root.parent
        if parent == project_root:
            return  # No .harness found
        project_root = parent
    else:
        return

    try:
        from harness_pro.drift.monitor import DriftMonitor
        monitor = DriftMonitor(project_root=project_root)
        score = monitor.measure(file_path)

        if score > 0.3:
            print(f"[Harness] HIGH DRIFT: {score:.2f} — {file_path.name} deviates from seed spec")
        elif score > 0.1:
            print(f"[Harness] Moderate drift: {score:.2f} — {file_path.name}")
    except ImportError:
        # harness_pro not installed, try lightweight check
        seeds_dir = project_root / ".harness" / "ouroboros" / "seeds"
        if seeds_dir.exists() and list(seeds_dir.glob("seed-v*.yaml")):
            # Basic check: just note that drift monitoring is available
            pass


if __name__ == "__main__":
    main()
