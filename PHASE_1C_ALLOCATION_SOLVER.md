# Phase 1C — Allocation Solver

## Purpose

Given a set of fan requests and a fixed inventory of ticket sections/price-levels,
allocate tickets to requests subject to promoter-defined constraints and a
specified objective function.

---

## Inputs

| Field | Type | Description |
|---|---|---|
| `event_id` | string | Unique event identifier |
| `sections` | list | Available sections, each with `section_id`, `capacity`, `price` |
| `requests` | list | Fan requests (schema below) |
| `objective` | enum | `MAXIMIZE_REVENUE` \| `MAXIMIZE_ACCESS` \| `HYBRID(w_rev, w_acc)` |
| `tie_break_policy` | enum | `DETERMINISTIC_LOTTERY` (default) \| `FLEXIBILITY_FIRST` \| `QUANTITY_ASC` |
| `lottery_seed` | int \| null | Seed for deterministic lottery; system-generated if null |

### Request Schema

| Field | Type | Description |
|---|---|---|
| `request_id` | string | Unique request identifier |
| `fan_id` | string | Fan identifier |
| `quantity` | int | Number of tickets requested |
| `max_price` | decimal \| null | Maximum price per ticket the fan will accept; null = no limit |
| `section_preferences` | list \| null | Ordered list of acceptable `section_id` values; null = any section |
| `substitution_tolerance` | int | Number of alternative sections the fan accepts (0 = exact match only) |
| `price_flexibility` | decimal | Fraction above `max_price` the fan would still accept (0.0–1.0) |
| `together_required` | bool | If true, all tickets in this request must be in the same section |
| `allow_split_if_needed` | bool | Default **false**. If true AND `together_required=true`, the solver may split the request across sections as a fallback |

---

## Tie-Break Policy

When multiple requests compete for the same scarce inventory and the objective
function does not distinguish between them, the solver must apply a
**deterministic tie-break policy** to decide processing order. The policy is
event-level and set by the `tie_break_policy` input.

### Allowable Policies

#### (a) `DETERMINISTIC_LOTTERY` — *default*

Requests are ordered by a stable hash of `(event_id, request_id, lottery_seed)`.
This produces a pseudo-random but fully reproducible ordering that is neutral
with respect to request attributes (quantity, price, timing).

```
order_key = SHA-256(event_id || request_id || lottery_seed)
```

- **Determinism**: identical inputs always produce the identical ordering.
- **Neutrality**: no request attribute (size, price, flexibility) is favoured.
- **Auditability**: any party with the seed can independently verify the order.

#### (b) `FLEXIBILITY_FIRST`

Requests are ordered by descending flexibility score, where:

```
flexibility_score = substitution_tolerance + price_flexibility
```

Ties within this ordering are broken by the deterministic lottery hash (a).

Rationale: requests that are easier to satisfy are processed first, which can
increase overall fill-rate without biasing toward high- or low-quantity requests.

#### (c) `QUANTITY_ASC`

Requests are ordered by `quantity` ascending. Ties are broken by the
deterministic lottery hash (a).

This policy is available as an explicit opt-in but is **not** the default,
because it systematically favours small requests and may disadvantage groups.

### Policy Requirements

- The chosen policy MUST be recorded in the allocation output for explainability.
- The `lottery_seed` MUST be recorded whenever policy (a) or any lottery-based
  tie-break sub-step is used.

---

## Allocation Algorithm

### Step 1 — Feasibility Filter

For each request, verify that at least one section can satisfy it:

- Section capacity >= `quantity`
- Section price <= `max_price * (1 + price_flexibility)` (if `max_price` is set)
- Section is in `section_preferences` (if specified), or within
  `substitution_tolerance` alternatives

Requests with no feasible section are immediately rejected
(reason: `NO_FEASIBLE_SECTION`).

### Step 2 — Order Requests by Tie-Break Policy

Sort the feasible requests using the active `tie_break_policy` as defined above.

### Step 3 — Greedy Assignment (First Pass)

Process requests in tie-break order. For each request:

1. Identify feasible sections (price, preference, capacity).
2. Select the best section according to the objective function.
3. If `together_required = true`, the full `quantity` must be allocable in a
   single section. If no single section can satisfy the full quantity:
   - If `allow_split_if_needed = false` → **skip this request** (do not split;
     it will be rejected after the second pass).
   - If `allow_split_if_needed = true` → **skip this request** for now; it is
     eligible for the split pass.
4. Deduct allocated tickets from section capacity.

### Step 4 — Split Pass (Second Pass)

Process only requests where ALL of the following are true:

- The request was **not** allocated in the first pass.
- `together_required = true`
- `allow_split_if_needed = true`

For each such request (in tie-break order):

1. Allocate as many tickets as possible in the most-preferred feasible section.
2. Allocate remaining tickets across other feasible sections until `quantity` is
   fulfilled or no capacity remains.
3. If the full `quantity` cannot be fulfilled even with splitting, reject the
   request (reason: `INSUFFICIENT_CAPACITY_AFTER_SPLIT`).

Requests where `together_required = true` AND `allow_split_if_needed = false`
that were not allocated in the first pass are rejected
(reason: `TOGETHER_REQUIRED_NO_SINGLE_SECTION`).

### Step 5 — Process Non-Together Requests That Were Skipped

Any remaining unallocated requests (where `together_required = false`) that could
not be fully satisfied in a single section are split across feasible sections.
If the full quantity still cannot be met, reject
(reason: `INSUFFICIENT_CAPACITY`).

---

## Rejection Reasons

| Code | Meaning |
|---|---|
| `NO_FEASIBLE_SECTION` | No section satisfies price, preference, and capacity constraints |
| `TOGETHER_REQUIRED_NO_SINGLE_SECTION` | `together_required=true`, `allow_split_if_needed=false`, and no single section has enough capacity |
| `INSUFFICIENT_CAPACITY_AFTER_SPLIT` | `together_required=true`, `allow_split_if_needed=true`, but total remaining capacity across all feasible sections is insufficient |
| `INSUFFICIENT_CAPACITY` | General capacity exhaustion for non-together requests |

Each rejection entry includes:

- `request_id`
- `rejection_reason` (code from table above)
- `narrative` — plain-language explanation suitable for a non-technical audience

---

## Output Schema

| Field | Type | Description |
|---|---|---|
| `event_id` | string | Echo of input |
| `tie_break_policy` | string | Policy used |
| `lottery_seed` | int \| null | Seed used (if applicable) |
| `allocations` | list | `{ request_id, section_id, quantity_allocated }` (one entry per section if split) |
| `rejections` | list | `{ request_id, rejection_reason, narrative }` |
| `objective_value` | decimal | Value of the objective function for this allocation |
| `summary` | object | `{ total_allocated, total_rejected, fill_rate, sections_utilization[] }` |

---

## Constraints on This Specification

- The **objective function** is not modified by this specification.
- All policies are **deterministic**: the same inputs always yield the same output.
- All allocation decisions are **explainable**: the output records the policy,
  seed, and per-request reasoning.
- The solver **never** splits a request when `together_required=true` and
  `allow_split_if_needed=false`. This is a hard constraint, not a heuristic.
