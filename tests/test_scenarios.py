"""Tests for scenario model and scenario_store (Phase 2B Step 1)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.models.scenario import Scenario
from src.dashboard.scenario_store import (
    ScenarioLocked,
    clone_scenario,
    create_scenario,
    delete_scenario,
    get_scenario,
    init_db,
    list_scenarios,
    lock_scenario,
    update_scenario,
)


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Provide a temporary DB path for each test."""
    p = tmp_path / "test.sqlite"
    init_db(p)
    return p


# ── Scenario model tests ───────────────────────────────────────────

class TestScenarioModel:
    def test_checksum_stable_for_same_inputs(self):
        s1 = Scenario(knobs={"a": 1, "b": 2}, seed_policy={"mode": "common", "seed": 42})
        s2 = Scenario(knobs={"b": 2, "a": 1}, seed_policy={"seed": 42, "mode": "common"})
        assert s1.compute_checksum() == s2.compute_checksum()

    def test_checksum_differs_for_different_inputs(self):
        s1 = Scenario(knobs={"a": 1})
        s2 = Scenario(knobs={"a": 2})
        assert s1.compute_checksum() != s2.compute_checksum()

    def test_to_dict_roundtrip(self):
        s = Scenario(name="test", knobs={"x": 10})
        s.update_checksum()
        d = s.to_dict()
        s2 = Scenario.from_dict(d)
        assert s2.name == s.name
        assert s2.knobs == s.knobs
        assert s2.checksum == s.checksum

    def test_update_checksum(self):
        s = Scenario(knobs={"a": 1})
        assert s.checksum == ""
        s.update_checksum()
        assert s.checksum != ""
        assert s.checksum == s.compute_checksum()


# ── Scenario store tests ───────────────────────────────────────────

class TestScenarioStore:
    def test_create_get_list(self, db_path: Path):
        sc = create_scenario({"name": "Test Scenario", "knobs": {"per_account_cap": 4}}, db_path)
        assert sc.name == "Test Scenario"
        assert sc.knobs == {"per_account_cap": 4}
        assert sc.checksum != ""

        fetched = get_scenario(sc.id, db_path)
        assert fetched is not None
        assert fetched.id == sc.id
        assert fetched.knobs == sc.knobs

        all_scenarios = list_scenarios(db_path)
        assert len(all_scenarios) == 1
        assert all_scenarios[0].id == sc.id

    def test_update_scenario(self, db_path: Path):
        sc = create_scenario({"name": "Original"}, db_path)
        updated = update_scenario(sc.id, {"name": "Updated", "knobs": {"holdback_pct": 0.1}}, db_path)
        assert updated.name == "Updated"
        assert updated.knobs == {"holdback_pct": 0.1}
        assert updated.checksum != sc.checksum

    def test_clone_produces_new_id(self, db_path: Path):
        sc = create_scenario({"name": "Original", "knobs": {"per_account_cap": 3}}, db_path)
        cloned = clone_scenario(sc.id, db_path)
        assert cloned.id != sc.id
        assert cloned.knobs == sc.knobs
        assert cloned.locked is False
        assert "clone" in cloned.name

    def test_lock_prevents_update(self, db_path: Path):
        sc = create_scenario({"name": "To Lock"}, db_path)
        locked = lock_scenario(sc.id, db_path)
        assert locked.locked is True

        with pytest.raises(ScenarioLocked):
            update_scenario(sc.id, {"name": "Nope"}, db_path)

    def test_delete_scenario(self, db_path: Path):
        sc = create_scenario({"name": "To Delete"}, db_path)
        delete_scenario(sc.id, db_path)
        assert get_scenario(sc.id, db_path) is None

    def test_checksum_stable_across_store_operations(self, db_path: Path):
        knobs = {"per_account_cap": 4, "holdback_pct": 0.05}
        sc1 = create_scenario({"name": "A", "knobs": knobs}, db_path)
        sc2 = create_scenario({"name": "B", "knobs": knobs}, db_path)
        # Same knobs + same default seed_policy + same default references → same checksum
        assert sc1.checksum == sc2.checksum

    def test_get_nonexistent(self, db_path: Path):
        assert get_scenario("nonexistent-id", db_path) is None

    def test_update_nonexistent_raises(self, db_path: Path):
        with pytest.raises(ValueError, match="not found"):
            update_scenario("nonexistent-id", {"name": "x"}, db_path)
