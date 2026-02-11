"""Demand-side schemas: fan profiles and ticket requests.

WTP (willingness-to-pay) is attached to fan profiles for *diagnostic purposes only*.
It is NOT used in allocation decisions — that belongs to Phase 3.
"""

from __future__ import annotations

import uuid
from enum import Enum
from pydantic import BaseModel, Field


class RequestStatus(str, Enum):
    PENDING = "pending"
    ALLOCATED = "allocated"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"


class FanProfile(BaseModel):
    """Synthetic fan used in demand simulation."""

    fan_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    label: str = ""
    # WTP is diagnostic only — not used for allocation in Phase 2B
    wtp: float | None = Field(
        default=None,
        description="Willingness-to-pay (diagnostic metric, not an allocation input)",
    )


class Request(BaseModel):
    """A fan's ticket request submitted during the request window."""

    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    fan: FanProfile
    tier_id: str
    quantity: int = Field(ge=1)
    timestamp_ms: int = Field(
        ge=0,
        description="Arrival timestamp in ms — used by FCFS, ignored by batch allocator",
    )
    status: RequestStatus = RequestStatus.PENDING


class DemandPool(BaseModel):
    """The full set of requests collected during a request window."""

    requests: list[Request]

    @property
    def total_requested(self) -> int:
        return sum(r.quantity for r in self.requests)

    def for_tier(self, tier_id: str) -> list[Request]:
        return [r for r in self.requests if r.tier_id == tier_id]
