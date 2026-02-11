"""Phase 2B — Tradeoff engine (scenario runner).

The tradeoff engine is the heart of Phase 2B.  It lets a promoter define a
Scenario (event + constraints + list of objectives to compare) and then
executes all allocator runs deterministically, producing a ComparisonReport.

Design principles:
- Promoters retain full pricing control; the engine never modifies prices.
- Allocation and pricing are architecturally separated.
- WTP is diagnostic only — it is recorded on fan profiles but never
  consulted by allocation logic.
- Determinism: identical inputs always produce identical outputs.
- Explainability: every run carries constraint/objective/rejection metadata.
"""

from __future__ import annotations

import uuid
from pydantic import BaseModel, Field

from src.models.event import Event, Tier, Inventory
from src.models.demand import DemandPool
from src.models.allocation import AllocationResult
from src.models.metrics import ComparisonReport
from src.simulation.demand_sim import generate_demand
from src.allocators.fcfs import allocate_fcfs
from src.allocators.batch import allocate_batch
from src.comparison.compare import build_comparison
from src.objectives.revenue import available_objectives


# ---------------------------------------------------------------------------
# Scenario definition (promoter-facing input)
# ---------------------------------------------------------------------------

class TierInput(BaseModel):
    """Promoter-provided tier definition."""
    name: str
    capacity: int = Field(ge=0)
    price: float = Field(ge=0.0)


class ScenarioConfig(BaseModel):
    """Everything a promoter supplies to define one tradeoff analysis."""

    scenario_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_name: str = "Unnamed Event"
    tiers: list[TierInput] = Field(
        default_factory=lambda: [
            TierInput(name="GA", capacity=500, price=75.0),
            TierInput(name="VIP", capacity=100, price=200.0),
        ],
    )
    max_tickets_per_request: int = Field(default=4, ge=1)
    allow_partial_fill: bool = False
    num_fans: int = Field(default=300, ge=1)
    objectives: list[str] = Field(
        default_factory=lambda: ["fill_capacity", "revenue_at_face_value"],
    )


# ---------------------------------------------------------------------------
# Run request / result (API-facing)
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    """Payload to trigger a tradeoff run."""
    scenario_id: str
    use_common_seed: bool = True
    seed: int = 42


class RunResult(BaseModel):
    """Full output of a tradeoff run — deterministic and explainable."""
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    scenario_id: str
    seed: int
    fcfs_result: AllocationResult
    batch_results: dict[str, AllocationResult]
    comparison: ComparisonReport


# ---------------------------------------------------------------------------
# In-memory store (sufficient for POC; no persistence layer needed)
# ---------------------------------------------------------------------------

_scenarios: dict[str, ScenarioConfig] = {}


def save_scenario(cfg: ScenarioConfig) -> ScenarioConfig:
    _scenarios[cfg.scenario_id] = cfg
    return cfg


def get_scenario(scenario_id: str) -> ScenarioConfig | None:
    return _scenarios.get(scenario_id)


def list_scenarios() -> list[ScenarioConfig]:
    return list(_scenarios.values())


def delete_scenario(scenario_id: str) -> bool:
    return _scenarios.pop(scenario_id, None) is not None


# ---------------------------------------------------------------------------
# Engine: execute a tradeoff run
# ---------------------------------------------------------------------------

def _build_event(cfg: ScenarioConfig) -> Event:
    """Convert promoter ScenarioConfig into the internal Event model."""
    tiers = [
        Tier(tier_id=f"tier_{i}", name=t.name, capacity=t.capacity, price=t.price)
        for i, t in enumerate(cfg.tiers)
    ]
    return Event(
        event_id=f"evt_{cfg.scenario_id}",
        name=cfg.event_name,
        inventory=Inventory(tiers=tiers),
        max_tickets_per_request=cfg.max_tickets_per_request,
        allow_partial_fill=cfg.allow_partial_fill,
    )


def execute_run(req: RunRequest) -> RunResult:
    """Execute a full tradeoff run for the given scenario.

    Steps:
    1. Build the Event from the promoter's ScenarioConfig.
    2. Generate synthetic demand (Phase 1A) with a deterministic seed.
    3. Run FCFS baseline (Phase 1B).
    4. Run batch allocator (Phase 1C) once per selected objective (Phase 2A).
    5. Build a comparison report (Phase 1D).

    The same seed is used across all allocator runs when use_common_seed=True
    so that demand is identical and differences are attributable solely to
    the allocation method.
    """
    cfg = get_scenario(req.scenario_id)
    if cfg is None:
        raise ValueError(f"Scenario {req.scenario_id!r} not found")

    event = _build_event(cfg)
    seed = req.seed

    # Phase 1A — generate demand (same pool for all allocators)
    demand = generate_demand(event, num_fans=cfg.num_fans, seed=seed)

    # Phase 1B — FCFS baseline
    fcfs_result = allocate_fcfs(event, demand)

    # Phase 1C + 2A — batch allocator under each selected objective
    batch_results: dict[str, AllocationResult] = {}
    for obj in cfg.objectives:
        # Regenerate demand so mutation from previous run does not leak
        obj_demand = generate_demand(event, num_fans=cfg.num_fans, seed=seed)
        batch_results[obj] = allocate_batch(
            event, obj_demand, seed=seed, objective=obj,
        )

    # Phase 1D — comparison report (FCFS + all batch variants)
    all_results = [fcfs_result] + list(batch_results.values())
    comparison = build_comparison(event, all_results)

    return RunResult(
        scenario_id=cfg.scenario_id,
        seed=seed,
        fcfs_result=fcfs_result,
        batch_results=batch_results,
        comparison=comparison,
    )
