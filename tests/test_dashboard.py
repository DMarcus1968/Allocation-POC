"""Tests for Phase 2B — tradeoff engine and API."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from src.dashboard.api import app
from src.dashboard.tradeoff_engine import (
    ScenarioConfig,
    RunRequest,
    save_scenario,
    get_scenario,
    delete_scenario,
    list_scenarios,
    execute_run,
    _scenarios,
)


@pytest.fixture(autouse=True)
def clean_store():
    """Clear the in-memory store between tests."""
    _scenarios.clear()
    yield
    _scenarios.clear()


# ---- Engine unit tests ------------------------------------------------------

def test_save_and_retrieve_scenario():
    cfg = ScenarioConfig(scenario_id="s1", event_name="Test")
    save_scenario(cfg)
    assert get_scenario("s1") is not None
    assert get_scenario("s1").event_name == "Test"


def test_delete_scenario():
    cfg = ScenarioConfig(scenario_id="s2", event_name="Gone")
    save_scenario(cfg)
    assert delete_scenario("s2") is True
    assert get_scenario("s2") is None
    assert delete_scenario("s2") is False


def test_list_scenarios():
    save_scenario(ScenarioConfig(scenario_id="a"))
    save_scenario(ScenarioConfig(scenario_id="b"))
    assert len(list_scenarios()) == 2


def test_execute_run_deterministic():
    """Same scenario + seed must yield identical results."""
    cfg = ScenarioConfig(scenario_id="det", num_fans=100)
    save_scenario(cfg)
    r1 = execute_run(RunRequest(scenario_id="det", seed=42))
    r2 = execute_run(RunRequest(scenario_id="det", seed=42))
    assert r1.fcfs_result.total_allocated == r2.fcfs_result.total_allocated
    for obj in cfg.objectives:
        assert (
            r1.batch_results[obj].total_allocated
            == r2.batch_results[obj].total_allocated
        )


def test_execute_run_has_comparison():
    cfg = ScenarioConfig(scenario_id="cmp", num_fans=100)
    save_scenario(cfg)
    result = execute_run(RunRequest(scenario_id="cmp", seed=7))
    assert len(result.comparison.scenarios) >= 2


def test_execute_run_missing_scenario():
    with pytest.raises(ValueError, match="not found"):
        execute_run(RunRequest(scenario_id="nope"))


def test_execute_run_explainability():
    cfg = ScenarioConfig(scenario_id="expl", num_fans=50)
    save_scenario(cfg)
    result = execute_run(RunRequest(scenario_id="expl", seed=1))
    assert len(result.fcfs_result.constraints_applied) > 0
    assert result.fcfs_result.objective_used != ""
    for obj, br in result.batch_results.items():
        assert len(br.constraints_applied) > 0
        assert br.objective_used == obj


# ---- API integration tests --------------------------------------------------

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "2B"


def test_objectives_endpoint():
    resp = client.get("/objectives")
    assert resp.status_code == 200
    keys = [o["key"] for o in resp.json()]
    assert "fill_capacity" in keys
    assert "revenue_at_face_value" in keys


def test_scenario_crud_via_api():
    payload = {
        "event_name": "API Test",
        "tiers": [{"name": "GA", "capacity": 100, "price": 50.0}],
        "num_fans": 50,
    }
    # Create
    resp = client.post("/scenarios", json=payload)
    assert resp.status_code == 201
    sid = resp.json()["scenario_id"]

    # List
    resp = client.get("/scenarios")
    assert resp.status_code == 200
    assert any(s["scenario_id"] == sid for s in resp.json())

    # Get
    resp = client.get(f"/scenarios/{sid}")
    assert resp.status_code == 200
    assert resp.json()["event_name"] == "API Test"

    # Delete
    resp = client.delete(f"/scenarios/{sid}")
    assert resp.status_code == 204

    # Get after delete
    resp = client.get(f"/scenarios/{sid}")
    assert resp.status_code == 404


def test_run_via_api():
    payload = {
        "scenario_id": "api_run",
        "event_name": "API Run Test",
        "tiers": [
            {"name": "GA", "capacity": 200, "price": 75.0},
            {"name": "VIP", "capacity": 50, "price": 200.0},
        ],
        "num_fans": 100,
    }
    resp = client.post("/scenarios", json=payload)
    assert resp.status_code == 201

    run_payload = {"scenario_id": "api_run", "use_common_seed": True, "seed": 42}
    resp = client.post("/runs", json=run_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_id"] == "api_run"
    assert data["seed"] == 42
    assert "comparison" in data
    assert len(data["comparison"]["scenarios"]) >= 2


def test_run_missing_scenario_404():
    resp = client.post("/runs", json={"scenario_id": "no_such"})
    assert resp.status_code == 404
