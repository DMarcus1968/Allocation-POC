"""Phase 1B — First-come, first-served allocator.

Processes requests in arrival_order. Each request tries its
section_preferences in order; the first section with enough
inventory fulfils the request.
"""

from __future__ import annotations

from src.models.allocation import Allocation, AllocationResult, Rejection
from src.models.event import EventConfig
from src.models.demand import TicketRequest


def allocate_fcfs(
    event: EventConfig,
    requests: list[TicketRequest],
) -> AllocationResult:
    """Allocate tickets on a strict first-come, first-served basis.

    Args:
        event: Event with sections and capacity.
        requests: Ticket requests (sorted by arrival_order internally).

    Returns:
        AllocationResult with allocations and rejections.
    """
    sorted_requests = sorted(requests, key=lambda r: r.arrival_order)

    inventory = {s.section_id: s.capacity for s in event.sections}

    allocations: list[Allocation] = []
    rejections: list[Rejection] = []

    for req in sorted_requests:
        allocated = False
        for section_id in req.section_preferences:
            if inventory.get(section_id, 0) >= req.qty_requested:
                inventory[section_id] -= req.qty_requested
                allocations.append(
                    Allocation(
                        account_id=req.account_id,
                        section_id=section_id,
                        qty_allocated=req.qty_requested,
                    )
                )
                allocated = True
                break

        if not allocated:
            rejections.append(
                Rejection(
                    account_id=req.account_id,
                    reason="insufficient_inventory",
                    qty_requested=req.qty_requested,
                )
            )

    return AllocationResult(allocations=allocations, rejections=rejections)
