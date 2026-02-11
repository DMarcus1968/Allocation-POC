"""Demo event/demand fixtures for the tradeoff dashboard.

Provides a simple loader for demo configurations so the preview
harness can run without an external event registry.
"""

from __future__ import annotations

from src.models.event import EventConfig, Pricebook, Section
from src.models.demand import DemandConfig


def load_demo_event(event_ref: str = "demo_event") -> EventConfig:
    """Return a demo EventConfig.

    The pricebook is read-only and promoter-set; allocation code
    never modifies these prices.
    """
    # A mid-size arena show with four sections
    sections = [
        Section(section_id="floor", name="Floor", capacity=200),
        Section(section_id="lower", name="Lower Bowl", capacity=400),
        Section(section_id="upper", name="Upper Bowl", capacity=600),
        Section(section_id="balcony", name="Balcony", capacity=300),
    ]

    pricebook = Pricebook(
        prices={
            "floor": 250.00,
            "lower": 150.00,
            "upper": 85.00,
            "balcony": 55.00,
        }
    )

    constraints = {
        "per_account_cap": 6,
        "group_size_cap": 8,
    }

    return EventConfig(
        event_id="demo_event_001",
        name="Demo Arena Show",
        venue="Demo Arena",
        sections=sections,
        pricebook=pricebook,
        constraints=constraints,
    )


def load_demand_config(demand_ref: str = "default") -> DemandConfig:
    """Return a demo DemandConfig."""
    return DemandConfig(
        num_accounts=500,
        avg_qty=2.5,
        std_qty=1.0,
        min_qty=1,
        max_qty=6,
        section_preference_weights={
            "floor": 3.0,
            "lower": 2.0,
            "upper": 1.5,
            "balcony": 1.0,
        },
        wtp_mean=120.0,
        wtp_std=40.0,
        loyalty_score_range=(0.0, 100.0),
    )
