"""Demand configuration and ticket request models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DemandConfig:
    """Configuration for synthetic demand generation."""

    num_accounts: int = 500
    avg_qty: float = 2.5
    std_qty: float = 1.0
    min_qty: int = 1
    max_qty: int = 6
    section_preference_weights: dict[str, float] | None = None
    wtp_mean: float = 100.0   # diagnostic only — does NOT drive allocation
    wtp_std: float = 30.0     # diagnostic only — does NOT drive allocation
    loyalty_score_range: tuple[float, float] = (0.0, 100.0)


@dataclass
class TicketRequest:
    """A single account's ticket request."""

    account_id: str
    qty_requested: int
    section_preferences: list[str] = field(default_factory=list)
    wtp: float = 0.0           # diagnostic only — does NOT drive allocation
    loyalty_score: float = 0.0
    arrival_order: int = 0
