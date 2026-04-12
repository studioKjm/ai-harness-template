"""MCP Server for AI Harness gates and tools.

Exposes harness gates, seed spec queries, and observability as MCP tools
so that any AI agent (not just Claude Code) can invoke them.

Usage:
    harness mcp-serve                      # Start MCP server (stdio)
    harness mcp-serve --transport sse      # Start with SSE transport

Requires: pip install ai-harness-pro[mcp]
"""

from __future__ import annotations

import json
import subprocess
import yaml
from pathlib import Path
from typing import Any


def create_server(project_root: Path | None = None):
    """Create and configure the MCP server with harness tools."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise ImportError(
            "MCP package not installed. Install with: pip install ai-harness-pro[mcp]"
        )

    root = Path(project_root) if project_root else Path(".")
    harness_dir = root / ".harness"
    ouroboros_dir = root / ".ouroboros"

    mcp = FastMCP(
        "AI Harness",
        description="Structural guardrails and specification-first development tools",
    )

    # ─── Gate Tools ─────────────────────────────────────────────

    def _run_gate(gate_name: str, extra_args: list[str] | None = None) -> dict:
        """Run a gate script and return structured result."""
        script = harness_dir / "gates" / gate_name
        if not script.exists():
            return {"status": "error", "message": f"Gate not found: {gate_name}"}

        cmd = ["bash", str(script), str(root)] + (extra_args or [])
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
            return {
                "status": "pass" if result.returncode == 0 else "fail",
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else "",
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Gate timed out (120s)"}

    @mcp.tool()
    def check_boundaries() -> str:
        """Check dependency boundary violations (import rules from boundaries.yaml)."""
        return json.dumps(_run_gate("check-boundaries.sh"), indent=2)

    @mcp.tool()
    def check_layers() -> str:
        """Check 3-tier layer separation (Presentation/Logic/Data)."""
        return json.dumps(_run_gate("check-layers.sh"), indent=2)

    @mcp.tool()
    def check_secrets() -> str:
        """Scan for leaked secrets, API keys, and credentials."""
        return json.dumps(_run_gate("check-secrets.sh"), indent=2)

    @mcp.tool()
    def check_security() -> str:
        """Run static application security testing (SAST)."""
        return json.dumps(_run_gate("check-security.sh"), indent=2)

    @mcp.tool()
    def check_structure() -> str:
        """Validate project file structure rules."""
        return json.dumps(_run_gate("check-structure.sh"), indent=2)

    @mcp.tool()
    def check_complexity() -> str:
        """Check code complexity (function length, params, nesting)."""
        return json.dumps(_run_gate("check-complexity.sh"), indent=2)

    @mcp.tool()
    def check_deps() -> str:
        """Scan dependencies for known vulnerabilities."""
        return json.dumps(_run_gate("check-deps.sh"), indent=2)

    @mcp.tool()
    def check_mutation(threshold: int = 60) -> str:
        """Run mutation testing to verify test quality."""
        return json.dumps(
            _run_gate("check-mutation.sh", [f"--threshold={threshold}"]),
            indent=2,
        )

    @mcp.tool()
    def check_performance(max_bundle: int = 500, max_deps: int = 50) -> str:
        """Check performance budgets (file sizes, dependency count, build output)."""
        return json.dumps(
            _run_gate("check-performance.sh", [
                f"--max-bundle={max_bundle}", f"--max-deps={max_deps}",
            ]),
            indent=2,
        )

    @mcp.tool()
    def check_ai_antipatterns() -> str:
        """Detect AI-generated code anti-patterns (hallucinated APIs, over-abstraction, naming drift)."""
        return json.dumps(_run_gate("check-ai-antipatterns.sh"), indent=2)

    @mcp.tool()
    def check_spec() -> str:
        """Check seed spec completeness (required fields, no TODO/TBD)."""
        return json.dumps(_run_gate("check-spec.sh"), indent=2)

    @mcp.tool()
    def run_all_gates() -> str:
        """Run all harness gates and return combined results."""
        gates = [
            "check-boundaries.sh", "check-layers.sh", "check-secrets.sh",
            "check-security.sh", "check-structure.sh", "check-spec.sh",
            "check-complexity.sh", "check-deps.sh", "check-mutation.sh",
            "check-performance.sh", "check-ai-antipatterns.sh",
        ]
        results = {}
        for gate in gates:
            name = gate.replace("check-", "").replace(".sh", "")
            results[name] = _run_gate(gate)
        passed = all(r["status"] == "pass" for r in results.values())
        return json.dumps({"verdict": "pass" if passed else "fail", "gates": results}, indent=2)

    # ─── Seed Spec Tools ────────────────────────────────────────

    @mcp.tool()
    def get_seed_spec(version: str = "latest") -> str:
        """Read the seed specification. Use version='latest' for most recent, or 'v1', 'v2', etc."""
        seeds_dir = ouroboros_dir / "seeds"
        if not seeds_dir.exists():
            return json.dumps({"error": "No seeds directory found"})

        if version == "latest":
            files = sorted(seeds_dir.glob("seed-v*.yaml"), reverse=True)
            if not files:
                return json.dumps({"error": "No seed files found"})
            seed_file = files[0]
        else:
            v = version.replace("v", "")
            seed_file = seeds_dir / f"seed-v{v}.yaml"

        if not seed_file.exists():
            return json.dumps({"error": f"Seed file not found: {seed_file.name}"})

        with open(seed_file) as f:
            data = yaml.safe_load(f)
        return json.dumps(data, indent=2, default=str)

    @mcp.tool()
    def get_interview(date: str = "latest") -> str:
        """Read interview data. Use date='latest' for most recent."""
        interviews_dir = ouroboros_dir / "interviews"
        if not interviews_dir.exists():
            return json.dumps({"error": "No interviews directory found"})

        if date == "latest":
            files = sorted(interviews_dir.glob("*.yaml"), reverse=True)
            if not files:
                return json.dumps({"error": "No interview files found"})
            interview_file = files[0]
        else:
            matches = list(interviews_dir.glob(f"{date}*.yaml"))
            if not matches:
                return json.dumps({"error": f"No interview found for date: {date}"})
            interview_file = matches[0]

        with open(interview_file) as f:
            data = yaml.safe_load(f)
        return json.dumps(data, indent=2, default=str)

    @mcp.tool()
    def get_ambiguity_score() -> str:
        """Get the current ambiguity score from the latest interview."""
        interviews_dir = ouroboros_dir / "interviews"
        if not interviews_dir.exists():
            return json.dumps({"error": "No interviews found"})

        files = sorted(interviews_dir.glob("*.yaml"), reverse=True)
        if not files:
            return json.dumps({"error": "No interview files found"})

        with open(files[0]) as f:
            data = yaml.safe_load(f)

        return json.dumps({
            "ambiguity_score": data.get("ambiguity_score", 1.0),
            "dimensions": data.get("dimensions", {}),
            "gate": "pass" if data.get("ambiguity_score", 1.0) <= 0.2 else "fail",
            "interview_date": data.get("date", ""),
        }, indent=2)

    # ─── Observability Tools ────────────────────────────────────

    @mcp.tool()
    def get_trace(trace_id: str = "latest") -> str:
        """Get agent observability trace data."""
        try:
            from harness_pro.observability.tracer import AgentTracer
            tracer = AgentTracer(project_root=root)
            if trace_id == "latest":
                traces = tracer.get_recent_traces(limit=1)
                if not traces:
                    return json.dumps({"error": "No traces found"})
                trace_id = traces[0]["trace_id"]
            return json.dumps(tracer.get_trace(trace_id), indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def get_audit_log(action: str = "", limit: int = 20) -> str:
        """Get audit log entries (gate runs, evaluations, rule changes)."""
        try:
            from harness_pro.persistence.store import EventStore
            store = EventStore(project_root=root)
            entries = store.get_audit_log(action=action or None, limit=limit)
            return json.dumps([
                {
                    "timestamp": e.timestamp, "action": e.action,
                    "target": e.target, "result": e.result, "actor": e.actor,
                }
                for e in entries
            ], indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ─── Resources ──────────────────────────────────────────────

    @mcp.resource("harness://architecture-invariants")
    def get_invariants() -> str:
        """Read the project's architecture invariants."""
        inv_file = root / "ARCHITECTURE_INVARIANTS.md"
        if inv_file.exists():
            return inv_file.read_text()
        return "No ARCHITECTURE_INVARIANTS.md found"

    @mcp.resource("harness://code-conventions")
    def get_conventions() -> str:
        """Read the project's coding conventions."""
        conv_file = root / "docs" / "code-convention.yaml"
        if conv_file.exists():
            return conv_file.read_text()
        return "No code-convention.yaml found"

    @mcp.resource("harness://boundary-rules")
    def get_boundary_rules() -> str:
        """Read the dependency boundary rules."""
        rules_file = harness_dir / "gates" / "rules" / "boundaries.yaml"
        if rules_file.exists():
            return rules_file.read_text()
        return "No boundaries.yaml found"

    return mcp
