"""Append-only audit trail for scenario lifecycle events.

Every mutating operation (create, update, clone, lock, run, export)
appends a compact audit entry.  Entries are immutable once written.

Schema:
  audits(id, scenario_id, event, actor, payload, created_at)

Privacy: payloads must never contain raw demand draws, PII, or
request-level data.  Actor is a user handle (masked if needed).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


_DB_DIR = Path(__file__).resolve().parents[2] / ".data"
_DB_PATH = _DB_DIR / "scenarios.sqlite"


# ── database lifecycle ──────────────────────────────────────────────

def _get_conn(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or _DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_audit_table(db_path: Path | None = None) -> None:
    """Create the audits table if it does not exist."""
    conn = _get_conn(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audits (
                id          TEXT PRIMARY KEY,
                scenario_id TEXT NOT NULL,
                event       TEXT NOT NULL,
                actor       TEXT NOT NULL DEFAULT 'system',
                payload     TEXT NOT NULL DEFAULT '{}',
                created_at  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audits_scenario
            ON audits(scenario_id, created_at DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audits_event
            ON audits(event, created_at DESC)
        """)
        conn.commit()
    finally:
        conn.close()


# ── public API ──────────────────────────────────────────────────────

def append_audit(
    scenario_id: str,
    event: str,
    actor: str = "system",
    payload: dict | None = None,
    db_path: Path | None = None,
) -> str:
    """Insert an audit entry. Returns the audit id."""
    audit_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    compact_payload = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))

    conn = _get_conn(db_path)
    try:
        conn.execute(
            """INSERT INTO audits (id, scenario_id, event, actor, payload, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (audit_id, scenario_id, event, actor, compact_payload, now),
        )
        conn.commit()
    finally:
        conn.close()

    return audit_id


def list_audits(
    scenario_id: str | None = None,
    event: str | None = None,
    limit: int = 100,
    since: str | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    """Query audit entries (most recent first).

    Args:
        scenario_id: filter by scenario (optional).
        event: filter by event type (optional).
        limit: max rows (default 100).
        since: ISO8601 timestamp lower bound (optional).
        db_path: DB path override.

    Returns:
        List of audit dicts (most recent first).
    """
    conn = _get_conn(db_path)
    try:
        clauses: list[str] = []
        params: list = []

        if scenario_id:
            clauses.append("scenario_id = ?")
            params.append(scenario_id)
        if event:
            clauses.append("event = ?")
            params.append(event)
        if since:
            clauses.append("created_at >= ?")
            params.append(since)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        sql = f"SELECT * FROM audits {where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "scenario_id": row["scenario_id"],
        "event": row["event"],
        "actor": row["actor"],
        "payload": json.loads(row["payload"]),
        "created_at": row["created_at"],
    }
