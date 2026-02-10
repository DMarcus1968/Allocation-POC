# Phase 2A — Revenue Optimization Objective (Within Promoter Constraints)

## Purpose

This document defines a **revenue-focused allocation objective** that a rights owner may explicitly select as an alternative to the fulfillment-oriented hybrid objective used in Phase 1C. It specifies the objective function, required guardrails, allocation logic, explainability requirements, expected outcome differences, and known risks.

**This objective is opt-in.** It is never applied as a default. The platform does not recommend, prefer, or assume revenue optimization. It is offered as one option on a menu of allocation objectives, selectable only by the rights owner for a specific event, with full visibility into the tradeoffs involved.

---

## 1. Objective Definition

### 1.1 Formal Objective Function

Given the set of all requests R, the set of tiers T, and the binary decision variable x(i,t) indicating whether request i is assigned to tier t, the revenue objective is:

```
Maximize: Z_rev = Σ_{i ∈ R} Σ_{t ∈ T} price(t) × group_size(i) × x(i,t)
```

Subject to all constraints enumerated in Section 2.

In plain language: **maximize total gross revenue from allocated tickets at fixed face prices, subject to all promoter-defined constraints and system guardrails.**

### 1.2 How This Differs from the Phase 1C Objective

The Phase 1C solver used a **weighted hybrid objective**:

```
Phase 1C: Z_hybrid = 0.6 × Σ price(t) × group_size(i) × x(i,t)
                    + 0.4 × Σ fulfilled(i) × normalization_constant
```

The Phase 1C objective balanced two goals — revenue (60%) and access (40%) — producing an interior solution on the revenue-access tradeoff surface.

The Phase 2A revenue objective differs in three specific ways:

| Dimension | Phase 1C (Hybrid) | Phase 2A (Revenue) |
|---|---|---|
| Objective function | Weighted sum of revenue and access | Revenue only |
| Access incentive | Built into the objective (0.4 weight) | Not in the objective; enforced via guardrails |
| Allocation gradient | Moderate WTP-fulfillment correlation | Stronger WTP-fulfillment correlation, bounded by guardrails |

The Phase 1C objective produces access as a *goal*. The Phase 2A objective produces access as a *constraint* — a floor to be met, not a value to be maximized.

### 1.3 What This Objective Does NOT Optimize

The revenue objective explicitly does **not** optimize for:

- **Fulfillment rate.** Maximizing the number of fulfilled requests is not a goal of this objective. Fulfillment is protected only by the minimum-fulfillment guardrail (Section 2.2).
- **Access parity across WTP levels.** Fans with lower WTP will, all else equal, have lower fulfillment probability. The objective does not seek to equalize access across WTP deciles.
- **Fairness as defined by equal treatment.** Unlike FCFS, which treats all fans identically conditional on arrival order, and unlike Phase 1C, which partially weights access, this objective explicitly prioritizes requests that contribute more gross revenue per ticket.
- **Fan satisfaction or experience.** Subjective experience metrics are not modeled and not optimized.
- **Secondary-market outcomes.** Resale behavior is out of scope.

### 1.4 Opt-In Requirement

The revenue objective may only be activated when:

1. The rights owner explicitly selects it from available objective options
2. The rights owner acknowledges the tradeoff profile (higher revenue, potentially lower access for low-WTP segments)
3. The selection is recorded in the event configuration as an auditable parameter

The platform must never default to revenue optimization. If no objective is specified, the system must prompt the rights owner for an explicit selection before proceeding.

---

## 2. Additional Constraints and Guardrails

### 2.1 Inviolable Constraints (Inherited from Phase 0)

The following hard constraints from Phase 0 and Phase 1A remain in force and **cannot be relaxed, overridden, or modified** by the revenue objective:

| # | Constraint | Specification |
|---|---|---|
| C1 | **Tier capacity limits** | No tier may exceed its stated capacity (Premium ≤ 1,000; Standard ≤ 5,000; Upper ≤ 4,000) |
| C2 | **All-or-nothing fulfillment** | A request is either fully fulfilled in one tier or not fulfilled at all; no partial group splits |
| C3 | **Fixed pricing** | Tier prices are set by the rights owner ($250 / $100 / $50) and are not modified by the solver |
| C4 | **WTP feasibility** | A request can only be assigned to a tier priced at or below its stated WTP |
| C5 | **Tier preference compliance** | A request can only be assigned to a tier listed in its preference order |
| C6 | **Single-tier assignment** | Each request is assigned to at most one tier |
| C7 | **No price modification** | The allocation mechanism does not set, adjust, suggest, or influence ticket prices |

**Constraint C3 and C7 deserve emphasis:** The revenue objective maximizes revenue *within* the rights owner's existing pricing structure. It does not introduce dynamic pricing, surge pricing, price discrimination, or any form of price adjustment. Revenue gains come exclusively from which requests are allocated to which tiers — never from changing what a ticket costs.

### 2.2 Revenue-Specific Guardrails

The following guardrails are introduced specifically for the revenue objective to prevent pathological outcomes that pure revenue maximization could produce if unconstrained:

| # | Guardrail | Type | Default | Description |
|---|---|---|---|---|
| G1 | **Minimum fulfillment rate** | Mandatory | 70% of requests | The solver must fulfill at least this fraction of total requests. Prevents the solver from rejecting large numbers of low-revenue requests to concentrate inventory on high-revenue ones. |
| G2 | **Maximum per-archetype fulfillment drop** | Mandatory | No archetype may fall below 60% fulfillment | Prevents any single fan segment from being systematically excluded. Ensures that even the lowest-WTP archetype retains meaningful access. |
| G3 | **Group-request priority preservation** | Mandatory | N/A | Group requests (size ≥ 2) must not be displaced solely to accommodate singles requesting the same tier at the same price. The solver must not break the principle that groups — who represent shared social experiences — are not disadvantaged relative to equivalent singles. |
| G4 | **Per-entity ticket limit** | Mandatory | As set by rights owner (default: 6 per request) | No single request may exceed the per-entity ticket limit. This constraint exists in Phase 0 but is restated here because revenue optimization could otherwise incentivize consolidation into fewer, larger requests. |
| G5 | **Maximum WTP-decile concentration** | Promoter-configurable | No single WTP decile may receive more than 20% of total allocated tickets | Prevents extreme concentration of allocations in the highest-WTP segment. Configurable by the rights owner — may be relaxed (e.g., to 30%) or tightened (e.g., to 15%). |
| G6 | **Minimum tier utilization** | Promoter-configurable | Each tier must achieve at least 50% utilization if sufficient eligible demand exists | Prevents the solver from entirely abandoning low-revenue tiers. Configurable by the rights owner based on venue or event-specific considerations. |

### 2.3 Guardrail Classification

**Mandatory guardrails** (G1–G4) are system-enforced and cannot be disabled by the rights owner. They exist to prevent outcomes that would be structurally harmful regardless of the rights owner's stated preferences:

- G1 and G2 prevent mass exclusion of fan segments
- G3 preserves the group-first allocation principle established in Phase 0
- G4 enforces existing per-entity limits

**Promoter-configurable guardrails** (G5–G6) have sensible defaults but can be adjusted by the rights owner within defined bounds. The rights owner may:

- Relax G5 from 20% to a maximum of 35% (allowing more concentration)
- Tighten G5 below 20% (forcing more distribution)
- Adjust G6 upward (requiring higher minimum utilization per tier)
- Disable G6 only with explicit acknowledgment that some tiers may be underutilized

---

## 3. Revenue-Aware Allocation Logic

### 3.1 Overview

When the rights owner selects the revenue objective, the allocation solver replaces the Phase 1C hybrid objective function with the revenue-only objective defined in Section 1.1, while retaining all hard constraints (Section 2.1) and adding the guardrails (Section 2.2). The solver remains a batch-mode optimizer: it collects all requests in a window and allocates simultaneously.

### 3.2 Step-by-Step Allocation Process

**Step 1: Request Collection**

All requests are collected during the request window. Each request contains the same fields as Phase 1A: `request_id`, `archetype`, `group_size`, `wtp`, `tier_preferences`, and `arrival_order` (recorded but not used for prioritization).

**Step 2: Feasibility Filtering**

For each request, compute the set of feasible tier assignments:
- A tier is feasible for request i if:
  - The tier appears in i's `tier_preferences`
  - The tier's face price ≤ i's `wtp`
  - The tier has not been marked infeasible by prior constraint analysis
- Requests with no feasible tier assignments are immediately marked as infeasible and excluded from the optimization. These requests would be rejected under any objective.

**Step 3: Revenue Scoring**

For each feasible (request, tier) pair, compute the revenue contribution:
```
revenue_score(i, t) = price(t) × group_size(i)
```

This score represents the gross revenue generated if request i is assigned to tier t. The solver will attempt to maximize the sum of these scores across all assignments.

**Step 4: Constraint Assembly**

The solver assembles the full constraint set:
- Hard constraints C1–C7 (Section 2.1)
- Mandatory guardrails G1–G4 (Section 2.2)
- Promoter-configurable guardrails G5–G6 at their configured values

**Step 5: Optimization**

The solver solves the constrained optimization problem:
```
Maximize:    Σ_{i,t} price(t) × group_size(i) × x(i,t)
Subject to:  C1–C7, G1–G6
```

The solver is a linear program. Because each request is assigned to at most one tier (binary assignment) and the constraint matrix is totally unimodular under the all-or-nothing and single-assignment constraints, the LP relaxation yields integral solutions.

**Step 6: Guardrail Verification**

After the solver produces a candidate allocation, verify all guardrails are satisfied:
- Compute overall fulfillment rate → must meet G1 threshold
- Compute per-archetype fulfillment rates → each must meet G2 threshold
- Verify no group request was displaced by singles in violation of G3
- Verify per-entity limits are respected (G4)
- Compute per-WTP-decile allocation shares → must satisfy G5
- Compute per-tier utilization → must satisfy G6

If any guardrail is violated, the solver re-runs with the binding guardrail(s) added as explicit constraints. This is a verification step, not a heuristic — the guardrails are enforced as hard constraints in the optimization.

**Step 7: Tiebreaking**

When multiple feasible allocations produce identical revenue (e.g., two requests of the same group size competing for the last slot in a tier at the same price), ties are broken deterministically using the following cascade:

1. **Larger group size first** — preserves group-experience priority
2. **Broader tier-preference list first** — rewards flexibility, improves packing efficiency
3. **Lower request_id first** — arbitrary but deterministic final tiebreaker

This tiebreaking order is fixed and not configurable. It ensures that the allocation is fully deterministic and reproducible.

**Step 8: Outcome Recording**

For every request, the solver records:
- Assignment decision (fulfilled with tier assignment, or rejected)
- The reason for rejection, if applicable (see Section 4)
- The revenue contribution of the assignment
- Which constraints were binding at the time of the decision

### 3.3 How Higher-WTP Requests Are Prioritized

The revenue objective prioritizes higher-WTP requests through the structure of the objective function, **without violating any existing policy**:

**Mechanism:** A request with WTP = $250 eligible for Premium tier contributes $250 × group_size to the objective when assigned to Premium. A request with WTP = $50 eligible only for Upper contributes $50 × group_size. The solver naturally prefers the higher-revenue assignment when capacity is scarce.

**What this does NOT do:**

- **Does not change prices.** The fan with WTP = $250 pays $250 (the face price of Premium). The fan with WTP = $50 pays $50 (the face price of Upper). No fan pays more or less than face price for their assigned tier.
- **Does not violate group-first policy.** A group of 3 with moderate WTP is not displaced by 3 singles with higher individual WTP, because G3 prevents singles from displacing groups requesting the same tier at the same price. The solver may allocate higher-WTP groups ahead of lower-WTP groups, but group integrity is preserved.
- **Does not violate per-entity ticket limits.** The solver cannot consolidate demand or exceed per-request limits (G4) to increase revenue.
- **Does not override tier preferences.** A fan who listed only Upper cannot be assigned to Standard or Premium, regardless of the revenue benefit. Fans are only placed in tiers they explicitly listed as acceptable.

**Where prioritization occurs:** When two requests are both eligible for the same tier and capacity is limited, the request contributing more revenue to the objective is preferred. This means:
- Between two singles competing for the last Premium seat, the one with higher WTP (who is eligible for Premium) is preferred
- Between two groups of equal size competing for Standard, the solver is indifferent (same price × same size = same revenue) and applies the tiebreaker
- A group of 4 for Standard ($400 total) is preferred over a group of 2 for Standard ($200 total) when both compete for limited Standard capacity — this is a natural consequence of the objective, not a special rule

---

## 4. Explainability and Optics

### 4.1 Individual Allocation Explanations

Every fulfilled or rejected request must be accompanied by a plain-language explanation. The explanation framework differs from Phase 1C because the objective function has changed.

**For fulfilled requests:**

> "Your request for [N] tickets was fulfilled in [Tier] at $[Price] per ticket. This event used a request-based allocation system. All requests were evaluated simultaneously based on the event's allocation criteria, and your request was accommodated within available inventory."

**For rejected requests — capacity exhaustion:**

> "Your request for [N] tickets could not be fulfilled. Demand for your preferred tier(s) exceeded available inventory, and your request was not selected in the final allocation. [Total requests] fans requested tickets for this event, and [fulfilled count] were accommodated. No additional inventory is available at this time."

**For rejected requests — no feasible tier:**

> "Your request for [N] tickets could not be fulfilled. The tier(s) you selected were either fully allocated or priced above the maximum you indicated. No alternative placement was available within your stated preferences."

### 4.2 What Explanations Must NOT Say

Explanations must never:

- State or imply that the fan was rejected because their willingness-to-pay was too low
- Reference the revenue objective by name or describe the optimization goal
- Compare the fan's WTP to other fans' WTP
- Suggest the fan would have been fulfilled if they had indicated a higher budget
- Use language implying the platform controls pricing or decided who "deserves" tickets
- Reference specific competing requests or their attributes

### 4.3 What Explanations May Say When Asked

If a fan or rights owner requests more detail about the allocation mechanism, the system may provide:

> "This event used a batch-allocation system where all requests were collected during the request window and evaluated simultaneously. The rights owner selected an allocation objective that prioritizes inventory utilization and revenue within fixed pricing. All requests were subject to the same constraints: tier capacity limits, group-size requirements, and the pricing set by the event organizer. The system does not adjust prices or treat any fan differently based on personal characteristics."

### 4.4 Rights-Owner Tradeoff Communication

When a rights owner selects the revenue objective, the system must present the following tradeoff summary **before** the objective is confirmed:

> **Revenue Optimization Objective — Tradeoff Summary**
>
> You have selected the revenue optimization objective for this event. Under this objective:
>
> - The allocation system will prioritize assignments that generate higher gross revenue at your fixed tier prices.
> - Fans eligible for higher-priced tiers will have an increased probability of fulfillment relative to a fulfillment-maximizing or first-come-first-served approach.
> - Fans eligible only for lower-priced tiers may have a reduced probability of fulfillment, subject to the minimum-fulfillment guardrail.
> - Total fulfilled requests may be lower than under a fulfillment-maximizing objective, because the solver may prefer fewer higher-revenue assignments over more lower-revenue ones.
> - All ticket prices remain exactly as you have set them. The allocation system does not change, suggest, or influence pricing.
>
> **Guardrails in effect:**
> - Minimum [X]% of requests must be fulfilled
> - No fan segment may fall below [Y]% fulfillment
> - Group requests are protected from displacement by singles
> - Per-entity ticket limits remain enforced
>
> Do you wish to proceed with this objective?

### 4.5 Avoiding Platform Price-Control Language

All system outputs — fan-facing, rights-owner-facing, and internal — must adhere to the language and framing rules established in Phase 0 (claude.md, Section 6):

- **Never say:** "The system decided this ticket should go to a higher-paying fan."
- **Instead say:** "Given the event's allocation criteria and available inventory, this assignment was determined by the solver."
- **Never say:** "Revenue optimization chose to reject your request."
- **Instead say:** "Demand exceeded available inventory for your preferred tier(s)."
- **Never say:** "The platform maximized revenue for this event."
- **Instead say:** "The rights owner selected an allocation objective that considers revenue within their fixed pricing structure."

The platform's role is execution within constraints. The rights owner's role is defining the objective and pricing. All language must maintain this separation.

---

## 5. Comparative Outcome Expectations

This section describes **qualitative expectations** for how outcomes under the Phase 2A revenue objective would differ from Phase 1C (hybrid) and Phase 1B (FCFS). No simulations have been run; these are directional predictions based on the structure of the objective function and constraints.

### 5.1 Expected Differences vs. Phase 1C (Fulfillment-Hybrid)

| Dimension | Phase 1C (Hybrid 60/40) | Phase 2A (Revenue) | Expected Direction |
|---|---|---|---|
| Gross revenue | $927,400 | Higher | Revenue is the sole objective; the solver will find assignments that the hybrid objective traded away for access |
| Total requests fulfilled | 3,471 (86.8%) | Lower | Without access weight, the solver has no incentive to fulfill low-revenue requests beyond the guardrail minimum |
| WTP-fulfillment gradient | Moderate (76.0%–93.5%) | Steeper | Higher-WTP requests contribute more to the objective; the gradient will be amplified |
| Low-WTP fulfillment (D1–D2) | 76.0%–79.0% | Lower, bounded by G2 | These segments contribute least to revenue; fulfillment will approach but not breach the guardrail floor |
| High-WTP fulfillment (D8–D10) | 91.8%–93.5% | Higher | These segments are strongly preferred by the objective function |
| Premium tier utilization | 99.2% | Similar or marginally higher | Already near capacity under hybrid; limited room for improvement |
| Upper tier utilization | 91.4% | Lower | The solver may leave more Upper-tier seats unsold if filling them requires displacing higher-tier allocations |
| Inventory fragmentation | 386 unsold | Potentially higher | Fewer low-revenue requests fulfilled means more residual capacity in cheaper tiers |

**Key insight:** The revenue objective is expected to produce a **Pareto-different** outcome from Phase 1C — higher revenue but lower fulfillment — not a Pareto-dominant one. The rights owner gains revenue at the cost of access breadth.

### 5.2 Expected Differences vs. Phase 1B (FCFS Baseline)

| Dimension | Phase 1B (FCFS) | Phase 2A (Revenue) | Expected Direction |
|---|---|---|---|
| Gross revenue | $867,450 | Materially higher | Both tier-packing efficiency and revenue-aware prioritization contribute |
| Total requests fulfilled | 3,196 (79.9%) | Likely higher, but by a smaller margin than Phase 1C | Batch processing eliminates fragmentation waste; guardrails ensure minimum access |
| WTP-fulfillment correlation | None (flat ~80%) | Strong positive correlation | Structural consequence of the objective function |
| Group-size penalty | 17.3 pp spread | Reduced | Batch processing handles groups more efficiently regardless of objective |
| Outcome determinism | Stochastic | Deterministic | Batch allocation is path-independent |
| Arrival-order dependence | Total | None | Same as Phase 1C |

**Key insight:** Relative to FCFS, the revenue objective is expected to deliver gains on **both** revenue and total access (due to better packing), while introducing a WTP-correlated fulfillment gradient that FCFS does not exhibit. The revenue gains relative to FCFS come from two distinct sources — mechanism efficiency and objective-driven prioritization — whereas Phase 1C gains came primarily from mechanism efficiency with moderate prioritization.

### 5.3 Where Revenue Gains Are Expected to Originate

Revenue gains under Phase 2A are expected to come from the following sources, none of which involve price changes:

1. **Higher-tier packing.** The solver will prioritize filling Premium and Standard tiers to capacity before allocating Upper-tier requests. When a fan is eligible for both Standard ($100) and Upper ($50), the solver prefers the Standard assignment because it generates more revenue. This shifts the tier-utilization mix upward.

2. **WTP-aware demand selection.** When capacity is scarce in a given tier, the solver selects requests that contribute more revenue. A group of 4 requesting Standard ($400 total contribution) is preferred over a group of 2 requesting Standard ($200 total). Among equal-size requests for the same tier, those with higher WTP (and therefore eligibility for higher tiers as fallbacks) are more likely to be retained.

3. **Reduced low-revenue allocations.** Under the hybrid objective, the access weight incentivized the solver to fill cheap-tier seats even when the revenue contribution was minimal. Under pure revenue, the solver has no such incentive beyond the guardrail floor. Seats that would have been allocated to low-WTP, low-tier requests may instead remain unsold if no high-revenue alternative exists — but the minimum utilization guardrail (G6) bounds this effect.

4. **Elimination of arrival-order inefficiency.** Same as Phase 1C: batch processing eliminates the fragmentation and group-size penalties inherent in sequential FCFS allocation, capturing revenue from seats that FCFS would have left unsold.

---

## 6. Known Risks and Limitations

### 6.1 Scenarios Where Revenue Optimization May Materially Reduce Access

| Scenario | Risk | Mechanism |
|---|---|---|
| **Low-demand events** (demand ≤ 1.2× capacity) | Revenue optimization provides little benefit but may still shift allocations away from low-WTP fans unnecessarily | The solver maximizes revenue even when all requests could be fulfilled; some requests may be rejected to place others in higher-revenue tiers |
| **Homogeneous-WTP populations** | The solver has minimal signal to differentiate requests, but may still create arbitrary winners and losers among similar fans | Tiebreaking becomes the primary allocation mechanism, reducing the explainability of outcomes |
| **Budget-Seeker-heavy events** | A large fraction of demand may be below the guardrail-protected minimum, compressing the fulfillment of other segments | Guardrails ensure Budget-Seekers are not eliminated but may reduce the solver's ability to optimize across segments |
| **Events with political or social sensitivity** | Any visible correlation between fan income/budget and ticket access creates optics risk | Even though the system does not know fan income, WTP-correlated allocation can be perceived as income-based exclusion |

### 6.2 Optics Risks

| Risk | Description |
|---|---|
| **"Pay-to-play" perception** | If fans learn that willingness-to-pay influences allocation, the system may be perceived as favoring wealthier fans — even though prices are fixed and the rights owner selected the objective |
| **Regulatory scrutiny** | Revenue optimization in ticketing is subject to heightened scrutiny in multiple jurisdictions. The system must be able to demonstrate that prices are not dynamic and that the rights owner, not the platform, selected the objective |
| **Media framing** | Outcomes can be framed as "Ticketmaster algorithm rejects budget fans" regardless of the nuances of the mechanism. The system must produce audit trails that demonstrate constraint compliance and rights-owner selection |
| **Comparison to FCFS** | Fans accustomed to FCFS (where WTP has no effect) may perceive any WTP-correlated outcome as unfair, even if total access is higher |

### 6.3 Conflicts with Promoter Goals

The revenue objective may conflict with rights-owner goals in non-obvious ways:

- **Fan-base cultivation:** A promoter seeking to build a younger or broader audience may not want low-WTP fans systematically deprioritized, even if short-term revenue increases.
- **Venue atmosphere:** Events benefit from full venues. If revenue optimization leaves more seats unsold (especially in visible upper tiers), the in-venue experience may suffer despite higher per-ticket revenue.
- **Long-term loyalty:** Fans who are repeatedly rejected under revenue optimization may disengage from the artist or venue over time, reducing future demand.
- **Sponsor expectations:** Some sponsors value total attendance over per-ticket revenue. Revenue optimization that reduces headcount may conflict with sponsorship agreements.

### 6.4 What Cannot Be Concluded Without Phase 2B

The following questions **cannot** be answered by Phase 2A alone and require a full tradeoff analysis (Phase 2B) with simulation:

| Question | Why It Requires Phase 2B |
|---|---|
| What is the exact revenue gain from switching to the revenue objective? | Requires running the solver with the revenue objective against the Phase 1A demand population |
| How many additional fans are rejected compared to Phase 1C? | Requires computing the allocation under both objectives and comparing fulfillment counts |
| At what guardrail settings does revenue optimization become effectively equivalent to the hybrid objective? | Requires parametric analysis across guardrail configurations |
| Does the minimum-fulfillment guardrail (G1) ever bind in practice? | Depends on the specific demand population and oversubscription ratio |
| Is the revenue gain material enough to justify the access reduction? | Requires both quantitative results and a rights-owner-specific value judgment |
| How sensitive are outcomes to the configurable guardrail settings (G5, G6)? | Requires sensitivity analysis across parameter ranges |
| What is the Pareto frontier between revenue and access for this demand population? | Requires sweeping objective weights and guardrail values systematically |

### 6.5 Structural Limitations of Revenue Optimization

- **WTP is self-reported.** The revenue objective assumes WTP reflects genuine willingness to pay. If fans learn that higher stated WTP increases allocation probability, strategic inflation may occur — undermining the signal the objective relies on. Incentive compatibility is not addressed in this phase.
- **Revenue is not profit.** The objective maximizes gross revenue at face price. It does not account for variable costs, marketing costs, or the economic value of filled vs. empty seats. A rights owner optimizing for net margin might make different choices than one optimizing for gross revenue.
- **Single-event scope.** Revenue optimization considers one event in isolation. A rights owner managing a tour or season may prefer to sacrifice single-event revenue to maximize lifetime fan value — a multi-event objective not modeled here.
- **No behavioral feedback.** The model does not capture how the existence of a revenue-optimizing allocation mechanism changes fan behavior over time (e.g., fans learning to overstate WTP, fans disengaging, fans shifting to secondary markets).

---

## Appendix: Relationship to Prior Phases

| Phase | Relationship to Phase 2A |
|---|---|
| **Phase 0** | Defines governance constraints and system boundaries. All Phase 0 constraints (C1–C7) are inherited without modification. Phase 0's requirement that the objective function be explicitly stated and auditable is the foundation for Phase 2A's opt-in design. |
| **Phase 1A** | Defines the demand model. Phase 2A does not modify any demand parameters. The same population, archetypes, WTP distributions, and group sizes apply. |
| **Phase 1B** | Establishes the FCFS baseline. Phase 2A uses FCFS outcomes as one comparison point for qualitative expectations (Section 5.2). |
| **Phase 1C** | Defines the hybrid allocation solver. Phase 2A replaces the Phase 1C objective function while retaining its constraint structure and batch-processing mechanism. The allocation logic (Section 3) is a modification of the Phase 1C solver, not a new system. |
| **Phase 1D** | Provides the comparative framework. Phase 2A extends Phase 1D's analysis by introducing a third mechanism for comparison. Quantitative comparison requires Phase 2B. |
| **Phase 2B** (future) | Will run the Phase 2A revenue objective against the Phase 1A demand population and produce quantitative results, enabling direct comparison with Phase 1B and 1C outcomes. |
