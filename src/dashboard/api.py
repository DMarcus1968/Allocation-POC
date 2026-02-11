"""Phase 2B — Flask API for the tradeoff dashboard.

Endpoints expose scenario CRUD, preview runs, and multi-scenario
comparison.  All wording avoids "optimize/recommend/best/fair".

Pricing control remains promoter-side; these endpoints deal only
with allocation knobs and read-only pricebook references.
"""

from __future__ import annotations

from flask import Flask, jsonify, request

from src.dashboard import scenario_store
from src.dashboard.scenario_store import ScenarioLocked
from src.dashboard.tradeoff_engine import run_preview, run_compare

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
    """Compare 2–4 scenarios side by side.

    Body: { "scenario_ids": ["...", "..."], "use_common_seed": true, "seed": <optional> }
    Returns: fcfs baseline, per-scenario batch metrics, pareto points,
             deltas vs FCFS, explainability deltas.
    """
    body = request.get_json(force=True)
    scenario_ids = body.get("scenario_ids", [])

    if not (2 <= len(scenario_ids) <= 4):
        return jsonify({"error": "Provide 2–4 scenario_ids"}), 400

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


# ── entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
    scenario_store.init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
