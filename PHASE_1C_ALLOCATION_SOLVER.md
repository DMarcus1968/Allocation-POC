# Phase 1C — Allocation Solver

## 1. Purpose

Implement a request-based allocation engine that processes the same demand set as Phase 1B but replaces arrival-time ordering with **constraint-satisfying allocation governed by an explicit objective function**. This is the core of the prototype.

## 2. Input

- The request set produced by Phase 1A. The `submission_time` field is **ignored**; all requests are treated as simultaneous.
- The event configuration from Phase 1A §2 (tiers, capacities, per-request limit, singles policy).
- A promoter-selected **objective function** (see §3).

## 3. Objective Function

The promoter must explicitly select one of the following. The solver does not assume a default.

| Objective | Formulation |
|---|---|
| **Maximize Access** | Maximize the number of distinct requests fulfilled, subject to hard constraints. |
| **Maximize Revenue** | Maximize `sum(request.group_size * tier.price)` for fulfilled requests, subject to hard constraints. |
| **Hybrid** | Maximize `α * normalized_access + (1 - α) * normalized_revenue`, where `α` is a promoter-defined weight in `[0, 1]`. |

If no objective is provided, the solver **halts and requests clarification**. It never defaults to revenue maximization.

## 4. Allocation Order and Singles Policy

### 4.1 Allocation Phases

Regardless of objective function, allocation proceeds in **two phases** when the singles policy is `filler_only`:

| Phase | Eligible Requests | Description |
|---|---|---|
| **Phase A: Group Allocation** | All requests with `group_size > 1` | The solver selects from group requests to optimize the chosen objective, subject to hard constraints. Selection among equally-ranked groups is resolved by **random lottery**. |
| **Phase B: Singles as Filler** | All requests with `group_size = 1` | After group allocation is finalized, remaining capacity is filled with single-ticket requests. Selection among eligible singles is resolved by **random lottery**. |

When the singles policy is `allowed`:
- All requests (group and single) compete in a single allocation phase. No sequencing distinction.

When the singles policy is `rejected`:
- Single requests are excluded before the solver runs.

### 4.2 Singles Cannot Displace Groups

Under the `filler_only` policy:
- **A single-ticket request can never displace a feasible group allocation.** Phase B only runs after Phase A is finalized.
- The solver does not re-open Phase A results to accommodate singles.
- If Phase A leaves 0 remaining capacity in a tier, no singles are allocated to that tier.

### 4.3 Lottery Mechanism

When the solver must choose among equally-ranked requests (same marginal contribution to the objective):
- Selection is by **uniform random lottery** using the configurable seed from Phase 1A §6.
- No fan attribute (submission time, loyalty, history) influences the lottery.

## 5. Hard Constraint Enforcement

| Constraint | How Enforced |
|---|---|
| **HC-1: Tier Capacity** | Modeled as a capacity constraint in the solver. No allocation plan may exceed tier capacity. Verified post-solve as an assertion. |
| **HC-2: Per-Request Limit** | Validated at input. Requests exceeding the limit are rejected before the solver runs with reason `exceeds_per_request_limit`. |
| **HC-3: Group Integrity** | Each request is an atomic unit. The solver either includes the full `group_size` or excludes the request entirely. No partial allocations exist in the solution space. |
| **HC-4: Tier Eligibility** | Each request is associated with exactly one tier. The solver does not move requests across tiers. |
| **HC-5: Singles Policy** | Enforced structurally via the two-phase allocation order (§4.1). Under `filler_only`, singles are excluded from Phase A. Under `rejected`, singles are excluded entirely. |

### 5.1 Post-Solve Validation

After the solver produces an allocation, the following assertions are checked:

1. No tier exceeds its capacity.
2. Every fulfilled request has `group_size` tickets allocated (no partial fills).
3. No fulfilled request exceeds the per-request limit.
4. Under `filler_only`, no single request displaced a feasible group allocation.
5. The objective function value is correctly computed.

If any assertion fails, the allocation is discarded and an error is raised. The system does not silently produce an invalid allocation.

## 6. Explainability

### 6.1 Requirement

Every request must receive a human-readable explanation of its outcome. The explanation must be understandable by a non-technical audience and must not reference internal solver mechanics.

### 6.2 Fulfilled Request Explanations

| Category | Template |
|---|---|
| **Selected by objective** | "Your request for {n} tickets in {tier} was fulfilled. The allocation optimized for {objective} across all eligible requests." |
| **Selected by lottery** | "Your request for {n} tickets in {tier} was fulfilled. Among equally eligible requests, yours was selected by random lottery." |
| **Singles filler** | "Your request for 1 ticket in {tier} was fulfilled as a filler allocation after group requests were processed." |

### 6.3 Rejected Request Explanations

| Category | Reason Code | Template |
|---|---|---|
| **Capacity exhausted** | `capacity_exhausted` | "Your request for {n} tickets in {tier} could not be fulfilled because all seats in that tier were allocated to other requests." |
| **Group too large for remaining capacity** | `group_exceeds_remaining` | "Your request for {n} tickets in {tier} could not be fulfilled because fewer than {n} seats remained in that tier after higher-priority allocations." |
| **Displaced by objective** | `displaced_by_objective` | "Your request for {n} tickets in {tier} was not selected because other requests better served the allocation objective ({objective})." |
| **Lottery not selected** | `lottery_not_selected` | "Your request for {n} tickets in {tier} was not selected. Among equally eligible requests, yours was not chosen in the random lottery." |
| **Singles policy** | `singles_policy_rejected` | "Your request for 1 ticket was not accepted because the event policy does not allow single-ticket requests." |
| **Singles filler — no capacity** | `singles_filler_no_capacity` | "Your request for 1 ticket in {tier} could not be fulfilled. After group allocations, no seats remained in that tier." |
| **Per-request limit exceeded** | `exceeds_per_request_limit` | "Your request for {n} tickets exceeds the maximum of {limit} tickets per request." |

### 6.4 Coverage Guarantee

Every possible rejection path in the solver maps to exactly one reason code and template above. There are no silent rejections or unexplained outcomes.

## 7. Output

### 7.1 Per-Request Result

Each request receives:

| Outcome | Fields |
|---|---|
| **Fulfilled** | `request_id`, `tier`, `quantity_allocated`, `explanation_category`, `explanation_text` |
| **Rejected** | `request_id`, `tier`, `quantity_requested`, `reason_code`, `explanation_text` |

### 7.2 Aggregate Metrics

| Metric | Description |
|---|---|
| `total_fulfilled` | Number of requests fulfilled. |
| `total_rejected` | Number of requests rejected. |
| `total_tickets_allocated` | Sum of tickets across fulfilled requests. |
| `capacity_utilization` | Per tier and overall. |
| `fill_rate` | `total_fulfilled / total_requests`. |
| `objective_value` | The computed value of the promoter's chosen objective function. |

### 7.3 Comparison Output

The solver produces a side-by-side comparison with Phase 1B FCFS results on the same demand set:

| Comparison Metric | Description |
|---|---|
| `delta_fulfilled` | Difference in fulfilled request count. |
| `delta_utilization` | Difference in capacity utilization. |
| `delta_objective` | Difference in objective function value (if applicable). |

## 8. What the Solver Does NOT Do

- **Does not use arrival time.** `submission_time` is ignored.
- **Does not assume revenue maximization.** The objective must be explicitly provided.
- **Does not learn from past events.** Each event is solved independently.
- **Does not assign specific seats.** Allocation is at the tier level only.
- **Does not guarantee all requests are fulfilled.** When demand exceeds supply, rejections are expected and explained.
