"""SQLite-backed scenario persistence for Phase 2B.

DB file: <repo_root>/.data/scenarios.sqlite
Uses only the standard library ``sqlite3`` module.

Supports both legacy flat ``knobs`` and the new categorized format
(``knobs_promoter_constraints`` + ``knobs_allocation_policy``).
When loading rows that only have flat ``knobs``, the split is
performed automatically using the taxonomy in ``src.models.scenario``.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from src.models.scenario import Scenario, split_knobs, merge_knobs
from src.dashboard.audit_store import init_audit_table, append_audit
from src.dashboard.preset_store import init_presets_table

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
    """Create the scenarios table if it does not exist, and migrate.

    Also initializes the audit and presets tables.
    """
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
                knobs_promoter_constraints TEXT NOT NULL DEFAULT '{}',
                knobs_allocation_policy    TEXT NOT NULL DEFAULT '{}',
                seed_policy   TEXT NOT NULL DEFAULT '{}',
                "references"  TEXT NOT NULL DEFAULT '{}',
                checksum      TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.commit()

        # Migration: add new columns if they don't exist (for pre-existing DBs)
        _migrate_add_knob_columns(conn)
    finally:
        conn.close()

    # Initialize audit and presets tables in the same DB
    init_audit_table(db_path)
    init_presets_table(db_path)


def _migrate_add_knob_columns(conn: sqlite3.Connection) -> None:
    """Add knobs_promoter_constraints / knobs_allocation_policy if missing."""
    cursor = conn.execute("PRAGMA table_info(scenarios)")
    existing_cols = {row["name"] for row in cursor.fetchall()}

    if "knobs_promoter_constraints" not in existing_cols:
        conn.execute(
            "ALTER TABLE scenarios ADD COLUMN knobs_promoter_constraints "
            "TEXT NOT NULL DEFAULT '{}'"
        )
    if "knobs_allocation_policy" not in existing_cols:
        conn.execute(
            "ALTER TABLE scenarios ADD COLUMN knobs_allocation_policy "
            "TEXT NOT NULL DEFAULT '{}'"
        )
    conn.commit()


# ── helpers ─────────────────────────────────────────────────────────

def _row_to_scenario(row: sqlite3.Row) -> Scenario:
    knobs_raw = json.loads(row["knobs"])
    pc_raw = json.loads(row["knobs_promoter_constraints"])
    ap_raw = json.loads(row["knobs_allocation_policy"])

    # Migration: if sub-dicts are empty but flat knobs exists, auto-split
    if not pc_raw and not ap_raw and knobs_raw:
        pc_raw, ap_raw = split_knobs(knobs_raw)

    return Scenario(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        locked=bool(row["locked"]),
        knobs=knobs_raw,
        knobs_promoter_constraints=pc_raw,
        knobs_allocation_policy=ap_raw,
        seed_policy=json.loads(row["seed_policy"]),
        references=json.loads(row["references"]),
        checksum=row["checksum"],
    )


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _resolve_knobs(payload: dict) -> tuple[dict, dict, dict]:
    """Accept either legacy ``knobs`` or categorized sub-dicts.

    Returns (flat_knobs, promoter_constraints, allocation_policy).
    """
    pc = payload.get("knobs_promoter_constraints", {})
    ap = payload.get("knobs_allocation_policy", {})

    if pc or ap:
        # Categorized format is authoritative
        flat = merge_knobs(pc, ap)
    elif "knobs" in payload:
        flat = payload["knobs"]
        pc, ap = split_knobs(flat)
    else:
        flat, pc, ap = {}, {}, {}

    return flat, pc, ap


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

    Accepts either ``knobs`` (legacy) or
    ``knobs_promoter_constraints`` + ``knobs_allocation_policy``.
    """
    now = _now_iso()
    flat, pc, ap = _resolve_knobs(payload)

    scenario = Scenario(
        id=str(uuid.uuid4()),
        name=payload.get("name", "Untitled"),
        description=payload.get("description"),
        created_by=payload.get("created_by", "system"),
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
        locked=False,
        knobs=flat,
        knobs_promoter_constraints=pc,
        knobs_allocation_policy=ap,
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
                locked, knobs, knobs_promoter_constraints,
                knobs_allocation_policy, seed_policy, "references", checksum)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                scenario.id,
                scenario.name,
                scenario.description,
                scenario.created_by,
                scenario.created_at.isoformat(),
                scenario.updated_at.isoformat(),
                int(scenario.locked),
                json.dumps(scenario.knobs, sort_keys=True),
                json.dumps(scenario.knobs_promoter_constraints, sort_keys=True),
                json.dumps(scenario.knobs_allocation_policy, sort_keys=True),
                json.dumps(scenario.seed_policy, sort_keys=True),
                json.dumps(scenario.references, sort_keys=True),
                scenario.checksum,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Audit: create
    append_audit(
        scenario.id,
        "create",
        actor=scenario.created_by,
        payload={
            "name": scenario.name,
            "knobs_promoter_constraints": list(scenario.knobs_promoter_constraints.keys()),
            "knobs_allocation_policy": list(scenario.knobs_allocation_policy.keys()),
            "checksum": scenario.checksum,
        },
        db_path=db_path,
    )

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
        raise ScenarioLocked(
            f"Scenario {scenario_id} is locked and cannot be updated"
        )

    now = _now_iso()

    # Resolve knobs: prefer sub-dicts from payload, fall back to flat, then existing
    if "knobs_promoter_constraints" in payload or "knobs_allocation_policy" in payload:
        pc = payload.get(
            "knobs_promoter_constraints", existing.knobs_promoter_constraints
        )
        ap = payload.get(
            "knobs_allocation_policy", existing.knobs_allocation_policy
        )
        flat = merge_knobs(pc, ap)
    elif "knobs" in payload:
        flat = payload["knobs"]
        pc, ap = split_knobs(flat)
    else:
        flat = existing.knobs
        pc = existing.knobs_promoter_constraints
        ap = existing.knobs_allocation_policy

    scenario = Scenario(
        id=existing.id,
        name=payload.get("name", existing.name),
        description=payload.get("description", existing.description),
        created_by=existing.created_by,
        created_at=existing.created_at,
        updated_at=datetime.fromisoformat(now),
        locked=existing.locked,
        knobs=flat,
        knobs_promoter_constraints=pc,
        knobs_allocation_policy=ap,
        seed_policy=payload.get("seed_policy", existing.seed_policy),
        references=payload.get("references", existing.references),
    )
    scenario.update_checksum()

    conn = _get_conn(db_path)
    try:
        conn.execute(
            """UPDATE scenarios
               SET name = ?, description = ?, updated_at = ?,
                   knobs = ?, knobs_promoter_constraints = ?,
                   knobs_allocation_policy = ?,
                   seed_policy = ?, "references" = ?, checksum = ?
               WHERE id = ?""",
            (
                scenario.name,
                scenario.description,
                scenario.updated_at.isoformat(),
                json.dumps(scenario.knobs, sort_keys=True),
                json.dumps(scenario.knobs_promoter_constraints, sort_keys=True),
                json.dumps(scenario.knobs_allocation_policy, sort_keys=True),
                json.dumps(scenario.seed_policy, sort_keys=True),
                json.dumps(scenario.references, sort_keys=True),
                scenario.checksum,
                scenario.id,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Audit: update
    changed_keys = [k for k in payload if k not in ("created_by",)]
    append_audit(
        scenario.id,
        "update",
        actor=existing.created_by,
        payload={
            "before_checksum": existing.checksum,
            "after_checksum": scenario.checksum,
            "changed_keys": changed_keys,
        },
        db_path=db_path,
    )

    return scenario


def clone_scenario(
    scenario_id: str,
    db_path: Path | None = None,
) -> Scenario:
    """Clone a scenario: new id, same knobs, locked=False."""
    existing = get_scenario(scenario_id, db_path)
    if existing is None:
        raise ValueError(f"Scenario {scenario_id} not found")

    cloned = create_scenario(
        {
            "name": f"{existing.name} (clone)",
            "description": existing.description,
            "created_by": existing.created_by,
            "knobs_promoter_constraints": dict(existing.knobs_promoter_constraints),
            "knobs_allocation_policy": dict(existing.knobs_allocation_policy),
            "seed_policy": dict(existing.seed_policy),
            "references": dict(existing.references),
        },
        db_path,
    )

    # Audit: clone (in addition to the create audit from create_scenario)
    append_audit(
        cloned.id,
        "clone",
        actor=existing.created_by,
        payload={
            "source_id": existing.id,
            "new_id": cloned.id,
        },
        db_path=db_path,
    )

    return cloned


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

    locked_sc = get_scenario(scenario_id, db_path)

    # Audit: lock
    append_audit(
        scenario_id,
        "lock",
        actor=existing.created_by,
        payload={
            "locked_by": existing.created_by,
            "locked_at": now,
        },
        db_path=db_path,
    )

    return locked_sc  # type: ignore[return-value]


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
