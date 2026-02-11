"""Phase 2B — Deterministic run harness and tradeoff engine.

Provides ``run_preview`` which loads a scenario, generates demand,
runs both FCFS and batch allocators with a single seeded RNG,
and returns a normalized output with manifest, results, metrics,
and explainability payload.

``run_compare`` generates demand ONCE and feeds the identical request
list into every scenario's allocators, guaranteeing identical demand
draws across scenarios.
"""

from __future__ import annotations

import hashlib
import json
import random
import uuid
from datetime import datetime

from src.models.scenario import Scenario
from src.models.demand import TicketRequest
from src.models.event import EventConfig
from src.dashboard import scenario_store
from src.dashboard.fixtures import load_demo_event, load_demand_config
from src.simulation.demand_sim import generate_demand
from src.allocators.fcfs import allocate_fcfs
from src.allocators.batch import allocate_batch
from src.comparison.compare import compute_metrics, compute_delta
from src.dashboard.explain import explain_run, explain_delta
from src.dashboard.audit_store import append_audit


# ── version tracking ────────────────────────────────────────────────

_ENGINE_VERSION = "2b.2"
_CODE_VERSION = "allocation-poc-2b"


def _git_commit() -> str:
    """Return short git commit hash, or 'unknown' if not in a repo."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _config_hash(obj) -> str:
    """Stable SHA-256 prefix of a JSON-serializable object."""
    raw = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── demand fingerprinting ──────────────────────────────────────────

def _demand_hash(requests: list[TicketRequest]) -> str:
    """Stable SHA-256 fingerprint of the demand draw.

    Hashes (request_id, account_id, qty_requested) tuples in order.
    Returned in manifests so callers can verify demand identity.
    """
    parts = [
        f"{r.request_id}:{r.account_id}:{r.qty_requested}"
        for r in requests
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


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
    # Sort for stable ordering
    requests.sort(key=lambda r: r.request_id)

    # 6–8. Run allocators and build output
    result = _build_preview_output(
        scenario=scenario,
        scenario_id=scenario_id,
        event=event,
        demand_cfg=demand_cfg,
        requests=requests,
        effective_seed=effective_seed,
        rng=rng,
    )

    # Audit: run
    _audit_run(scenario_id, result, scenario.created_by, db_path)

    return result


def _build_preview_output(
    *,
    scenario: Scenario,
    scenario_id: str,
    event: EventConfig,
    demand_cfg=None,
    requests: list[TicketRequest],
    effective_seed: int,
    rng: random.Random,
) -> dict:
    """Build the full preview output dict for a scenario + request list."""

    # Run FCFS
    fcfs_result = allocate_fcfs(event, requests)

    # Run batch allocator with scenario knobs
    #   Create a child RNG so batch shuffle doesn't consume the same stream
    batch_rng = random.Random(rng.randint(0, 2**31))
    batch_result = allocate_batch(
        event,
        requests,
        knobs=scenario.knobs,
        constraints=event.constraints,
        rng=batch_rng,
    )

    # Compute metrics
    fcfs_metrics = compute_metrics(event, fcfs_result)
    batch_metrics = compute_metrics(event, batch_result)
    delta = compute_delta(fcfs_metrics, batch_metrics)

    # Config hashes for reproducibility
    event_obj = {
        "event_id": event.event_id,
        "sections": [
            {"id": s.section_id, "capacity": s.capacity} for s in event.sections
        ],
        "constraints": event.constraints,
    }
    demand_obj = {}
    if demand_cfg is not None:
        demand_obj = {
            "num_accounts": getattr(demand_cfg, "num_accounts", "default"),
            "avg_qty": getattr(demand_cfg, "avg_qty", "default"),
            "std_qty": getattr(demand_cfg, "std_qty", "default"),
            "min_qty": getattr(demand_cfg, "min_qty", "default"),
            "max_qty": getattr(demand_cfg, "max_qty", "default"),
        }
    config_hashes = {
        "event_config_hash": _config_hash(event_obj),
        "demand_config_hash": _config_hash(demand_obj),
        "pricebook_hash": _config_hash(event.pricebook.prices),
    }

    # Manifest
    run_id = str(uuid.uuid4())
    manifest = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "seed": effective_seed,
        "checksum": scenario.checksum,
        "demand_hash": _demand_hash(requests),
        "timestamp": datetime.utcnow().isoformat(),
        "git_commit": _git_commit(),
        "code_version": _CODE_VERSION,
        "config_hashes": config_hashes,
        "versions": {
            "engine": _ENGINE_VERSION,
        },
    }

    # Reproducibility warning for locked scenarios with changed configs
    if scenario.locked and scenario.reference_hashes:
        mismatches = {}
        for key, locked_hash in scenario.reference_hashes.items():
            current = config_hashes.get(key)
            if current and current != locked_hash:
                mismatches[key] = {"locked": locked_hash, "current": current}
        if mismatches:
            manifest["repro_warning"] = "References changed since lock"
            manifest["repro_mismatches"] = mismatches

    # Raw results
    results = {
        "fcfs": {
            "allocations": [
                {
                    "account_id": a.account_id,
                    "section_id": a.section_id,
                    "qty": a.qty_allocated,
                }
                for a in fcfs_result.allocations
            ],
            "rejections": [
                {
                    "account_id": r.account_id,
                    "reason": r.reason,
                    "qty": r.qty_requested,
                }
                for r in fcfs_result.rejections
            ],
        },
        "batch": {
            "allocations": [
                {
                    "account_id": a.account_id,
                    "section_id": a.section_id,
                    "qty": a.qty_allocated,
                }
                for a in batch_result.allocations
            ],
            "rejections": [
                {
                    "account_id": r.account_id,
                    "reason": r.reason,
                    "qty": r.qty_requested,
                }
                for r in batch_result.rejections
            ],
        },
    }

    # Metrics payload
    metrics = {
        "fcfs": fcfs_metrics.to_dict(),
        "batch": batch_metrics.to_dict(),
        "delta_batch_vs_fcfs": delta,
    }

    # Explainability
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
    """Compare 2–4 scenarios with a SINGLE demand draw.

    Demand is generated once with a single RNG seed, then the same
    request list (identical order) is fed to each scenario's FCFS
    and batch allocators.

    Returns a payload with:
      - manifest
      - pinned FCFS baseline
      - per-scenario batch metrics + pareto points + explainability
      - deltas vs FCFS
      - explainability deltas vs the first scenario (base)
    """
    if not (2 <= len(scenario_ids) <= 4):
        raise ValueError("Compare requires 2–4 scenario IDs")

    # 1. Load all scenarios
    scenarios: list[Scenario] = []
    for sid in scenario_ids:
        sc = scenario_store.get_scenario(sid, db_path=db_path)
        if sc is None:
            raise ValueError(f"Scenario {sid} not found")
        scenarios.append(sc)

    # 2. Resolve seed from first scenario's policy (or explicit)
    effective_seed = _resolve_seed(scenarios[0], seed, use_common_seed)

    # 3. Load event + demand config ONCE
    event = load_demo_event(
        scenarios[0].references.get("event_ref", "demo_event")
    )
    demand_cfg = load_demand_config(
        scenarios[0].references.get("demand_config_ref", "default")
    )

    # 4. Generate demand ONCE with a single RNG
    rng = random.Random(effective_seed)
    requests = generate_demand(event, demand_cfg, rng)
    # Stable ordering by request_id
    requests.sort(key=lambda r: r.request_id)

    d_hash = _demand_hash(requests)

    # 5. For each scenario, run FCFS + batch against the SAME requests
    previews: list[dict] = []
    for sc in scenarios:
        # Each scenario gets a fresh child RNG (derived deterministically
        # per-scenario by hashing the seed + scenario id)
        sc_seed = int(
            hashlib.sha256(
                f"{effective_seed}:{sc.id}".encode()
            ).hexdigest()[:8],
            16,
        )
        sc_rng = random.Random(sc_seed)
        preview = _build_preview_output(
            scenario=sc,
            scenario_id=sc.id,
            event=event,
            demand_cfg=demand_cfg,
            requests=requests,
            effective_seed=effective_seed,
            rng=sc_rng,
        )
        previews.append(preview)

    # 6. Build compare manifest
    manifest = {
        "seed": effective_seed,
        "demand_hash": d_hash,
        "scenario_count": len(scenario_ids),
        "timestamp": datetime.utcnow().isoformat(),
        "versions": {"engine": _ENGINE_VERSION},
    }

    # FCFS baseline: pinned from the first preview
    # (FCFS is deterministic on the same requests regardless of scenario knobs)
    fcfs_baseline = {
        "metrics": previews[0]["metrics"]["fcfs"],
        "note": "FCFS baseline is pinned across all scenarios (identical demand draw).",
    }

    # Per-scenario batch metrics + pareto + explainability
    scenario_entries: list[dict] = []
    deltas_vs_fcfs: list[dict] = []
    for sc, p in zip(scenarios, previews):
        batch_m = p["metrics"]["batch"]
        scenario_entries.append({
            "scenario_id": sc.id,
            "scenario_name": sc.name,
            "scenario": sc.to_dict(),
            "metrics": batch_m,
            "pareto": {
                "x_accounts_fulfilled_pct": batch_m["accounts_fulfilled_pct"],
                "y_gross_revenue": batch_m["gross_revenue_fixed_pricebook"],
            },
            "explainability": p["explainability"],
        })
        deltas_vs_fcfs.append({
            "scenario_id": sc.id,
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

    # Pareto points (top level, for convenience)
    pareto_points = [
        {
            "scenario_id": e["scenario_id"],
            "scenario_name": e["scenario_name"],
            "x_accounts_fulfilled_pct": e["pareto"]["x_accounts_fulfilled_pct"],
            "y_gross_revenue": e["pareto"]["y_gross_revenue"],
        }
        for e in scenario_entries
    ]

    # Flat scenario_metrics list (backward compat)
    scenario_metrics = [
        {
            "scenario_id": e["scenario_id"],
            "scenario_name": e["scenario_name"],
            "metrics": e["metrics"],
        }
        for e in scenario_entries
    ]

    return {
        "manifest": manifest,
        "fcfs_baseline": fcfs_baseline,
        "scenarios": scenario_entries,
        "scenario_metrics": scenario_metrics,
        "pareto_points": pareto_points,
        "deltas_vs_fcfs": deltas_vs_fcfs,
        "explainability_deltas": explainability_deltas,
    }


# ── audit helper ────────────────────────────────────────────────────

def _audit_run(
    scenario_id: str,
    result: dict,
    actor: str = "system",
    db_path=None,
) -> None:
    """Append a compact 'run' audit entry from a preview result."""
    manifest = result.get("manifest", {})
    batch_m = result.get("metrics", {}).get("batch", {})
    append_audit(
        scenario_id,
        "run",
        actor=actor,
        payload={
            "run_id": manifest.get("run_id"),
            "seed": manifest.get("seed"),
            "checksum": manifest.get("checksum"),
            "demand_hash": manifest.get("demand_hash"),
            "tickets_fulfilled": batch_m.get("tickets_fulfilled"),
            "accounts_fulfilled_pct": batch_m.get("accounts_fulfilled_pct"),
            "gross_revenue": batch_m.get("gross_revenue_fixed_pricebook"),
        },
        db_path=db_path,
    )


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
