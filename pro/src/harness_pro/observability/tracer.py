"""Agent Observability — structured tracing for Ouroboros cycles.

Tracks agent decisions, tool usage, token costs, and phase transitions
across the specification-first workflow. Stores traces in SQLite
for post-hoc analysis and debugging.

Usage:
    tracer = AgentTracer(project_root)
    with tracer.span("interview", agent="interviewer") as span:
        span.event("question_asked", {"dimension": "goal_clarity"})
        span.metric("ambiguity_score", 0.35)
    tracer.summary()
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Generator


@dataclass
class SpanEvent:
    name: str
    timestamp: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    id: str
    trace_id: str
    name: str  # interview, seed, run, evaluate, evolve
    agent: str  # interviewer, seed-architect, evaluator, etc.
    start_time: float
    end_time: float = 0.0
    status: str = "in_progress"  # in_progress, completed, failed
    events: list[SpanEvent] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end_time > 0:
            return round((self.end_time - self.start_time) * 1000, 2)
        return round((time.time() - self.start_time) * 1000, 2)

    def event(self, name: str, data: dict[str, Any] | None = None) -> None:
        """Record an event within this span."""
        self.events.append(SpanEvent(
            name=name,
            timestamp=datetime.now().isoformat(),
            data=data or {},
        ))

    def metric(self, name: str, value: float) -> None:
        """Record a numeric metric."""
        self.metrics[name] = value

    def tag(self, key: str, value: Any) -> None:
        """Add metadata tag."""
        self.metadata[key] = value

    def fail(self, reason: str) -> None:
        """Mark span as failed."""
        self.status = "failed"
        self.metadata["failure_reason"] = reason

    def complete(self) -> None:
        """Mark span as completed."""
        self.end_time = time.time()
        if self.status == "in_progress":
            self.status = "completed"


class AgentTracer:
    """Structured tracing for AI agent workflows."""

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = Path(project_root)
        self.db_path = self.project_root / ".ouroboros" / "session.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.trace_id = str(uuid.uuid4())[:12]
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS traces (
                    id TEXT PRIMARY KEY,
                    created TEXT NOT NULL,
                    phase TEXT NOT NULL DEFAULT '',
                    span_count INTEGER DEFAULT 0,
                    total_duration_ms REAL DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS spans (
                    id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    agent TEXT NOT NULL DEFAULT '',
                    start_time REAL NOT NULL,
                    end_time REAL DEFAULT 0,
                    duration_ms REAL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'in_progress',
                    events TEXT DEFAULT '[]',
                    metrics TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (trace_id) REFERENCES traces(id)
                );

                CREATE INDEX IF NOT EXISTS idx_spans_trace
                    ON spans(trace_id, start_time);
            """)

    def new_trace(self, phase: str = "") -> str:
        """Start a new trace (top-level workflow execution)."""
        self.trace_id = str(uuid.uuid4())[:12]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO traces (id, created, phase) VALUES (?, ?, ?)",
                (self.trace_id, datetime.now().isoformat(), phase),
            )
        return self.trace_id

    @contextmanager
    def span(self, name: str, agent: str = "") -> Generator[Span, None, None]:
        """Create a traced span (context manager).

        Usage:
            with tracer.span("evaluate", agent="evaluator") as s:
                s.event("stage_started", {"stage": "mechanical"})
                s.metric("ac_compliance", 0.85)
        """
        s = Span(
            id=str(uuid.uuid4())[:8],
            trace_id=self.trace_id,
            name=name,
            agent=agent,
            start_time=time.time(),
        )
        try:
            yield s
            s.complete()
        except Exception as e:
            s.fail(str(e))
            raise
        finally:
            self._save_span(s)

    def record_span(
        self,
        name: str,
        agent: str = "",
        status: str = "completed",
        events: list[dict] | None = None,
        metrics: dict[str, float] | None = None,
        metadata: dict[str, Any] | None = None,
        duration_ms: float = 0,
    ) -> Span:
        """Record a span without context manager (for non-interactive use)."""
        now = time.time()
        s = Span(
            id=str(uuid.uuid4())[:8],
            trace_id=self.trace_id,
            name=name,
            agent=agent,
            start_time=now - (duration_ms / 1000),
            end_time=now,
            status=status,
            metrics=metrics or {},
            metadata=metadata or {},
        )
        if events:
            for e in events:
                s.event(e.get("name", ""), e.get("data", {}))
        self._save_span(s)
        return s

    def _save_span(self, span: Span) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO spans "
                "(id, trace_id, name, agent, start_time, end_time, duration_ms, "
                "status, events, metrics, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    span.id, span.trace_id, span.name, span.agent,
                    span.start_time, span.end_time, span.duration_ms,
                    span.status,
                    json.dumps([{"name": e.name, "timestamp": e.timestamp, "data": e.data}
                                for e in span.events]),
                    json.dumps(span.metrics),
                    json.dumps(span.metadata),
                ),
            )
            conn.execute(
                "UPDATE traces SET span_count = span_count + 1, "
                "total_duration_ms = total_duration_ms + ? WHERE id = ?",
                (span.duration_ms, span.trace_id),
            )

    def get_trace(self, trace_id: str | None = None) -> dict:
        """Get a complete trace with all spans."""
        tid = trace_id or self.trace_id
        with sqlite3.connect(self.db_path) as conn:
            trace = conn.execute(
                "SELECT id, created, phase, span_count, total_duration_ms, metadata "
                "FROM traces WHERE id = ?", (tid,)
            ).fetchone()
            if not trace:
                return {}

            spans = conn.execute(
                "SELECT id, name, agent, duration_ms, status, events, metrics, metadata "
                "FROM spans WHERE trace_id = ? ORDER BY start_time", (tid,)
            ).fetchall()

        return {
            "trace_id": trace[0],
            "created": trace[1],
            "phase": trace[2],
            "span_count": trace[3],
            "total_duration_ms": trace[4],
            "spans": [
                {
                    "id": s[0], "name": s[1], "agent": s[2],
                    "duration_ms": s[3], "status": s[4],
                    "events": json.loads(s[5]),
                    "metrics": json.loads(s[6]),
                    "metadata": json.loads(s[7]),
                }
                for s in spans
            ],
        }

    def get_recent_traces(self, limit: int = 10) -> list[dict]:
        """Get recent traces summary."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, created, phase, span_count, total_duration_ms "
                "FROM traces ORDER BY created DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {"trace_id": r[0], "created": r[1], "phase": r[2],
             "span_count": r[3], "total_duration_ms": r[4]}
            for r in rows
        ]

    def summary(self, trace_id: str | None = None) -> str:
        """Generate human-readable trace summary."""
        trace = self.get_trace(trace_id)
        if not trace:
            return "No trace found."

        lines = [
            f"Trace: {trace['trace_id']} ({trace['phase'] or 'unknown'})",
            f"Created: {trace['created'][:19]}",
            f"Spans: {trace['span_count']}",
            f"Duration: {trace['total_duration_ms']:.0f}ms",
            "",
        ]

        for s in trace["spans"]:
            status_icon = {"completed": "+", "failed": "!", "in_progress": "~"}.get(s["status"], "?")
            lines.append(
                f"  [{status_icon}] {s['name']}"
                f" ({s['agent'] or '-'})"
                f" {s['duration_ms']:.0f}ms"
                f" {s['status']}"
            )
            for k, v in s["metrics"].items():
                lines.append(f"      {k}: {v}")
            for e in s["events"]:
                lines.append(f"      > {e['name']}")

        return "\n".join(lines)
