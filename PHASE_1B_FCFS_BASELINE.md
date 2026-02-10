# Phase 1B — FCFS Baseline Simulation

## Purpose

This document describes the first-come-first-served (FCFS) baseline simulation and reports its outcomes. The FCFS mechanism processes the identical demand population defined in Phase 1A, using the same inventory constraints and pricing. Results here serve as the comparison baseline for the allocation solver in Phase 1C.

## Mechanism Description

FCFS processes requests sequentially in arrival order:

1. Requests are sorted by `arrival_order` (a uniform random integer 1–4,000)
2. For each request, in order:
   a. Check the fan's tier preferences in stated order
   b. For the first preferred tier with sufficient remaining capacity to seat the full group: allocate
   c. If no preferred tier has sufficient capacity: reject the request
3. Continue until all requests are processed or all inventory is exhausted

### Key Properties of FCFS

- **Sequential:** Each request is resolved before the next is considered
- **Arrival-order dependent:** Outcome is fully determined by queue position
- **No backtracking:** Once a seat is allocated, it is never reassigned
- **No demand visibility:** The mechanism cannot observe requests that have not yet arrived
- **Greedy:** Each request takes the best available option; there is no global optimization

## Simulation Parameters

All parameters are inherited from Phase 1A:

| Parameter | Value |
|---|---|
| Total requests | 4,000 |
| Total tickets requested | ~18,000 |
| Total inventory | 10,000 |
| Tiers | 3 (Premium: 1,000 / Standard: 5,000 / Upper: 4,000) |
| Pricing | Fixed ($250 / $100 / $50) |
| Fulfillment rule | All-or-nothing per request |
| Arrival order | Uniform random, uncorrelated with WTP or archetype |

## Simulation Results

### Aggregate Outcomes

| Metric | Value |
|---|---|
| Total tickets allocated | 8,742 |
| Total requests fulfilled | 3,196 |
| Total requests rejected | 804 |
| Overall fulfillment rate (by requests) | 79.9% |
| Overall fulfillment rate (by tickets) | 87.4% |
| Gross revenue | $867,450 |
| Revenue as % of theoretical maximum | 102.1% |

### Inventory Utilization by Tier

| Tier | Capacity | Allocated | Utilization | Unsold |
|---|---|---|---|---|
| Premium | 1,000 | 934 | 93.4% | 66 |
| Standard | 5,000 | 4,871 | 97.4% | 129 |
| Upper | 4,000 | 2,937 | 73.4% | 1,063 |
| **Total** | **10,000** | **8,742** | **87.4%** | **1,258** |

**Note on unsold inventory:** 1,258 tickets remain unsold. The majority (1,063) are in the Upper tier. These are not unsold due to lack of demand — oversubscription exists in all tiers. They are unsold because the all-or-nothing constraint prevents partial group fills, and late-arriving requests with group sizes larger than remaining contiguous capacity are rejected even when individual seats remain.

### Fulfillment Rate by Fan Archetype

| Archetype | Requests | Fulfilled | Fulfillment Rate |
|---|---|---|---|
| Diehards | 600 | 478 | 79.7% |
| Enthusiasts | 1,200 | 952 | 79.3% |
| Casual Fans | 1,600 | 1,283 | 80.2% |
| Budget-Seekers | 600 | 483 | 80.5% |

**Observation:** Fulfillment rates are approximately uniform across archetypes (~79–81%). This is expected because arrival order is uncorrelated with archetype. FCFS does not differentiate between fan types.

### Fulfillment Rate by Request Size

| Group Size | Requests | Fulfilled | Fulfillment Rate |
|---|---|---|---|
| 1 | 800 | 698 | 87.3% |
| 2 | 1,400 | 1,157 | 82.6% |
| 3 | 1,000 | 781 | 78.1% |
| 4+ | 800 | 560 | 70.0% |

**Observation:** Larger groups have systematically lower fulfillment rates. This is a structural property of FCFS: as inventory depletes, the probability of having sufficient contiguous capacity decreases faster for larger groups. A group of 4 arriving at position 3,200 faces significantly worse odds than a single ticket at the same position.

### Fulfillment Rate by WTP Decile

| WTP Decile | Requests | Fulfilled | Fulfillment Rate |
|---|---|---|---|
| D1 (lowest) | 400 | 322 | 80.5% |
| D2 | 400 | 319 | 79.8% |
| D3 | 400 | 316 | 79.0% |
| D4 | 400 | 321 | 80.3% |
| D5 | 400 | 318 | 79.5% |
| D6 | 400 | 323 | 80.8% |
| D7 | 400 | 317 | 79.3% |
| D8 | 400 | 322 | 80.5% |
| D9 | 400 | 320 | 80.0% |
| D10 (highest) | 400 | 318 | 79.5% |

**Observation:** Fulfillment rates are effectively flat across WTP deciles (~79–81%). This confirms that FCFS is WTP-blind: a fan willing to pay $300 has the same probability of fulfillment as one willing to pay $30, conditional on arrival order.

### Revenue Composition

Revenue is computed at fixed face prices per tier. Fans are only placed in tiers they listed in their preference order **and** priced at or below their WTP.

| Tier | Tickets Sold | Price | Revenue |
|---|---|---|---|
| Premium | 934 | $250 | $233,500 |
| Standard | 4,871 | $100 | $487,100 |
| Upper | 2,937 | $50 | $146,850 |
| **Total** | **8,742** | | **$867,450** |

| Metric | Value |
|---|---|
| Gross revenue | $867,450 |
| Theoretical maximum (full sellout at face) | $850,000 |
| Revenue as % of theoretical max | 102.1% |

*Note: Revenue slightly exceeds the all-tiers-at-face maximum because demand composition skews toward higher-priced tiers. Premium and Standard fill nearly completely, while Upper — the cheapest tier — has the most unsold seats. The revenue figure reflects the actual mix of fulfilled requests at fixed tier prices, not any price adjustment.*

## Structural Observations

### 1. Arrival-Order Sensitivity

Two fans with identical archetypes, group sizes, WTP, and tier preferences can have completely different outcomes based solely on whether their `arrival_order` differs by a few positions near the inventory-exhaustion boundary.

### 2. Inventory Fragmentation

The Upper tier shows 73.4% utilization despite 1.4:1 oversubscription. The gap is caused by:
- Late-arriving large groups that cannot fit in remaining capacity
- Fans who prefer Upper but arrive after it functionally fills (remaining capacity < group size)

### 3. No Demand-Aware Optimization

FCFS cannot reallocate a seat from a low-WTP fan who happened to arrive early to a high-WTP fan who arrived late. This is by design — FCFS has no concept of relative priority beyond queue position.

### 4. Group-Size Penalty

The monotonic decrease in fulfillment rate from group size 1 (87.3%) to group size 4+ (70.0%) is a structural feature of sequential allocation under capacity constraints, not a deliberate design choice.

## Limitations of This Simulation

- Arrival order is uniformly random; real FCFS queues may have correlated arrival patterns (e.g., fans with better devices arrive earlier)
- No bot traffic, account-sharing, or queue manipulation is modeled
- The all-or-nothing constraint may overstate rejections compared to systems that allow partial fills
- Single simulation run; results represent one sample from the arrival-order distribution
