"""Phase 1B stub — First-Come-First-Served allocator.

Processes requests in arrival-time order.  Once a tier is exhausted,
subsequent requests for that tier are rejected.
This is the baseline that the batch allocator is compared against.
"""

from __future__ import annotations

from src.models.event import Event
from src.models.demand import DemandPool, RequestStatus
from src.models.allocation import AllocationResult, Reservation


def allocate_fcfs(event: Event, demand: DemandPool) -> AllocationResult:
    """Run FCFS allocation -- deterministic given the same input timestamps."""

    sorted_requests = sorted(demand.requests, key=lambda r: r.timestamp_ms)
    remaining: dict[str, int] = {t.tier_id: t.capacity for t in event.inventory.tiers}
    reservations: list[Reservation] = []

    for req in sorted_requests:
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
                reservation_id=f"rsv_fcfs_{req.request_id}",
                request_id=req.request_id,
                fan_id=req.fan.fan_id,
                tier_id=req.tier_id,
                quantity_requested=req.quantity,
                quantity_allocated=allocated,
            )
        )

    return AllocationResult(
        result_id=f"fcfs_{event.event_id}",
        allocator_name="fcfs",
        event_id=event.event_id,
        reservations=reservations,
        constraints_applied=[
            f"max_tickets_per_request={event.max_tickets_per_request}",
            f"allow_partial_fill={event.allow_partial_fill}",
            "arrival-time ordering (FCFS)",
        ],
        objective_used="serve requests in arrival order until capacity exhausted",
        alternatives_considered=[
            "random-order allocation",
            "batch allocation (Phase 1C)",
        ],
        rejection_reasons=[
            "tier capacity exhausted at time of processing",
        ],
    )
