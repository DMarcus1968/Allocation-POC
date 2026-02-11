"""Metrics schemas for comparing allocation outcomes.

All metrics are descriptive — they report what happened, not what *should* happen.
No language implying one outcome is "better" or "fairer"; comparisons are dimensional.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TierMetrics(BaseModel):
    """Per-tier descriptive metrics."""

    tier_id: str
    tier_name: str
    capacity: int
    total_requested: int
    total_allocated: int
    requests_fully_filled: int
    requests_partially_filled: int
    requests_rejected: int
    revenue_at_face_value: float = Field(
        description="Tickets allocated × promoter-set price (no markup or guidance)"
    )
    demand_to_supply_ratio: float


class ScenarioMetrics(BaseModel):
    """Aggregate metrics for a single allocator run on a single event."""

    allocator_name: str
    event_id: str
    tier_metrics: list[TierMetrics]

    total_capacity: int
    total_requested: int
    total_allocated: int
    overall_fill_rate: float
    total_revenue_at_face_value: float

    requests_fully_filled: int
    requests_partially_filled: int
    requests_rejected: int

    # Explainability (pass-through from AllocationResult)
    constraints_applied: list[str] = Field(default_factory=list)
    objective_used: str = ""


class ComparisonReport(BaseModel):
    """Side-by-side comparison of multiple allocation scenarios.

    Presents dimensional differences — does not rank or label any scenario
    as superior.
    """

    event_id: str
    scenarios: list[ScenarioMetrics]
    dimension_deltas: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description=(
            "Per-dimension differences between scenarios, e.g. "
            "{'revenue_at_face_value': {'batch_vs_fcfs': 1200.0}}"
        ),
    )
