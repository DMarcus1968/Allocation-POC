"""Phase 1A stub — synthetic demand generation.

Generates a DemandPool of fan requests against an Event.
Uses a seeded RNG so results are deterministic and reproducible.
"""

from __future__ import annotations

import random
from src.models.event import Event
from src.models.demand import DemandPool, FanProfile, Request


def generate_demand(
    event: Event,
    num_fans: int = 200,
    seed: int = 42,
) -> DemandPool:
    """Create a synthetic demand pool for *event*.

    Each fan requests 1-max_tickets_per_request tickets in a randomly chosen
    tier.  Arrival timestamps are uniformly distributed across a simulated
    request window (0 - 60 000 ms).

    WTP values are attached for diagnostic purposes only and are NOT used
    in any allocation logic.
    """
    rng = random.Random(seed)
    requests: list[Request] = []
    tiers = event.inventory.tiers

    for i in range(num_fans):
        tier = rng.choice(tiers)
        qty = rng.randint(1, event.max_tickets_per_request)
        # WTP is diagnostic only -- drawn from a uniform distribution
        # centered loosely around the tier price.  It has zero bearing on
        # allocation in Phase 2B.
        wtp_diagnostic = round(tier.price * rng.uniform(0.5, 2.0), 2)

        fan = FanProfile(
            fan_id=f"fan_{seed}_{i:04d}",
            label=f"Fan {i}",
            wtp=wtp_diagnostic,
        )
        req = Request(
            request_id=f"req_{seed}_{i:04d}",
            fan=fan,
            tier_id=tier.tier_id,
            quantity=qty,
            timestamp_ms=rng.randint(0, 60_000),
        )
        requests.append(req)

    return DemandPool(requests=requests)
