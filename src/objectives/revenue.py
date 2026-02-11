"""Phase 2A — Revenue objective computation.

Computes gross revenue from a fixed, read-only pricebook.
Pricing control remains with the promoter/rights-owner;
this module only *reads* prices, never modifies them.
"""

from __future__ import annotations

from src.models.event import EventConfig
from src.models.allocation import AllocationResult


def compute_revenue(event: EventConfig, result: AllocationResult) -> float:
    """Compute gross revenue using the promoter-set pricebook.

    Args:
        event: Event configuration containing the pricebook.
        result: Allocation result with per-section ticket allocations.

    Returns:
        Total gross revenue (rounded to 2 decimal places).
    """
    prices = event.pricebook.prices
    total = 0.0
    for alloc in result.allocations:
        price = prices.get(alloc.section_id, 0.0)
        total += price * alloc.qty_allocated
    return round(total, 2)
