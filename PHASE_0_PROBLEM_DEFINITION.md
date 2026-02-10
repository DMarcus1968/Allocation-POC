# Phase 0 — Problem Definition

## Purpose

This document defines the core problem that the Allocation POC addresses: the structural limitations of first-come-first-served (FCFS) ticket sales and the potential for a batch-allocation mechanism to produce superior outcomes under identical constraints.

## Context

In the current live-entertainment ticketing ecosystem, tickets for high-demand events are sold via FCFS queues. The rights owner (promoter, artist, team) sets all constraints — pricing, inventory tiers, onsale timing, and release strategy. The platform (Ticketmaster) executes the sale within those constraints.

FCFS was designed for moderate-demand scenarios. Under excess demand, it produces well-documented failure modes that harm both rights owners and fans.

## Failure Modes of FCFS Under Excess Demand

| Failure Mode | Description |
|---|---|
| Race-condition dynamics | Outcome determined by network latency, device speed, and queue-entry timing rather than fan preference or willingness to pay |
| Binary success/failure cliffs | Fans with nearly identical arrival times experience completely different outcomes (full allocation vs. total shutout) |
| No demand visibility | Rights owner cannot observe aggregate demand shape before committing inventory |
| Suboptimal revenue capture | High-WTP fans may be shut out while low-WTP fans succeed, leaving revenue on the table within the rights owner's own pricing structure |
| Poor fan experience | Anxiety, frustration, and perception of unfairness driven by speed-based competition |
| Inventory fragmentation | Partial fills and odd-lot remainders accumulate in less desirable tiers |

## What This POC Explores

This prototype compares two mechanisms under identical demand and constraint conditions:

1. **FCFS Baseline (Phase 1B):** Simulates a traditional queue-based sale where fans arrive in a random order and are served sequentially until inventory is exhausted.

2. **Batch Allocation (Phase 1C):** Collects all requests in a window, then uses an optimization solver to allocate inventory across the full request set simultaneously.

Both mechanisms operate under the same:
- Demand population (Phase 1A)
- Inventory constraints (tier capacities, price points)
- Request characteristics (group sizes, tier preferences)

## What This POC Does NOT Explore

- Dynamic or variable pricing (prices are fixed by the rights owner)
- Seat-level adjacency or view-quality optimization
- Resale market effects
- Production-ready system design
- Multi-event or season-ticket allocation
- Real-world queue infrastructure (bot mitigation, verified fan, etc.)

## Governance Constraints

All allocation decisions are made **within** the constraints set by the rights owner:

- The platform does not set prices
- The platform does not decide inventory release strategy
- The platform does not override tier capacity limits
- The objective function used in allocation is explicitly stated and auditable

## Success Criteria

The POC is considered informative (not "successful" in a normative sense) if:

1. Both mechanisms can be simulated under identical conditions
2. Outcome differences can be attributed to mechanism design rather than parameter tuning
3. Tradeoffs between mechanisms are surfaced transparently
4. Results are explainable to a non-technical audience
