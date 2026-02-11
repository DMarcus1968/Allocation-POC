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
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


_DB_DIR = Path(__file__).resolve().parents[2] / ".data"
_DB_PATH = _DB_DIR / "scenarios.sqlite"

# ── event constants ─────────────────────────────────────────────────

SCENARIO_CREATE = "create"
SCENARIO_UPDATE = "update"
SCENARIO_CLONE = "clone"
SCENARIO_LOCK = "lock"
PREVIEW_RUN = "run"
COMPARE_RUN = "compare_run"
EXPORT = "export"
CREATE_FROM_TEMPLATE = "create_from_template"

# ── redaction + stability helpers ──────────────────────────────────

_EMAIL_RE = re.compile(r"([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")

_MAX_PAYLOAD_BYTES = 8000
_MAX_LIST_LEN = 20
_MAX_STR_LEN = 500


def redact_actor(value: str) -> str:
    """Mask emails: ``alice@corp.com`` -> ``a***@corp.com``."""
    if not value or "@" not in value:
        return value
    return _EMAIL_RE.sub(lambda m: f"{m.group(1)}***@{m.group(2)}", value)


def stable_json(obj) -> str:
    """Deterministic compact JSON."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def bound_payload(details: dict, max_bytes: int = _MAX_PAYLOAD_BYTES) -> dict:
    """Truncate large text fields and cap list lengths in a details dict."""
    if not isinstance(details, dict):
        return details

    bounded: dict = {}
    for k, v in details.items():
        if isinstance(v, str) and len(v) > _MAX_STR_LEN:
            bounded[k] = v[:_MAX_STR_LEN] + "..."
        elif isinstance(v, list) and len(v) > _MAX_LIST_LEN:
            bounded[k] = v[:_MAX_LIST_LEN]
        elif isinstance(v, dict):
            bounded[k] = bound_payload(v, max_bytes)
        else:
            bounded[k] = v

    serialized = stable_json(bounded)
    if len(serialized.encode()) > max_bytes:
        bounded["_truncated"] = True
        trunc_json = stable_json(bounded)
        while len(trunc_json.encode()) > max_bytes and bounded:
            largest_key = max(
                (k for k in bounded if k != "_truncated"),
                key=lambda k: len(stable_json(bounded[k])),
                default=None,
            )
            if largest_key is None:
                break
            bounded[largest_key] = "...(truncated)"
            trunc_json = stable_json(bounded)

    return bounded


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
    summary: str = "",
    db_path: Path | None = None,
) -> str:
    """Insert an audit entry. Returns the audit id.

    Automatically redacts the actor and bounds the payload.
    """
    audit_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    safe_actor = redact_actor(actor)

    raw_details = payload or {}
    bounded = bound_payload(raw_details)

    # Build canonical payload
    canonical = {
        "event": event,
        "scenario_id": scenario_id,
        "actor": safe_actor,
        "timestamp": now,
        "entity": {
            "type": _entity_type(event),
            "id": scenario_id,
        },
        "summary": summary or _default_summary(event),
        "details": bounded,
    }
    compact_payload = stable_json(canonical)

    conn = _get_conn(db_path)
    try:
        conn.execute(
            """INSERT INTO audits (id, scenario_id, event, actor, payload, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (audit_id, scenario_id, event, safe_actor, compact_payload, now),
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
    """Query audit entries (most recent first)."""
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


# ── internal helpers ────────────────────────────────────────────────

def _entity_type(event: str) -> str:
    if event in (PREVIEW_RUN, COMPARE_RUN):
        return "run"
    if event == EXPORT:
        return "export"
    if event == CREATE_FROM_TEMPLATE:
        return "preset"
    return "scenario"


def _default_summary(event: str) -> str:
    summaries = {
        SCENARIO_CREATE: "Scenario created",
        SCENARIO_UPDATE: "Scenario updated",
        SCENARIO_CLONE: "Scenario cloned",
        SCENARIO_LOCK: "Scenario locked",
        PREVIEW_RUN: "Preview run completed",
        COMPARE_RUN: "Compare run completed",
        EXPORT: "Data exported",
        CREATE_FROM_TEMPLATE: "Scenario created from template",
    }
    return summaries.get(event, f"Event: {event}")


def _row_to_dict(row: sqlite3.Row) -> dict:
    raw_payload = json.loads(row["payload"])
    return {
        "id": row["id"],
        "scenario_id": row["scenario_id"],
        "event": row["event"],
        "actor": row["actor"],
        "payload": raw_payload,
        "created_at": row["created_at"],
    }
