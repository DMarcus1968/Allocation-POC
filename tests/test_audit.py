"""Tests for the audit trail (Phase 2B Steps 7-9)."""

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
from src.dashboard.audit_store import (
    append_audit,
    bound_payload,
    list_audits,
    redact_actor,
    stable_json,
)
from src.dashboard.explain import sanitize_notes
from src.dashboard.tradeoff_engine import run_preview


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.sqlite"
    init_db(p)
    return p


class TestRedaction:
    def test_redact_email(self):
        assert redact_actor("alice@corp.com") == "a***@corp.com"

    def test_redact_complex_email(self):
        result = redact_actor("d.marcus@ticketmaster.com")
        assert result == "d***@ticketmaster.com"

    def test_no_email_unchanged(self):
        assert redact_actor("system") == "system"

    def test_empty_string(self):
        assert redact_actor("") == ""


class TestBoundPayload:
    def test_truncates_long_strings(self):
        payload = {"note": "x" * 600}
        bounded = bound_payload(payload)
        assert len(bounded["note"]) <= 503  # 500 + "..."

    def test_caps_long_lists(self):
        payload = {"items": list(range(50))}
        bounded = bound_payload(payload)
        assert len(bounded["items"]) <= 20

    def test_small_payload_unchanged(self):
        payload = {"key": "val"}
        bounded = bound_payload(payload)
        assert bounded == payload

    def test_total_payload_bounded(self):
        payload = {f"key_{i}": "x" * 400 for i in range(30)}
        bounded = bound_payload(payload, max_bytes=2000)
        serialized = stable_json(bounded)
        assert len(serialized.encode()) <= 2500  # reasonable bounds


class TestStableJson:
    def test_sorted_keys(self):
        result = stable_json({"b": 2, "a": 1})
        assert result == '{"a":1,"b":2}'

    def test_compact(self):
        result = stable_json({"key": "value"})
        assert " " not in result


class TestSanitizeNotes:
    def test_empty_returns_default(self):
        assert sanitize_notes([]) == "No binding constraints detected."

    def test_strips_uuids(self):
        notes = ["Run f47ac10b-58cc-4372-a567-0e02b2c3d479 completed."]
        result = sanitize_notes(notes)
        assert "f47ac10b" not in result
        assert "completed" in result

    def test_strips_long_hex_tokens(self):
        notes = ["Hash: abc123def456789 detected."]
        result = sanitize_notes(notes)
        assert "abc123def456789" not in result

    def test_strips_internal_tokens(self):
        notes = ["request_id acct_000123 was processed."]
        result = sanitize_notes(notes)
        assert "request_id" not in result
        assert "acct_000123" not in result

    def test_truncates_to_max_chars(self):
        notes = ["A" * 200, "B" * 200]
        result = sanitize_notes(notes, max_chars=100)
        assert len(result) <= 100

    def test_joins_with_pipe(self):
        notes = ["Note one.", "Note two."]
        result = sanitize_notes(notes)
        assert " | " in result

    def test_normal_notes_pass_through(self):
        notes = ["Per account cap (4): 12 binding(s)."]
        result = sanitize_notes(notes)
        assert "Per account cap" in result


class TestAuditAppend:
    def test_append_returns_id(self, db_path: Path):
        audit_id = append_audit(
            "test-scenario", "test_event", "tester", {"key": "val"}, db_path=db_path
        )
        assert isinstance(audit_id, str)
        assert len(audit_id) > 0

    def test_list_audits_returns_entry(self, db_path: Path):
        append_audit("sc-1", "create", "tester", {"name": "test"}, db_path=db_path)
        audits = list_audits(scenario_id="sc-1", db_path=db_path)
        assert len(audits) >= 1
        assert audits[0]["event"] == "create"
        # Actor should be stored
        assert audits[0]["actor"] == "tester"

    def test_canonical_payload_structure(self, db_path: Path):
        append_audit("sc-2", "create", "user@test.com", {"name": "test"}, db_path=db_path)
        audits = list_audits(scenario_id="sc-2", db_path=db_path)
        payload = audits[0]["payload"]
        # Canonical structure
        assert "event" in payload
        assert "scenario_id" in payload
        assert "actor" in payload
        assert "timestamp" in payload
        assert "entity" in payload
        assert "summary" in payload
        assert "details" in payload
        # Actor redacted
        assert payload["actor"] == "u***@test.com"
        # Details contain original data
        assert payload["details"]["name"] == "test"

    def test_actor_redacted_in_db(self, db_path: Path):
        append_audit("sc-3", "create", "alice@corp.com", db_path=db_path)
        audits = list_audits(scenario_id="sc-3", db_path=db_path)
        assert audits[0]["actor"] == "a***@corp.com"

    def test_payload_bounded(self, db_path: Path):
        huge = {"big_field": "x" * 10000}
        append_audit("sc-4", "create", "system", huge, db_path=db_path)
        audits = list_audits(scenario_id="sc-4", db_path=db_path)
        details = audits[0]["payload"]["details"]
        assert len(details["big_field"]) <= 503  # truncated


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

        # Verify update payload has checksums in details
        update_audit = next(a for a in audits if a["event"] == "update")
        details = update_audit["payload"]["details"]
        assert "before_checksum" in details
        assert "after_checksum" in details

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
        details = clone_audit["payload"]["details"]
        assert details["source_id"] == sc.id
        assert details["new_id"] == cloned.id

    def test_lock_produces_audit(self, db_path: Path):
        sc = create_scenario({"name": "Lock Me"}, db_path)
        lock_scenario(sc.id, db_path)
        audits = list_audits(scenario_id=sc.id, db_path=db_path)
        events = [a["event"] for a in audits]
        assert "lock" in events

        lock_audit = next(a for a in audits if a["event"] == "lock")
        details = lock_audit["payload"]["details"]
        assert "reference_hashes" in details

    def test_locked_scenario_rejects_update(self, db_path: Path):
        sc = create_scenario({"name": "Lock Test"}, db_path)
        lock_scenario(sc.id, db_path)
        with pytest.raises(ScenarioLocked):
            update_scenario(sc.id, {"name": "Nope"}, db_path)

    def test_lock_stores_reference_hashes(self, db_path: Path):
        sc = create_scenario({"name": "Freeze Test"}, db_path)
        locked = lock_scenario(sc.id, db_path)
        assert locked.frozen_references is True
        assert locked.frozen_at is not None
        assert locked.frozen_by is not None
        assert "event_config_hash" in locked.reference_hashes
        assert "demand_config_hash" in locked.reference_hashes
        assert "pricebook_hash" in locked.reference_hashes


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
        details = run_audit["payload"]["details"]
        assert "run_id" in details
        assert "seed" in details
        assert "checksum" in details
        assert "demand_hash" in details
        assert "tickets_fulfilled" in details
        assert "gross_revenue_fixed_pricebook" in details

        # entity.id should be run_id, not scenario_id
        entity = run_audit["payload"]["entity"]
        assert entity["type"] == "run"
        assert entity["id"] == details["run_id"]
        # scenario_id remains at top level
        assert run_audit["payload"]["scenario_id"] == sc.id

    def test_run_manifest_has_config_hashes(self, db_path: Path):
        sc = create_scenario(
            {"name": "Config Hash Test", "seed_policy": {"mode": "common", "seed": 42}},
            db_path,
        )
        result = run_preview(sc.id, seed=42, db_path=db_path)
        manifest = result["manifest"]
        assert "git_commit" in manifest
        assert "code_version" in manifest
        assert "config_hashes" in manifest
        assert "event_config_hash" in manifest["config_hashes"]
        assert "demand_config_hash" in manifest["config_hashes"]
        assert "pricebook_hash" in manifest["config_hashes"]


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
