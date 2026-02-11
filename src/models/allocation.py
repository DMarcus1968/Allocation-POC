"""Allocation output schemas.

An AllocationResult is the deterministic output of running one allocator
against one (Event, DemandPool) pair.
"""

from __future__ import annotations

import uuid
from pydantic import BaseModel, Field


class Reservation(BaseModel):
    """A single fulfilled (or partially fulfilled) allocation."""

    reservation_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    request_id: str
    fan_id: str
    tier_id: str
    quantity_requested: int
    quantity_allocated: int = Field(ge=0)

    @property
    def is_full_fill(self) -> bool:
        return self.quantity_allocated == self.quantity_requested

    @property
    def is_partial_fill(self) -> bool:
        return 0 < self.quantity_allocated < self.quantity_requested


class AllocationResult(BaseModel):
    """Complete output from a single allocator run."""

    result_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    allocator_name: str
    event_id: str
    reservations: list[Reservation]
    seed: int | None = Field(
        default=None, description="RNG seed used (for deterministic replay)"
    )

    # Explainability block (required by claude.md §5)
    constraints_applied: list[str] = Field(default_factory=list)
    objective_used: str = ""
    alternatives_considered: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)

    @property
    def total_allocated(self) -> int:
        return sum(r.quantity_allocated for r in self.reservations)

    @property
    def total_requested(self) -> int:
        return sum(r.quantity_requested for r in self.reservations)

    @property
    def fill_rate(self) -> float:
        if self.total_requested == 0:
            return 0.0
        return self.total_allocated / self.total_requested

    def reservations_for_tier(self, tier_id: str) -> list[Reservation]:
        return [r for r in self.reservations if r.tier_id == tier_id]
