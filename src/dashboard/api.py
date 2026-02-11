"""Phase 2B — Flask API for the tradeoff dashboard.

Endpoints expose scenario CRUD, preset templates, audit trail,
preview runs, multi-scenario comparison, and CSV/JSON export.
All wording avoids "optimize/recommend/best/fair".

Pricing control remains promoter-side; these endpoints deal only
with allocation knobs and read-only pricebook references.
"""

from __future__ import annotations

import csv
import io
import json

from flask import Flask, Response, jsonify, request

from src.dashboard import scenario_store
from src.dashboard.scenario_store import ScenarioLocked
from src.dashboard.tradeoff_engine import run_preview, run_compare
from src.dashboard.audit_store import append_audit, list_audits
from src.dashboard.explain import sanitize_notes
from src.dashboard import preset_store

app = Flask(__name__)


# ── lifecycle ───────────────────────────────────────────────────────

@app.before_request
def _ensure_db():
    scenario_store.init_db()


# ── scenario CRUD ───────────────────────────────────────────────────

@app.route("/scenarios", methods=["GET"])
def list_scenarios():
    scenarios = scenario_store.list_scenarios()
    return jsonify([s.to_dict() for s in scenarios])


@app.route("/scenarios", methods=["POST"])
def create_scenario():
    payload = request.get_json(force=True)
    scenario = scenario_store.create_scenario(payload)
    return jsonify(scenario.to_dict()), 201


@app.route("/scenarios/<scenario_id>", methods=["GET"])
def get_scenario(scenario_id: str):
    scenario = scenario_store.get_scenario(scenario_id)
    if scenario is None:
        return jsonify({"error": "Scenario not found"}), 404
    return jsonify(scenario.to_dict())


@app.route("/scenarios/<scenario_id>", methods=["PUT"])
def update_scenario(scenario_id: str):
    payload = request.get_json(force=True)
    try:
        scenario = scenario_store.update_scenario(scenario_id, payload)
    except ScenarioLocked as exc:
        return jsonify({"error": str(exc)}), 409
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(scenario.to_dict())


@app.route("/scenarios/<scenario_id>/clone", methods=["POST"])
def clone_scenario(scenario_id: str):
    try:
        scenario = scenario_store.clone_scenario(scenario_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(scenario.to_dict()), 201


@app.route("/scenarios/<scenario_id>/lock", methods=["POST"])
def lock_scenario(scenario_id: str):
    try:
        scenario = scenario_store.lock_scenario(scenario_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(scenario.to_dict())


@app.route("/scenarios/<scenario_id>", methods=["DELETE"])
def delete_scenario(scenario_id: str):
    scenario_store.delete_scenario(scenario_id)
    return "", 204


# ── preview + compare ───────────────────────────────────────────────

@app.route("/preview", methods=["POST"])
def preview():
    """Run a deterministic preview for a single scenario.

    Body: { "scenario_id": "...", "use_common_seed": true, "seed": <optional int> }
    Returns: manifest / results / metrics / explainability
    """
    body = request.get_json(force=True)
    scenario_id = body.get("scenario_id")
    if not scenario_id:
        return jsonify({"error": "scenario_id is required"}), 400

    use_common_seed = body.get("use_common_seed", True)
    seed = body.get("seed")

    try:
        result = run_preview(
            scenario_id,
            seed=seed,
            use_common_seed=use_common_seed,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(result)


@app.route("/compare", methods=["POST"])
def compare():
    """Compare 2-4 scenarios side by side.

    Body: { "scenario_ids": ["...", "..."], "use_common_seed": true, "seed": <optional> }
    """
    body = request.get_json(force=True)
    scenario_ids = body.get("scenario_ids", [])

    if not (2 <= len(scenario_ids) <= 4):
        return jsonify({"error": "Provide 2\u20134 scenario_ids"}), 400

    use_common_seed = body.get("use_common_seed", True)
    seed = body.get("seed")

    try:
        result = run_compare(
            scenario_ids,
            seed=seed,
            use_common_seed=use_common_seed,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(result)


# ── CSV compare export ──────────────────────────────────────────────

@app.route("/export/compare.csv", methods=["POST"])
def export_compare_csv():
    """Export compare results as a CSV.

    Body: same as /compare.
    Returns: text/csv with one row per scenario.
    """
    body = request.get_json(force=True)
    scenario_ids = body.get("scenario_ids", [])

    if not (2 <= len(scenario_ids) <= 4):
        return jsonify({"error": "Provide 2\u20134 scenario_ids"}), 400

    use_common_seed = body.get("use_common_seed", True)
    seed = body.get("seed")

    try:
        result = run_compare(
            scenario_ids,
            seed=seed,
            use_common_seed=use_common_seed,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    fcfs_m = result["fcfs_baseline"]["metrics"]

    columns = [
        "scenario_id",
        "scenario_name",
        "accounts_fulfilled_pct",
        "tickets_fulfilled",
        "unsold_inventory_count",
        "gross_revenue_fixed_pricebook",
        "delta_revenue_vs_fcfs",
        "delta_unsold_vs_fcfs",
    ]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()

    for sm in result["scenario_metrics"]:
        m = sm["metrics"]
        writer.writerow({
            "scenario_id": sm["scenario_id"],
            "scenario_name": sm["scenario_name"],
            "accounts_fulfilled_pct": m["accounts_fulfilled_pct"],
            "tickets_fulfilled": m["tickets_fulfilled"],
            "unsold_inventory_count": m["unsold_inventory_count"],
            "gross_revenue_fixed_pricebook": m["gross_revenue_fixed_pricebook"],
            "delta_revenue_vs_fcfs": round(
                m["gross_revenue_fixed_pricebook"]
                - fcfs_m["gross_revenue_fixed_pricebook"],
                2,
            ),
            "delta_unsold_vs_fcfs": (
                m["unsold_inventory_count"] - fcfs_m["unsold_inventory_count"]
            ),
        })

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=compare.csv"},
    )


# ── scenario export (CSV / JSON) ───────────────────────────────────

@app.route("/scenarios/<scenario_id>/export", methods=["POST"])
def export_scenario(scenario_id: str):
    """Export the last preview run for a scenario.

    Body: {
        "mode": "metrics_csv"|"long_csv"|"summary_json",
        "include_explainability": true|false,
        "seed": <optional>, "use_common_seed": true
    }

    mode defaults to "metrics_csv" (wide format, one row per run).
    "long_csv" = metric_name/metric_value long form.
    "summary_json" = manifest + metrics + explainability summary (no raw allocations).

    Exports never include raw requests/demand draws or fan-identifiable data.
    """
    sc = scenario_store.get_scenario(scenario_id)
    if sc is None:
        return jsonify({"error": "Scenario not found"}), 404

    body = request.get_json(force=True) if request.data else {}
    # Backward compat: accept "format" as alias for "mode"
    mode = body.get("mode") or body.get("format", "metrics_csv")
    # Map legacy format values
    if mode == "csv":
        mode = "long_csv"
    if mode == "json":
        mode = "summary_json"

    include_expl = body.get("include_explainability", True)
    seed = body.get("seed")
    use_common_seed = body.get("use_common_seed", True)

    try:
        result = run_preview(
            scenario_id,
            seed=seed,
            use_common_seed=use_common_seed,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    manifest = result["manifest"]
    batch_m = result["metrics"]["batch"]
    expl_notes = result.get("explainability", {}).get("notes", [])
    safe_notes = [n[:200] for n in expl_notes[:10]]
    # sanitize_notes strips UUIDs/hashes/internal tokens and caps length
    expl_summary = sanitize_notes(expl_notes, max_chars=300) if include_expl else ""

    actor = body.get("actor", sc.created_by)
    config_hashes = manifest.get("config_hashes", {})

    if mode == "summary_json":
        export_payload = {
            "manifest": manifest,
            "metrics": {
                "fcfs": result["metrics"]["fcfs"],
                "batch": batch_m,
                "delta_batch_vs_fcfs": result["metrics"]["delta_batch_vs_fcfs"],
            },
        }
        if include_expl:
            # Only include bindings/notes — never raw allocations
            expl = result.get("explainability", {})
            export_payload["explainability_summary"] = {
                "bindings": expl.get("bindings", {}),
                "lost_tickets_estimates": expl.get("lost_tickets_estimates", {}),
                "notes": safe_notes,
            }

        append_audit(
            scenario_id,
            "export",
            actor=actor,
            payload={"format": "summary_json", "rows": 1, "filename": f"{scenario_id}_export.json"},
        )

        return jsonify(export_payload)

    elif mode == "metrics_csv":
        # Wide format: one row with all metric columns sorted alphabetically
        metric_keys = sorted(batch_m.keys())
        columns = [
            "scenario_id", "scenario_name", "run_id", "run_timestamp",
            "seed", "checksum", "git_commit",
            "event_config_hash", "demand_config_hash", "pricebook_hash",
        ] + metric_keys
        if include_expl:
            columns.append("explainability_notes")

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns)
        writer.writeheader()

        row = {
            "scenario_id": scenario_id,
            "scenario_name": sc.name,
            "run_id": manifest["run_id"],
            "run_timestamp": manifest["timestamp"],
            "seed": manifest["seed"],
            "checksum": manifest["checksum"],
            "git_commit": manifest.get("git_commit", ""),
            "event_config_hash": config_hashes.get("event_config_hash", ""),
            "demand_config_hash": config_hashes.get("demand_config_hash", ""),
            "pricebook_hash": config_hashes.get("pricebook_hash", ""),
        }
        for mk in metric_keys:
            row[mk] = batch_m[mk]
        if include_expl:
            row["explainability_notes"] = expl_summary
        writer.writerow(row)

        append_audit(
            scenario_id,
            "export",
            actor=actor,
            payload={"format": "metrics_csv", "rows": 1, "filename": f"{scenario_id}_export.csv"},
        )

        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={scenario_id}_metrics.csv"
            },
        )

    else:
        # long_csv: metric_name/metric_value long form
        columns = [
            "scenario_id", "scenario_name", "run_id", "run_timestamp",
            "seed", "checksum", "git_commit",
            "event_config_hash", "demand_config_hash", "pricebook_hash",
            "metric_name", "metric_value",
        ]
        if include_expl:
            columns.append("explainability_notes")

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns)
        writer.writeheader()

        row_count = 0
        for metric_name in sorted(batch_m.keys()):
            row = {
                "scenario_id": scenario_id,
                "scenario_name": sc.name,
                "run_id": manifest["run_id"],
                "run_timestamp": manifest["timestamp"],
                "seed": manifest["seed"],
                "checksum": manifest["checksum"],
                "git_commit": manifest.get("git_commit", ""),
                "event_config_hash": config_hashes.get("event_config_hash", ""),
                "demand_config_hash": config_hashes.get("demand_config_hash", ""),
                "pricebook_hash": config_hashes.get("pricebook_hash", ""),
                "metric_name": metric_name,
                "metric_value": batch_m[metric_name],
            }
            if include_expl:
                row["explainability_notes"] = expl_summary
            writer.writerow(row)
            row_count += 1

        append_audit(
            scenario_id,
            "export",
            actor=actor,
            payload={
                "format": "long_csv",
                "rows": row_count,
                "filename": f"{scenario_id}_export.csv",
            },
        )

        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={scenario_id}_export.csv"
            },
        )


# ── presets ─────────────────────────────────────────────────────────

@app.route("/presets", methods=["GET"])
def list_presets_endpoint():
    presets = preset_store.list_presets()
    return jsonify(presets)


@app.route("/presets/<preset_id>", methods=["GET"])
def get_preset_endpoint(preset_id: str):
    preset = preset_store.get_preset(preset_id)
    if preset is None:
        return jsonify({"error": "Preset not found"}), 404
    return jsonify(preset)


@app.route("/presets", methods=["POST"])
def create_preset_endpoint():
    payload = request.get_json(force=True)
    preset = preset_store.create_preset(payload)
    return jsonify(preset), 201


@app.route("/presets/<preset_id>", methods=["DELETE"])
def delete_preset_endpoint(preset_id: str):
    deleted = preset_store.delete_preset(preset_id)
    if not deleted:
        return jsonify({"error": "Preset not found"}), 404
    return "", 204


@app.route("/presets/<preset_id>/apply", methods=["POST"])
def apply_preset_endpoint(preset_id: str):
    """Create a new scenario pre-populated with the preset's knobs."""
    body = request.get_json(force=True) if request.data else {}
    created_by = body.get("created_by", "system")

    try:
        scenario = preset_store.apply_preset_to_new_scenario(
            preset_id, created_by=created_by
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(scenario.to_dict()), 201


# ── audit trail ─────────────────────────────────────────────────────

@app.route("/scenarios/<scenario_id>/audits", methods=["GET"])
def scenario_audits(scenario_id: str):
    """List audit entries for a specific scenario."""
    limit = request.args.get("limit", 50, type=int)
    since = request.args.get("since")
    audits = list_audits(
        scenario_id=scenario_id,
        limit=limit,
        since=since,
    )
    return jsonify(audits)


@app.route("/audits", methods=["GET"])
def global_audits():
    """Query all audit entries with optional filters."""
    event = request.args.get("event")
    limit = request.args.get("limit", 100, type=int)
    since = request.args.get("since")
    audits = list_audits(
        event=event,
        limit=limit,
        since=since,
    )
    return jsonify(audits)


@app.route("/scenarios/<scenario_id>/audits/export", methods=["GET"])
def export_audits_csv(scenario_id: str):
    """Download audit entries for a scenario as CSV."""
    audits = list_audits(scenario_id=scenario_id, limit=1000)

    columns = ["id", "scenario_id", "event", "actor", "payload", "created_at"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    for a in audits:
        writer.writerow({
            "id": a["id"],
            "scenario_id": a["scenario_id"],
            "event": a["event"],
            "actor": a["actor"],
            "payload": json.dumps(a["payload"], separators=(",", ":")),
            "created_at": a["created_at"],
        })

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={scenario_id}_audits.csv"
        },
    )


# ── entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
    scenario_store.init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
