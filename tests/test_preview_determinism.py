"""Tests for preview determinism and compare payload (Phase 2B Steps 2–4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.dashboard.scenario_store import create_scenario, init_db
from src.dashboard.tradeoff_engine import run_preview, run_compare


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.sqlite"
    init_db(p)
    return p


@pytest.fixture()
def scenario_id(db_path: Path) -> str:
    sc = create_scenario(
        {
            "name": "Determinism Test",
            "knobs": {
                "per_account_cap": 4,
                "group_size_cap": 6,
                "holdback_pct": 0.0,
                "priority_mode": "random",
                "singles_avoidance": True,
            },
            "seed_policy": {"mode": "common", "seed": 42},
        },
        db_path,
    )
    return sc.id


# ── determinism tests ───────────────────────────────────────────────

class TestPreviewDeterminism:
    def test_same_seed_identical_metrics(self, scenario_id: str, db_path: Path):
        r1 = run_preview(scenario_id, seed=42, db_path=db_path)
        r2 = run_preview(scenario_id, seed=42, db_path=db_path)

        assert r1["metrics"]["fcfs"] == r2["metrics"]["fcfs"]
        assert r1["metrics"]["batch"] == r2["metrics"]["batch"]
        assert r1["metrics"]["delta_batch_vs_fcfs"] == r2["metrics"]["delta_batch_vs_fcfs"]

    def test_same_seed_identical_allocations(self, scenario_id: str, db_path: Path):
        r1 = run_preview(scenario_id, seed=42, db_path=db_path)
        r2 = run_preview(scenario_id, seed=42, db_path=db_path)

        assert r1["results"]["fcfs"]["allocations"] == r2["results"]["fcfs"]["allocations"]
        assert r1["results"]["batch"]["allocations"] == r2["results"]["batch"]["allocations"]

    def test_different_seeds_differ(self, scenario_id: str, db_path: Path):
        r1 = run_preview(scenario_id, seed=42, db_path=db_path)
        r2 = run_preview(scenario_id, seed=999, db_path=db_path)

        # Demand draws should differ → at least some metrics should differ
        m1 = r1["metrics"]["batch"]
        m2 = r2["metrics"]["batch"]
        # It's extremely unlikely all metrics are identical with different seeds
        differs = any(m1[k] != m2[k] for k in m1)
        assert differs, "Different seeds should produce different results"


# ── preview output structure ────────────────────────────────────────

class TestPreviewOutput:
    def test_manifest_fields(self, scenario_id: str, db_path: Path):
        result = run_preview(scenario_id, seed=42, db_path=db_path)
        manifest = result["manifest"]
        assert "run_id" in manifest
        assert manifest["scenario_id"] == scenario_id
        assert manifest["seed"] == 42
        assert "checksum" in manifest
        assert "timestamp" in manifest
        assert "versions" in manifest

    def test_metrics_fields(self, scenario_id: str, db_path: Path):
        result = run_preview(scenario_id, seed=42, db_path=db_path)
        for key in ("fcfs", "batch"):
            m = result["metrics"][key]
            assert "accounts_fulfilled_pct" in m
            assert "tickets_fulfilled" in m
            assert "avg_tickets_per_fulfilled_account" in m
            assert "singles_stranded_count" in m
            assert "inventory_sold_pct" in m
            assert "unsold_inventory_count" in m
            assert "gross_revenue_fixed_pricebook" in m

    def test_delta_fields(self, scenario_id: str, db_path: Path):
        result = run_preview(scenario_id, seed=42, db_path=db_path)
        delta = result["metrics"]["delta_batch_vs_fcfs"]
        assert "revenue_delta_vs_fcfs" in delta

    def test_explainability_present(self, scenario_id: str, db_path: Path):
        result = run_preview(scenario_id, seed=42, db_path=db_path)
        assert "explainability" in result
        expl = result["explainability"]
        assert "bindings" in expl
        assert "notes" in expl
        assert isinstance(expl["notes"], list)


# ── compare tests ───────────────────────────────────────────────────

class TestCompare:
    def test_compare_payload_structure(self, db_path: Path):
        sc1 = create_scenario(
            {"name": "Scenario A", "knobs": {"per_account_cap": 4}},
            db_path,
        )
        sc2 = create_scenario(
            {"name": "Scenario B", "knobs": {"per_account_cap": 2}},
            db_path,
        )

        result = run_compare(
            [sc1.id, sc2.id], seed=42, db_path=db_path
        )

        assert "fcfs_baseline" in result
        assert "scenario_metrics" in result
        assert "pareto_points" in result
        assert "deltas_vs_fcfs" in result
        assert "explainability_deltas" in result

        assert len(result["scenario_metrics"]) == 2
        assert len(result["pareto_points"]) == 2
        assert len(result["deltas_vs_fcfs"]) == 2
        # Explainability deltas: one per alt scenario (excl. base)
        assert len(result["explainability_deltas"]) == 1

    def test_compare_pareto_points(self, db_path: Path):
        sc1 = create_scenario(
            {"name": "Low Cap", "knobs": {"per_account_cap": 2}},
            db_path,
        )
        sc2 = create_scenario(
            {"name": "High Cap", "knobs": {"per_account_cap": 6}},
            db_path,
        )

        result = run_compare(
            [sc1.id, sc2.id], seed=42, db_path=db_path
        )

        for pt in result["pareto_points"]:
            assert "x_accounts_fulfilled_pct" in pt
            assert "y_gross_revenue" in pt

    def test_compare_requires_2_to_4_ids(self, db_path: Path):
        sc1 = create_scenario({"name": "A"}, db_path)

        with pytest.raises(ValueError, match="2–4"):
            run_compare([sc1.id], db_path=db_path)

    def test_compare_explainability_deltas(self, db_path: Path):
        sc1 = create_scenario(
            {"name": "Base", "knobs": {"per_account_cap": 4, "holdback_pct": 0.0}},
            db_path,
        )
        sc2 = create_scenario(
            {"name": "Alt", "knobs": {"per_account_cap": 2, "holdback_pct": 0.1}},
            db_path,
        )

        result = run_compare(
            [sc1.id, sc2.id], seed=42, db_path=db_path
        )

        ed = result["explainability_deltas"][0]
        assert ed["base_scenario_id"] == sc1.id
        assert ed["alt_scenario_id"] == sc2.id
        delta = ed["delta"]
        assert "knob_changes" in delta
        assert "notes" in delta
        # There should be knob changes detected
        assert len(delta["knob_changes"]) > 0
