"""Event Store for session persistence.

Uses SQLite to persist session state across conversation boundaries.
Enables long-running loops with audit logging.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Event:
    id: str
    session_id: str
    event_type: str  # interview_start, answer, seed_created, run_phase, eval_stage, evolve
    timestamp: str
    data: dict
    generation: int = 0


@dataclass
class Session:
    id: str
    created: str
    phase: str  # interview | seed | run | evaluate | evolve | converged
    seed_ref: str | None = None
    generation: int = 0
    event_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class AuditEntry:
    id: str
    timestamp: str
    action: str  # gate_run, rule_change, eval_run, seed_create, config_change
    actor: str  # cli, hook, ci, user
    target: str  # file or gate name
    result: str  # pass, fail, error, skip
    details: dict = field(default_factory=dict)


class EventStore:
    """SQLite-backed event store for session continuity."""

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = Path(project_root)
        self.db_path = self.project_root / ".harness" / "ouroboros" / "session.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created TEXT NOT NULL,
                    phase TEXT NOT NULL DEFAULT 'interview',
                    seed_ref TEXT,
                    generation INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL DEFAULT '{}',
                    generation INTEGER DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE INDEX IF NOT EXISTS idx_events_session
                    ON events(session_id, timestamp);

                CREATE INDEX IF NOT EXISTS idx_events_type
                    ON events(event_type);

                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL DEFAULT 'cli',
                    target TEXT NOT NULL DEFAULT '',
                    result TEXT NOT NULL DEFAULT '',
                    details TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_audit_action
                    ON audit_log(action, timestamp);

                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                    ON audit_log(timestamp);
            """)

    def create_session(self, metadata: dict | None = None) -> Session:
        """Create a new session."""
        session = Session(
            id=str(uuid.uuid4())[:8],
            created=datetime.now().isoformat(),
            phase="interview",
            metadata=metadata or {},
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (id, created, phase, metadata) VALUES (?, ?, ?, ?)",
                (session.id, session.created, session.phase, json.dumps(session.metadata)),
            )
        return session

    def get_current_session(self) -> Session | None:
        """Get the most recent active session."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, created, phase, seed_ref, generation, metadata "
                "FROM sessions ORDER BY created DESC LIMIT 1"
            ).fetchone()

        if not row:
            return None

        event_count = self._count_events(row[0])
        return Session(
            id=row[0],
            created=row[1],
            phase=row[2],
            seed_ref=row[3],
            generation=row[4],
            event_count=event_count,
            metadata=json.loads(row[5]) if row[5] else {},
        )

    def update_phase(self, session_id: str, phase: str) -> None:
        """Update session phase."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET phase = ? WHERE id = ?",
                (phase, session_id),
            )

    def update_generation(self, session_id: str, generation: int, seed_ref: str) -> None:
        """Update session generation and seed reference."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET generation = ?, seed_ref = ? WHERE id = ?",
                (generation, seed_ref, session_id),
            )

    def append_event(self, session_id: str, event_type: str, data: dict, generation: int = 0) -> Event:
        """Append an event to the session."""
        event = Event(
            id=str(uuid.uuid4())[:8],
            session_id=session_id,
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=data,
            generation=generation,
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events (id, session_id, event_type, timestamp, data, generation) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (event.id, event.session_id, event.event_type,
                 event.timestamp, json.dumps(event.data), event.generation),
            )
        return event

    def get_events(self, session_id: str, event_type: str | None = None) -> list[Event]:
        """Get events for a session, optionally filtered by type."""
        with sqlite3.connect(self.db_path) as conn:
            if event_type:
                rows = conn.execute(
                    "SELECT id, session_id, event_type, timestamp, data, generation "
                    "FROM events WHERE session_id = ? AND event_type = ? ORDER BY timestamp",
                    (session_id, event_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, session_id, event_type, timestamp, data, generation "
                    "FROM events WHERE session_id = ? ORDER BY timestamp",
                    (session_id,),
                ).fetchall()

        return [
            Event(
                id=r[0], session_id=r[1], event_type=r[2],
                timestamp=r[3], data=json.loads(r[4]), generation=r[5],
            )
            for r in rows
        ]

    def get_generation_history(self, session_id: str) -> list[dict]:
        """Get evolution history across generations."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT generation, MIN(timestamp) as start_time "
                "FROM events WHERE session_id = ? GROUP BY generation ORDER BY generation",
                (session_id,),
            ).fetchall()
        return [{"generation": r[0], "started": r[1]} for r in rows]

    def _count_events(self, session_id: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM events WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return row[0] if row else 0

    # ─── Audit Log ────────────────────────────────────────────────

    def log_audit(
        self,
        action: str,
        target: str,
        result: str,
        actor: str = "cli",
        details: dict | None = None,
    ) -> AuditEntry:
        """Record an audit log entry."""
        entry = AuditEntry(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            action=action,
            actor=actor,
            target=target,
            result=result,
            details=details or {},
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO audit_log (id, timestamp, action, actor, target, result, details) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entry.id, entry.timestamp, entry.action, entry.actor,
                 entry.target, entry.result, json.dumps(entry.details)),
            )
        return entry

    def get_audit_log(
        self,
        action: str | None = None,
        limit: int = 50,
    ) -> list[AuditEntry]:
        """Query audit log entries, optionally filtered by action."""
        with sqlite3.connect(self.db_path) as conn:
            if action:
                rows = conn.execute(
                    "SELECT id, timestamp, action, actor, target, result, details "
                    "FROM audit_log WHERE action = ? ORDER BY timestamp DESC LIMIT ?",
                    (action, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, timestamp, action, actor, target, result, details "
                    "FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()

        return [
            AuditEntry(
                id=r[0], timestamp=r[1], action=r[2], actor=r[3],
                target=r[4], result=r[5],
                details=json.loads(r[6]) if r[6] else {},
            )
            for r in rows
        ]

    def get_audit_summary(self) -> dict:
        """Get a summary of audit log activity."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT action, result, COUNT(*) as cnt "
                "FROM audit_log GROUP BY action, result ORDER BY cnt DESC"
            ).fetchall()
        summary: dict[str, dict[str, int]] = {}
        for action, result, count in rows:
            summary.setdefault(action, {})[result] = count
        return summary
