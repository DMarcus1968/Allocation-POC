"""Tests for FCFS and batch allocators."""

from __future__ import annotations

import random

from src.models.event import EventConfig, Pricebook, Section
from src.models.demand import TicketRequest
from src.allocators.fcfs import allocate_fcfs
from src.allocators.batch import allocate_batch


def _make_event() -> EventConfig:
    return EventConfig(
        event_id="test",
        name="Test Event",
        venue="Test Venue",
        sections=[
            Section("sec_a", "Section A", 10),
            Section("sec_b", "Section B", 20),
        ],
        pricebook=Pricebook(prices={"sec_a": 100.0, "sec_b": 50.0}),
        constraints={"per_account_cap": 4, "group_size_cap": 6},
    )


def _make_requests(n: int = 5) -> list[TicketRequest]:
    return [
        TicketRequest(
            account_id=f"acct_{i}",
            qty_requested=2,
            section_preferences=["sec_a", "sec_b"],
            arrival_order=i,
        )
        for i in range(n)
    ]


class TestFCFS:
    def test_basic_allocation(self):
        event = _make_event()
        requests = _make_requests(3)
        result = allocate_fcfs(event, requests)
        assert len(result.allocations) == 3
        assert len(result.rejections) == 0

    def test_overflow(self):
        event = _make_event()
        # 20 requests × 2 tickets = 40, but total capacity = 30
        requests = _make_requests(20)
        result = allocate_fcfs(event, requests)
        total_allocated = sum(a.qty_allocated for a in result.allocations)
        assert total_allocated <= 30
        assert len(result.rejections) > 0

    def test_arrival_order_respected(self):
        event = _make_event()
        requests = _make_requests(5)
        result = allocate_fcfs(event, requests)
        # First accounts should be allocated first
        allocated_ids = [a.account_id for a in result.allocations]
        assert allocated_ids[0] == "acct_0"


class TestBatch:
    def test_basic_allocation(self):
        event = _make_event()
        requests = _make_requests(3)
        rng = random.Random(42)
        result = allocate_batch(event, requests, rng=rng)
        assert len(result.allocations) > 0

    def test_per_account_cap(self):
        event = _make_event()
        # One account requests many tickets
        requests = [
            TicketRequest(
                account_id="acct_0",
                qty_requested=2,
                section_preferences=["sec_a", "sec_b"],
                arrival_order=i,
            )
            for i in range(5)
        ]
        rng = random.Random(42)
        result = allocate_batch(event, requests, knobs={"per_account_cap": 4}, rng=rng)
        total_for_acct = sum(
            a.qty_allocated for a in result.allocations if a.account_id == "acct_0"
        )
        assert total_for_acct <= 4

    def test_holdback(self):
        event = _make_event()
        requests = _make_requests(3)
        rng = random.Random(42)
        result_no_holdback = allocate_batch(event, requests, knobs={"holdback_pct": 0.0}, rng=random.Random(42))
        result_holdback = allocate_batch(event, requests, knobs={"holdback_pct": 0.5}, rng=random.Random(42))
        # With 50% holdback, effective capacity is halved
        total_hb = sum(a.qty_allocated for a in result_holdback.allocations)
        total_no = sum(a.qty_allocated for a in result_no_holdback.allocations)
        assert total_hb <= total_no

    def test_debug_output(self):
        event = _make_event()
        requests = _make_requests(3)
        rng = random.Random(42)
        result = allocate_batch(event, requests, rng=rng)
        assert "binding_counts" in result.debug
        assert "remaining_inventory" in result.debug

    def test_determinism(self):
        event = _make_event()
        requests = _make_requests(10)
        r1 = allocate_batch(event, requests, rng=random.Random(42))
        r2 = allocate_batch(event, requests, rng=random.Random(42))
        allocs1 = [(a.account_id, a.section_id, a.qty_allocated) for a in r1.allocations]
        allocs2 = [(a.account_id, a.section_id, a.qty_allocated) for a in r2.allocations]
        assert allocs1 == allocs2
