# Phase 1C: Allocation Solver

## Overview

Phase 1C defines the core allocation solver that processes a batch of ticket requests against available inventory, subject to promoter-defined constraints. The solver operates on a request-based model (not first-come-first-served) and must produce explainable, auditable results.

## Inputs

- **Inventory**: A set of ticket pools, each with a defined capacity.
- **Requests**: A batch of fan requests, each specifying a desired quantity (1..N) and applicable pool.
- **Constraints**: Promoter-defined hard constraints (e.g., max per-customer limits, pool caps, hold-backs).

## Objective Function

The solver selects a feasible subset of requests that maximizes the number of fulfilled requests (or another explicitly specified objective), subject to all hard constraints. The objective function must be explicitly stated for each run and is not modified by ordering or tie-break logic.

## Allocation Order Policy (Groups-First; Singles-Last)

Before the solver evaluates tie-breaks, requests are partitioned and ordered as follows:

1. **Partitioning**: Requests are partitioned into two classes:
   - **Group** requests: quantity >= 2.
   - **Single** requests: quantity == 1.

2. **Processing order**: All Group requests are processed before any Single requests. The solver completes the full group-allocation pass first, then proceeds to singles.

3. **Non-displacement guarantee**: Single requests are processed last and are never used to displace feasible group allocations. A group allocation that is feasible at the end of the group pass remains in the solution.

4. **Singles-as-filler (opt-in only)**: If the model supports a "singles-as-filler" mode (filling residual gaps left after the group pass), this behaviour is opt-in only and applies exclusively after the group pass has completed.

## Tie-Break Policy (applies within the current partition/order step)

When multiple requests of equal priority compete for the same constrained inventory within a given partition step, ties are broken using the following cascade:

1. **Randomized lottery** (default): Each tied request receives an equal probability of selection.
2. **Weighted lottery** (if configured by the promoter): Requests are weighted by a promoter-supplied priority score.
3. **Deterministic fallback**: If a stable ordering is needed for reproducibility, ties are broken by request ID (lexicographic).

The tie-break policy is applied independently within the group pass and within the single pass. It does not influence the ordering between partitions.

## Feasibility and Rejection

- Every rejected request must include a reason code (e.g., `CAPACITY_EXCEEDED`, `CONSTRAINT_VIOLATED`).
- The solver must enumerate at least the top alternative allocation considered, with an explanation of why it was not selected.

## Output

- A list of fulfilled requests with assigned inventory.
- A list of rejected requests with reason codes.
- Summary statistics: fill rate, requests fulfilled by partition (group vs. single), and capacity utilisation.
