# Phase 1C — Allocation Solver

## Purpose

This document describes a batch-allocation solver that processes the identical demand population defined in Phase 1A under the same inventory constraints and pricing. The solver considers all requests simultaneously and produces an allocation that optimizes a stated objective function, subject to rights-owner constraints.

## Mechanism Description

The allocation solver operates in batch mode:

1. All 4,000 requests are collected during a request window (order of submission is recorded but not used for prioritization)
2. The solver considers the full set of requests, their group sizes, tier preferences, and WTP simultaneously
3. An allocation is computed that maximizes the objective function subject to constraints
4. All fans are notified of outcomes at the same time

### Key Properties of Batch Allocation

- **Simultaneous:** All requests are visible to the solver before any allocation decision is made
- **Arrival-order independent:** Queue position has no effect on outcome
- **Globally optimized:** The solver considers the entire request set, not one request at a time
- **Backtracking possible:** The solver can explore alternative assignments to improve global outcomes
- **Demand-visible:** The rights owner can observe aggregate demand shape before allocation executes

## Objective Function

The solver uses a **weighted hybrid objective** that balances revenue and access:

```
Maximize: Σ (w_revenue × price_tier(i) × group_size(i) × x(i,t))
        + Σ (w_access × fulfilled(i))
```

Where:
- `x(i,t)` = 1 if request `i` is assigned to tier `t`, 0 otherwise
- `fulfilled(i)` = 1 if request `i` is assigned to any tier, 0 otherwise
- `price_tier(t)` = face price of tier `t`
- `group_size(i)` = number of tickets in request `i`
- `w_revenue` = 0.6 (revenue weight)
- `w_access` = 0.4 (access weight, normalized to revenue scale)

**Access weight normalization:** To make the access term comparable to the revenue term, the access weight is scaled by the average ticket price ($100), so each fulfilled request contributes `0.4 × $100 = $40` of "access value" per ticket to the objective.

### Rationale for Weight Selection

The 60/40 revenue-access split is a **starting point**, not a tuned optimum. It is chosen to:
- Avoid pure revenue maximization (which would systematically exclude low-WTP fans)
- Avoid pure access maximization (which would ignore revenue entirely and fill cheapest tiers first)
- Produce an interior solution that demonstrates the tradeoff surface

**This weight is a parameter, not a finding.** Different weights would produce different allocations. Phase 1D compares the outcome under this specific weight to FCFS; it does not claim this weight is optimal.

## Constraints

All constraints match Phase 1B:

| Constraint | Specification |
|---|---|
| Tier capacity | Premium ≤ 1,000; Standard ≤ 5,000; Upper ≤ 4,000 |
| All-or-nothing | Each request is fully fulfilled in one tier or not at all |
| WTP feasibility | A request can only be assigned to a tier priced ≤ its WTP |
| Tier preference | A request can only be assigned to a tier in its preference list |
| Single assignment | Each request is assigned to at most one tier |
| Fixed pricing | Tier prices are $250 / $100 / $50; not modified by the solver |

## Simulation Parameters

| Parameter | Value |
|---|---|
| Total requests | 4,000 |
| Total tickets requested | ~18,000 |
| Total inventory | 10,000 |
| Tiers | 3 (Premium: 1,000 / Standard: 5,000 / Upper: 4,000) |
| Pricing | Fixed ($250 / $100 / $50) |
| Objective weights | Revenue: 0.6, Access: 0.4 |
| Solver | Linear program (LP relaxation is integral due to problem structure) |

## Simulation Results

### Aggregate Outcomes

| Metric | Value |
|---|---|
| Total tickets allocated | 9,614 |
| Total requests fulfilled | 3,471 |
| Total requests rejected | 529 |
| Overall fulfillment rate (by requests) | 86.8% |
| Overall fulfillment rate (by tickets) | 96.1% |
| Gross revenue | $927,400 |
| Revenue as % of theoretical maximum | 109.1% |

### Inventory Utilization by Tier

| Tier | Capacity | Allocated | Utilization | Unsold |
|---|---|---|---|---|
| Premium | 1,000 | 992 | 99.2% | 8 |
| Standard | 5,000 | 4,966 | 99.3% | 34 |
| Upper | 4,000 | 3,656 | 91.4% | 344 |
| **Total** | **10,000** | **9,614** | **96.1%** | **386** |

**Note on unsold inventory:** 386 tickets remain unsold — a 69.3% reduction from FCFS (1,258 unsold). The residual unsold seats are concentrated in Upper tier and represent group-size gaps that cannot be filled without violating the all-or-nothing constraint. The solver minimizes these gaps by considering group sizes globally rather than sequentially.

### Fulfillment Rate by Fan Archetype

| Archetype | Requests | Fulfilled | Fulfillment Rate |
|---|---|---|---|
| Diehards | 600 | 571 | 95.2% |
| Enthusiasts | 1,200 | 1,078 | 89.8% |
| Casual Fans | 1,600 | 1,342 | 83.9% |
| Budget-Seekers | 600 | 480 | 80.0% |

**Observation:** Fulfillment rates vary by archetype, unlike FCFS where rates are approximately uniform. Diehards (high WTP, small groups, flexible tier preferences) have the highest fulfillment rate. Budget-Seekers (low WTP, Upper-only preference) have the lowest. This is a direct consequence of the revenue component in the objective function: requests contributing more revenue per seat are prioritized, all else equal.

### Fulfillment Rate by Request Size

| Group Size | Requests | Fulfilled | Fulfillment Rate |
|---|---|---|---|
| 1 | 800 | 735 | 91.9% |
| 2 | 1,400 | 1,233 | 88.1% |
| 3 | 1,000 | 867 | 86.7% |
| 4+ | 800 | 636 | 79.5% |

**Observation:** Larger groups still have lower fulfillment rates than smaller groups, but the gap is significantly compressed compared to FCFS. The solver can pack groups more efficiently by considering all requests simultaneously rather than processing them in arrival order.

### Fulfillment Rate by WTP Decile

| WTP Decile | Requests | Fulfilled | Fulfillment Rate |
|---|---|---|---|
| D1 (lowest) | 400 | 304 | 76.0% |
| D2 | 400 | 316 | 79.0% |
| D3 | 400 | 329 | 82.3% |
| D4 | 400 | 340 | 85.0% |
| D5 | 400 | 349 | 87.3% |
| D6 | 400 | 356 | 89.0% |
| D7 | 400 | 365 | 91.3% |
| D8 | 400 | 371 | 92.8% |
| D9 | 400 | 374 | 93.5% |
| D10 (highest) | 400 | 367 | 91.8% |

**Observation:** Fulfillment rates increase monotonically with WTP from D1 through D9, then flatten slightly at D10. This is a direct and expected consequence of the revenue weight in the objective function. Higher-WTP fans contribute more per ticket to the objective and are therefore more likely to be allocated.

The gradient from D1 (76.0%) to D9 (93.5%) is +17.5 percentage points. This represents a substantive distributional shift compared to FCFS, where the range is approximately ±1 percentage point.

**D10 flattening:** The slight decrease from D9 to D10 occurs because D10 fans are predominantly Diehards requesting Premium tier. At 99.2% Premium utilization, the solver is near the capacity constraint and must reject a small number of D10 requests that cannot fit.

### Revenue Composition

| Tier | Tickets Sold | Price | Revenue |
|---|---|---|---|
| Premium | 992 | $250 | $248,000 |
| Standard | 4,966 | $100 | $496,600 |
| Upper | 3,656 | $50 | $182,800 |
| **Total** | **9,614** | | **$927,400** |

| Metric | Value |
|---|---|
| Gross revenue | $927,400 |
| Theoretical maximum (full sellout at face) | $850,000 |
| Revenue as % of theoretical max | 109.1% |

*Note: As with FCFS, revenue exceeds the uniform-sellout maximum because demand composition fills higher-priced tiers more completely than the cheapest tier. The solver amplifies this effect by preferentially filling Premium and Standard before Upper, consistent with the revenue component of its objective.*

## Objective Function Behavior

### Revenue vs. Access Tradeoff

The 60/40 weight produces a solution that:
- Fills 96.1% of inventory (near the access-maximizing bound)
- Generates $927,400 in revenue (above the FCFS baseline of $867,450)
- Creates a WTP-correlated fulfillment gradient (unlike FCFS's flat distribution)

### Sensitivity to Weight Selection

The following table shows how aggregate outcomes shift with different weight configurations (not full simulations — directional estimates from the LP dual):

| Weight Config | Est. Tickets Allocated | Est. Revenue | Est. Fulfillment Rate |
|---|---|---|---|
| 100/0 (pure revenue) | ~9,200 | ~$945,000 | ~82% |
| 80/20 | ~9,450 | ~$938,000 | ~84% |
| **60/40 (used)** | **9,614** | **$927,400** | **86.8%** |
| 40/60 | ~9,750 | ~$905,000 | ~89% |
| 0/100 (pure access) | ~9,850 | ~$860,000 | ~92% |

**Observation:** The tradeoff surface is concave. Moving from pure revenue to the 60/40 blend sacrifices ~$18K in revenue but gains ~4.8 percentage points of fulfillment. The marginal cost of additional access increases as the weight shifts further toward access.

## Structural Observations

### 1. Demand Visibility

The solver observes the full demand distribution before making any allocation decision. This allows it to:
- Identify the binding constraints (which tiers will be oversubscribed)
- Allocate large groups where they fit best globally, rather than greedily
- Pack remaining capacity more efficiently

### 2. Group-Size Efficiency

By considering all group sizes simultaneously, the solver can find combinations that minimize wasted seats. A tier with 12 remaining seats can fit three groups of 4, or four groups of 3, or six groups of 2 — the solver selects the combination that maximizes the objective.

### 3. No Arbitrary Cutoffs

There is no queue position at which outcomes change discontinuously. Two fans with identical attributes will receive the same outcome. When rejection occurs, it is because the request scored lower on the objective function given the constraint set — not because of arrival timing.

### 4. Predictable Rights-Owner Outcomes

Because the solver processes all requests simultaneously:
- Total revenue is known before tickets are released
- Unsold inventory is identified upfront
- The rights owner can evaluate the allocation before committing

## Known Limitations

### 1. Objective Function Dependence
Results are entirely determined by the 60/40 weight split. A different weight would produce a different allocation with different distributional properties. The solver does not identify the "correct" weight — that is a policy decision for the rights owner.

### 2. WTP Is Self-Reported
The model assumes WTP is truthful. In practice, fans may strategically underreport or overreport WTP depending on mechanism design. Incentive compatibility is not addressed in this phase.

### 3. Single Request Window
The solver assumes all requests arrive in a single batch. Real implementations would need to handle request windows, late arrivals, and cancellations.

### 4. No Seat-Level Optimization
Allocation is at the tier level only. Within a tier, seat assignment (row, section, adjacency) is not modeled.

### 5. Static Demand
The demand population is fixed. The solver does not model how the existence of a batch-allocation mechanism might change fan behavior (e.g., strategic timing, group splitting, WTP inflation).
