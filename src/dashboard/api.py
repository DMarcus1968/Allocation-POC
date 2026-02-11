"""Phase 2B — FastAPI routes for the promoter tradeoff dashboard.

Endpoints let a promoter:
1. Create / list / retrieve / delete scenario configurations.
2. Execute a tradeoff run (deterministic, explainable).
3. Retrieve available allocation objectives.

Language rules (from claude.md s6):
- No "optimize / recommend / best / fair" in responses or labels.
- Conditional framing: "given these constraints, the system allocates..."
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from src.dashboard.tradeoff_engine import (
    ScenarioConfig,
    RunRequest,
    RunResult,
    save_scenario,
    get_scenario,
    list_scenarios,
    delete_scenario,
    execute_run,
)
from src.objectives.revenue import available_objectives

app = FastAPI(
    title="Allocation POC — Promoter Tradeoff Dashboard",
    description=(
        "Phase 2B API.  Lets promoters define scenarios, run deterministic "
        "allocation comparisons, and inspect tradeoffs.  "
        "All pricing is promoter-controlled; the system never modifies prices."
    ),
    version="0.2.0",
)


# ---- Scenario CRUD ---------------------------------------------------------

@app.post("/scenarios", response_model=ScenarioConfig, status_code=201)
def create_scenario(cfg: ScenarioConfig) -> ScenarioConfig:
    """Create a new scenario.  Promoter defines tiers, pricing, and constraints."""
    return save_scenario(cfg)


@app.get("/scenarios", response_model=list[ScenarioConfig])
def list_all_scenarios() -> list[ScenarioConfig]:
    return list_scenarios()


@app.get("/scenarios/{scenario_id}", response_model=ScenarioConfig)
def get_scenario_by_id(scenario_id: str) -> ScenarioConfig:
    cfg = get_scenario(scenario_id)
    if cfg is None:
        raise HTTPException(404, detail=f"Scenario {scenario_id!r} not found")
    return cfg


@app.delete("/scenarios/{scenario_id}", status_code=204)
def remove_scenario(scenario_id: str) -> None:
    if not delete_scenario(scenario_id):
        raise HTTPException(404, detail=f"Scenario {scenario_id!r} not found")


# ---- Tradeoff Runs ----------------------------------------------------------

@app.post("/runs", response_model=RunResult, status_code=200)
def trigger_run(req: RunRequest) -> RunResult:
    """Execute a tradeoff run.

    Given a scenario_id and seed, produces a deterministic comparison of
    FCFS vs batch allocation under each selected objective.
    Identical inputs always yield identical outputs.
    """
    try:
        return execute_run(req)
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc))


# ---- Reference data ---------------------------------------------------------

@app.get("/objectives")
def get_objectives() -> list[dict[str, str]]:
    """Return the set of allocation objectives a promoter may select."""
    return available_objectives()


# ---- Health -----------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "phase": "2B"}
