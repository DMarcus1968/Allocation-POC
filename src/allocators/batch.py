"""Phase 1C stub — Batch allocator.

Collects all requests in the request window, then allocates using a
deterministic heuristic.  Arrival time is intentionally ignored so that
speed-based competition is removed.

The heuristic used here is a seeded random shuffle -- this is the simplest
allocation that breaks the FCFS timing advantage while remaining
deterministic.  More sophisticated objectives are layered in Phase 2A+.
"""

from __future__ import annotations

import random
from src.models.event import Event
from src.models.demand import DemandPool, RequestStatus
from src.models.allocation import AllocationResult, Reservation


def allocate_batch(
    event: Event,
    demand: DemandPool,
    seed: int = 42,
    objective: str = "fill_capacity",
) -> AllocationResult:
    """Run batch allocation with a deterministic seed.

    Parameters
    ----------
    objective : str
        Label for the allocation objective.  In this stub the only
        implemented strategies are ``"fill_capacity"`` (allocate as many
        requests as capacity allows in seeded-random order) and
        ``"revenue_at_face_value"`` which sorts by
        promoter-set tier price x quantity descending.
    """
    rng = random.Random(seed)
    requests = list(demand.requests)
    remaining: dict[str, int] = {t.tier_id: t.capacity for t in event.inventory.tiers}

    if objective == "revenue_at_face_value":
        tier_prices = {t.tier_id: t.price for t in event.inventory.tiers}
        requests.sort(
            key=lambda r: tier_prices.get(r.tier_id, 0) * r.quantity,
            reverse=True,
        )
    else:
        rng.shuffle(requests)

    reservations: list[Reservation] = []

    for req in requests:
        avail = remaining.get(req.tier_id, 0)

        if avail >= req.quantity:
            allocated = req.quantity
            remaining[req.tier_id] -= allocated
            req.status = RequestStatus.ALLOCATED
        elif avail > 0 and event.allow_partial_fill:
            allocated = avail
            remaining[req.tier_id] = 0
            req.status = RequestStatus.PARTIALLY_FILLED
        else:
            allocated = 0
            req.status = RequestStatus.REJECTED

        reservations.append(
            Reservation(
                reservation_id=f"rsv_batch_{req.request_id}",
                request_id=req.request_id,
                fan_id=req.fan.fan_id,
                tier_id=req.tier_id,
                quantity_requested=req.quantity,
                quantity_allocated=allocated,
            )
        )

    return AllocationResult(
        result_id=f"batch_{event.event_id}",
        allocator_name="batch",
        event_id=event.event_id,
        reservations=reservations,
        seed=seed,
        constraints_applied=[
            f"max_tickets_per_request={event.max_tickets_per_request}",
            f"allow_partial_fill={event.allow_partial_fill}",
            "arrival-time ignored (batch window)",
        ],
        objective_used=objective,
        alternatives_considered=[
            "FCFS baseline (Phase 1B)",
            "random shuffle with different seed",
        ],
        rejection_reasons=[
            "tier capacity exhausted after higher-priority requests processed",
        ],
    )
