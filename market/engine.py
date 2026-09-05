from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import random
from typing import Iterable


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    rank: int
    floor: int
    ceiling: int
    price: int
    capacity: int
    holds: int
    color: str
    vip: bool = False
    block_size: int = 20


@dataclass(frozen=True)
class Request:
    fan_id: str
    quantity: int
    selections: tuple[str, ...]
    cohorts: tuple[str, ...] = ()
    fewer_ok: bool = False
    vip: bool = False
    timestamp: int = 0
    accepted_alternatives: tuple[str, ...] = ()
    latent_wtp: int = 0  # simulation-only; never used to set the price


@dataclass(frozen=True)
class Allocation:
    fan_id: str
    zone: str
    quantity: int
    unit_price: int
    vip: bool
    reason: str
    block: int


DEFAULT_ZONES = (
    Zone("front_floor", "Front Floor", 1, 350, 700, 625, 6500, 700, "#f06449", True),
    Zone("front_lower", "Front Lower Bowl", 2, 250, 650, 475, 9500, 900, "#f49d55", True),
    Zone("mid_floor", "Mid Floor", 3, 300, 500, 425, 6500, 600, "#e9c46a", True),
    Zone("mid_lower", "Mid Lower Bowl", 4, 200, 400, 325, 10500, 800, "#62c6a5", True),
    Zone("rear_floor", "Rear Floor", 5, 250, 350, 325, 6500, 500, "#5ab5d8", True),
    Zone("rear_lower", "Rear Lower Bowl", 6, 150, 300, 245, 10500, 800, "#6f8ee8", True),
    Zone("premium_upper", "Premium Upper", 7, 100, 225, 175, 11000, 600, "#9277d8"),
    Zone("standard_upper", "Standard Upper", 8, 75, 175, 125, 13000, 600, "#bf7fbc"),
)


def validate_prices(zones: Iterable[Zone]) -> list[str]:
    zones = sorted(zones, key=lambda z: z.rank)
    errors = []
    for z in zones:
        if not z.floor <= z.price <= z.ceiling:
            errors.append(f"{z.name}: offered price is outside approved range")
    for better, worse in zip(zones, zones[1:]):
        if worse.price > better.price * 1.20:
            errors.append(f"{worse.name}: irrational inversion versus {better.name}")
    return errors


def _tie(seed: int, fan_id: str) -> int:
    return int.from_bytes(sha256(f"{seed}:{fan_id}".encode()).digest()[:8], "big")


def allocate(requests: Iterable[Request], zones: Iterable[Zone] = DEFAULT_ZONES, seed: int = 41,
             cohort_weights: dict[str, int] | None = None, sponsor_min: int = 0,
             ticket_limit: int = 4, vip_multiplier: float = 3.0) -> tuple[list[Allocation], list[Request]]:
    """Auditable priority + seeded-lottery allocation; arrival time is deliberately absent."""
    zones_by_id = {z.id: z for z in zones}
    if validate_prices(zones_by_id.values()):
        raise ValueError("invalid price architecture")
    remaining = {z.id: z.capacity - z.holds for z in zones_by_id.values()}
    blocks = {}
    for z in zones_by_id.values():
        available = z.capacity - z.holds
        full, tail = divmod(available, z.block_size)
        blocks[z.id] = [z.block_size] * full + ([tail] if tail else [])
    weights = cohort_weights or {"fan_club": 30, "past_buyer": 20, "local": 8, "new_fan": 5, "sponsor": 25}
    unique: dict[str, Request] = {}
    for r in requests:
        unique.setdefault(r.fan_id, r)
    def score(r: Request):
        sponsor = 1 if "sponsor" in r.cohorts and sponsor_min else 0
        return (-sponsor, -sum(weights.get(c, 0) for c in r.cohorts), _tie(seed, r.fan_id))
    ordered = sorted(unique.values(), key=score)
    out, failed = [], []
    sponsor_used = 0
    for r in ordered:
        qty = min(max(r.quantity, 1), ticket_limit)
        choices = r.selections + r.accepted_alternatives
        placed = False
        for zid in choices:
            z = zones_by_id.get(zid)
            if not z or (r.vip and not z.vip):
                continue
            candidate_qty = qty
            while candidate_qty and not any(b >= candidate_qty for b in blocks[zid]):
                candidate_qty = candidate_qty - 1 if r.fewer_ok else 0
            if candidate_qty and remaining[zid] >= candidate_qty:
                bi = next(i for i, b in enumerate(blocks[zid]) if b >= candidate_qty)
                blocks[zid][bi] -= candidate_qty
                remaining[zid] -= candidate_qty  # VIP and standard consume the same pool
                price = round(z.price * vip_multiplier) if r.vip else z.price
                reason = "sponsor minimum" if "sponsor" in r.cohorts and sponsor_used < sponsor_min else "policy score + seeded lottery"
                sponsor_used += candidate_qty if "sponsor" in r.cohorts else 0
                out.append(Allocation(r.fan_id, zid, candidate_qty, price, r.vip, reason, bi))
                placed = True
                break
        if not placed:
            failed.append(r)
    return out, failed


def negotiate(request: Request, zones: Iterable[Zone], remaining: dict[str, int]) -> list[dict]:
    """Structured mock agent: it can only quote approved catalog prices."""
    catalog = sorted(zones, key=lambda z: z.rank)
    proposals = []
    requested_ranks = [z.rank for z in catalog if z.id in request.selections]
    anchor = requested_ranks[0] if requested_ranks else 1
    for z in catalog:
        if z.id not in request.selections and remaining.get(z.id, 0) >= request.quantity and abs(z.rank-anchor) <= 4:
            proposals.append({"zone": z.id, "name": z.name, "quantity": request.quantity,
                              "unit_price": z.price, "message": f"{request.quantity} together in {z.name} at the approved ${z.price} price."})
        if len(proposals) == 3:
            break
    return proposals


def synthetic_summary(seed: int = 2026, fans: int = 500_000, zones: Iterable[Zone] = DEFAULT_ZONES) -> dict:
    """Memory-efficient aggregate population generator at full requested scale."""
    rng = random.Random(seed)
    quantities = {"1": 0, "2": 0, "3": 0, "4": 0}
    demand = {z.id: 0 for z in zones}
    cohorts = {k: 0 for k in ("fan_club", "past_buyer", "merch_buyer", "streaming", "new_fan", "sponsor", "local", "vip_oriented")}
    vip_requests = 0
    total = 0
    zone_list = list(zones)
    qpop = [1, 2, 2, 2, 2, 3, 4, 4]
    for _ in range(fans):
        q = rng.choice(qpop); quantities[str(q)] += 1; total += q
        preferred = min(int(rng.betavariate(1.7, 2.3) * len(zone_list)), len(zone_list)-1)
        demand[zone_list[preferred].id] += q
        for key, p in (("fan_club", .22),("past_buyer", .31),("merch_buyer", .18),("streaming", .42),("new_fan", .27),("sponsor", .12),("local", .38),("vip_oriented", .08)):
            if rng.random() < p: cohorts[key] += 1
        if preferred < 6 and rng.random() < .09: vip_requests += q
    supply = sum(z.capacity-z.holds for z in zone_list)
    return {"seed": seed, "fans": fans, "tickets_requested": total, "available_supply": supply,
            "gross_capacity": sum(z.capacity for z in zone_list), "holds": sum(z.holds for z in zone_list),
            "demand_supply_ratio": round(total/supply, 1), "quantity": quantities, "demand_by_zone": demand,
            "cohorts": cohorts, "vip_demand": vip_requests}


def zone_dicts(zones=DEFAULT_ZONES):
    return [asdict(z) for z in zones]
