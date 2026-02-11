"""Tests for demand simulation."""

from __future__ import annotations

import random

from src.models.demand import DemandConfig
from src.models.event import EventConfig, Section
from src.simulation.demand_sim import generate_demand


def _make_event() -> EventConfig:
    return EventConfig(
        event_id="test",
        name="Test",
        venue="Venue",
        sections=[
            Section("sec_a", "A", 100),
            Section("sec_b", "B", 200),
        ],
    )


class TestDemandSim:
    def test_generates_correct_count(self):
        event = _make_event()
        config = DemandConfig(num_accounts=50)
        rng = random.Random(42)
        requests = generate_demand(event, config, rng)
        assert len(requests) == 50

    def test_deterministic(self):
        event = _make_event()
        config = DemandConfig(num_accounts=100)
        r1 = generate_demand(event, config, random.Random(42))
        r2 = generate_demand(event, config, random.Random(42))
        assert [r.account_id for r in r1] == [r.account_id for r in r2]
        assert [r.qty_requested for r in r1] == [r.qty_requested for r in r2]
        assert [r.wtp for r in r1] == [r.wtp for r in r2]

    def test_qty_within_bounds(self):
        event = _make_event()
        config = DemandConfig(num_accounts=200, min_qty=1, max_qty=4)
        rng = random.Random(42)
        requests = generate_demand(event, config, rng)
        for req in requests:
            assert config.min_qty <= req.qty_requested <= config.max_qty

    def test_section_preferences_contain_all_sections(self):
        event = _make_event()
        config = DemandConfig(num_accounts=10)
        rng = random.Random(42)
        requests = generate_demand(event, config, rng)
        section_ids = {"sec_a", "sec_b"}
        for req in requests:
            assert set(req.section_preferences) == section_ids
