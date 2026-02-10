# Phase 1B — FCFS Baseline

## 1. Purpose

Implement a traditional first-come-first-served (FCFS) ticket processing simulation to serve as a **comparison baseline** for the allocation solver in Phase 1C. This phase intentionally reproduces the dynamics of conventional onsale systems to make their limitations visible.

## 2. Input

The request set produced by Phase 1A, including `submission_time` for each request.

## 3. Processing Order

Requests are sorted by `submission_time` (ascending) and processed sequentially. This is the **only** phase in which arrival time determines allocation order.

### 3.1 Tie-Breaking

When multiple requests share the same `submission_time`, ties are broken by `request.id` (ascending). This is arbitrary but deterministic.

## 4. Allocation Logic

For each request, in submission-time order:

```
for request in sorted_requests:
    tier = request.tier
    if tier.remaining_capacity >= request.group_size:
        allocate(request)
        tier.remaining_capacity -= request.group_size
    else:
        reject(request, reason="insufficient_capacity")
```

### 4.1 Hard Constraint Enforcement

| Constraint | How Enforced |
|---|---|
| **HC-1: Tier Capacity** | Checked on every allocation. A request is rejected if `remaining_capacity < group_size`. Capacity is decremented atomically per request. |
| **HC-2: Per-Request Limit** | Enforced at request generation time (Phase 1A §2.2). Requests exceeding the limit never enter the FCFS queue. |
| **HC-3: Group Integrity** | Enforced by the all-or-nothing check: `remaining_capacity >= group_size`. No partial fills. |
| **HC-4: Tier Eligibility** | Each request targets exactly one tier. FCFS does not reassign across tiers. |
| **HC-5: Singles Policy** | See §4.2. |

### 4.2 Singles Policy in FCFS

The singles policy is applied as follows:

| Policy | FCFS Behavior |
|---|---|
| `allowed` | Single and group requests are interleaved by submission time. No distinction. |
| `filler_only` | **Two-pass processing.** Pass 1: process all group requests (`group_size > 1`) in submission-time order. Pass 2: process single requests (`group_size = 1`) in submission-time order against remaining capacity. |
| `rejected` | Single requests are excluded before processing begins. |

Under `filler_only`:
- **Pass 1 (Groups):** All group requests are processed in submission-time order. Singles are skipped.
- **Pass 2 (Singles as Filler):** Single requests are processed in submission-time order against whatever capacity remains after Pass 1.
- A single request **never displaces** a group request, even if the group request arrives later in submission time. Groups are always processed first.

## 5. Output

### 5.1 Per-Request Result

Each request receives one of two outcomes:

| Outcome | Fields |
|---|---|
| **Fulfilled** | `request_id`, `tier`, `quantity_allocated`, `position_in_queue` |
| **Rejected** | `request_id`, `tier`, `quantity_requested`, `reason` |

### 5.2 Rejection Reasons

| Reason Code | Meaning |
|---|---|
| `insufficient_capacity` | The tier did not have enough remaining seats when this request was reached in the queue. |
| `singles_policy_rejected` | The request was a single-ticket request and the singles policy is `rejected`. |
| `exceeds_per_request_limit` | The request exceeded the per-request limit (filtered pre-queue). |

### 5.3 Aggregate Metrics

| Metric | Description |
|---|---|
| `total_fulfilled` | Number of requests fulfilled. |
| `total_rejected` | Number of requests rejected. |
| `total_tickets_allocated` | Sum of tickets across fulfilled requests. |
| `capacity_utilization` | `total_tickets_allocated / total_capacity` per tier and overall. |
| `fill_rate` | `total_fulfilled / total_requests`. |

## 6. Limitations (By Design)

These are not bugs — they are the documented weaknesses of FCFS that Phase 1C is designed to address:

1. **Arrival-time dependence.** Outcome is determined by submission speed, not by allocation merit or promoter objective.
2. **Capacity waste.** A group request of 4 may be rejected while 3 seats remain, leaving those seats unfilled (no backfill of smaller groups or singles in `allowed` mode).
3. **No objective optimization.** FCFS does not consider revenue, access maximization, or any promoter-defined objective.
4. **No explainability beyond queue position.** The only explanation for rejection is "you were too late."
5. **Race-condition dynamics.** Fans who submit faster are rewarded, incentivizing bot use and system strain.

## 7. What FCFS Does NOT Do

- Does not optimize for any objective function.
- Does not randomize order (uses arrival time only).
- Does not produce alternative allocations or sensitivity analysis.
- Does not backfill gaps left by rejected group requests (in `allowed` mode with sequential processing).
