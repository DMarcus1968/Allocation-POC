"""Tests for the Flask API (Phase 2B Step 4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dashboard.api import app
from src.dashboard import scenario_store


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.sqlite"
    scenario_store.init_db(p)
    return p


@pytest.fixture()
def client(db_path: Path, monkeypatch):
    """Flask test client with isolated DB."""
    monkeypatch.setattr(scenario_store, "_DB_PATH", db_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestScenarioAPI:
    def test_create_and_list(self, client):
        resp = client.post(
            "/scenarios",
            data=json.dumps({"name": "API Test", "knobs": {"per_account_cap": 3}}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "API Test"
        sid = data["id"]

        resp = client.get("/scenarios")
        assert resp.status_code == 200
        scenarios = resp.get_json()
        assert any(s["id"] == sid for s in scenarios)

    def test_get_scenario(self, client):
        resp = client.post(
            "/scenarios",
            data=json.dumps({"name": "Get Test"}),
            content_type="application/json",
        )
        sid = resp.get_json()["id"]

        resp = client.get(f"/scenarios/{sid}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == sid

    def test_get_nonexistent_404(self, client):
        resp = client.get("/scenarios/nonexistent")
        assert resp.status_code == 404

    def test_update_scenario(self, client):
        resp = client.post(
            "/scenarios",
            data=json.dumps({"name": "Before Update"}),
            content_type="application/json",
        )
        sid = resp.get_json()["id"]

        resp = client.put(
            f"/scenarios/{sid}",
            data=json.dumps({"name": "After Update"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "After Update"

    def test_update_locked_409(self, client):
        resp = client.post(
            "/scenarios",
            data=json.dumps({"name": "Lock Me"}),
            content_type="application/json",
        )
        sid = resp.get_json()["id"]

        client.post(f"/scenarios/{sid}/lock")
        resp = client.put(
            f"/scenarios/{sid}",
            data=json.dumps({"name": "Nope"}),
            content_type="application/json",
        )
        assert resp.status_code == 409

    def test_clone_scenario(self, client):
        resp = client.post(
            "/scenarios",
            data=json.dumps({"name": "Original", "knobs": {"x": 1}}),
            content_type="application/json",
        )
        sid = resp.get_json()["id"]

        resp = client.post(f"/scenarios/{sid}/clone")
        assert resp.status_code == 201
        cloned = resp.get_json()
        assert cloned["id"] != sid
        assert cloned["knobs"] == {"x": 1}

    def test_delete_scenario(self, client):
        resp = client.post(
            "/scenarios",
            data=json.dumps({"name": "Delete Me"}),
            content_type="application/json",
        )
        sid = resp.get_json()["id"]

        resp = client.delete(f"/scenarios/{sid}")
        assert resp.status_code == 204

        resp = client.get(f"/scenarios/{sid}")
        assert resp.status_code == 404


class TestPreviewAPI:
    def test_preview_success(self, client):
        resp = client.post(
            "/scenarios",
            data=json.dumps({
                "name": "Preview Test",
                "knobs": {"per_account_cap": 4, "priority_mode": "random"},
            }),
            content_type="application/json",
        )
        sid = resp.get_json()["id"]

        resp = client.post(
            "/preview",
            data=json.dumps({"scenario_id": sid, "seed": 42}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "manifest" in data
        assert "results" in data
        assert "metrics" in data
        assert "explainability" in data

    def test_preview_missing_scenario(self, client):
        resp = client.post(
            "/preview",
            data=json.dumps({"scenario_id": "bad-id"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_preview_missing_scenario_id(self, client):
        resp = client.post(
            "/preview",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestCompareAPI:
    def test_compare_success(self, client):
        ids = []
        for name in ("A", "B"):
            resp = client.post(
                "/scenarios",
                data=json.dumps({"name": name, "knobs": {"per_account_cap": 4}}),
                content_type="application/json",
            )
            ids.append(resp.get_json()["id"])

        resp = client.post(
            "/compare",
            data=json.dumps({"scenario_ids": ids, "seed": 42}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "fcfs_baseline" in data
        assert "scenario_metrics" in data
        assert "pareto_points" in data

    def test_compare_too_few_ids(self, client):
        resp = client.post(
            "/scenarios",
            data=json.dumps({"name": "Lone"}),
            content_type="application/json",
        )
        sid = resp.get_json()["id"]

        resp = client.post(
            "/compare",
            data=json.dumps({"scenario_ids": [sid]}),
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestExportCSV:
    def test_export_csv_success(self, client):
        ids = []
        for name in ("X", "Y"):
            resp = client.post(
                "/scenarios",
                data=json.dumps({"name": name, "knobs": {"per_account_cap": 4}}),
                content_type="application/json",
            )
            ids.append(resp.get_json()["id"])

        resp = client.post(
            "/export/compare.csv",
            data=json.dumps({"scenario_ids": ids, "seed": 42}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.content_type == "text/csv; charset=utf-8"
        body = resp.data.decode()
        assert "scenario_id" in body
        assert "accounts_fulfilled_pct" in body
        assert "delta_revenue_vs_fcfs" in body
        # Should have header + 2 data rows
        lines = [l for l in body.strip().split("\n") if l.strip()]
        assert len(lines) == 3

    def test_export_csv_too_few_ids(self, client):
        resp = client.post(
            "/scenarios",
            data=json.dumps({"name": "Solo"}),
            content_type="application/json",
        )
        sid = resp.get_json()["id"]

        resp = client.post(
            "/export/compare.csv",
            data=json.dumps({"scenario_ids": [sid]}),
            content_type="application/json",
        )
        assert resp.status_code == 400
