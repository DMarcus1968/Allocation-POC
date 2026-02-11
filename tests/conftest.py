"""Shared test fixtures for the Allocation POC."""

from __future__ import annotations

import sys
import os
import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.event import Event, Tier, Inventory
from src.models.demand import DemandPool
from src.simulation.demand_sim import generate_demand
from src.dashboard.tradeoff_engine import ScenarioConfig, save_scenario


@pytest.fixture
def sample_tiers() -> list[Tier]:
    return [
        Tier(tier_id="tier_0", name="GA", capacity=500, price=75.0),
        Tier(tier_id="tier_1", name="VIP", capacity=100, price=200.0),
    ]


@pytest.fixture
def sample_event(sample_tiers: list[Tier]) -> Event:
    return Event(
        event_id="evt_test",
        name="Test Concert",
        inventory=Inventory(tiers=sample_tiers),
        max_tickets_per_request=4,
        allow_partial_fill=False,
    )


@pytest.fixture
def sample_demand(sample_event: Event) -> DemandPool:
    return generate_demand(sample_event, num_fans=200, seed=42)


@pytest.fixture
def sample_scenario() -> ScenarioConfig:
    cfg = ScenarioConfig(
        scenario_id="test_scenario_001",
        event_name="Test Concert",
        tiers=[
            {"name": "GA", "capacity": 500, "price": 75.0},
            {"name": "VIP", "capacity": 100, "price": 200.0},
        ],
        max_tickets_per_request=4,
        allow_partial_fill=False,
        num_fans=200,
        objectives=["fill_capacity", "revenue_at_face_value"],
    )
    save_scenario(cfg)
    return cfg
