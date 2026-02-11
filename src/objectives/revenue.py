"""Phase 2A stub — Revenue objective definition.

Defines the "revenue_at_face_value" objective that the batch allocator
can use.  This objective sorts requests so that higher-revenue requests
(promoter-set price x quantity) are processed first.

IMPORTANT:
- Revenue is calculated using ONLY promoter-set face-value prices.
- WTP is not consulted.  No pricing guidance is generated.
- The system does not suggest price changes to the promoter.
"""

from __future__ import annotations

OBJECTIVE_REGISTRY: dict[str, str] = {
    "fill_capacity": (
        "Allocate as many requests as capacity allows, "
        "in seeded-random order within the batch window."
    ),
    "revenue_at_face_value": (
        "Within promoter-set prices, process requests that contribute "
        "higher face-value revenue first.  Prices are never modified."
    ),
}


def available_objectives() -> list[dict[str, str]]:
    """Return the list of objectives a promoter can select from."""
    return [{"key": k, "description": v} for k, v in OBJECTIVE_REGISTRY.items()]
