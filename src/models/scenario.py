"""Scenario model for Phase 2B.

A Scenario captures a named set of allocation knobs, a seed policy,
and references to an event/demand/pricebook configuration.  Scenarios
are the unit of comparison in the tradeoff dashboard.

Knobs are split into two explicit categories:
  - **promoter_constraints**: rules set by the promoter/rights-owner
    (per_account_cap, holdback_pct, group_size_cap, section_eligibility,
    presale_split).  These are hard constraints.
  - **allocation_policy**: controls for how requests are processed
    within those constraints (priority_mode, singles_avoidance, etc.).
    Still promoter-chosen but labelled as policy.

Pricing is NOT part of the scenario; the pricebook reference is
read-only and never edited through the scenario interface.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime


# Keys that map to promoter hard constraints
PROMOTER_CONSTRAINT_KEYS: frozenset[str] = frozenset({
    "per_account_cap",
    "holdback_pct",
    "group_size_cap",
    "section_eligibility",
    "presale_split",
})


def split_knobs(knobs: dict) -> tuple[dict, dict]:
    """Split a flat knobs dict into (promoter_constraints, allocation_policy)."""
    promoter: dict = {}
    policy: dict = {}
    for k, v in sorted(knobs.items()):
        if k in PROMOTER_CONSTRAINT_KEYS:
            promoter[k] = v
        else:
            policy[k] = v
    return promoter, policy


def merge_knobs(promoter: dict, policy: dict) -> dict:
    """Merge promoter constraints and allocation policy into a flat knobs dict."""
    merged = {}
    merged.update(promoter)
    merged.update(policy)
    return merged


@dataclass
class Scenario:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str | None = None
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    locked: bool = False
    knobs: dict = field(default_factory=dict)
    knobs_promoter_constraints: dict = field(default_factory=dict)
    knobs_allocation_policy: dict = field(default_factory=dict)
    seed_policy: dict = field(
        default_factory=lambda: {"mode": "common", "seed": 42}
    )
    references: dict = field(
        default_factory=lambda: {
            "event_ref": "demo_event",
            "demand_config_ref": "default",
            "pricebook_ref": "read_only_default",
        }
    )
    checksum: str = ""

    # Freeze metadata — populated when scenario is locked
    frozen_references: bool = False
    frozen_at: str | None = None
    frozen_by: str | None = None
    reference_hashes: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure knobs, promoter_constraints, and allocation_policy stay in sync."""
        self._sync_knobs()

    def _sync_knobs(self) -> None:
        """Reconcile knobs ↔ sub-dicts.

        If sub-dicts are populated, they are authoritative and knobs is rebuilt.
        If only knobs is populated (legacy), auto-split into sub-dicts.
        """
        has_sub = bool(self.knobs_promoter_constraints or self.knobs_allocation_policy)
        has_flat = bool(self.knobs)

        if has_sub:
            # Sub-dicts authoritative → rebuild flat knobs
            self.knobs = merge_knobs(
                self.knobs_promoter_constraints,
                self.knobs_allocation_policy,
            )
        elif has_flat:
            # Legacy flat knobs → auto-split
            self.knobs_promoter_constraints, self.knobs_allocation_policy = split_knobs(
                self.knobs
            )
        # else: all empty, nothing to do

    def compute_checksum(self) -> str:
        """Stable hash of knobs + seed_policy + references.

        Uses sorted JSON serialization for determinism.  Checksum is
        computed from the categorized sub-dicts so that
        ``split_knobs(knobs)`` order doesn't matter.
        """
        payload = {
            "knobs_promoter_constraints": self.knobs_promoter_constraints,
            "knobs_allocation_policy": self.knobs_allocation_policy,
            "seed_policy": self.seed_policy,
            "references": self.references,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()

    def update_checksum(self) -> None:
        self.checksum = self.compute_checksum()

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "locked": self.locked,
            "knobs": self.knobs,
            "knobs_promoter_constraints": self.knobs_promoter_constraints,
            "knobs_allocation_policy": self.knobs_allocation_policy,
            "seed_policy": self.seed_policy,
            "references": self.references,
            "checksum": self.checksum,
            "frozen_references": self.frozen_references,
            "frozen_at": self.frozen_at,
            "frozen_by": self.frozen_by,
            "reference_hashes": self.reference_hashes,
        }
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Scenario:
        def _parse_dt(val: str | datetime | None) -> datetime:
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                return datetime.fromisoformat(val)
            return datetime.utcnow()

        return cls(
            id=d["id"],
            name=d.get("name", ""),
            description=d.get("description"),
            created_by=d.get("created_by", "system"),
            created_at=_parse_dt(d.get("created_at")),
            updated_at=_parse_dt(d.get("updated_at")),
            locked=d.get("locked", False),
            knobs=d.get("knobs", {}),
            knobs_promoter_constraints=d.get("knobs_promoter_constraints", {}),
            knobs_allocation_policy=d.get("knobs_allocation_policy", {}),
            seed_policy=d.get("seed_policy", {"mode": "common", "seed": 42}),
            references=d.get("references", {}),
            checksum=d.get("checksum", ""),
            frozen_references=d.get("frozen_references", False),
            frozen_at=d.get("frozen_at"),
            frozen_by=d.get("frozen_by"),
            reference_hashes=d.get("reference_hashes", {}),
        )
