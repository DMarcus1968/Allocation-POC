"""Tests for shared data models."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.event import Tier, Inventory, Event
from src.models.demand import FanProfile, Request, DemandPool, RequestStatus
from src.models.allocation import Reservation, AllocationResult
from src.models.metrics import TierMetrics, ScenarioMetrics


def test_tier_creation():
    t = Tier(tier_id="t1", name="GA", capacity=100, price=50.0)
    assert t.capacity == 100
    assert t.price == 50.0


def test_inventory_total_capacity():
    inv = Inventory(tiers=[
        Tier(tier_id="a", name="GA", capacity=100, price=50),
        Tier(tier_id="b", name="VIP", capacity=50, price=150),
    ])
    assert inv.total_capacity == 150


def test_inventory_tier_lookup():
    inv = Inventory(tiers=[
        Tier(tier_id="a", name="GA", capacity=100, price=50),
    ])
    assert inv.tier_by_id("a") is not None
    assert inv.tier_by_id("missing") is None
    assert inv.tier_by_name("GA") is not None


def test_request_status_default():
    fan = FanProfile(fan_id="f1")
    req = Request(fan=fan, tier_id="t1", quantity=2, timestamp_ms=0)
    assert req.status == RequestStatus.PENDING


def test_demand_pool_total():
    fan = FanProfile(fan_id="f1")
    pool = DemandPool(requests=[
        Request(fan=fan, tier_id="t1", quantity=2, timestamp_ms=0),
        Request(fan=fan, tier_id="t1", quantity=3, timestamp_ms=100),
    ])
    assert pool.total_requested == 5


def test_reservation_fill_flags():
    r = Reservation(
        request_id="r1", fan_id="f1", tier_id="t1",
        quantity_requested=4, quantity_allocated=4,
    )
    assert r.is_full_fill is True
    assert r.is_partial_fill is False

    r2 = Reservation(
        request_id="r2", fan_id="f1", tier_id="t1",
        quantity_requested=4, quantity_allocated=2,
    )
    assert r2.is_full_fill is False
    assert r2.is_partial_fill is True


def test_allocation_result_fill_rate():
    res = AllocationResult(
        allocator_name="test",
        event_id="e1",
        reservations=[
            Reservation(
                request_id="r1", fan_id="f1", tier_id="t1",
                quantity_requested=10, quantity_allocated=5,
            ),
        ],
    )
    assert res.fill_rate == 0.5
    assert res.total_allocated == 5
    assert res.total_requested == 10
