"""Phase 1A — Synthetic demand generation.

Generates a list of TicketRequests from a DemandConfig and EventConfig
using a seeded RNG for full determinism.
"""

from __future__ import annotations

import random

from src.models.demand import DemandConfig, TicketRequest
from src.models.event import EventConfig


def generate_demand(
    event: EventConfig,
    config: DemandConfig,
    rng: random.Random,
) -> list[TicketRequest]:
    """Generate synthetic ticket demand for an event.

    Args:
        event: Event configuration with sections.
        config: Demand generation parameters.
        rng: Seeded random number generator (caller controls seed).

    Returns:
        Deterministic list of TicketRequests (stable for same seed).
    """
    section_ids = sorted(s.section_id for s in event.sections)

    if config.section_preference_weights:
        weights = [
            config.section_preference_weights.get(sid, 1.0)
            for sid in section_ids
        ]
    else:
        weights = [1.0] * len(section_ids)

    requests: list[TicketRequest] = []
    for i in range(config.num_accounts):
        qty_raw = rng.gauss(config.avg_qty, config.std_qty)
        qty = max(config.min_qty, min(config.max_qty, round(qty_raw)))

        prefs = _weighted_shuffle(section_ids, weights, rng)

        wtp = max(0.0, rng.gauss(config.wtp_mean, config.wtp_std))

        lo, hi = config.loyalty_score_range
        loyalty = rng.uniform(lo, hi)

        requests.append(
            TicketRequest(
                account_id=f"acct_{i:06d}",
                qty_requested=qty,
                request_id=f"req_{i:06d}",
                section_preferences=prefs,
                wtp=round(wtp, 2),
                loyalty_score=round(loyalty, 2),
                arrival_order=i,
            )
        )

    return requests


def _weighted_shuffle(
    items: list[str],
    weights: list[float],
    rng: random.Random,
) -> list[str]:
    """Shuffle items with weighted probability (higher weight = more likely picked first)."""
    paired = list(zip(items, weights))
    result: list[str] = []
    remaining = list(paired)
    while remaining:
        w = [p[1] for p in remaining]
        total = sum(w)
        if total <= 0:
            result.extend(p[0] for p in remaining)
            break
        r = rng.uniform(0, total)
        cumulative = 0.0
        for idx, (item, weight) in enumerate(remaining):
            cumulative += weight
            if r <= cumulative:
                result.append(item)
                remaining.pop(idx)
                break
    return result
