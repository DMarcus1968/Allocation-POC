"""Event, Tier, and Inventory schemas.

These represent the promoter-defined supply side.
Promoters set all pricing and capacity — the platform never overrides these.
"""

from __future__ import annotations

import uuid
from pydantic import BaseModel, Field


class Tier(BaseModel):
    """A single price tier within an event, defined entirely by the promoter."""

    tier_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    capacity: int = Field(ge=0, description="Total seats the promoter has released in this tier")
    price: float = Field(ge=0.0, description="Promoter-set face-value price")


class Inventory(BaseModel):
    """Inventory snapshot for an event — one entry per tier."""

    tiers: list[Tier]

    @property
    def total_capacity(self) -> int:
        return sum(t.capacity for t in self.tiers)

    def tier_by_id(self, tier_id: str) -> Tier | None:
        return next((t for t in self.tiers if t.tier_id == tier_id), None)

    def tier_by_name(self, name: str) -> Tier | None:
        return next((t for t in self.tiers if t.name == name), None)


class Event(BaseModel):
    """A single event whose parameters are set by the rights-owner (promoter)."""

    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    inventory: Inventory

    # Promoter-set constraints (hard constraints — never relaxed by the system)
    max_tickets_per_request: int = Field(
        default=4, ge=1,
        description="Promoter-imposed cap on tickets per fan request",
    )
    allow_partial_fill: bool = Field(
        default=False,
        description="Whether the promoter permits partial fills of a request",
    )
