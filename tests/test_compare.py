"""Tests for comparison and metrics computation."""

from __future__ import annotations

import random

from src.models.event import EventConfig, Pricebook, Section
from src.models.demand import DemandConfig
from src.simulation.demand_sim import generate_demand
from src.allocators.fcfs import allocate_fcfs
from src.allocators.batch import allocate_batch
from src.comparison.compare import compute_metrics, compare_results, compute_delta


def _make_event() -> EventConfig:
    return EventConfig(
        event_id="test",
        name="Test",
        venue="Venue",
        sections=[
            Section("floor", "Floor", 100),
            Section("upper", "Upper", 200),
        ],
        pricebook=Pricebook(prices={"floor": 200.0, "upper": 80.0}),
        constraints={"per_account_cap": 4},
    )


class TestMetrics:
    def test_compute_metrics(self):
        event = _make_event()
        config = DemandConfig(num_accounts=50)
        rng = random.Random(42)
        requests = generate_demand(event, config, rng)
        result = allocate_fcfs(event, requests)
        metrics = compute_metrics(event, result)

        assert 0 <= metrics.accounts_fulfilled_pct <= 100
        assert metrics.tickets_fulfilled >= 0
        assert metrics.inventory_sold_pct >= 0
        assert metrics.gross_revenue_fixed_pricebook >= 0

    def test_compare_results(self):
        event = _make_event()
        config = DemandConfig(num_accounts=100)
        rng = random.Random(42)
        requests = generate_demand(event, config, rng)

        fcfs = allocate_fcfs(event, requests)
        batch = allocate_batch(event, requests, rng=random.Random(42))

        comp = compare_results(event, fcfs, batch)
        assert "fcfs" in comp
        assert "batch" in comp
        assert "delta_batch_vs_fcfs" in comp

    def test_delta_has_revenue_field(self):
        event = _make_event()
        config = DemandConfig(num_accounts=50)
        requests = generate_demand(event, config, random.Random(42))

        fcfs = allocate_fcfs(event, requests)
        batch = allocate_batch(event, requests, rng=random.Random(42))

        fcfs_m = compute_metrics(event, fcfs)
        batch_m = compute_metrics(event, batch)
        delta = compute_delta(fcfs_m, batch_m)

        assert "gross_revenue_fixed_pricebook" in delta
