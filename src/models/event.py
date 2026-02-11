"""Event configuration models.

An Event represents a ticketed event with sections, capacity,
and a read-only pricebook set by the promoter/rights-owner.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Section:
    section_id: str
    name: str
    capacity: int


@dataclass
class Pricebook:
    """Read-only pricing set by the promoter/rights-owner.

    Allocation code must never modify these prices.
    """

    prices: dict[str, float] = field(default_factory=dict)  # section_id -> price


@dataclass
class EventConfig:
    event_id: str
    name: str
    venue: str
    sections: list[Section] = field(default_factory=list)
    pricebook: Pricebook = field(default_factory=Pricebook)
    constraints: dict = field(default_factory=dict)  # promoter hard constraints

    def total_capacity(self) -> int:
        return sum(s.capacity for s in self.sections)

    def section_map(self) -> dict[str, Section]:
        return {s.section_id: s for s in self.sections}
