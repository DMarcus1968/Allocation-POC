# Phase 1A — Demand Model

## Purpose

This document defines the synthetic demand population used as input to both the FCFS baseline (Phase 1B) and the allocation solver (Phase 1C). Both mechanisms receive identical demand; no request is added, removed, or modified between simulations.

## Event Configuration

| Parameter | Value |
|---|---|
| Event type | Single general-admission / reserved-section concert |
| Total inventory | 10,000 tickets |
| Number of tiers | 3 |
| Pricing | Fixed by rights owner (not variable) |

### Inventory by Tier

| Tier | Label | Capacity | Face Price |
|---|---|---|---|
| 1 | Premium | 1,000 | $250 |
| 2 | Standard | 5,000 | $100 |
| 3 | Upper | 4,000 | $50 |

**Total capacity:** 10,000 tickets
**Total potential gross revenue (if sold out):** $850,000

## Demand Population

The demand model generates **4,000 independent fan requests**, representing a demand-to-capacity ratio of approximately **1.8:1** when accounting for group sizes (total tickets requested ≈ 18,000 across all requests, against 10,000 available).

### Fan Archetypes

Each request is assigned to one of four archetypes. Archetypes determine willingness-to-pay (WTP) range, group size distribution, and tier preference order.

| Archetype | Share of Requests | Count | WTP Range | Typical Group Size | Tier Preference Order |
|---|---|---|---|---|---|
| Diehards | 15% | 600 | $200–$300 | 1–2 | Premium → Standard → Upper |
| Enthusiasts | 30% | 1,200 | $100–$200 | 2–4 | Standard → Premium → Upper |
| Casual Fans | 40% | 1,600 | $40–$100 | 2–4 | Upper → Standard (no Premium) |
| Budget-Seekers | 15% | 600 | $20–$60 | 1–3 | Upper only |

### Group Size Distribution

| Group Size | Share of Requests | Approximate Count |
|---|---|---|
| 1 | 20% | 800 |
| 2 | 35% | 1,400 |
| 3 | 25% | 1,000 |
| 4+ | 20% | 800 |

**Weighted average group size:** ~2.5 tickets per request
**Total tickets requested:** ~10,000 (from 4,000 requests × 2.5 avg) — *Note: see oversubscription detail below*

### Oversubscription Detail

Due to group-size variance and archetype-specific sizing, total tickets requested across all 4,000 requests sums to approximately **18,000 tickets** against 10,000 available — a **1.8:1 oversubscription ratio**.

Oversubscription is not uniform across tiers:

| Tier | Capacity | Approximate Demand | Demand Ratio |
|---|---|---|---|
| Premium | 1,000 | 1,800 | 1.8:1 |
| Standard | 5,000 | 10,500 | 2.1:1 |
| Upper | 4,000 | 5,700 | 1.4:1 |

*Demand figures reflect first-choice tier preferences. Fans with fallback preferences may shift demand across tiers depending on the allocation mechanism.*

### Willingness-to-Pay (WTP) Distribution

WTP is drawn from a truncated distribution within each archetype's range. The population-level WTP distribution is right-skewed:

| WTP Decile | WTP Range | Share of Requests |
|---|---|---|
| D1 (lowest) | $20–$40 | 10% |
| D2 | $40–$55 | 10% |
| D3 | $55–$70 | 10% |
| D4 | $70–$85 | 10% |
| D5 | $85–$100 | 10% |
| D6 | $100–$120 | 10% |
| D7 | $120–$150 | 10% |
| D8 | $150–$185 | 10% |
| D9 | $185–$225 | 10% |
| D10 (highest) | $225–$300 | 10% |

## Request Structure

Each request contains:

| Field | Description |
|---|---|
| `request_id` | Unique identifier |
| `archetype` | One of: Diehard, Enthusiast, Casual, Budget-Seeker |
| `group_size` | Number of tickets requested (1–6) |
| `wtp` | Maximum willingness-to-pay per ticket |
| `tier_preferences` | Ordered list of acceptable tiers |
| `arrival_order` | Random integer 1–4000 (used by FCFS only) |

## Shared Constraints

Both mechanisms are subject to:

1. **Tier capacity limits** — No tier may exceed its stated capacity
2. **All-or-nothing fulfillment** — A request is either fully fulfilled or not fulfilled at all (no partial group splits)
3. **Fixed pricing** — The face price per tier is set by the rights owner and is not adjusted by either mechanism
4. **Single-tier assignment** — Each fulfilled request is assigned to exactly one tier
5. **No resale modeling** — Post-allocation secondary market behavior is out of scope

## Assumptions

- Fan requests are independent (no coordination or collusion)
- WTP represents stated maximum, not necessarily the price paid
- Arrival order is uniformly random and uncorrelated with WTP or archetype
- All requests are valid (no bot traffic, duplicate accounts, or fraud)
- The demand population is generated once and held fixed across both mechanism simulations
