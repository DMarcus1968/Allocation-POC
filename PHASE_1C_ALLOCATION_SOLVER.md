# Phase 1C — Allocation Solver

## Overview

The allocation solver processes a batch of ticket requests for a given event and
produces a deterministic, explainable allocation.  It operates **within**
promoter-defined constraints and does **not** introduce pricing or revenue
optimization.

**Objective function:** maximize total fulfilled ticket quantity, subject to all
hard constraints described below.

---

## 1  Inputs

| Input | Description |
|---|---|
| `event_id` | Identifier for the event being allocated. |
| `inventory` | Available ticket inventory (count, and optionally seat-map fragments). |
| `requests[]` | Fan ticket requests (see schema below). |
| `entity_ticket_limit` | Promoter-set maximum tickets any single entity may receive across all requests for this event. |
| `seed` | Deterministic random seed for lottery tie-breaks. |
| `promoter_priority_rules` | *(optional)* Promoter-defined priority ordering that overrides the default lottery tie-break. |

### Request schema

```
{
  request_id:        string,
  entity_id:         string,
  quantity:          int,        // >= 1
  together_required: bool,       // true = all seats must be contiguous
  allow_singles_fill: bool       // true = accept leftover single-seat fragments
                                 //        (only relevant when quantity >= 2
                                 //         AND together_required == false)
}
```

---

## 2  Hard constraints

### 2.1  Per-entity ticket limit

The promoter sets a per-entity ticket limit (`entity_ticket_limit`) for the
event.  This is enforced as a **hard constraint**:

1. The solver maintains a running counter `tickets_allocated_by_entity_id`
   (a map of `entity_id -> int`, initialized to 0 for every entity).
2. Before fulfilling **any** request, the solver checks:

   ```
   tickets_allocated_by_entity_id[entity_id] + requested_qty <= entity_ticket_limit
   ```

3. If this condition is **not** satisfied, the request is **rejected in full**
   with reason `"ENTITY_LIMIT_EXCEEDED"`.
   - Partial fills are **not** performed unless the promoter constraint
     explicitly allows partial fulfillment for that entity.
4. Upon successful allocation, the counter is incremented:

   ```
   tickets_allocated_by_entity_id[entity_id] += allocated_qty
   ```

### 2.2  Sit-together (contiguity)

- When `together_required == true`, all allocated seats for that request **must**
  be contiguous.  The solver must never violate this constraint.
- Contiguity is **not** relaxed for any reason when `together_required == true`.
- Contiguity may only be relaxed when **both** of the following hold:
  - `together_required == false`
  - `allow_singles_fill == true`

  In that case, the request may be filled with non-contiguous leftover
  single-seat fragments (see Pass 3 below).

### 2.3  Inventory capacity

Total allocated tickets must not exceed available inventory.

---

## 3  Allocation order — groups-first policy

**The solver never prefers single-ticket requests over group requests.**
Singles are processed *after* groups.  Singles-as-filler is opt-in only.

Requests are partitioned and processed in three sequential passes:

### Pass 1 — Groups-first allocation

**Scope:** All requests where `quantity >= 2`.

Processing order within this pass:

- If `promoter_priority_rules` are defined, use the promoter-specified ordering.
- Otherwise, use a **deterministic lottery tie-break**:
  `sort_key = hash(event_id + request_id + seed)`
  Requests are processed in ascending `sort_key` order.

For each request (in order):

1. Check the per-entity ticket limit (Section 2.1).  Reject if exceeded.
2. Check inventory availability.
3. If `together_required == true`, check that a contiguous block of
   `quantity` seats is available.  If not, the request is **not fulfilled**
   in this pass (reason: `"CONTIGUOUS_BLOCK_UNAVAILABLE"`).
4. If `together_required == false`, allocate `quantity` seats from available
   inventory (contiguous preferred but not required).
5. On success, decrement inventory and update `tickets_allocated_by_entity_id`.

### Pass 2 — Singles allocation (explicit single requests)

**Scope:** All requests where `quantity == 1`.

These are requests that are inherently single-ticket requests.  The
`allow_singles_fill` flag is irrelevant here (the request is already for one
seat).

Processing order: same deterministic lottery tie-break (or promoter rules) as
Pass 1.

For each request (in order):

1. Check the per-entity ticket limit (Section 2.1).  Reject if exceeded.
2. Check inventory availability.
3. Allocate one seat.
4. On success, decrement inventory and update `tickets_allocated_by_entity_id`.

### Pass 3 — Singles-as-filler (gap fill)

**Scope:** Requests from Pass 1 that were **not fulfilled** (or not fully
fulfilled in a future partial-fill extension), where **all** of the following
are true:

- Original `quantity >= 2`
- `allow_singles_fill == true`
- `together_required == false`

This pass uses **only leftover single-seat inventory fragments** created by
earlier allocations (e.g., isolated seats between allocated blocks).

Processing order: same deterministic lottery tie-break (or promoter rules).

For each eligible request (in order):

1. Check the per-entity ticket limit (Section 2.1).  Reject if exceeded.
2. Identify available single-seat fragments in remaining inventory.
3. Allocate up to `quantity` seats from those fragments (non-contiguous is
   acceptable since `together_required == false`).
4. On success, decrement inventory and update `tickets_allocated_by_entity_id`.

---

## 4  Output

### Allocation result (per request)

```
{
  request_id:      string,
  entity_id:       string,
  status:          "FULFILLED" | "PARTIALLY_FULFILLED" | "REJECTED",
  allocated_qty:   int,
  allocated_seats: [seat_id, ...],    // if seat-level tracking is enabled
  rejection_reason: string | null,    // see Section 5
  pass:            1 | 2 | 3 | null   // which pass fulfilled this request
}
```

### Summary statistics

- Total requests processed
- Total requests fulfilled / partially fulfilled / rejected
- Total tickets allocated vs. total tickets requested
- Remaining inventory
- Rejection breakdown by reason

---

## 5  Rejection reasons

| Reason code | Description |
|---|---|
| `ENTITY_LIMIT_EXCEEDED` | Allocating this request would cause the entity to exceed the promoter-set per-entity ticket limit. The request is rejected in full (no partial fill). |
| `INVENTORY_EXHAUSTED` | Insufficient inventory remaining to fulfill the request. |
| `CONTIGUOUS_BLOCK_UNAVAILABLE` | The request requires contiguous seating (`together_required == true`) but no contiguous block of the required size is available. |

---

## 6  Explainability

Every allocation run produces a human-readable explanation log.  The log
includes, at minimum:

1. **Constraints applied** — entity ticket limit value, inventory size,
   per-request flags.
2. **Objective function** — "maximize total fulfilled ticket quantity."
3. **Allocation order rationale:**
   > The solver processes group requests (quantity >= 2) before single-ticket
   > requests (quantity == 1).  The solver **never prefers singles over groups**.
   > Singles are allocated only after all group requests have been evaluated.
   > Singles-as-filler (Pass 3) is opt-in: a request must have
   > `allow_singles_fill == true` and `together_required == false` to be
   > eligible.  The solver does not relax contiguity constraints unless the
   > fan has explicitly opted in.
4. **Tie-break method** — deterministic lottery using
   `hash(event_id + request_id + seed)`, or promoter-defined priority rules
   if specified.
5. **Top alternative allocations considered** — at least one alternative
   ordering and its outcome metrics (total fulfilled quantity, rejection
   count).
6. **Reasons alternatives were rejected** — e.g., "Alternative A fulfilled
   fewer total tickets."
7. **Entity limit enforcement log** — for each entity that hit the limit, the
   log records which requests were rejected and the running total at the time
   of rejection.

---

## 7  Design principles

- **Deterministic:** Given the same inputs and seed, the solver always produces
  the same output.
- **Simple:** No pricing, revenue optimization, or market-based mechanisms.
- **Promoter-governed:** The entity ticket limit and priority rules are promoter
  inputs treated as hard constraints, never suggestions.
- **Fair by construction:** Groups are processed first; singles never receive
  preferential treatment.  Tie-breaks are resolved by a transparent,
  deterministic lottery (or promoter rules).
- **Explainable:** Every allocation decision can be justified in plain language
  to a non-technical audience.
