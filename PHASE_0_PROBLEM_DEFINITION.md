# Phase 0 — Problem Definition

## 1. Context

This document defines the problem space for a **request-based ticket allocation prototype** that replaces real-time first-come-first-served (FCFS) ticket sales with a structured allocation model.

The platform (Ticketmaster) operates as an **allocation engine**. It does not control pricing, inventory release strategy, or onsale timing. Those decisions belong to **rights owners** (concert promoters, artists, teams).

## 2. Stakeholders

| Stakeholder | Role |
|---|---|
| **Rights Owner (Promoter)** | Defines all hard constraints: pricing tiers, capacity per tier, purchase limits, group-size policies, and any access restrictions. |
| **Fan** | Submits a request specifying desired tier, quantity, and group composition. Does **not** compete on speed. |
| **Platform** | Executes allocation logic within promoter-defined constraints. Produces explainable outcomes. |

## 3. Problem Statement

Traditional FCFS ticket sales create race-condition dynamics, reward speed over genuine demand, and produce opaque outcomes. This prototype explores whether a **request-collection-then-allocation** model can:

- Reduce race-condition dynamics
- Improve predictability and transparency for rights owners
- Improve perceived fairness and usability for fans
- Produce outcomes that are explainable to non-technical audiences

## 4. Hard Constraints (Promoter-Defined)

The following constraints are defined by the rights owner and treated as **inviolable** by the allocation engine. They are never suggestions or soft preferences.

| ID | Constraint | Description |
|---|---|---|
| **HC-1** | **Tier Capacity** | Each pricing tier has a fixed seat count. The system must never allocate more tickets in a tier than the capacity allows. |
| **HC-2** | **Per-Request Limit** | Maximum number of tickets a single request may receive (e.g., max 4 per request). |
| **HC-3** | **Group Integrity** | A group request must be fulfilled entirely or not at all. Partial fills are not permitted. |
| **HC-4** | **Tier Eligibility** | A request targets a specific tier. The system does not reassign requests across tiers unless explicitly configured by the promoter. |
| **HC-5** | **Singles Policy** | The promoter defines whether single-ticket requests are accepted and under what conditions (e.g., only as filler after group allocation). |

## 5. What the System Does NOT Do

- **Does not set prices.** Prices are promoter inputs.
- **Does not optimize revenue by default.** Revenue optimization requires explicit promoter selection as an objective.
- **Does not use arrival time as an allocation factor.** Requests are collected over a window; order of arrival is irrelevant to allocation.
- **Does not guarantee allocation.** Demand may exceed supply; some requests will be rejected.
- **Does not solve seat-level adjacency.** Seat assignment within a tier is out of scope for this prototype.

## 6. Objective Function

The system does **not** assume a default objective. The promoter must explicitly select one of:

| Objective | Description |
|---|---|
| **Maximize Access** | Serve the greatest number of distinct requests (fans). |
| **Maximize Revenue** | Allocate to maximize total ticket revenue within constraints. |
| **Hybrid** | Weighted combination of access and revenue, with weights defined by the promoter. |

If no objective is specified, the system must **halt and request clarification** rather than assuming one.

## 7. Fairness Model

This prototype uses a **lottery-based fairness model**:

- All requests submitted within the request window are treated equally regardless of submission time.
- Selection among equally eligible requests is resolved by random lottery.
- The system does not use fan history, loyalty status, or spending patterns as allocation inputs unless the promoter explicitly configures such criteria.

## 8. Allocation Phases

| Phase | Description |
|---|---|
| **Phase 1A** | Demand Model — Generate synthetic fan populations and requests. |
| **Phase 1B** | FCFS Baseline — Simulate traditional first-come-first-served processing as a comparison baseline. |
| **Phase 1C** | Allocation Solver — Implement request-based allocation with hard constraints, explainability, and objective-function discipline. |

## 9. Success Criteria

The prototype succeeds if it can demonstrate, in simulation, that request-based allocation:

1. Produces superior outcomes to FCFS on at least one metric (access, fairness, transparency).
2. Enforces all promoter-defined hard constraints without violation.
3. Produces a human-readable explanation for every allocation and rejection.
4. Avoids introducing implicit assumptions about revenue optimization, arrival time, or fairness that were not explicitly configured.
