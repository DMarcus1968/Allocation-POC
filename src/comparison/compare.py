"""Phase 1D stub — Metrics computation and scenario comparison.

All metrics are descriptive.  No ranking or normative language.
"""

from __future__ import annotations

from src.models.event import Event
from src.models.allocation import AllocationResult
from src.models.metrics import TierMetrics, ScenarioMetrics, ComparisonReport


def compute_scenario_metrics(
    event: Event, result: AllocationResult
) -> ScenarioMetrics:
    """Derive descriptive metrics from a single allocation run."""

    tier_metrics_list: list[TierMetrics] = []
    total_cap = 0
    total_req = 0
    total_alloc = 0
    total_rev = 0.0
    full = 0
    partial = 0
    rejected = 0

    for tier in event.inventory.tiers:
        reservations = result.reservations_for_tier(tier.tier_id)
        t_req = sum(r.quantity_requested for r in reservations)
        t_alloc = sum(r.quantity_allocated for r in reservations)
        t_full = sum(1 for r in reservations if r.is_full_fill)
        t_partial = sum(1 for r in reservations if r.is_partial_fill)
        t_rej = sum(1 for r in reservations if r.quantity_allocated == 0)
        t_rev = t_alloc * tier.price
        ds_ratio = t_req / tier.capacity if tier.capacity > 0 else 0.0

        tier_metrics_list.append(
            TierMetrics(
                tier_id=tier.tier_id,
                tier_name=tier.name,
                capacity=tier.capacity,
                total_requested=t_req,
                total_allocated=t_alloc,
                requests_fully_filled=t_full,
                requests_partially_filled=t_partial,
                requests_rejected=t_rej,
                revenue_at_face_value=t_rev,
                demand_to_supply_ratio=round(ds_ratio, 3),
            )
        )
        total_cap += tier.capacity
        total_req += t_req
        total_alloc += t_alloc
        total_rev += t_rev
        full += t_full
        partial += t_partial
        rejected += t_rej

    return ScenarioMetrics(
        allocator_name=result.allocator_name,
        event_id=event.event_id,
        tier_metrics=tier_metrics_list,
        total_capacity=total_cap,
        total_requested=total_req,
        total_allocated=total_alloc,
        overall_fill_rate=round(total_alloc / total_req, 4) if total_req else 0.0,
        total_revenue_at_face_value=total_rev,
        requests_fully_filled=full,
        requests_partially_filled=partial,
        requests_rejected=rejected,
        constraints_applied=result.constraints_applied,
        objective_used=result.objective_used,
    )


def build_comparison(
    event: Event, results: list[AllocationResult]
) -> ComparisonReport:
    """Compare multiple allocator runs on the same event.

    Computes per-dimension deltas between scenarios.
    No scenario is labeled as superior -- deltas are signed numbers only.
    """
    scenarios = [compute_scenario_metrics(event, r) for r in results]
    deltas: dict[str, dict[str, float]] = {}

    if len(scenarios) == 2:
        a, b = scenarios
        tag = f"{a.allocator_name}_vs_{b.allocator_name}"
        deltas["total_allocated"] = {tag: a.total_allocated - b.total_allocated}
        deltas["overall_fill_rate"] = {
            tag: round(a.overall_fill_rate - b.overall_fill_rate, 4)
        }
        deltas["revenue_at_face_value"] = {
            tag: round(
                a.total_revenue_at_face_value - b.total_revenue_at_face_value, 2
            )
        }
        deltas["requests_rejected"] = {
            tag: a.requests_rejected - b.requests_rejected
        }

    return ComparisonReport(
        event_id=event.event_id,
        scenarios=scenarios,
        dimension_deltas=deltas,
    )
