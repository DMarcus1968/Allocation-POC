"""Phase 1C — Batch allocator with configurable knobs.

Unlike FCFS, the batch allocator collects all requests, then processes
them according to promoter-set constraints and configurable allocation
knobs (per_account_cap, group_size_cap, holdback, priority ordering, etc.).

Knobs control allocation behaviour; pricing remains promoter-side and
is never modified here.
"""

from __future__ import annotations

import random

from src.models.allocation import Allocation, AllocationResult, Rejection
from src.models.event import EventConfig
from src.models.demand import TicketRequest


DEFAULT_KNOBS: dict = {
    "per_account_cap": 4,
    "group_size_cap": 6,
    "holdback_pct": 0.0,
    "priority_mode": "random",      # "random" | "loyalty" | "fifo"
    "singles_avoidance": True,
    # section_eligibility: optional dict[str, bool]
}


def allocate_batch(
    event: EventConfig,
    requests: list[TicketRequest],
    knobs: dict | None = None,
    constraints: dict | None = None,
    rng: random.Random | None = None,
) -> AllocationResult:
    """Run batch allocation with the given knobs and promoter constraints.

    Promoter hard constraints (from event.constraints or the *constraints*
    parameter) override knobs where applicable.

    Args:
        event: Event configuration.
        requests: All collected ticket requests.
        knobs: Allocation knobs (merged with DEFAULT_KNOBS).
        constraints: Explicit promoter hard constraints (override knobs).
        rng: Seeded RNG for deterministic shuffling.

    Returns:
        AllocationResult including a ``debug`` dict with binding counts.
    """
    if rng is None:
        rng = random.Random(42)

    k = {**DEFAULT_KNOBS, **(knobs or {})}
    hard = constraints or event.constraints or {}

    # Promoter hard constraints override knobs where both exist
    per_account_cap: int = hard.get("per_account_cap", k["per_account_cap"])
    group_size_cap: int = hard.get("group_size_cap", k["group_size_cap"])
    holdback_pct: float = float(k["holdback_pct"])
    priority_mode: str = k["priority_mode"]
    singles_avoidance: bool = k["singles_avoidance"]
    section_eligibility: dict[str, bool] | None = k.get("section_eligibility")

    # Effective inventory after holdback
    inventory: dict[str, int] = {}
    holdback_applied: dict[str, int] = {}
    for s in event.sections:
        holdback = int(s.capacity * holdback_pct)
        inventory[s.section_id] = s.capacity - holdback
        holdback_applied[s.section_id] = holdback

    # Prioritize requests
    sorted_requests = _prioritize(requests, priority_mode, rng)

    allocations: list[Allocation] = []
    rejections: list[Rejection] = []
    per_account: dict[str, int] = {}

    binding_counts: dict[str, int] = {
        "per_account_cap": 0,
        "group_size_cap": 0,
        "section_eligibility": 0,
        "holdback": sum(holdback_applied.values()),
        "insufficient_inventory": 0,
    }
    rejection_summaries: list[dict] = []

    for req in sorted_requests:
        acct_used = per_account.get(req.account_id, 0)
        remaining_cap = per_account_cap - acct_used

        if remaining_cap <= 0:
            binding_counts["per_account_cap"] += 1
            rejections.append(
                Rejection(
                    account_id=req.account_id,
                    reason="per_account_cap_exceeded",
                    qty_requested=req.qty_requested,
                )
            )
            rejection_summaries.append({
                "account_id": req.account_id,
                "reason": "per_account_cap_exceeded",
                "cap": per_account_cap,
                "used": acct_used,
            })
            continue

        qty = min(req.qty_requested, remaining_cap, group_size_cap)
        if req.qty_requested > group_size_cap:
            binding_counts["group_size_cap"] += 1

        allocated = False
        for section_id in req.section_preferences:
            if section_eligibility and not section_eligibility.get(section_id, True):
                binding_counts["section_eligibility"] += 1
                continue

            avail = inventory.get(section_id, 0)
            if avail < qty:
                continue

            # Singles avoidance: avoid leaving exactly 1 seat in a section
            effective_qty = qty
            if singles_avoidance and avail - qty == 1 and qty > 1:
                effective_qty = qty - 1

            inventory[section_id] -= effective_qty
            per_account[req.account_id] = acct_used + effective_qty
            allocations.append(
                Allocation(
                    account_id=req.account_id,
                    section_id=section_id,
                    qty_allocated=effective_qty,
                )
            )
            allocated = True
            break

        if not allocated:
            binding_counts["insufficient_inventory"] += 1
            rejections.append(
                Rejection(
                    account_id=req.account_id,
                    reason="no_eligible_section_with_capacity",
                    qty_requested=req.qty_requested,
                )
            )
            rejection_summaries.append({
                "account_id": req.account_id,
                "reason": "no_eligible_section_with_capacity",
                "qty_requested": req.qty_requested,
            })

    # Count sections with exactly 1 remaining seat
    singles_stranded = sum(1 for v in inventory.values() if v == 1)
    binding_counts["singles_stranded"] = singles_stranded

    debug = {
        "binding_counts": binding_counts,
        "rejections": rejection_summaries[:50],
        "effective_inventory_before": {s.section_id: s.capacity for s in event.sections},
        "holdback_applied": holdback_applied,
        "holdback_pct": holdback_pct,
        "priority_mode": priority_mode,
        "remaining_inventory": dict(inventory),
    }

    return AllocationResult(
        allocations=allocations,
        rejections=rejections,
        debug=debug,
    )


def _prioritize(
    requests: list[TicketRequest],
    mode: str,
    rng: random.Random,
) -> list[TicketRequest]:
    """Return a new list of requests in the specified priority order."""
    reqs = list(requests)
    if mode == "fifo":
        reqs.sort(key=lambda r: r.arrival_order)
    elif mode == "loyalty":
        reqs.sort(key=lambda r: (-r.loyalty_score, r.arrival_order))
    elif mode == "random":
        rng.shuffle(reqs)
    else:
        # Unknown mode falls back to arrival order
        reqs.sort(key=lambda r: r.arrival_order)
    return reqs
