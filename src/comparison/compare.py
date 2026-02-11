"""Phase 1D — Allocation comparison and metrics computation.

Computes MetricsSummary for an allocation result and produces
side-by-side comparison with delta metrics.
"""

from __future__ import annotations

from src.models.event import EventConfig
from src.models.allocation import AllocationResult
from src.models.metrics import MetricsSummary
from src.objectives.revenue import compute_revenue


def compute_metrics(
    event: EventConfig,
    result: AllocationResult,
    *,
    requests: list | None = None,
) -> MetricsSummary:
    """Compute normalized metrics for an allocation result.

    Args:
        event: Event configuration (sections, pricebook).
        result: Allocation result to evaluate.
        requests: Original request list. When provided, total requesting
            accounts is derived from the input (not just allocations +
            rejections), ensuring the denominator for
            ``accounts_fulfilled_pct`` reflects all demand.

    Returns:
        MetricsSummary with all required metrics.
    """
    total_capacity = event.total_capacity()

    fulfilled_accounts: set[str] = set()
    tickets_by_account: dict[str, int] = {}
    tickets_fulfilled = 0

    for alloc in result.allocations:
        fulfilled_accounts.add(alloc.account_id)
        tickets_by_account[alloc.account_id] = (
            tickets_by_account.get(alloc.account_id, 0) + alloc.qty_allocated
        )
        tickets_fulfilled += alloc.qty_allocated

    # Total requesting accounts: prefer input-side count when available
    if requests is not None:
        total_accounts = len({r.account_id for r in requests})
    else:
        rejected_accounts = {r.account_id for r in result.rejections}
        all_accounts = fulfilled_accounts | rejected_accounts
        total_accounts = len(all_accounts)

    accounts_fulfilled_pct = (
        (len(fulfilled_accounts) / total_accounts * 100)
        if total_accounts > 0
        else 0.0
    )

    avg_per = (
        (tickets_fulfilled / len(fulfilled_accounts))
        if fulfilled_accounts
        else 0.0
    )

    # Remaining inventory per section
    section_remaining: dict[str, int] = {
        s.section_id: s.capacity for s in event.sections
    }
    for alloc in result.allocations:
        section_remaining[alloc.section_id] -= alloc.qty_allocated

    singles_stranded = sum(1 for v in section_remaining.values() if v == 1)
    unsold = sum(max(0, v) for v in section_remaining.values())
    sold_pct = (
        ((total_capacity - unsold) / total_capacity * 100)
        if total_capacity > 0
        else 0.0
    )

    revenue = compute_revenue(event, result)

    return MetricsSummary(
        accounts_fulfilled_pct=round(accounts_fulfilled_pct, 2),
        tickets_fulfilled=tickets_fulfilled,
        avg_tickets_per_fulfilled_account=round(avg_per, 2),
        singles_stranded_count=singles_stranded,
        inventory_sold_pct=round(sold_pct, 2),
        unsold_inventory_count=unsold,
        gross_revenue_fixed_pricebook=revenue,
    )


def compute_delta(
    base: MetricsSummary,
    alt: MetricsSummary,
) -> dict:
    """Compute the delta between two metrics summaries."""
    return {
        "accounts_fulfilled_pct": round(
            alt.accounts_fulfilled_pct - base.accounts_fulfilled_pct, 2
        ),
        "tickets_fulfilled": alt.tickets_fulfilled - base.tickets_fulfilled,
        "avg_tickets_per_fulfilled_account": round(
            alt.avg_tickets_per_fulfilled_account
            - base.avg_tickets_per_fulfilled_account,
            2,
        ),
        "singles_stranded_count": (
            alt.singles_stranded_count - base.singles_stranded_count
        ),
        "inventory_sold_pct": round(
            alt.inventory_sold_pct - base.inventory_sold_pct, 2
        ),
        "unsold_inventory_count": (
            alt.unsold_inventory_count - base.unsold_inventory_count
        ),
        "gross_revenue_fixed_pricebook": round(
            alt.gross_revenue_fixed_pricebook
            - base.gross_revenue_fixed_pricebook,
            2,
        ),
    }


def compare_results(
    event: EventConfig,
    fcfs_result: AllocationResult,
    batch_result: AllocationResult,
) -> dict:
    """Side-by-side comparison of FCFS vs batch allocation.

    Returns:
        Dict with fcfs metrics, batch metrics, and delta.
    """
    fcfs_metrics = compute_metrics(event, fcfs_result)
    batch_metrics = compute_metrics(event, batch_result)
    delta = compute_delta(fcfs_metrics, batch_metrics)

    return {
        "fcfs": fcfs_metrics.to_dict(),
        "batch": batch_metrics.to_dict(),
        "delta_batch_vs_fcfs": delta,
    }
