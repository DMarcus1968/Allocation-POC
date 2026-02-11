"""Scenario model for Phase 2B.

A Scenario captures a named set of allocation knobs, a seed policy,
and references to an event/demand/pricebook configuration.  Scenarios
are the unit of comparison in the tradeoff dashboard.

Pricing is NOT part of the scenario; the pricebook reference is
read-only and never edited through the scenario interface.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime


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

    def compute_checksum(self) -> str:
        """Stable hash of knobs + seed_policy + references.

        Uses sorted JSON serialization for determinism.
        """
        payload = {
            "knobs": self.knobs,
            "seed_policy": self.seed_policy,
            "references": self.references,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()

    def update_checksum(self) -> None:
        self.checksum = self.compute_checksum()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "locked": self.locked,
            "knobs": self.knobs,
            "seed_policy": self.seed_policy,
            "references": self.references,
            "checksum": self.checksum,
        }

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
            seed_policy=d.get("seed_policy", {"mode": "common", "seed": 42}),
            references=d.get("references", {}),
            checksum=d.get("checksum", ""),
        )
