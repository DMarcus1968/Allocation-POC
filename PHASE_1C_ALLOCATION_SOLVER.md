# Phase 1C — Allocation Solver (Fulfillment-Maximizing Baseline)

## Purpose

This document defines a batch-based ticket allocation algorithm that
serves as the first alternative to the FCFS baseline defined in
Phase 1B. The solver operates on the same demand inputs (Phase 1A)
and the same promoter-defined constraints (Phase 0), but removes
arrival-time ordering entirely. Allocation decisions are made after
all requests have been collected, treating them as a single batch.

The goal is not optimality. The goal is to demonstrate that removing
race conditions and allocating in batch can materially improve
outcomes under identical demand conditions.

---

## 1. Objective Function

### 1.1 Formal Definition

Let:

- `R` = the set of all fan requests in the batch
- `x_r ∈ {0, 1}` = binary decision variable: 1 if request `r` is fulfilled, 0 otherwise
- `q_r` = the ticket quantity requested by request `r`
- `C_t` = the capacity (available inventory) for tier `t`
- `T(r)` = the tier requested by request `r`

**Objective:**

```
Maximize  Σ (x_r · q_r)  for all r ∈ R
```

**Subject to:**

```
Σ (x_r · q_r) ≤ C_t   for all tiers t,  where sum is over {r : T(r) = t}
x_r ∈ {0, 1}           for all r ∈ R
All promoter-defined constraints (see §2.2)
```

### 1.2 What This Objective Optimizes

- **Total fulfilled ticket quantity.** The solver maximizes the
  number of tickets allocated across all fulfilled requests.
- Requests are fulfilled entirely or not at all (no partial fills).
  A request for 4 tickets either receives 4 or receives 0.

### 1.3 What This Objective Does NOT Optimize

- **Revenue.** Prices are fixed by the promoter. The solver does not
  consider price when making allocation decisions.
- **Fan priority or loyalty.** No fan is ranked above another based
  on purchase history, status, or any external attribute.
- **Seat-level placement.** The solver operates at the tier/inventory
  level, not at the individual seat level.
- **Fairness across fans.** The solver does not attempt to equalize
  outcomes. A fan requesting 1 ticket and a fan requesting 4 tickets
  are not weighted differently beyond their quantity impact on the
  objective.
- **Resale outcomes.** Secondary market behavior is out of scope.

---

## 2. Inputs and Constraints

### 2.1 Fan Inputs (from Phase 1A Demand Model)

Each request `r` in the batch contains:

| Field               | Type    | Description                                           |
|----------------------|---------|-------------------------------------------------------|
| `request_id`        | string  | Unique identifier for the request                     |
| `fan_id`            | string  | Unique identifier for the fan                         |
| `tier_id`           | string  | The inventory tier requested (e.g., "Floor", "Lower") |
| `quantity`          | integer | Number of tickets requested (subject to per-request limits) |
| `sit_together`      | boolean | Whether all tickets in this request must be adjacent  |
| `alt_tier_ids`      | list    | Ordered list of acceptable alternative tiers (may be empty) |

**Key properties of the input batch:**

- Every request in the batch is treated equally. There is no arrival
  timestamp, no queue position, and no speed-based ordering.
- A fan may submit at most one request per event (enforced upstream
  by the demand model).
- The batch is closed before allocation begins. No requests are added
  or removed during processing.

### 2.2 Promoter Constraints (Hard Requirements)

These constraints are defined by the rights owner (promoter, artist,
team) and are treated as inviolable. The solver must never relax,
override, or suggest modifying them.

| Constraint                  | Description                                                    |
|-----------------------------|----------------------------------------------------------------|
| **Tier capacity**           | Maximum tickets available per tier. Cannot be exceeded.        |
| **Per-request quantity limit** | Maximum tickets a single request may ask for (e.g., max 6). |
| **Tier pricing**            | Fixed price per ticket per tier. Not a decision variable.      |
| **Holdbacks / reserves**    | Inventory withheld from this allocation (e.g., accessibility, artist holds). Reduces available capacity before the solver runs. |
| **Sit-together requirement** | If a request specifies `sit_together = true`, all tickets must be allocable as a contiguous block within the tier. If no such block exists, the request is infeasible for that tier. |

### 2.3 Tie-Breaking Rules

When multiple feasible allocations produce the same total fulfilled
quantity (i.e., the objective value is tied), the solver must select
among them deterministically using the following ordered rules:

1. **Maximize the number of fulfilled requests.** Among allocations
   with the same total ticket count, prefer the one that fulfills
   more distinct requests (i.e., serves more fans).

2. **Lexicographic ordering by request_id.** If a tie persists after
   rule 1, fulfill requests in ascending lexicographic order of
   `request_id`. This provides a fully deterministic, reproducible
   result with no dependence on arrival time or randomness.

These rules ensure that:

- Given identical inputs, the solver always produces the identical
  output.
- No fan gains advantage from external factors (timing, network
  speed, device choice).
- The tie-breaking logic is simple enough to explain to any
  stakeholder.

---

## 3. Allocation Algorithm (Step-by-Step)

### 3.1 Overview

The algorithm processes all requests as a single batch. It uses a
greedy approach that is simple to implement, simple to audit, and
simple to explain. It does not require a general-purpose optimization
solver.

### 3.2 Preprocessing

**Step 0: Prepare inventory.**

```
For each tier t:
    available[t] = tier_capacity[t] − holdbacks[t]
```

**Step 1: Validate requests.**

```
For each request r:
    If r.quantity > per_request_limit:
        Mark r as REJECTED (reason: "exceeds per-request limit")
        Remove r from the batch
    If r.tier_id is not a valid tier:
        Mark r as REJECTED (reason: "invalid tier")
        Remove r from the batch
```

### 3.3 Sorting

**Step 2: Sort requests for processing.**

Requests are sorted by the following keys, in order:

1. **Quantity ascending.** Smaller requests are processed first.
   This directly supports the objective: fulfilling many small
   requests yields more total tickets than fulfilling fewer large
   requests when inventory is constrained.

2. **request_id ascending (lexicographic).** Breaks ties
   deterministically.

*Rationale for quantity-ascending ordering:* Consider 10 remaining
seats. One request for 10 tickets and ten requests for 1 ticket each
produce the same total fulfillment (10 tickets). But the tie-breaking
rule (§2.3, rule 1) prefers serving more fans, so small requests are
processed first. In cases where a large request would block multiple
small requests, processing small requests first naturally maximizes
both total tickets and total fans served.

### 3.4 Primary Allocation Pass

**Step 3: Attempt allocation for each request in sorted order.**

```
For each request r in sorted order:
    If r.sit_together is true:
        If available[r.tier_id] >= r.quantity
           AND a contiguous block of r.quantity exists in tier r.tier_id:
            Allocate r.quantity tickets from tier r.tier_id
            available[r.tier_id] -= r.quantity
            Mark r as FULFILLED
            Continue to next request
    Else:
        If available[r.tier_id] >= r.quantity:
            Allocate r.quantity tickets from tier r.tier_id
            available[r.tier_id] -= r.quantity
            Mark r as FULFILLED
            Continue to next request

    # Primary tier failed — try alternatives
    For each alt_tier in r.alt_tier_ids (in order):
        If r.sit_together is true:
            If available[alt_tier] >= r.quantity
               AND a contiguous block of r.quantity exists in alt_tier:
                Allocate r.quantity from alt_tier
                available[alt_tier] -= r.quantity
                Mark r as FULFILLED (note: allocated to alt_tier)
                Break
        Else:
            If available[alt_tier] >= r.quantity:
                Allocate r.quantity from alt_tier
                available[alt_tier] -= r.quantity
                Mark r as FULFILLED (note: allocated to alt_tier)
                Break

    If r is not FULFILLED:
        Mark r as UNFULFILLED (pending second pass)
```

### 3.5 Contiguous Block Handling

Since this solver does not perform seat-level optimization (per
Phase 0 scope), the `sit_together` constraint is evaluated at the
inventory level using a simplified model:

- Each tier maintains a list of available contiguous blocks
  (e.g., `[12, 8, 4, 2]` representing four blocks of those sizes).
- A `sit_together` request for quantity `q` requires at least one
  block of size `≥ q`.
- When allocated, the block is split: a block of size `b` used for
  quantity `q` produces a remaining block of size `b − q`.
- Blocks of size 0 are removed.

This is a simplification. Real seat maps have complex adjacency
rules. This model is sufficient to demonstrate the allocation
logic and to produce meaningful comparisons against FCFS.

### 3.6 Second Pass (Relaxation)

**Step 4: Attempt to fulfill remaining requests with relaxed
sit-together.**

Some requests marked UNFULFILLED may have failed only because no
contiguous block was large enough, even though total inventory in the
tier was sufficient. The second pass offers these fans a choice (in
simulation, this is modeled as automatic acceptance):

```
For each UNFULFILLED request r where r.sit_together is true:
    If available[r.tier_id] >= r.quantity (ignoring contiguity):
        Mark r as FULFILLED_SPLIT
            (allocated in tier, but seats may not be adjacent)
        available[r.tier_id] -= r.quantity
, Continue

    # Try alternatives with relaxed contiguity
    For each alt_tier in r.alt_tier_ids (in order):
        If available[alt_tier] >= r.quantity:
            Mark r as FULFILLED_SPLIT (in alt_tier)
            available[alt_tier] -= r.quantity
            Break

    If r is still UNFULFILLED:
        Mark r as REJECTED
            (reason: "insufficient inventory in all eligible tiers")
```

**Step 5: Mark remaining UNFULFILLED requests as REJECTED.**

```
For each request r still marked UNFULFILLED:
    Mark r as REJECTED
        (reason: "insufficient inventory in requested and alternative tiers")
```

### 3.7 Output Assembly

**Step 6: Produce the allocation result.**

For each request, the output record contains:

| Field              | Description                                              |
|--------------------|----------------------------------------------------------|
| `request_id`       | The original request identifier                          |
| `fan_id`           | The fan who made the request                             |
| `status`           | FULFILLED, FULFILLED_SPLIT, or REJECTED                  |
| `allocated_tier`   | The tier from which tickets were allocated (if fulfilled) |
| `allocated_qty`    | Number of tickets allocated (equals requested qty or 0)  |
| `rejection_reason` | Human-readable explanation (if rejected)                 |
| `pass`             | Which pass fulfilled the request (1 or 2), if applicable |

---

## 4. Explainability Guarantees

### 4.1 Explaining Any Individual Allocation

Every fulfilled request can be explained with a statement of the
following form:

> "Your request for [quantity] tickets in [tier] was fulfilled
> because sufficient inventory was available at the time your
> request was processed. Requests are processed in order from
> smallest to largest quantity, with ties broken by request
> identifier. No fan receives priority based on speed, timing,
> or status."

For `FULFILLED_SPLIT` requests:

> "Your request for [quantity] tickets in [tier] was fulfilled,
> but adjacent seating could not be guaranteed. Sufficient total
> inventory was available, but no contiguous block of [quantity]
> seats remained."

### 4.2 Explaining Rejected Requests

Every rejected request receives a specific, verifiable reason:

| Rejection Reason                         | Explanation to Fan                                                                                          |
|------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| Exceeds per-request limit                | "Your request exceeded the maximum of [limit] tickets per request set by the event organizer."               |
| Invalid tier                             | "The ticket tier you selected is not available for this event."                                               |
| Insufficient inventory (all tiers)       | "All tickets in your requested tier (and any alternatives you selected) were allocated to other requests. Demand exceeded supply." |
| Contiguity impossible (no relaxation)    | "Adjacent seating for your group size was not available. You were offered split seating but this was not accepted." |

### 4.3 Alternatives Considered

For each rejected request, the solver records:

1. **Primary tier status at time of processing.** How many tickets
   remained in the requested tier when this request was evaluated.
2. **Alternative tier status.** For each alternative tier listed,
   how many tickets remained.
3. **Contiguous block sizes available.** If `sit_together` was
   requested, the sizes of available contiguous blocks.
4. **What would have been required.** The minimum inventory change
   that would have made this request fulfillable (e.g., "3 additional
   tickets in Tier A, or 1 contiguous block of size ≥ 4 in Tier B").

This information enables after-the-fact audit of any allocation
decision without re-running the solver.

---

## 5. Output Metrics

The solver produces the following metrics, identical in structure to
the Phase 1B FCFS baseline to enable direct comparison.

### 5.1 Fulfillment Metrics

| Metric                          | Definition                                                              |
|----------------------------------|-------------------------------------------------------------------------|
| Total requests received          | Count of all valid requests in the batch                                |
| Total requests fulfilled         | Count of requests with status FULFILLED or FULFILLED_SPLIT              |
| Total requests rejected          | Count of requests with status REJECTED                                  |
| Fulfillment rate (requests)      | Fulfilled requests / Total requests                                     |
| Total tickets requested          | Sum of `quantity` across all valid requests                             |
| Total tickets allocated          | Sum of `allocated_qty` across all fulfilled requests                    |
| Fulfillment rate (tickets)       | Total tickets allocated / Total tickets requested                       |
| Tickets allocated per tier       | Breakdown of allocated tickets by tier                                  |

### 5.2 Demand vs. Supply Metrics

| Metric                          | Definition                                                              |
|----------------------------------|-------------------------------------------------------------------------|
| Oversubscription ratio (by tier) | Total tickets requested for tier / Tier capacity                        |
| Remaining inventory (by tier)    | Tier capacity − Tickets allocated in tier                               |
| Unmet demand (by tier)           | Tickets requested for tier − Tickets allocated in tier                  |

### 5.3 Seat Contiguity Metrics

| Metric                              | Definition                                                         |
|---------------------------------------|--------------------------------------------------------------------|
| Sit-together requests received        | Count of requests with `sit_together = true`                       |
| Sit-together requests fulfilled       | Count of sit-together requests with status FULFILLED               |
| Sit-together requests fulfilled split | Count with status FULFILLED_SPLIT (contiguity relaxed)             |
| Sit-together requests rejected        | Count of sit-together requests with status REJECTED                |
| Sit-together fulfillment rate         | (Fulfilled + Fulfilled_split) / Sit-together requests received     |

### 5.4 Comparison Metrics (vs. FCFS Baseline)

These metrics are computed when both FCFS and batch solver outputs
exist for the same demand scenario:

| Metric                              | Definition                                                         |
|---------------------------------------|--------------------------------------------------------------------|
| Δ Tickets allocated                   | Batch total − FCFS total                                           |
| Δ Fulfillment rate (tickets)          | Batch rate − FCFS rate                                             |
| Δ Requests fulfilled                  | Batch fulfilled count − FCFS fulfilled count                       |
| Δ Fulfillment rate (requests)         | Batch request rate − FCFS request rate                             |
| Fan overlap                           | Count of fans fulfilled by both methods                            |
| Fans gained (batch only)              | Fans fulfilled by batch solver but not FCFS                        |
| Fans lost (FCFS only)                 | Fans fulfilled by FCFS but not batch solver                        |

---

## 6. Known Limitations

### 6.1 Explicit Weaknesses

1. **Greedy, not globally optimal.** The quantity-ascending sort
   heuristic does not guarantee a globally optimal solution. A
   mixed-integer program could find allocations with higher total
   fulfillment in edge cases. The greedy approach is chosen for
   simplicity and explainability.

2. **No fan preferences beyond tier and quantity.** The solver does
   not consider price sensitivity, willingness to accept alternatives,
   or any fan attribute. All requests are treated identically.

3. **Simplified contiguity model.** The contiguous block model is an
   approximation. Real venues have rows, sections, aisles, and
   complex adjacency rules that this solver does not represent.

4. **No partial fulfillment.** A request for 4 tickets that cannot be
   fully satisfied results in 0 tickets, even if 3 are available.
   This can reduce total fulfillment in inventory-constrained
   scenarios.

5. **Single-pass greedy with fixed sort order.** The quantity-ascending
   heuristic can underperform when a mix of large and small requests
   exists and inventory fragmentation matters. For example, fulfilling
   one request for 6 might block three requests for 2 — but the
   reverse (blocking the 6 to serve three 2s) is always preferred by
   the sort order, even when the 6-ticket request might have been the
   "better" allocation for other reasons.

6. **No revenue awareness.** Since the solver ignores prices, it
   cannot distinguish between allocating a $50 ticket and a $500
   ticket. In scenarios where the promoter would prefer higher-priced
   tiers to sell out first, this solver provides no mechanism for
   that preference.

### 6.2 Scenarios Where This Solver Performs Poorly

| Scenario                               | Why It Struggles                                                    |
|-----------------------------------------|---------------------------------------------------------------------|
| Nearly full venue, many large requests  | Greedy small-first may leave fragmented inventory unusable by remaining large requests |
| Heavy sit-together demand               | Simplified block model may reject requests a real seat map could serve |
| Heterogeneous tier demand               | No cross-tier balancing or steering; relies entirely on fan-specified alternatives |
| Promoter wants revenue prioritization   | Solver is revenue-blind by design                                   |

### 6.3 Why These Limitations Are Acceptable

This solver is Phase 1C — the first batch alternative to FCFS. Its
purpose is narrowly scoped:

1. **Prove the concept.** Demonstrate that batch allocation with a
   simple heuristic can outperform FCFS on total fulfillment when
   demand exceeds supply.

2. **Establish the comparison framework.** Define the metric set and
   output format that all subsequent solvers will use, enabling
   apples-to-apples comparison.

3. **Provide an explainability baseline.** Show that every allocation
   decision can be justified in plain language, setting the standard
   for more complex solvers that follow.

4. **Keep complexity low.** A solver that requires a PhD to explain
   is not useful for stakeholder buy-in. This solver can be explained
   in one paragraph:

   > "All requests are collected before any tickets are assigned.
   > Requests are sorted from smallest to largest. Each request is
   > fulfilled if enough tickets remain in the requested tier.
   > If not, alternative tiers are tried. If no tier has enough
   > inventory, the request is declined. No one gets priority for
   > being faster."

The limitations above are addressed in subsequent phases by
introducing more sophisticated solvers (e.g., mixed-integer
programming, multi-objective optimization) that build on the
infrastructure and metrics established here.

---

## Appendix A: Relationship to Other Phases

| Phase | Document                       | Relationship                                                |
|-------|--------------------------------|-------------------------------------------------------------|
| 0     | PHASE_0_PROBLEM_DEFINITION.md  | Defines the problem scope, promoter constraints, and system boundaries this solver operates within |
| 1A    | PHASE_1A_DEMAND_MODEL.md       | Defines the synthetic demand generation that produces the request batch this solver consumes |
| 1B    | PHASE_1B_FCFS_BASELINE.md      | Defines the FCFS baseline this solver is compared against using the metrics in §5 |
| 1C    | This document                  | Defines the first batch-based allocation solver              |

---

## Appendix B: Worked Example

**Setup:**

- Tier A: 10 seats available, contiguous blocks = [6, 4]
- Tier B: 5 seats available, contiguous blocks = [5]
- Per-request limit: 6
- Holdbacks: 0

**Requests (unsorted):**

| request_id | fan_id | tier_id | quantity | sit_together | alt_tier_ids |
|------------|--------|---------|----------|--------------|--------------|
| R003       | F3     | A       | 4        | true         | [B]          |
| R001       | F1     | A       | 2        | false        | []           |
| R005       | F5     | A       | 6        | true         | []           |
| R002       | F2     | A       | 2        | true         | [B]          |
| R004       | F4     | B       | 3        | false        | []           |

**Step 2 — Sorted order:** R001 (qty 2), R002 (qty 2), R004 (qty 3),
R003 (qty 4), R005 (qty 6)

**Step 3 — Primary allocation pass:**

1. **R001** (qty 2, Tier A, no sit-together):
   Available A = 10. Allocate 2. Available A = 8. Blocks = [6, 2].
   → **FULFILLED**

2. **R002** (qty 2, Tier A, sit-together):
   Available A = 8. Block [6] ≥ 2. Allocate 2 from block of 6.
   Available A = 6. Blocks = [4, 2, 2]. → **FULFILLED**

3. **R004** (qty 3, Tier B, no sit-together):
   Available B = 5. Allocate 3. Available B = 2. Blocks = [2].
   → **FULFILLED**

4. **R003** (qty 4, Tier A, sit-together):
   Available A = 6. Block [4] ≥ 4. Allocate 4 from block of 4.
   Available A = 2. Blocks = [2, 2]. → **FULFILLED**

5. **R005** (qty 6, Tier A, sit-together):
   Available A = 2. No block ≥ 6. Try alternatives: none listed.
   → **UNFULFILLED**

**Step 4 — Second pass:** R005 has sit-together = true. Available
A = 2, which is less than quantity 6. No alternatives. Cannot relax.
→ **REJECTED** (reason: insufficient inventory)

**Results:**

| request_id | status    | allocated_tier | allocated_qty | reason                  |
|------------|-----------|----------------|---------------|-------------------------|
| R001       | FULFILLED | A              | 2             | —                       |
| R002       | FULFILLED | A              | 2             | —                       |
| R003       | FULFILLED | A              | 4             | —                       |
| R004       | FULFILLED | B              | 3             | —                       |
| R005       | REJECTED  | —              | 0             | Insufficient inventory  |

**Metrics:**

- Total tickets requested: 17
- Total tickets allocated: 11
- Fulfillment rate (tickets): 64.7%
- Fulfillment rate (requests): 80% (4 of 5)
- Remaining inventory: Tier A = 2, Tier B = 2

**FCFS comparison note:** Under FCFS, if F5 (requesting 6) arrived
first, they would consume 6 of Tier A's 10 seats. F3 (requesting 4,
sit-together) would then need a block of 4 from the remaining
[4] — feasible. But F1 and F2 (2 each) might or might not be served
depending on arrival order. The batch solver guarantees F1, F2, F3,
and F4 are served (11 tickets, 4 fans), whereas many FCFS orderings
serve only 3 fans for 10-13 tickets. The batch solver sacrifices one
large request to serve more fans and more total tickets.
