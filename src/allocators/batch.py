"""Phase 1C — Batch allocator with configurable knobs.

Unlike FCFS, the batch allocator collects all requests, then processes
them according to promoter-set constraints and configurable allocation
knobs (per_account_cap, group_size_cap, holdback, priority ordering, etc.).

Knobs control allocation behaviour; pricing remains promoter-side and
is never modified here.

The ``debug`` dict in the returned ``AllocationResult`` provides
section-aware binding counts and lost-ticket estimates for each
constraint, supporting the explainability layer.
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
        AllocationResult including a ``debug`` dict with section-aware
        binding counts and lost-ticket estimates.
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

    section_ids = sorted(s.section_id for s in event.sections)

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

    # Section-aware binding counters
    bindings = _empty_binding_map()
    lost = _empty_binding_map()
    rejection_summaries: list[dict] = []

    for req in sorted_requests:
        acct_used = per_account.get(req.account_id, 0)
        remaining_cap = per_account_cap - acct_used

        if remaining_cap <= 0:
            # Attribute to first preferred section for section-level tracking
            attributed_section = (
                req.section_preferences[0]
                if req.section_preferences
                else section_ids[0]
            )
            _incr(bindings, "per_account_cap", attributed_section)
            _incr(lost, "per_account_cap", attributed_section, req.qty_requested)
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

        allocated = False
        for section_id in req.section_preferences:
            if section_eligibility and not section_eligibility.get(section_id, True):
                _incr(bindings, "section_eligibility", section_id)
                _incr(lost, "section_eligibility", section_id, qty)
                continue

            avail = inventory.get(section_id, 0)
            if avail < qty:
                continue

            # Singles avoidance: avoid leaving exactly 1 seat in a section
            effective_qty = qty
            if singles_avoidance and avail - qty == 1 and qty > 1:
                effective_qty = qty - 1

            # Track group_size_cap binding at the allocated section
            if req.qty_requested > group_size_cap:
                _incr(bindings, "group_size_cap", section_id)
                tickets_lost_to_cap = req.qty_requested - min(
                    req.qty_requested, remaining_cap, group_size_cap
                )
                if tickets_lost_to_cap > 0:
                    _incr(lost, "group_size_cap", section_id, tickets_lost_to_cap)

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
            attributed_section = (
                req.section_preferences[0]
                if req.section_preferences
                else section_ids[0]
            )
            _incr(bindings, "insufficient_inventory", attributed_section)
            _incr(lost, "insufficient_inventory", attributed_section, req.qty_requested)
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

    # Holdback bindings: tracked as tickets withheld per section
    for sid in section_ids:
        hb = holdback_applied.get(sid, 0)
        if hb > 0:
            bindings["holdback"]["total"] += 1
            bindings["holdback"]["by_section"][sid] = 1
            lost["holdback"]["total"] += hb
            lost["holdback"]["by_section"][sid] = hb

    # Count sections with exactly 1 remaining seat
    singles_stranded = sum(1 for v in inventory.values() if v == 1)

    debug = {
        "bindings": bindings,
        "lost_tickets_estimates": lost,
        "singles_stranded": singles_stranded,
        "rejections": rejection_summaries[:50],
        "effective_inventory_before": {
            s.section_id: s.capacity for s in event.sections
        },
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


# ── internal helpers ────────────────────────────────────────────────

def _empty_binding_map() -> dict:
    """Create an empty section-aware binding structure."""
    return {
        "per_account_cap": {"total": 0, "by_section": {}},
        "group_size_cap": {"total": 0, "by_section": {}},
        "section_eligibility": {"total": 0, "by_section": {}},
        "holdback": {"total": 0, "by_section": {}},
        "insufficient_inventory": {"total": 0, "by_section": {}},
    }


def _incr(
    mapping: dict,
    constraint: str,
    section_id: str,
    amount: int = 1,
) -> None:
    """Increment a section-aware binding counter."""
    entry = mapping[constraint]
    entry["total"] += amount
    entry["by_section"][section_id] = (
        entry["by_section"].get(section_id, 0) + amount
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
