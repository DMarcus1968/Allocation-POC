"""
Ticket Allocation Engine - Core simulation and allocation logic.

This module implements a request-based allocation model that replaces
first-come-first-served ticket sales with fair, explainable allocation.
"""

import random
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Section:
    name: str
    capacity: int
    price: float


@dataclass
class Event:
    name: str
    venue: str
    sections: list
    max_tickets_per_person: int = 4

    @property
    def total_capacity(self):
        return sum(s["capacity"] for s in self.sections)


@dataclass
class FanRequest:
    fan_id: str
    preferred_section: str
    quantity: int
    max_price: float
    signup_order: int  # order in which they registered (not speed-based)
    fan_type: str = "general"  # general, verified_fan, presale


@dataclass
class AllocationResult:
    fan_id: str
    section: str
    quantity: int
    price_per_ticket: float
    total_price: float
    status: str  # "allocated", "waitlist", "rejected"
    reason: str = ""


def generate_synthetic_demand(event, demand_multiplier=1.5, seed=None):
    """
    Generate synthetic fan demand for an event.

    Args:
        event: Event configuration
        demand_multiplier: How much demand exceeds supply (1.5 = 50% oversold)
        seed: Random seed for reproducibility
    """
    if seed is not None:
        random.seed(seed)

    total_demand = int(event.total_capacity * demand_multiplier)

    # Build section lookup
    section_map = {s["name"]: s for s in event.sections}
    section_names = [s["name"] for s in event.sections]

    # Fan type distribution
    fan_types = []
    fan_types += ["verified_fan"] * int(total_demand * 0.20)
    fan_types += ["presale"] * int(total_demand * 0.15)
    fan_types += ["general"] * (total_demand - len(fan_types))
    random.shuffle(fan_types)

    requests = []
    for i in range(total_demand):
        # Preference weighted toward cheaper sections (more realistic)
        weights = []
        for s in event.sections:
            # Lower price = higher demand weight
            base_weight = 1.0 / (s["price"] / 100)
            weights.append(base_weight)

        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        preferred = random.choices(section_names, weights=weights, k=1)[0]
        section_price = section_map[preferred]["price"]

        # Willingness to pay: normally distributed around section price
        # Some fans willing to pay more, some less
        wtp_factor = random.gauss(1.0, 0.25)
        wtp_factor = max(0.5, min(2.0, wtp_factor))
        max_price = round(section_price * wtp_factor, 2)

        quantity = random.choices([1, 2, 3, 4], weights=[0.15, 0.45, 0.25, 0.15], k=1)[0]
        quantity = min(quantity, event.max_tickets_per_person)

        requests.append(FanRequest(
            fan_id=f"FAN-{i+1:05d}",
            preferred_section=preferred,
            quantity=quantity,
            max_price=max_price,
            signup_order=i + 1,
            fan_type=fan_types[i] if i < len(fan_types) else "general",
        ))

    random.shuffle(requests)  # Remove any ordering bias
    return requests


def allocate_fcfs(event, requests):
    """
    First-Come-First-Served allocation (baseline for comparison).
    Allocates in signup_order - whoever registered first gets priority.
    """
    sorted_requests = sorted(requests, key=lambda r: r.signup_order)
    section_remaining = {s["name"]: s["capacity"] for s in event.sections}
    section_price = {s["name"]: s["price"] for s in event.sections}

    results = []
    for req in sorted_requests:
        section = req.preferred_section
        price = section_price[section]

        if req.max_price < price:
            results.append(AllocationResult(
                fan_id=req.fan_id, section=section, quantity=0,
                price_per_ticket=price, total_price=0,
                status="rejected",
                reason=f"Willingness to pay (${req.max_price:.2f}) below section price (${price:.2f})"
            ))
        elif section_remaining[section] >= req.quantity:
            section_remaining[section] -= req.quantity
            results.append(AllocationResult(
                fan_id=req.fan_id, section=section, quantity=req.quantity,
                price_per_ticket=price, total_price=price * req.quantity,
                status="allocated",
                reason="Allocated in registration order"
            ))
        else:
            available = section_remaining[section]
            if available > 0:
                section_remaining[section] = 0
                results.append(AllocationResult(
                    fan_id=req.fan_id, section=section, quantity=available,
                    price_per_ticket=price, total_price=price * available,
                    status="allocated",
                    reason=f"Partial allocation: requested {req.quantity}, received {available} (section filled)"
                ))
            else:
                results.append(AllocationResult(
                    fan_id=req.fan_id, section=section, quantity=0,
                    price_per_ticket=price, total_price=0,
                    status="waitlist",
                    reason="Section sold out before this fan's turn in queue"
                ))

    return results, _build_explanation("First-Come-First-Served", event, requests, results)


def allocate_lottery(event, requests, seed=None):
    """
    Random lottery allocation - every eligible fan has equal chance.
    Removes speed advantage entirely.
    """
    if seed is not None:
        random.seed(seed)

    shuffled = list(requests)
    random.shuffle(shuffled)

    section_remaining = {s["name"]: s["capacity"] for s in event.sections}
    section_price = {s["name"]: s["price"] for s in event.sections}

    results = []
    for req in shuffled:
        section = req.preferred_section
        price = section_price[section]

        if req.max_price < price:
            results.append(AllocationResult(
                fan_id=req.fan_id, section=section, quantity=0,
                price_per_ticket=price, total_price=0,
                status="rejected",
                reason=f"Willingness to pay (${req.max_price:.2f}) below section price (${price:.2f})"
            ))
        elif section_remaining[section] >= req.quantity:
            section_remaining[section] -= req.quantity
            results.append(AllocationResult(
                fan_id=req.fan_id, section=section, quantity=req.quantity,
                price_per_ticket=price, total_price=price * req.quantity,
                status="allocated",
                reason="Won random lottery draw"
            ))
        else:
            available = section_remaining[section]
            if available > 0:
                section_remaining[section] = 0
                results.append(AllocationResult(
                    fan_id=req.fan_id, section=section, quantity=available,
                    price_per_ticket=price, total_price=price * available,
                    status="allocated",
                    reason=f"Partial allocation via lottery: requested {req.quantity}, received {available}"
                ))
            else:
                results.append(AllocationResult(
                    fan_id=req.fan_id, section=section, quantity=0,
                    price_per_ticket=price, total_price=0,
                    status="waitlist",
                    reason="Section sold out - unlucky in lottery draw"
                ))

    return results, _build_explanation("Random Lottery", event, requests, results)


def allocate_tiered_priority(event, requests, seed=None):
    """
    Tiered priority allocation - verified fans and presale get priority,
    then lottery within each tier. Balances fairness with fan engagement.
    """
    if seed is not None:
        random.seed(seed)

    tier_order = {"verified_fan": 0, "presale": 1, "general": 2}
    sorted_requests = sorted(requests, key=lambda r: (tier_order.get(r.fan_type, 2), random.random()))

    section_remaining = {s["name"]: s["capacity"] for s in event.sections}
    section_price = {s["name"]: s["price"] for s in event.sections}

    results = []
    for req in sorted_requests:
        section = req.preferred_section
        price = section_price[section]

        if req.max_price < price:
            results.append(AllocationResult(
                fan_id=req.fan_id, section=section, quantity=0,
                price_per_ticket=price, total_price=0,
                status="rejected",
                reason=f"Willingness to pay (${req.max_price:.2f}) below section price (${price:.2f})"
            ))
        elif section_remaining[section] >= req.quantity:
            section_remaining[section] -= req.quantity
            tier_label = req.fan_type.replace("_", " ").title()
            results.append(AllocationResult(
                fan_id=req.fan_id, section=section, quantity=req.quantity,
                price_per_ticket=price, total_price=price * req.quantity,
                status="allocated",
                reason=f"Allocated via {tier_label} tier priority"
            ))
        else:
            available = section_remaining[section]
            if available > 0:
                section_remaining[section] = 0
                results.append(AllocationResult(
                    fan_id=req.fan_id, section=section, quantity=available,
                    price_per_ticket=price, total_price=price * available,
                    status="allocated",
                    reason=f"Partial allocation in {req.fan_type} tier: requested {req.quantity}, received {available}"
                ))
            else:
                results.append(AllocationResult(
                    fan_id=req.fan_id, section=section, quantity=0,
                    price_per_ticket=price, total_price=0,
                    status="waitlist",
                    reason=f"Section sold out before reaching this fan in {req.fan_type} tier"
                ))

    return results, _build_explanation("Tiered Priority", event, requests, results)


def allocate_access_maximizing(event, requests, seed=None):
    """
    Access-maximizing allocation - prioritizes getting tickets to as many
    unique fans as possible. Reduces quantity per fan when demand is high.
    """
    if seed is not None:
        random.seed(seed)

    shuffled = list(requests)
    random.shuffle(shuffled)

    section_remaining = {s["name"]: s["capacity"] for s in event.sections}
    section_price = {s["name"]: s["price"] for s in event.sections}

    # Calculate demand ratio per section
    section_demand = {}
    for req in requests:
        section_demand[req.preferred_section] = section_demand.get(req.preferred_section, 0) + req.quantity

    results = []
    for req in shuffled:
        section = req.preferred_section
        price = section_price[section]

        if req.max_price < price:
            results.append(AllocationResult(
                fan_id=req.fan_id, section=section, quantity=0,
                price_per_ticket=price, total_price=0,
                status="rejected",
                reason=f"Willingness to pay (${req.max_price:.2f}) below section price (${price:.2f})"
            ))
            continue

        # Cap quantity to spread access - if demand > 2x supply, limit to 2 tickets
        demand_ratio = section_demand.get(section, 0) / max(1, section_remaining.get(section, 1) + (
            sum(r.quantity for r in results if r.section == section and r.status == "allocated")
        ))
        cap = req.quantity
        if demand_ratio > 3:
            cap = min(req.quantity, 1)
        elif demand_ratio > 2:
            cap = min(req.quantity, 2)

        if section_remaining[section] >= cap:
            section_remaining[section] -= cap
            reason = f"Allocated {cap} tickets (access-maximizing)"
            if cap < req.quantity:
                reason += f" — reduced from {req.quantity} to serve more fans"
            results.append(AllocationResult(
                fan_id=req.fan_id, section=section, quantity=cap,
                price_per_ticket=price, total_price=price * cap,
                status="allocated",
                reason=reason,
            ))
        else:
            available = section_remaining[section]
            if available > 0:
                section_remaining[section] = 0
                results.append(AllocationResult(
                    fan_id=req.fan_id, section=section, quantity=available,
                    price_per_ticket=price, total_price=price * available,
                    status="allocated",
                    reason=f"Partial: received {available} of {req.quantity} requested (section filling up)"
                ))
            else:
                results.append(AllocationResult(
                    fan_id=req.fan_id, section=section, quantity=0,
                    price_per_ticket=price, total_price=0,
                    status="waitlist",
                    reason="Section sold out"
                ))

    return results, _build_explanation("Access Maximizing", event, requests, results)


def _build_explanation(strategy_name, event, requests, results):
    """Build a plain-language explanation of the allocation outcome."""
    allocated = [r for r in results if r.status == "allocated"]
    waitlisted = [r for r in results if r.status == "waitlist"]
    rejected = [r for r in results if r.status == "rejected"]

    total_tickets_sold = sum(r.quantity for r in allocated)
    total_revenue = sum(r.total_price for r in allocated)
    unique_fans_served = len(allocated)
    total_fans = len(requests)

    # Per-section breakdown
    section_stats = {}
    for s in event.sections:
        name = s["name"]
        sec_allocated = [r for r in allocated if r.section == name]
        sec_waitlisted = [r for r in waitlisted if r.section == name]
        sec_demand = [req for req in requests if req.preferred_section == name]
        section_stats[name] = {
            "capacity": s["capacity"],
            "price": s["price"],
            "tickets_sold": sum(r.quantity for r in sec_allocated),
            "fans_served": len(sec_allocated),
            "fans_waitlisted": len(sec_waitlisted),
            "total_demand_tickets": sum(req.quantity for req in sec_demand),
            "total_demand_fans": len(sec_demand),
            "revenue": sum(r.total_price for r in sec_allocated),
            "fill_rate": round(sum(r.quantity for r in sec_allocated) / max(1, s["capacity"]) * 100, 1),
        }

    # Fan type breakdown
    fan_type_stats = {}
    for ft in ["verified_fan", "presale", "general"]:
        ft_requests = [r for r in requests if r.fan_type == ft]
        ft_allocated = [r for r in allocated if any(
            req.fan_id == r.fan_id and req.fan_type == ft for req in requests
        )]
        fan_type_stats[ft] = {
            "total_requests": len(ft_requests),
            "fans_served": len(ft_allocated),
            "success_rate": round(len(ft_allocated) / max(1, len(ft_requests)) * 100, 1),
        }

    return {
        "strategy": strategy_name,
        "summary": {
            "total_requests": total_fans,
            "total_capacity": event.total_capacity,
            "demand_to_supply_ratio": round(sum(r.quantity for r in requests) / max(1, event.total_capacity), 2),
            "tickets_sold": total_tickets_sold,
            "unique_fans_served": unique_fans_served,
            "fans_waitlisted": len(waitlisted),
            "fans_rejected": len(rejected),
            "total_revenue": round(total_revenue, 2),
            "fill_rate": round(total_tickets_sold / max(1, event.total_capacity) * 100, 1),
            "fan_success_rate": round(unique_fans_served / max(1, total_fans) * 100, 1),
        },
        "sections": section_stats,
        "fan_types": fan_type_stats,
        "constraints_applied": [
            f"Max {event.max_tickets_per_person} tickets per person",
            "Section prices set by rights owner (hard constraint)",
            "Section capacities set by venue/rights owner (hard constraint)",
        ],
        "objective": _get_objective_description(strategy_name),
        "alternatives_considered": _get_alternatives(strategy_name),
    }


def _get_objective_description(strategy):
    descriptions = {
        "First-Come-First-Served": "Allocate tickets in registration order. Objective: serve fans who signed up earliest. No optimization applied.",
        "Random Lottery": "Allocate tickets by random draw among all eligible fans. Objective: equal opportunity regardless of registration timing.",
        "Tiered Priority": "Allocate tickets by fan tier (Verified Fan > Presale > General), with lottery within each tier. Objective: reward engaged fans while maintaining fairness.",
        "Access Maximizing": "Maximize the number of unique fans who receive tickets, reducing per-fan quantity when demand is high. Objective: maximize access breadth.",
    }
    return descriptions.get(strategy, "")


def _get_alternatives(strategy):
    all_strategies = {
        "First-Come-First-Served": "Rewards early registration but creates race conditions and speed-based unfairness.",
        "Random Lottery": "Maximally fair in opportunity but does not reward fan engagement or loyalty.",
        "Tiered Priority": "Balances fairness with fan loyalty but may feel exclusionary to general fans.",
        "Access Maximizing": "Serves the most fans but reduces ticket quantity per person, which may frustrate groups.",
    }
    alternatives = []
    for name, desc in all_strategies.items():
        if name != strategy:
            alternatives.append({"strategy": name, "tradeoff": desc})
    return alternatives


def run_comparison(event, requests, seed=42):
    """Run all allocation strategies and return comparative results."""
    results = {}

    fcfs_results, fcfs_explanation = allocate_fcfs(event, requests)
    results["fcfs"] = {"results": fcfs_results, "explanation": fcfs_explanation}

    lottery_results, lottery_explanation = allocate_lottery(event, requests, seed=seed)
    results["lottery"] = {"results": lottery_results, "explanation": lottery_explanation}

    tiered_results, tiered_explanation = allocate_tiered_priority(event, requests, seed=seed)
    results["tiered"] = {"results": tiered_results, "explanation": tiered_explanation}

    access_results, access_explanation = allocate_access_maximizing(event, requests, seed=seed)
    results["access"] = {"results": access_results, "explanation": access_explanation}

    return results
