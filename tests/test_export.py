"""Tests for scenario export endpoints (Phase 2B Step 7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dashboard.api import app
from src.dashboard import scenario_store
from src.dashboard.audit_store import list_audits


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.sqlite"
    scenario_store.init_db(p)
    return p


@pytest.fixture()
def client(db_path: Path, monkeypatch):
    """Flask test client with isolated DB."""
    monkeypatch.setattr(scenario_store, "_DB_PATH", db_path)

    # Also patch audit_store and preset_store DB paths
    from src.dashboard import audit_store, preset_store
    monkeypatch.setattr(audit_store, "_DB_PATH", db_path)
    monkeypatch.setattr(preset_store, "_DB_PATH", db_path)

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _create_scenario(client, name="Export Test", knobs=None):
    knobs = knobs or {"per_account_cap": 4}
    resp = client.post(
        "/scenarios",
        data=json.dumps({"name": name, "knobs": knobs}),
        content_type="application/json",
    )
    return resp.get_json()["id"]


class TestScenarioExportCSV:
    def test_export_csv_returns_csv(self, client):
        sid = _create_scenario(client)
        resp = client.post(
            f"/scenarios/{sid}/export",
            data=json.dumps({"format": "csv", "include_explainability": True}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.content_type == "text/csv; charset=utf-8"

        body = resp.data.decode()
        assert "scenario_id" in body
        assert "metric_name" in body
        assert "metric_value" in body
        assert "explainability_notes" in body

        lines = [l for l in body.strip().split("\n") if l.strip()]
        # Header + 7 metric rows
        assert len(lines) == 8

    def test_export_csv_without_explainability(self, client):
        sid = _create_scenario(client)
        resp = client.post(
            f"/scenarios/{sid}/export",
            data=json.dumps({"format": "csv", "include_explainability": False}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "explainability_notes" not in body

    def test_export_csv_creates_audit_entry(self, client, db_path):
        sid = _create_scenario(client)
        client.post(
            f"/scenarios/{sid}/export",
            data=json.dumps({"format": "csv"}),
            content_type="application/json",
        )
        audits = list_audits(scenario_id=sid, db_path=db_path)
        events = [a["event"] for a in audits]
        assert "export" in events

        export_audit = next(a for a in audits if a["event"] == "export")
        details = export_audit["payload"]["details"]
        assert details["format"] == "long_csv"
        assert details["rows"] > 0

    def test_export_nonexistent_scenario(self, client):
        resp = client.post(
            "/scenarios/nonexistent/export",
            data=json.dumps({"format": "csv"}),
            content_type="application/json",
        )
        assert resp.status_code == 404


class TestMetricsCsvExport:
    def test_metrics_csv_wide_format(self, client):
        sid = _create_scenario(client)
        resp = client.post(
            f"/scenarios/{sid}/export",
            data=json.dumps({"mode": "metrics_csv", "include_explainability": True}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.content_type == "text/csv; charset=utf-8"

        body = resp.data.decode()
        lines = [l for l in body.strip().split("\n") if l.strip()]
        # Wide format: header + 1 data row
        assert len(lines) == 2

        header = lines[0]
        assert "scenario_id" in header
        assert "git_commit" in header
        assert "event_config_hash" in header
        assert "demand_config_hash" in header
        assert "pricebook_hash" in header
        assert "tickets_fulfilled" in header
        assert "explainability_notes" in header

    def test_metrics_csv_deterministic_columns(self, client):
        """Metric columns should be sorted alphabetically."""
        sid = _create_scenario(client)
        resp = client.post(
            f"/scenarios/{sid}/export",
            data=json.dumps({"mode": "metrics_csv", "include_explainability": False}),
            content_type="application/json",
        )
        body = resp.data.decode()
        header = body.strip().split("\n")[0].strip()
        cols = [c.strip() for c in header.split(",")]
        # Find the metric columns (after pricebook_hash)
        ph_idx = cols.index("pricebook_hash")
        metric_cols = cols[ph_idx + 1:]
        assert metric_cols == sorted(metric_cols)

    def test_metrics_csv_config_hashes_present(self, client):
        sid = _create_scenario(client)
        resp = client.post(
            f"/scenarios/{sid}/export",
            data=json.dumps({"mode": "metrics_csv"}),
            content_type="application/json",
        )
        body = resp.data.decode()
        data_line = body.strip().split("\n")[1]
        # Config hash columns should have non-empty values
        header = body.strip().split("\n")[0].split(",")
        values = data_line.split(",")
        row = dict(zip(header, values))
        assert len(row["event_config_hash"]) > 0
        assert len(row["demand_config_hash"]) > 0
        assert len(row["pricebook_hash"]) > 0

    def test_export_no_raw_requests(self, client):
        """Exports must never include raw request data or PII."""
        sid = _create_scenario(client)
        # JSON export
        resp = client.post(
            f"/scenarios/{sid}/export",
            data=json.dumps({"mode": "summary_json", "include_explainability": True}),
            content_type="application/json",
        )
        data = resp.get_json()
        raw = json.dumps(data)
        assert "request_id" not in raw
        assert "account_id" not in raw


class TestScenarioExportJSON:
    def test_export_json_returns_json(self, client):
        sid = _create_scenario(client)
        resp = client.post(
            f"/scenarios/{sid}/export",
            data=json.dumps({"format": "json", "include_explainability": True}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "manifest" in data
        assert "metrics" in data
        assert "explainability_summary" in data

    def test_export_json_without_explainability(self, client):
        sid = _create_scenario(client)
        resp = client.post(
            f"/scenarios/{sid}/export",
            data=json.dumps({"format": "json", "include_explainability": False}),
            content_type="application/json",
        )
        data = resp.get_json()
        assert "manifest" in data
        assert "metrics" in data
        assert "explainability_summary" not in data

    def test_export_json_creates_audit_entry(self, client, db_path):
        sid = _create_scenario(client)
        client.post(
            f"/scenarios/{sid}/export",
            data=json.dumps({"format": "json"}),
            content_type="application/json",
        )
        audits = list_audits(scenario_id=sid, db_path=db_path)
        events = [a["event"] for a in audits]
        assert "export" in events


class TestPresetAPI:
    def test_list_presets(self, client):
        resp = client.get("/presets")
        assert resp.status_code == 200
        presets = resp.get_json()
        assert len(presets) >= 3
        names = {p["name"] for p in presets}
        assert "Fan-first" in names

    def test_get_preset(self, client):
        resp = client.get("/presets/preset_fan_first")
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Fan-first"

    def test_get_nonexistent_preset(self, client):
        resp = client.get("/presets/nonexistent")
        assert resp.status_code == 404

    def test_create_preset(self, client):
        resp = client.post(
            "/presets",
            data=json.dumps({
                "name": "Custom",
                "description": "Test",
                "knobs_promoter_constraints": {"per_account_cap": 2},
                "knobs_allocation_policy": {"priority_mode": "loyalty"},
            }),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Custom"

    def test_delete_preset(self, client):
        resp = client.post(
            "/presets",
            data=json.dumps({"name": "To Delete"}),
            content_type="application/json",
        )
        pid = resp.get_json()["id"]
        resp = client.delete(f"/presets/{pid}")
        assert resp.status_code == 204

    def test_apply_preset(self, client):
        resp = client.post(
            "/presets/preset_fan_first/apply",
            data=json.dumps({"created_by": "test@example.com"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "Fan-first" in data["name"]
        assert data["knobs_promoter_constraints"]["per_account_cap"] == 6

    def test_apply_nonexistent_preset(self, client):
        resp = client.post(
            "/presets/nonexistent/apply",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 404


class TestAuditAPI:
    def test_scenario_audits(self, client):
        sid = _create_scenario(client, "Audit API Test")
        resp = client.get(f"/scenarios/{sid}/audits")
        assert resp.status_code == 200
        audits = resp.get_json()
        assert len(audits) >= 1
        assert audits[0]["event"] == "create"

    def test_global_audits(self, client):
        _create_scenario(client, "Global Audit Test")
        resp = client.get("/audits?event=create&limit=10")
        assert resp.status_code == 200
        audits = resp.get_json()
        assert all(a["event"] == "create" for a in audits)

    def test_audit_export_csv(self, client):
        sid = _create_scenario(client, "Audit CSV Test")
        resp = client.get(f"/scenarios/{sid}/audits/export")
        assert resp.status_code == 200
        assert resp.content_type == "text/csv; charset=utf-8"
        body = resp.data.decode()
        assert "event" in body
        assert "create" in body
