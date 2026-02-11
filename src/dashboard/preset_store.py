"""Named presets (scenario templates) for promoter-facing quick-start.

Presets are read-mostly templates.  Creating a scenario from a preset
copies the knobs into a new Scenario; the preset itself is never mutated
by allocation runs.

Three system presets are seeded at ``init_presets_table()`` time.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from src.dashboard import scenario_store
from src.dashboard.audit_store import append_audit
from src.models.scenario import Scenario


_DB_DIR = Path(__file__).resolve().parents[2] / ".data"
_DB_PATH = _DB_DIR / "scenarios.sqlite"


# ── system presets (seed data) ──────────────────────────────────────

_SYSTEM_PRESETS: list[dict] = [
    {
        "id": "preset_fan_first",
        "name": "Fan-first",
        "description": "Maximize tickets served per account, groups prioritized.",
        "creator": "system",
        "knobs_promoter_constraints": {
            "per_account_cap": 6,
            "holdback_pct": 0.0,
            "section_eligibility": {},
        },
        "knobs_allocation_policy": {
            "singles_avoidance": True,
            "priority_mode": "random",
        },
    },
    {
        "id": "preset_revenue_protect",
        "name": "Revenue-protect",
        "description": "Lower holdbacks, preserve higher-priced section allocation.",
        "creator": "system",
        "knobs_promoter_constraints": {
            "per_account_cap": 4,
            "holdback_pct": 0.05,
        },
        "knobs_allocation_policy": {
            "singles_avoidance": False,
            "priority_mode": "promoter_provided_tier",
        },
    },
    {
        "id": "preset_vip_holdback",
        "name": "VIP-holdback",
        "description": "Preserve inventory for VIP / artist allocations.",
        "creator": "system",
        "knobs_promoter_constraints": {
            "per_account_cap": 4,
            "holdback_pct": 0.15,
            "holdback_target": "VIP",
        },
        "knobs_allocation_policy": {
            "singles_avoidance": False,
            "priority_mode": "tier_then_time",
        },
    },
]


# ── database lifecycle ──────────────────────────────────────────────

def _get_conn(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or _DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_presets_table(db_path: Path | None = None) -> None:
    """Create presets table and seed system presets if not present."""
    conn = _get_conn(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS presets (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                creator     TEXT NOT NULL DEFAULT 'system',
                knobs_promoter_constraints TEXT NOT NULL DEFAULT '{}',
                knobs_allocation_policy    TEXT NOT NULL DEFAULT '{}',
                created_at  TEXT NOT NULL
            )
        """)
        conn.commit()

        # Seed system presets (skip if already present)
        for preset in _SYSTEM_PRESETS:
            existing = conn.execute(
                "SELECT id FROM presets WHERE id = ?", (preset["id"],)
            ).fetchone()
            if existing is None:
                now = datetime.utcnow().isoformat()
                conn.execute(
                    """INSERT INTO presets
                       (id, name, description, creator,
                        knobs_promoter_constraints, knobs_allocation_policy,
                        created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        preset["id"],
                        preset["name"],
                        preset["description"],
                        preset["creator"],
                        json.dumps(preset["knobs_promoter_constraints"], sort_keys=True),
                        json.dumps(preset["knobs_allocation_policy"], sort_keys=True),
                        now,
                    ),
                )
        conn.commit()
    finally:
        conn.close()


# ── helpers ─────────────────────────────────────────────────────────

def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "creator": row["creator"],
        "knobs_promoter_constraints": json.loads(row["knobs_promoter_constraints"]),
        "knobs_allocation_policy": json.loads(row["knobs_allocation_policy"]),
        "created_at": row["created_at"],
    }


# ── public API ──────────────────────────────────────────────────────

def list_presets(db_path: Path | None = None) -> list[dict]:
    """Return all presets ordered by creation date."""
    conn = _get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM presets ORDER BY created_at"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_preset(preset_id: str, db_path: Path | None = None) -> dict | None:
    """Return a single preset or None."""
    conn = _get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM presets WHERE id = ?", (preset_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def create_preset(payload: dict, db_path: Path | None = None) -> dict:
    """Create a new preset from a payload dict."""
    preset_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = _get_conn(db_path)
    try:
        conn.execute(
            """INSERT INTO presets
               (id, name, description, creator,
                knobs_promoter_constraints, knobs_allocation_policy, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                preset_id,
                payload.get("name", "Custom template"),
                payload.get("description", ""),
                payload.get("creator", "promoter"),
                json.dumps(payload.get("knobs_promoter_constraints", {}), sort_keys=True),
                json.dumps(payload.get("knobs_allocation_policy", {}), sort_keys=True),
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return get_preset(preset_id, db_path)  # type: ignore[return-value]


def delete_preset(preset_id: str, db_path: Path | None = None) -> bool:
    """Delete a preset. Returns True if a row was deleted."""
    conn = _get_conn(db_path)
    try:
        cursor = conn.execute(
            "DELETE FROM presets WHERE id = ?", (preset_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def apply_preset_to_new_scenario(
    preset_id: str,
    created_by: str = "system",
    db_path: Path | None = None,
) -> Scenario:
    """Create a new scenario pre-populated with the preset's knobs.

    Computes a fresh checksum and appends audit entries for both
    the create and the template-apply events.
    """
    preset = get_preset(preset_id, db_path)
    if preset is None:
        raise ValueError(f"Preset {preset_id} not found")

    scenario = scenario_store.create_scenario(
        {
            "name": f"{preset['name']} scenario",
            "description": f"Created from template: {preset['name']}",
            "created_by": created_by,
            "knobs_promoter_constraints": dict(preset["knobs_promoter_constraints"]),
            "knobs_allocation_policy": dict(preset["knobs_allocation_policy"]),
        },
        db_path,
    )

    # Audit: record that this scenario was created from a template
    append_audit(
        scenario.id,
        "create_from_template",
        actor=created_by,
        payload={
            "preset_id": preset_id,
            "preset_name": preset["name"],
            "scenario_id": scenario.id,
        },
        db_path=db_path,
    )

    return scenario
