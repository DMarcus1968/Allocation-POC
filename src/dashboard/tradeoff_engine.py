"""Phase 2B — Deterministic run harness and tradeoff engine.

Provides ``run_preview`` which loads a scenario, generates demand,
runs both FCFS and batch allocators with a single seeded RNG,
and returns a normalized output with manifest, results, metrics,
and explainability payload.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime

from src.models.scenario import Scenario
from src.models.metrics import MetricsSummary
from src.dashboard import scenario_store
from src.dashboard.fixtures import load_demo_event, load_demand_config
from src.simulation.demand_sim import generate_demand
from src.allocators.fcfs import allocate_fcfs
from src.allocators.batch import allocate_batch
from src.comparison.compare import compute_metrics, compute_delta
from src.dashboard.explain import explain_run, explain_delta


# ── version tracking ────────────────────────────────────────────────

_ENGINE_VERSION = "2b.0"


# ── primary entry point ─────────────────────────────────────────────

def run_preview(
    scenario_id: str,
    *,
    seed: int | None = None,
    use_common_seed: bool = True,
    db_path=None,
) -> dict:
    """Run a deterministic preview for a single scenario.

    Steps:
      1. Load Scenario from the store.
      2. Load Event + Demand configs via fixtures.
      3. Create one seeded RNG and pass it through all stochastic steps.
      4. Generate demand.
      5. Run FCFS allocator.
      6. Run batch allocator with scenario.knobs.
      7. Compute metrics and deltas.
      8. Attach explainability payload.

    Args:
        scenario_id: UUID of the scenario to preview.
        seed: Explicit seed override.  If None, uses scenario.seed_policy.
        use_common_seed: When True and seed is None, use the common
            seed from seed_policy for all stochastic steps.
        db_path: Optional DB path override (for testing).

    Returns:
        Normalized preview dict with manifest / results / metrics /
        explainability sections.
    """
    # 1. Load scenario
    scenario = scenario_store.get_scenario(scenario_id, db_path=db_path)
    if scenario is None:
        raise ValueError(f"Scenario {scenario_id} not found")

    # 2. Resolve seed
    effective_seed = _resolve_seed(scenario, seed, use_common_seed)

    # 3. Load configs
    event = load_demo_event(scenario.references.get("event_ref", "demo_event"))
    demand_cfg = load_demand_config(
        scenario.references.get("demand_config_ref", "default")
    )

    # 4. Single seeded RNG
    rng = random.Random(effective_seed)

    # 5. Generate demand (stable iteration: sections sorted in demand_sim)
    requests = generate_demand(event, demand_cfg, rng)

    # 6. Run FCFS
    fcfs_result = allocate_fcfs(event, requests)

    # 7. Run batch allocator with scenario knobs
    #    Create a child RNG so batch shuffle doesn't consume the same stream
    batch_rng = random.Random(rng.randint(0, 2**31))
    batch_result = allocate_batch(
        event,
        requests,
        knobs=scenario.knobs,
        constraints=event.constraints,
        rng=batch_rng,
    )

    # 8. Compute metrics
    fcfs_metrics = compute_metrics(event, fcfs_result)
    batch_metrics = compute_metrics(event, batch_result)
    delta = compute_delta(fcfs_metrics, batch_metrics)

    # 9. Manifest
    run_id = str(uuid.uuid4())
    manifest = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "seed": effective_seed,
        "checksum": scenario.checksum,
        "timestamp": datetime.utcnow().isoformat(),
        "versions": {
            "engine": _ENGINE_VERSION,
        },
    }

    # 10. Build raw results
    results = {
        "fcfs": {
            "allocations": [
                {"account_id": a.account_id, "section_id": a.section_id, "qty": a.qty_allocated}
                for a in fcfs_result.allocations
            ],
            "rejections": [
                {"account_id": r.account_id, "reason": r.reason, "qty": r.qty_requested}
                for r in fcfs_result.rejections
            ],
        },
        "batch": {
            "allocations": [
                {"account_id": a.account_id, "section_id": a.section_id, "qty": a.qty_allocated}
                for a in batch_result.allocations
            ],
            "rejections": [
                {"account_id": r.account_id, "reason": r.reason, "qty": r.qty_requested}
                for r in batch_result.rejections
            ],
        },
    }

    # 11. Metrics payload
    metrics = {
        "fcfs": fcfs_metrics.to_dict(),
        "batch": batch_metrics.to_dict(),
        "delta_batch_vs_fcfs": delta,
    }

    # 12. Explainability
    explainability = explain_run(batch_result, scenario)

    return {
        "manifest": manifest,
        "results": results,
        "metrics": metrics,
        "explainability": explainability,
    }


# ── compare mode ────────────────────────────────────────────────────

def run_compare(
    scenario_ids: list[str],
    *,
    seed: int | None = None,
    use_common_seed: bool = True,
    db_path=None,
) -> dict:
    """Compare 2–4 scenarios.

    Returns a payload with:
      - pinned FCFS baseline
      - per-scenario batch metrics
      - pareto points (x = accounts_fulfilled_pct, y = gross_revenue)
      - deltas vs FCFS
      - explainability deltas vs the first scenario (base)
    """
    if not (2 <= len(scenario_ids) <= 4):
        raise ValueError("Compare requires 2–4 scenario IDs")

    previews: list[dict] = []
    scenarios: list[Scenario] = []
    for sid in scenario_ids:
        p = run_preview(sid, seed=seed, use_common_seed=use_common_seed, db_path=db_path)
        previews.append(p)
        sc = scenario_store.get_scenario(sid, db_path=db_path)
        scenarios.append(sc)  # type: ignore[arg-type]

    # FCFS baseline is pinned from the first preview (same seed → same FCFS)
    fcfs_baseline = previews[0]["metrics"]["fcfs"]

    # Per-scenario batch metrics + pareto points
    scenario_metrics: list[dict] = []
    pareto_points: list[dict] = []
    deltas_vs_fcfs: list[dict] = []

    for i, p in enumerate(previews):
        batch_m = p["metrics"]["batch"]
        scenario_metrics.append({
            "scenario_id": scenario_ids[i],
            "scenario_name": scenarios[i].name,
            "metrics": batch_m,
        })
        pareto_points.append({
            "scenario_id": scenario_ids[i],
            "scenario_name": scenarios[i].name,
            "x_accounts_fulfilled_pct": batch_m["accounts_fulfilled_pct"],
            "y_gross_revenue": batch_m["gross_revenue_fixed_pricebook"],
        })
        deltas_vs_fcfs.append({
            "scenario_id": scenario_ids[i],
            "delta": p["metrics"]["delta_batch_vs_fcfs"],
        })

    # Explainability deltas: each scenario vs the first (base)
    base_preview = previews[0]
    base_scenario = scenarios[0]
    explainability_deltas: list[dict] = []
    for i in range(1, len(previews)):
        ed = explain_delta(
            base_preview, previews[i], base_scenario, scenarios[i]
        )
        explainability_deltas.append({
            "base_scenario_id": scenario_ids[0],
            "alt_scenario_id": scenario_ids[i],
            "delta": ed,
        })

    return {
        "fcfs_baseline": fcfs_baseline,
        "scenario_metrics": scenario_metrics,
        "pareto_points": pareto_points,
        "deltas_vs_fcfs": deltas_vs_fcfs,
        "explainability_deltas": explainability_deltas,
    }


# ── helpers ─────────────────────────────────────────────────────────

def _resolve_seed(
    scenario: Scenario,
    explicit_seed: int | None,
    use_common_seed: bool,
) -> int:
    """Resolve the effective seed for a preview run."""
    if explicit_seed is not None:
        return explicit_seed
    policy = scenario.seed_policy
    if use_common_seed and policy.get("mode") == "common":
        return int(policy.get("seed", 42))
    if policy.get("mode") == "per_scenario":
        return int(policy.get("seed", hash(scenario.id) % (2**31)))
    return int(policy.get("seed", 42))
