"""Allocation result models shared across allocator implementations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Allocation:
    account_id: str
    section_id: str
    qty_allocated: int


@dataclass
class Rejection:
    account_id: str
    reason: str
    qty_requested: int


@dataclass
class AllocationResult:
    allocations: list[Allocation] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)
    debug: dict = field(default_factory=dict)
