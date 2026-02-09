# Phase 1A — Demand Simulation Model

> **Status:** Draft
> **Depends on:** `claude.md` (governance constraints)
> **Consumed by:** Future allocation strategy phases (objective function and solver are **out of scope** here)

---

## 1. Purpose and Scope

### 1.1 What This Model Is For

This document defines a **synthetic fan demand generator** for simulating high-demand ticket onsales. Its purpose is to produce realistic-enough request populations that can stress-test different allocation strategies under controlled, repeatable conditions.

Specifically, this model:

- Represents a population of fans, each with individual preferences, willingness-to-pay, and quantity needs.
- Generates a complete set of ticket requests for a single onsale event.
- Provides tunable parameters so that the same model can produce widely different demand scenarios (e.g., mass-market pop concert vs. niche club show vs. prestige limited-run event).
- Remains **neutral to any allocation objective**—it produces demand; it does not decide how to satisfy it.

### 1.2 What This Model Does NOT Attempt

- **No allocation logic.** This model generates requests. It does not propose how to fulfill them.
- **No objective function.** It does not assume whether the goal is revenue maximization, access maximization, fairness, or any hybrid.
- **No real data.** All distributions and parameters are synthetic. No proprietary Ticketmaster data is referenced or implied.
- **No secondary market.** Resale behavior, speculative purchasing, and bot-driven demand are excluded.
- **No time-sequenced arrivals.** Requests are modeled as a batch (request window), not as a real-time queue. The model assumes fans submit requests within a collection period, consistent with the request-based allocation paradigm described in the governing constraints.
- **No seat-level geometry.** The model references sections and price tiers but does not model individual seat positions, sightlines, or adjacency graphs.
- **No dynamic pricing.** Prices are treated as fixed inputs set by the rights owner. The demand model reacts to prices; it does not influence them.

---

## 2. Fan Population Model

### 2.1 Individual Fan Representation

Each synthetic fan is represented as a record with the following attributes:

| Attribute | Type | Description |
|---|---|---|
| `fan_id` | unique identifier | Distinguishes each fan in the simulation |
| `archetype` | enum | One of the defined fan archetypes (see §2.2) |
| `wtp_max` | currency (float) | Maximum willingness-to-pay per ticket |
| `qty_requested` | integer (1–8) | Number of tickets requested |
| `together_required` | boolean | Whether all tickets must be in the same section |
| `section_preferences` | ordered list | Ranked list of acceptable sections/tiers |
| `substitution_tolerance` | float [0, 1] | Willingness to accept a non-preferred section (0 = rigid, 1 = fully flexible) |
| `price_flexibility` | float [0, 1] | Willingness to pay above their ideal price point for a better section (0 = none, 1 = fully flexible) |

### 2.2 Fan Archetypes

The model defines three archetypes. Each archetype governs the probability distributions from which fan attributes are drawn. The archetypes are not rigid categories—they are parameter bundles that produce characteristic demand patterns.

#### Casual Fan
- **Description:** Attends events opportunistically. Price-sensitive. Flexible on seating. Typically requests 1–2 tickets.
- **WTP tendency:** Low to moderate. Concentrated near face value of lower-priced tiers.
- **Quantity tendency:** Small (1–2).
- **Flexibility:** High substitution tolerance; low together-requirement rate.
- **Real-world analog:** Someone who sees an ad and decides to go if the price is right.

#### Committed Fan
- **Description:** Plans to attend. Has a target budget and section preference but will make reasonable trade-offs. Requests 2–4 tickets (often attending with a group).
- **WTP tendency:** Moderate. Willing to pay above face value of mid-tier sections but has a ceiling.
- **Quantity tendency:** Medium (2–4).
- **Flexibility:** Moderate substitution tolerance; moderate-to-high together-requirement rate.
- **Real-world analog:** A fan who registered for a presale and has a specific experience in mind.

#### Superfan
- **Description:** Will do almost anything to attend. High willingness-to-pay. Strong section preference (typically premium or closest-to-stage). Requests 1–4 tickets and strongly requires them together.
- **WTP tendency:** High. Long right tail; some are willing to pay multiples of face value.
- **Quantity tendency:** Small to medium (1–4).
- **Flexibility:** Low substitution tolerance (wants the best sections); high together-requirement rate.
- **Real-world analog:** A fan who joins every presale, follows the artist on tour, and treats attendance as non-negotiable.

### 2.3 Population Mix

The proportion of each archetype in the synthetic population is a **tunable parameter**, not a fixed assumption.

| Parameter | Default | Meaning |
|---|---|---|
| `pct_casual` | 0.50 | Fraction of fans who are Casual |
| `pct_committed` | 0.35 | Fraction of fans who are Committed |
| `pct_superfan` | 0.15 | Fraction of fans who are Superfans |

These must sum to 1.0. Changing the mix shifts the aggregate demand curve and stress-tests allocation strategies differently (e.g., a superfan-heavy population creates intense competition for premium inventory).

---

## 3. Willingness-to-Pay (WTP) Distributions

WTP is modeled **per ticket** and represents the maximum price a fan would accept before walking away entirely. The model provides three alternative distribution shapes that can be selected per scenario. All distributions are parameterized so that the same shape can be scaled and shifted.

> **Note:** All currency values below are illustrative. The distributions are defined by their shape and parameters, not by specific dollar amounts.

### 3.1 Distribution A — Broad / Mass-Market Demand

**Intuitive shape:** A bell curve centered around a moderate price, with relatively thin tails. Most fans cluster near a common willingness-to-pay, with few extreme-low or extreme-high outliers.

**Real-world approximation:** A large-venue pop or country concert where demand is wide but price sensitivity is relatively uniform. Most fans want to pay "around face value" with modest variance.

**Mathematical form:** Log-normal distribution (ensures WTP > 0 and provides a slight right skew).

**Parameters:**

| Parameter | Symbol | Meaning |
|---|---|---|
| `wtp_loc` | μ | Log-mean of the distribution (controls center) |
| `wtp_scale` | σ | Log-standard-deviation (controls spread) |

**Characteristics:**
- Median WTP close to the event's mid-tier face value.
- ~68% of fans fall within a narrow band.
- Very few fans at extreme high end.
- Produces demand curves where most inventory clears at similar prices.

### 3.2 Distribution B — Polarized Demand with Long Tail

**Intuitive shape:** A bimodal or heavily skewed distribution. A large cluster of fans at low WTP, a smaller cluster at high WTP, and a thin but meaningful tail extending to very high values.

**Real-world approximation:** A prestige event (e.g., farewell tour, championship game) where casual fans want cheap tickets, dedicated fans will pay a premium, and a small group will pay almost any price. There is a "gap" in the middle where few fans naturally fall.

**Mathematical form:** Mixture of two log-normal distributions with different means.

**Parameters:**

| Parameter | Symbol | Meaning |
|---|---|---|
| `wtp_loc_low` | μ₁ | Log-mean of the lower cluster |
| `wtp_scale_low` | σ₁ | Log-spread of the lower cluster |
| `wtp_loc_high` | μ₂ | Log-mean of the upper cluster |
| `wtp_scale_high` | σ₂ | Log-spread of the upper cluster |
| `mix_weight_high` | w | Probability of a fan being drawn from the upper cluster (0–1) |

**Characteristics:**
- Two distinct demand segments.
- A "valley" in mid-range WTP where few fans sit.
- Long right tail from the upper cluster.
- Stress-tests allocation when a single price tier must serve very different willingness-to-pay groups.

### 3.3 Distribution C — Whale-Heavy Demand with Extreme Outliers

**Intuitive shape:** A steep, sharply right-skewed distribution. The bulk of fans have moderate WTP, but a non-trivial fraction (the "whales") have WTP many multiples higher than the median. The tail is fat and long.

**Real-world approximation:** A limited-capacity, culturally significant event (e.g., Super Bowl, exclusive residency, reunion show) where scarcity drives extreme outlier behavior. A small group of fans or corporate buyers will pay 5–20× face value.

**Mathematical form:** Pareto-tailed distribution—log-normal body with a Pareto (power-law) tail above a threshold.

**Parameters:**

| Parameter | Symbol | Meaning |
|---|---|---|
| `wtp_loc_body` | μ | Log-mean of the body distribution |
| `wtp_scale_body` | σ | Log-spread of the body distribution |
| `tail_threshold` | x_min | WTP value above which the Pareto tail begins |
| `tail_exponent` | α | Pareto shape parameter (lower α = fatter tail = more extreme whales) |

**Characteristics:**
- Median fan has moderate WTP.
- Top 5% of fans may account for 30–50% of total willingness-to-pay in the population.
- Produces scenarios where revenue-maximizing and access-maximizing allocations diverge sharply.
- Useful for testing whether an allocation strategy is disproportionately influenced by outliers.

### 3.4 WTP by Archetype

Each archetype draws from the scenario's WTP distribution but with archetype-specific scaling:

| Archetype | WTP Multiplier (default) | Effect |
|---|---|---|
| Casual | 0.7 | Shifts the drawn WTP downward |
| Committed | 1.0 | Uses the distribution as-is |
| Superfan | 1.6 | Shifts the drawn WTP upward |

The multiplier is applied to the drawn WTP value: `fan.wtp_max = draw(distribution) × archetype_multiplier`. This preserves the distribution shape while shifting it per archetype.

---

## 4. Quantity and Flexibility Modeling

### 4.1 Requested Quantity

Each fan requests a number of tickets drawn from an archetype-specific discrete distribution.

| Archetype | Distribution | Support | Default Mean |
|---|---|---|---|
| Casual | Geometric-like (right-skewed) | {1, 2, 3, 4} | ~1.5 |
| Committed | Peaked around 2–3 | {1, 2, 3, 4, 5, 6} | ~2.8 |
| Superfan | Peaked around 2 | {1, 2, 3, 4} | ~2.0 |

Quantity is capped at a configurable maximum (`max_qty_per_request`, default: 8) reflecting typical onsale purchase limits imposed by the rights owner.

### 4.2 "Must Sit Together" vs. "Flexible" Requests

Each request has a boolean `together_required` flag, drawn per-archetype:

| Archetype | P(together_required = true) | Default |
|---|---|---|
| Casual | Low | 0.30 |
| Committed | Moderate-to-High | 0.70 |
| Superfan | High | 0.85 |

When `together_required = true`, all tickets in the request must be allocated to the **same section/tier**. When false, tickets may be split across sections if doing so satisfies the request.

> **Note on downstream impact:** The together-requirement constrains allocation solvers. This model only generates the flag; it does not determine how solvers handle it.

### 4.3 Substitution Tolerance

Substitution tolerance captures how willing a fan is to accept a section/tier other than their first preference. It is modeled as a continuous value in [0, 1]:

- **0.0** — Rigid. Will only accept their top-ranked section. If unavailable, the request is unfulfillable.
- **1.0** — Fully flexible. Will accept any section at or below their WTP.
- **Intermediate values** — Will accept sections ranked within the top `(substitution_tolerance × number_of_sections)` of their preference list.

Default distributions by archetype:

| Archetype | Substitution Tolerance Distribution | Default Mean |
|---|---|---|
| Casual | Beta(2, 2) — centered, moderate spread | 0.65 |
| Committed | Beta(3, 4) — skewed toward moderate | 0.45 |
| Superfan | Beta(2, 6) — skewed toward rigid | 0.25 |

### 4.4 Price Flexibility

Price flexibility captures willingness to pay above a fan's "ideal" price point in exchange for a better (higher-ranked) section. Modeled as a continuous value in [0, 1]:

- **0.0** — No price flexibility. Will not pay more than the face value of their preferred section.
- **1.0** — Fully flexible. Willing to pay up to their `wtp_max` regardless of section pricing.

Default distributions by archetype:

| Archetype | Price Flexibility Distribution | Default Mean |
|---|---|---|
| Casual | Beta(2, 5) — low | 0.25 |
| Committed | Beta(3, 3) — moderate | 0.50 |
| Superfan | Beta(5, 2) — high | 0.70 |

---

## 5. Tunable Parameters for Scenario Analysis

All parameters below are intended to be adjustable between simulation runs. No parameter is hard-coded.

### 5.1 Population Parameters

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `total_fans` | integer | 10,000 | Total number of fans generating requests |
| `pct_casual` | float [0,1] | 0.50 | Fraction of Casual fans |
| `pct_committed` | float [0,1] | 0.35 | Fraction of Committed fans |
| `pct_superfan` | float [0,1] | 0.15 | Fraction of Superfan fans |
| `max_qty_per_request` | integer | 8 | Maximum tickets any single fan can request |

### 5.2 WTP Distribution Parameters

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `wtp_distribution` | enum {A, B, C} | A | Which WTP distribution shape to use |
| `wtp_loc` | float | 4.5 (log-scale) | Log-mean for Distribution A |
| `wtp_scale` | float | 0.4 | Log-std-dev for Distribution A |
| `wtp_loc_low` | float | 4.0 | Log-mean of lower cluster (Dist B) |
| `wtp_scale_low` | float | 0.3 | Log-spread of lower cluster (Dist B) |
| `wtp_loc_high` | float | 5.5 | Log-mean of upper cluster (Dist B) |
| `wtp_scale_high` | float | 0.4 | Log-spread of upper cluster (Dist B) |
| `mix_weight_high` | float [0,1] | 0.25 | Upper-cluster weight (Dist B) |
| `wtp_loc_body` | float | 4.5 | Log-mean of body (Dist C) |
| `wtp_scale_body` | float | 0.3 | Log-spread of body (Dist C) |
| `tail_threshold` | float | 300.0 | Pareto tail start threshold (Dist C) |
| `tail_exponent` | float | 1.5 | Pareto shape α (Dist C); lower = fatter tail |

### 5.3 Archetype Behavior Parameters

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `wtp_multiplier_casual` | float | 0.7 | WTP scaling for Casual fans |
| `wtp_multiplier_committed` | float | 1.0 | WTP scaling for Committed fans |
| `wtp_multiplier_superfan` | float | 1.6 | WTP scaling for Superfans |
| `qty_mean_casual` | float | 1.5 | Mean quantity requested by Casual fans |
| `qty_mean_committed` | float | 2.8 | Mean quantity requested by Committed fans |
| `qty_mean_superfan` | float | 2.0 | Mean quantity requested by Superfans |
| `p_together_casual` | float [0,1] | 0.30 | P(together_required) for Casual |
| `p_together_committed` | float [0,1] | 0.70 | P(together_required) for Committed |
| `p_together_superfan` | float [0,1] | 0.85 | P(together_required) for Superfans |
| `sub_tol_casual_alpha` | float | 2.0 | Beta α for Casual substitution tolerance |
| `sub_tol_casual_beta` | float | 2.0 | Beta β for Casual substitution tolerance |
| `sub_tol_committed_alpha` | float | 3.0 | Beta α for Committed substitution tolerance |
| `sub_tol_committed_beta` | float | 4.0 | Beta β for Committed substitution tolerance |
| `sub_tol_superfan_alpha` | float | 2.0 | Beta α for Superfan substitution tolerance |
| `sub_tol_superfan_beta` | float | 6.0 | Beta β for Superfan substitution tolerance |
| `price_flex_casual_alpha` | float | 2.0 | Beta α for Casual price flexibility |
| `price_flex_casual_beta` | float | 5.0 | Beta β for Casual price flexibility |
| `price_flex_committed_alpha` | float | 3.0 | Beta α for Committed price flexibility |
| `price_flex_committed_beta` | float | 3.0 | Beta β for Committed price flexibility |
| `price_flex_superfan_alpha` | float | 5.0 | Beta α for Superfan price flexibility |
| `price_flex_superfan_beta` | float | 2.0 | Beta β for Superfan price flexibility |

### 5.4 Scenario-Level Parameters

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `demand_supply_ratio` | float | 3.0 | Ratio of total requested tickets to total available inventory. Controls oversubscription intensity. |
| `num_sections` | integer | 5 | Number of distinct sections/price tiers in the venue |
| `random_seed` | integer | None | Seed for reproducibility; None = non-deterministic |

---

## 6. Known Limitations

### 6.1 Simplified or Excluded Demand Behaviors

| Limitation | Description | Potential Downstream Impact |
|---|---|---|
| **No temporal dynamics** | All requests are treated as a simultaneous batch. There is no modeling of early-bird vs. late-arriving demand. | Allocation strategies that depend on arrival order cannot be tested. |
| **No social/network effects** | Fans make independent decisions. There is no modeling of group coordination, social media influence, or viral demand spikes. | May underestimate demand clustering (e.g., fan groups all targeting the same section). |
| **No bot or speculative demand** | The model assumes all requests are genuine fan demand. Automated bulk purchasing and resale-motivated demand are excluded. | Underestimates total request volume and overestimates the "quality" of the request pool in real-world conditions. |
| **No repeat interaction** | Each simulation is a one-shot event. There is no modeling of fan loyalty accrual, past purchase history, or learning across events. | Cannot evaluate allocation strategies that reward loyalty or past behavior. |
| **No cancellation or no-show** | Once a request is generated, it is assumed the fan will follow through if allocated. | Overestimates effective demand. Allocation strategies cannot account for expected attrition. |
| **Static preferences** | Fan preferences and WTP are fixed at generation time. There is no modeling of fans adjusting behavior in response to available options. | Cannot test allocation mechanisms that involve iterative fan interaction (e.g., counter-offers). |
| **Coarse venue geometry** | Sections are modeled as discrete tiers, not as spatially arranged seats. Adjacency, row depth, and view quality are not represented. | Allocation strategies that optimize seat-level placement cannot be tested without extending this model. |
| **Independence assumption** | Fan attributes are drawn independently (conditional on archetype). In reality, group members may have correlated preferences and WTP. | May produce unrealistically heterogeneous groups in multi-ticket requests. |
| **Three-archetype granularity** | Real fan populations are more continuous. Three archetypes are a simplification for tractability. | Edge-case demand patterns (e.g., corporate block buyers, accessibility-need fans) are not represented. |

### 6.2 Limitations That Could Materially Affect Downstream Results

The following limitations deserve particular attention when interpreting simulation outputs:

1. **Demand-supply ratio is exogenous.** The model sets oversubscription as a parameter rather than deriving it from population and pricing. This means the model cannot capture how pricing changes would shift total demand volume—only how a fixed demand pool interacts with a fixed supply.

2. **No bot/speculative demand** means any allocation strategy that appears to "solve" fairness in simulation may still fail in practice if a significant fraction of real requests are non-genuine.

3. **Independence of fans** may cause the model to understate contention for specific sections. If real-world demand clusters (e.g., 500 fans all wanting Section A, Row 1–5), the model may spread demand more uniformly than reality.

4. **Static WTP** means the model cannot evaluate mechanisms that reveal true preferences through interaction (e.g., ascending auctions, iterative bidding). Strategies that depend on fan response to offers require a different model.

---

## Appendix: Relationship to Governing Constraints

This model has been designed in compliance with the following constraints from `claude.md`:

| Constraint | How This Model Complies |
|---|---|
| No allocation logic (§ Objective Function Discipline) | This model generates demand only. No allocation or optimization is proposed. |
| No assumed objective function | WTP distributions are provided as inputs to future solvers; this model does not favor any objective. |
| No proprietary data (§ Modeling Scope) | All parameters and distributions are synthetic. |
| Explainability (§ Explainability Requirements) | Every parameter is named, typed, defaulted, and described. Distribution choices are justified intuitively. |
| Iterative development (§ Iterative Development Mode) | The model starts with three archetypes and three distribution shapes—minimal viable complexity. Extensions are noted in Limitations. |
| No speed/time-pressure mechanics (§ Fairness) | The model uses batch requests, not time-sequenced arrivals. |
| Promoter inputs as hard constraints (§ Governance) | Venue capacity, section structure, and price tiers are treated as external inputs, not model outputs. |
