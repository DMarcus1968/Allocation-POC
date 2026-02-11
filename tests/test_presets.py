"""Tests for preset templates (Phase 2B Step 7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.dashboard.scenario_store import init_db, get_scenario
from src.dashboard.preset_store import (
    apply_preset_to_new_scenario,
    create_preset,
    delete_preset,
    get_preset,
    list_presets,
)


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.sqlite"
    init_db(p)
    return p


class TestPresetStore:
    def test_system_presets_seeded(self, db_path: Path):
        presets = list_presets(db_path)
        assert len(presets) >= 3
        names = {p["name"] for p in presets}
        assert "Fan-first" in names
        assert "Revenue-protect" in names
        assert "VIP-holdback" in names

    def test_get_preset(self, db_path: Path):
        preset = get_preset("preset_fan_first", db_path)
        assert preset is not None
        assert preset["name"] == "Fan-first"
        assert "per_account_cap" in preset["knobs_promoter_constraints"]

    def test_get_nonexistent_preset(self, db_path: Path):
        assert get_preset("nonexistent", db_path) is None

    def test_create_custom_preset(self, db_path: Path):
        preset = create_preset(
            {
                "name": "Custom Template",
                "description": "Test template",
                "knobs_promoter_constraints": {"per_account_cap": 3},
                "knobs_allocation_policy": {"priority_mode": "fifo"},
            },
            db_path,
        )
        assert preset["name"] == "Custom Template"
        assert preset["knobs_promoter_constraints"] == {"per_account_cap": 3}
        assert preset["knobs_allocation_policy"] == {"priority_mode": "fifo"}

        # Verify it appears in list
        presets = list_presets(db_path)
        ids = {p["id"] for p in presets}
        assert preset["id"] in ids

    def test_delete_preset(self, db_path: Path):
        preset = create_preset(
            {"name": "To Delete", "description": "temp"},
            db_path,
        )
        assert delete_preset(preset["id"], db_path) is True
        assert get_preset(preset["id"], db_path) is None

    def test_delete_nonexistent_returns_false(self, db_path: Path):
        assert delete_preset("nonexistent", db_path) is False


class TestApplyPreset:
    def test_apply_creates_scenario_with_same_knobs(self, db_path: Path):
        preset = get_preset("preset_fan_first", db_path)
        assert preset is not None

        scenario = apply_preset_to_new_scenario(
            "preset_fan_first",
            created_by="test_user",
            db_path=db_path,
        )

        assert scenario.name == "Fan-first scenario"
        assert scenario.knobs_promoter_constraints == preset["knobs_promoter_constraints"]
        assert scenario.knobs_allocation_policy == preset["knobs_allocation_policy"]
        assert scenario.checksum != ""
        assert scenario.created_by == "test_user"

    def test_apply_creates_checksum(self, db_path: Path):
        scenario = apply_preset_to_new_scenario(
            "preset_revenue_protect",
            db_path=db_path,
        )
        assert scenario.checksum != ""
        assert scenario.checksum == scenario.compute_checksum()

    def test_apply_scenario_persisted(self, db_path: Path):
        scenario = apply_preset_to_new_scenario(
            "preset_vip_holdback",
            db_path=db_path,
        )
        fetched = get_scenario(scenario.id, db_path)
        assert fetched is not None
        assert fetched.knobs_promoter_constraints == scenario.knobs_promoter_constraints

    def test_apply_nonexistent_preset_raises(self, db_path: Path):
        with pytest.raises(ValueError, match="not found"):
            apply_preset_to_new_scenario("nonexistent", db_path=db_path)
