# Phase 1B: FCFS Baseline Simulation

## Overview

Phase 1B defines the first-come-first-served (FCFS) baseline against which alternative allocation mechanisms are evaluated. The baseline reproduces the standard real-time queue model with deterministic rule enforcement, including all promoter-defined hard constraints.

## Inputs

- **Inventory**: A set of ticket pools, each with a defined capacity.
- **Requests**: An ordered sequence of fan requests, each specifying a desired quantity and applicable pool. Requests arrive in strict chronological (arrival-time) order.
- **Constraints**: Promoter-defined hard constraints, including per-entity ticket limits and pool caps.

## Processing Rules

### Arrival Order

Requests are processed sequentially in arrival order. There is no batching, randomisation, or re-ordering; the first request to arrive is the first request evaluated.

### All-or-Nothing Fulfilment

Each request is evaluated atomically against available inventory:

- If the full requested quantity can be satisfied without violating any constraint, the request is **fulfilled**.
- If the full requested quantity cannot be satisfied (insufficient inventory or constraint violation), the request is **rejected** in its entirety. Partial fills are not issued.

### Per-Entity Ticket Limit (Hard Constraint)

The promoter may set a maximum number of tickets that any single entity (identified by `entity_id`) may be allocated across all requests for a given event. This limit is enforced deterministically as follows:

1. **State tracking**: The simulation maintains a running map `tickets_allocated_by_entity_id`, initialised to zero for each entity at the start of the run.

2. **Limit check**: When a request from `entity_id` for quantity `q` is evaluated, the simulation computes:
   ```
   remaining = per_entity_limit - tickets_allocated_by_entity_id[entity_id]
   ```

3. **Enforcement**:
   - If `q <= remaining` and pool capacity is sufficient, the request is **fulfilled** and `tickets_allocated_by_entity_id[entity_id]` is incremented by `q`.
   - If `q > remaining`, the request is **rejected** (reason: `PER_ENTITY_LIMIT_EXCEEDED`). The request is not truncated to `remaining`; all-or-nothing semantics apply.

4. **Scope**: The limit applies across all requests from the same `entity_id` within a single event, regardless of pool.

### Pool Capacity

Each pool has a fixed capacity. A request is rejected if fulfilling it would exceed the pool's remaining capacity (reason: `CAPACITY_EXCEEDED`).

## Output

- A list of fulfilled requests with assigned inventory.
- A list of rejected requests with reason codes (`CAPACITY_EXCEEDED`, `PER_ENTITY_LIMIT_EXCEEDED`).
- Summary statistics: fill rate, rejection breakdown by reason, and capacity utilisation per pool.

## Scope Boundaries

This baseline intentionally does **not** include:

- Batching, lottery, or priority-based ordering.
- Dynamic pricing or yield optimisation.
- Group-vs-single partitioning or tie-breaking logic.

These are reserved for alternative allocation mechanisms (Phase 1C and beyond) and compared against this baseline in evaluation.
