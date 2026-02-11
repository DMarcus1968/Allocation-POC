"""SQLite-backed scenario persistence for Phase 2B.

DB file: <repo_root>/.data/scenarios.sqlite
Uses only the standard library ``sqlite3`` module.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from src.models.scenario import Scenario

_DB_DIR = Path(__file__).resolve().parents[2] / ".data"
_DB_PATH = _DB_DIR / "scenarios.sqlite"


class ScenarioLocked(Exception):
    """Raised when attempting to update a locked scenario."""


# ── database lifecycle ──────────────────────────────────────────────

def _get_conn(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or _DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Create the scenarios table if it does not exist."""
    conn = _get_conn(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id            TEXT PRIMARY KEY,
                name          TEXT NOT NULL DEFAULT '',
                description   TEXT,
                created_by    TEXT NOT NULL DEFAULT 'system',
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL,
                locked        INTEGER NOT NULL DEFAULT 0,
                knobs         TEXT NOT NULL DEFAULT '{}',
                seed_policy   TEXT NOT NULL DEFAULT '{}',
                "references"  TEXT NOT NULL DEFAULT '{}',
                checksum      TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ── helpers ─────────────────────────────────────────────────────────

def _row_to_scenario(row: sqlite3.Row) -> Scenario:
    return Scenario(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        locked=bool(row["locked"]),
        knobs=json.loads(row["knobs"]),
        seed_policy=json.loads(row["seed_policy"]),
        references=json.loads(row["references"]),
        checksum=row["checksum"],
    )


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# ── public API ──────────────────────────────────────────────────────

def list_scenarios(db_path: Path | None = None) -> list[Scenario]:
    conn = _get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM scenarios ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_scenario(r) for r in rows]
    finally:
        conn.close()


def get_scenario(scenario_id: str, db_path: Path | None = None) -> Scenario | None:
    conn = _get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM scenarios WHERE id = ?", (scenario_id,)
        ).fetchone()
        return _row_to_scenario(row) if row else None
    finally:
        conn.close()


def create_scenario(payload: dict, db_path: Path | None = None) -> Scenario:
    """Create a new scenario from a payload dict.

    Required: ``name``.  Optional: description, created_by, knobs,
    seed_policy, references.
    """
    now = _now_iso()
    scenario = Scenario(
        id=str(uuid.uuid4()),
        name=payload.get("name", "Untitled"),
        description=payload.get("description"),
        created_by=payload.get("created_by", "system"),
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
        locked=False,
        knobs=payload.get("knobs", {}),
        seed_policy=payload.get("seed_policy", {"mode": "common", "seed": 42}),
        references=payload.get("references", {
            "event_ref": "demo_event",
            "demand_config_ref": "default",
            "pricebook_ref": "read_only_default",
        }),
    )
    scenario.update_checksum()

    conn = _get_conn(db_path)
    try:
        conn.execute(
            """INSERT INTO scenarios
               (id, name, description, created_by, created_at, updated_at,
                locked, knobs, seed_policy, "references", checksum)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                scenario.id,
                scenario.name,
                scenario.description,
                scenario.created_by,
                scenario.created_at.isoformat(),
                scenario.updated_at.isoformat(),
                int(scenario.locked),
                json.dumps(scenario.knobs, sort_keys=True),
                json.dumps(scenario.seed_policy, sort_keys=True),
                json.dumps(scenario.references, sort_keys=True),
                scenario.checksum,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return scenario


def update_scenario(
    scenario_id: str,
    payload: dict,
    db_path: Path | None = None,
) -> Scenario:
    """Update a scenario.  Raises ScenarioLocked if locked."""
    existing = get_scenario(scenario_id, db_path)
    if existing is None:
        raise ValueError(f"Scenario {scenario_id} not found")
    if existing.locked:
        raise ScenarioLocked(f"Scenario {scenario_id} is locked and cannot be updated")

    now = _now_iso()
    updated_name = payload.get("name", existing.name)
    updated_desc = payload.get("description", existing.description)
    updated_knobs = payload.get("knobs", existing.knobs)
    updated_seed = payload.get("seed_policy", existing.seed_policy)
    updated_refs = payload.get("references", existing.references)

    scenario = Scenario(
        id=existing.id,
        name=updated_name,
        description=updated_desc,
        created_by=existing.created_by,
        created_at=existing.created_at,
        updated_at=datetime.fromisoformat(now),
        locked=existing.locked,
        knobs=updated_knobs,
        seed_policy=updated_seed,
        references=updated_refs,
    )
    scenario.update_checksum()

    conn = _get_conn(db_path)
    try:
        conn.execute(
            """UPDATE scenarios
               SET name = ?, description = ?, updated_at = ?,
                   knobs = ?, seed_policy = ?, "references" = ?, checksum = ?
               WHERE id = ?""",
            (
                scenario.name,
                scenario.description,
                scenario.updated_at.isoformat(),
                json.dumps(scenario.knobs, sort_keys=True),
                json.dumps(scenario.seed_policy, sort_keys=True),
                json.dumps(scenario.references, sort_keys=True),
                scenario.checksum,
                scenario.id,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return scenario


def clone_scenario(
    scenario_id: str,
    db_path: Path | None = None,
) -> Scenario:
    """Clone a scenario: new id, same knobs, locked=False."""
    existing = get_scenario(scenario_id, db_path)
    if existing is None:
        raise ValueError(f"Scenario {scenario_id} not found")

    return create_scenario(
        {
            "name": f"{existing.name} (clone)",
            "description": existing.description,
            "created_by": existing.created_by,
            "knobs": dict(existing.knobs),
            "seed_policy": dict(existing.seed_policy),
            "references": dict(existing.references),
        },
        db_path,
    )


def lock_scenario(
    scenario_id: str,
    db_path: Path | None = None,
) -> Scenario:
    """Lock a scenario, preventing further updates."""
    existing = get_scenario(scenario_id, db_path)
    if existing is None:
        raise ValueError(f"Scenario {scenario_id} not found")

    now = _now_iso()
    conn = _get_conn(db_path)
    try:
        conn.execute(
            "UPDATE scenarios SET locked = 1, updated_at = ? WHERE id = ?",
            (now, scenario_id),
        )
        conn.commit()
    finally:
        conn.close()

    return get_scenario(scenario_id, db_path)  # type: ignore[return-value]


def delete_scenario(
    scenario_id: str,
    db_path: Path | None = None,
) -> None:
    """Delete a scenario by id."""
    conn = _get_conn(db_path)
    try:
        conn.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
        conn.commit()
    finally:
        conn.close()
