# Phase 0 — Problem Definition

## Overview

This document defines the problem space for a ticket allocation and yield optimization prototype. The system replaces real-time, first-come-first-served ticket sales with a request-based allocation model. All allocation decisions are made within constraints specified by rights owners (promoters, artists, teams).

## Objectives

The allocation system aims to:

- Demonstrate superior outcomes to first-come-first-served in simulation
- Reduce race-condition dynamics
- Improve predictability and transparency for rights owners
- Improve perceived fairness and usability for fans

The specific objective function (revenue, access, hybrid) is selected per event by the promoter. The system does not assume a default objective.

## Promoter Constraints (Hard, Inviolable)

The platform treats all promoter-specified constraints as hard constraints. These are never relaxed or overridden by the allocation system.

- Pricing tiers and price points (set by rights owner)
- Inventory caps per tier or section
- Onsale timing and release windows
- Hold-back and allocation reserves (e.g., artist holds, presale pools)
- Eligibility rules (e.g., fan club membership, geographic restrictions)
- Per-entity ticket limit (max tickets per account / identity / household as specified by promoter)

## Inputs and Constraints

### Inputs

- **Demand pool**: Set of fan requests submitted during a request window, each specifying quantity, tier preferences, and willingness-to-pay signals (where applicable)
- **Inventory**: Available ticket inventory segmented by tier, section, and release wave as defined by the promoter
- **Promoter configuration**: Objective function selection, pricing, eligibility rules, per-entity limits, and all hard constraints listed above

### Constraint Enforcement

- The platform enforces all promoter-specified constraints strictly during allocation. No feasible allocation may violate any hard constraint.
- **Per-entity limits**: The platform enforces per-entity limits strictly during allocation. The definition of "entity" is promoter-configurable (e.g., account, payment instrument, household heuristic), but enforcement is required regardless of the entity definition chosen.
- Allocation logic must be explainable in plain language to a non-technical audience.
- If a constraint renders the problem infeasible, the system must surface the conflict and request promoter resolution rather than silently relaxing constraints.

## Assumptions

- Fan demand is modeled using synthetic populations (no proprietary data).
- Willingness-to-pay distributions are estimated, not observed.
- Perfect information and frictionless markets are not assumed.
- All outputs are experimental and revisable.

## Out of Scope

- Production-ready system design
- Seat-level adjacency or view optimization (unless explicitly requested)
- Resale market optimization
- Real-time bidding or auction mechanics (unless explicitly requested)
