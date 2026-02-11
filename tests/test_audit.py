"""Tests for the audit trail (Phase 2B Step 7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.dashboard.scenario_store import (
    ScenarioLocked,
    create_scenario,
    clone_scenario,
    init_db,
    lock_scenario,
    update_scenario,
)
from src.dashboard.audit_store import append_audit, list_audits
from src.dashboard.tradeoff_engine import run_preview


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.sqlite"
    init_db(p)
    return p


class TestAuditAppend:
    def test_append_returns_id(self, db_path: Path):
        audit_id = append_audit(
            "test-scenario", "test_event", "tester", {"key": "val"}, db_path
        )
        assert isinstance(audit_id, str)
        assert len(audit_id) > 0

    def test_list_audits_returns_entry(self, db_path: Path):
        append_audit("sc-1", "create", "tester", {"name": "test"}, db_path)
        audits = list_audits(scenario_id="sc-1", db_path=db_path)
        assert len(audits) >= 1
        assert audits[0]["event"] == "create"
        assert audits[0]["actor"] == "tester"
        assert audits[0]["payload"]["name"] == "test"


class TestAuditFromScenarioStore:
    def test_create_produces_audit(self, db_path: Path):
        sc = create_scenario(
            {"name": "Audit Test", "knobs": {"per_account_cap": 4}},
            db_path,
        )
        audits = list_audits(scenario_id=sc.id, db_path=db_path)
        events = [a["event"] for a in audits]
        assert "create" in events

    def test_update_produces_audit(self, db_path: Path):
        sc = create_scenario({"name": "Before"}, db_path)
        update_scenario(sc.id, {"name": "After"}, db_path)
        audits = list_audits(scenario_id=sc.id, db_path=db_path)
        events = [a["event"] for a in audits]
        assert "update" in events

        # Verify update payload has checksums
        update_audit = next(a for a in audits if a["event"] == "update")
        assert "before_checksum" in update_audit["payload"]
        assert "after_checksum" in update_audit["payload"]

    def test_clone_produces_audit(self, db_path: Path):
        sc = create_scenario(
            {"name": "Original", "knobs": {"per_account_cap": 3}},
            db_path,
        )
        cloned = clone_scenario(sc.id, db_path)
        audits = list_audits(scenario_id=cloned.id, db_path=db_path)
        events = [a["event"] for a in audits]
        assert "clone" in events

        clone_audit = next(a for a in audits if a["event"] == "clone")
        assert clone_audit["payload"]["source_id"] == sc.id
        assert clone_audit["payload"]["new_id"] == cloned.id

    def test_lock_produces_audit(self, db_path: Path):
        sc = create_scenario({"name": "Lock Me"}, db_path)
        lock_scenario(sc.id, db_path)
        audits = list_audits(scenario_id=sc.id, db_path=db_path)
        events = [a["event"] for a in audits]
        assert "lock" in events

    def test_locked_scenario_rejects_update(self, db_path: Path):
        sc = create_scenario({"name": "Lock Test"}, db_path)
        lock_scenario(sc.id, db_path)
        with pytest.raises(ScenarioLocked):
            update_scenario(sc.id, {"name": "Nope"}, db_path)


class TestAuditFromRun:
    def test_preview_produces_run_audit(self, db_path: Path):
        sc = create_scenario(
            {
                "name": "Run Audit Test",
                "knobs": {"per_account_cap": 4},
                "seed_policy": {"mode": "common", "seed": 42},
            },
            db_path,
        )
        run_preview(sc.id, seed=42, db_path=db_path)
        audits = list_audits(scenario_id=sc.id, db_path=db_path)
        events = [a["event"] for a in audits]
        assert "run" in events

        run_audit = next(a for a in audits if a["event"] == "run")
        assert "run_id" in run_audit["payload"]
        assert "seed" in run_audit["payload"]
        assert "checksum" in run_audit["payload"]
        assert "demand_hash" in run_audit["payload"]
        assert "tickets_fulfilled" in run_audit["payload"]


class TestAuditFilters:
    def test_filter_by_event(self, db_path: Path):
        sc = create_scenario({"name": "Filter Test"}, db_path)
        update_scenario(sc.id, {"name": "Updated"}, db_path)

        create_audits = list_audits(event="create", db_path=db_path)
        assert all(a["event"] == "create" for a in create_audits)

        update_audits = list_audits(event="update", db_path=db_path)
        assert all(a["event"] == "update" for a in update_audits)

    def test_limit(self, db_path: Path):
        sc = create_scenario({"name": "Limit Test"}, db_path)
        for i in range(5):
            update_scenario(sc.id, {"name": f"v{i}"}, db_path)

        audits = list_audits(scenario_id=sc.id, limit=3, db_path=db_path)
        assert len(audits) <= 3

    def test_order_most_recent_first(self, db_path: Path):
        sc = create_scenario({"name": "Order Test"}, db_path)
        update_scenario(sc.id, {"name": "v1"}, db_path)
        update_scenario(sc.id, {"name": "v2"}, db_path)

        audits = list_audits(scenario_id=sc.id, db_path=db_path)
        timestamps = [a["created_at"] for a in audits]
        assert timestamps == sorted(timestamps, reverse=True)
