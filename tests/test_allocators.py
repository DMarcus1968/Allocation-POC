"""Tests for FCFS and batch allocators."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.event import Event, Tier, Inventory
from src.allocators.fcfs import allocate_fcfs
from src.allocators.batch import allocate_batch
from src.simulation.demand_sim import generate_demand


def _make_event() -> Event:
    return Event(
        event_id="evt_test",
        name="Test",
        inventory=Inventory(tiers=[
            Tier(tier_id="tier_0", name="GA", capacity=50, price=75.0),
        ]),
        max_tickets_per_request=4,
        allow_partial_fill=False,
    )


def test_fcfs_deterministic():
    """FCFS with same input must produce identical output."""
    event = _make_event()
    d1 = generate_demand(event, num_fans=100, seed=1)
    d2 = generate_demand(event, num_fans=100, seed=1)
    r1 = allocate_fcfs(event, d1)
    r2 = allocate_fcfs(event, d2)
    assert r1.total_allocated == r2.total_allocated
    assert r1.fill_rate == r2.fill_rate


def test_fcfs_respects_capacity():
    event = _make_event()  # 50 GA seats
    demand = generate_demand(event, num_fans=200, seed=7)
    result = allocate_fcfs(event, demand)
    assert result.total_allocated <= 50


def test_batch_deterministic():
    """Batch with same seed must produce identical output."""
    event = _make_event()
    d1 = generate_demand(event, num_fans=100, seed=1)
    d2 = generate_demand(event, num_fans=100, seed=1)
    r1 = allocate_batch(event, d1, seed=99)
    r2 = allocate_batch(event, d2, seed=99)
    assert r1.total_allocated == r2.total_allocated


def test_batch_respects_capacity():
    event = _make_event()
    demand = generate_demand(event, num_fans=200, seed=7)
    result = allocate_batch(event, demand, seed=7)
    assert result.total_allocated <= 50


def test_batch_revenue_objective():
    event = _make_event()
    demand = generate_demand(event, num_fans=100, seed=5)
    result = allocate_batch(event, demand, seed=5, objective="revenue_at_face_value")
    assert result.objective_used == "revenue_at_face_value"
    assert result.total_allocated <= 50


def test_fcfs_has_explainability():
    event = _make_event()
    demand = generate_demand(event, num_fans=10, seed=1)
    result = allocate_fcfs(event, demand)
    assert len(result.constraints_applied) > 0
    assert result.objective_used != ""


def test_batch_has_explainability():
    event = _make_event()
    demand = generate_demand(event, num_fans=10, seed=1)
    result = allocate_batch(event, demand, seed=1)
    assert len(result.constraints_applied) > 0
    assert result.objective_used != ""
