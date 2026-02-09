# Phase 0: Problem Definition

## 1. Problem Statement

The current dominant model for high-demand event ticket sales is **first-come-first-served (FCFS)**. Under FCFS, ticket inventory is released at a fixed time, and fans compete on speed to secure purchases. This creates several well-documented failure modes:

- **Race-condition dynamics**: Outcomes depend on network latency, device capability, and bot sophistication rather than genuine fan interest.
- **Unpredictable demand surges**: Simultaneous load spikes degrade system reliability and fan experience.
- **Opaque allocation**: Fans receive no explanation for why they did or did not obtain tickets.
- **Misalignment with rights-owner goals**: Promoters and artists have objectives (demographic reach, geographic distribution, pricing tiers) that FCFS cannot express or enforce.

This prototype investigates a **request-based allocation model** as an alternative. Instead of real-time competition, fans submit requests within a defined window, and an allocation engine assigns tickets after the window closes, subject to constraints defined by the rights owner (promoter, artist, team).

The platform (Ticketmaster) does **not** control pricing, inventory, onsale timing, or release strategy. The platform's role is to allocate and optimize **within** constraints set by rights owners.

---

## 2. Stakeholder Inputs

### 2.1 Fan Inputs

These are attributes submitted by individual fans during the request window. They represent demand signals, not entitlements.

| Input | Description |
|---|---|
| **Requested event** | The specific event the fan wants to attend |
| **Quantity requested** | Number of tickets (subject to per-order limits) |
| **Price-tier preference** | Which price tier(s) the fan is willing to accept |
| **Maximum willingness to pay** | Upper bound the fan will pay per ticket (if the system solicits this) |
| **Acceptable sections/zones** | Seating preferences (general area, not seat-level) |
| **Flexibility flags** | Whether the fan accepts partial fulfillment, alternate dates, or waitlist placement |

### 2.2 Promoter Constraints

These are **hard constraints** defined by rights owners. The allocation engine must treat them as inviolable — they are not suggestions, recommendations, or optimization targets.

| Constraint | Description |
|---|---|
| **Pricing tiers and prices** | The defined price points for each tier; the platform does not set or modify prices |
| **Inventory per tier** | Number of tickets available in each pricing tier |
| **Per-order ticket limits** | Maximum tickets a single request can receive |
| **Hold-backs and reserves** | Inventory withheld from general allocation (artist holds, sponsor blocks, accessibility reserves) |
| **Geographic or demographic rules** | Distribution requirements (e.g., minimum % to local zip codes, fan-club priority windows) |
| **Onsale window timing** | When the request window opens and closes |
| **Release strategy** | Whether inventory is released in phases or all at once |
| **Resale restrictions** | Any transfer or resale limitations attached to allocated tickets |

### 2.3 Platform Objectives

These are goals the allocation engine *may* pursue, but only when explicitly selected. No objective is assumed by default.

| Objective | Description |
|---|---|
| **Fulfillment rate** | Fraction of fan requests that receive any allocation |
| **Constraint satisfaction** | Degree to which all promoter constraints are met (must be 100% for hard constraints) |
| **Allocation explainability** | Whether every allocation decision can be justified in plain language |
| **Perceived fairness** | Fan sentiment regarding the transparency and equity of outcomes |
| **Revenue within constraints** | Total revenue generated, given fixed promoter-defined prices and tiers |
| **Predictability for rights owners** | Reducing variance in sell-through rates and demand forecasting |

---

## 3. Candidate Objective Functions

The following are candidate objective functions the allocation engine could optimize. **No function is selected at this stage.** Each has distinct tradeoffs that must be evaluated through simulation before a choice is made.

### 3.1 Maximize Total Fulfillment

**Formulation**: Maximize the number of fan requests that receive at least a partial allocation, subject to all promoter constraints.

- **Favors**: Broad access; distributes tickets across as many fans as possible.
- **Tradeoff**: May fragment allocations (e.g., fans who requested 4 tickets receive 1). Does not account for intensity of preference or willingness to pay.
- **Metric**: Fulfillment rate = (requests receiving ≥1 ticket) / (total requests).

### 3.2 Maximize Revenue Given Fixed Prices

**Formulation**: Maximize total revenue by allocating higher-priced tiers first to fans whose willingness-to-pay meets or exceeds the tier price, subject to all promoter constraints.

- **Favors**: Revenue generation within promoter-defined pricing; fills premium tiers before general admission.
- **Tradeoff**: Systematically disadvantages fans with lower budgets. May concentrate access among higher-income demographics. Requires careful framing — the platform is optimizing *allocation* given fixed prices, not setting prices.
- **Metric**: Total revenue = Σ (allocated tickets × tier price).

### 3.3 Maximize Weighted Fan Satisfaction

**Formulation**: Maximize a composite score that weights fulfillment, preference match (tier, section), and request completeness (full quantity vs. partial), subject to all promoter constraints.

- **Favors**: Quality of individual fan experience; rewards giving fans what they actually asked for.
- **Tradeoff**: Requires defining and justifying weights, which introduces subjectivity. Different weight vectors produce materially different allocations. Must be transparent about weight selection.
- **Metric**: Satisfaction score = Σ (w₁ × fulfillment_i + w₂ × preference_match_i + w₃ × completeness_i).

### 3.4 Minimize Maximum Unfairness (Egalitarian / Minimax)

**Formulation**: Minimize the worst-case outcome across all fans — i.e., no single fan or group of fans should be disproportionately disadvantaged by the allocation, subject to all promoter constraints.

- **Favors**: Equity; protects against systematic exclusion of any identifiable group.
- **Tradeoff**: May sacrifice aggregate efficiency. Could produce allocations where many fans receive mediocre outcomes to avoid one fan receiving a poor outcome. Defining "unfairness" requires an explicit metric (unmet demand, distance from preference, etc.).
- **Metric**: Minimize max(unmet_demand_i) across all fans i.

### 3.5 Hybrid: Pareto-Optimal Frontier

**Formulation**: Rather than selecting a single objective, compute the set of allocations that are Pareto-optimal across two or more objectives (e.g., fulfillment rate vs. revenue vs. fairness). Present the frontier to the rights owner for selection.

- **Favors**: Transparency; makes tradeoffs explicit rather than hiding them inside a single score.
- **Tradeoff**: Computationally more expensive. Requires rights owners to evaluate and choose among multiple feasible allocations. May be impractical for high-volume events without summarization.
- **Metric**: Set of non-dominated allocation vectors across chosen objective dimensions.

---

## 4. Assumptions

These are simplifying assumptions adopted for the prototype. Each is a candidate for relaxation in future iterations.

1. **Single-event scope**: The prototype models allocation for one event at a time. Multi-event bundles, season tickets, and cross-event demand interactions are out of scope.
2. **No seat-level granularity**: Allocation operates at the tier/zone level, not at individual seats. Seat adjacency, view quality, and row optimization are excluded unless explicitly requested.
3. **Synthetic demand only**: Fan populations and willingness-to-pay distributions are simulated. No proprietary or real-world Ticketmaster data is used.
4. **Perfect constraint information**: Promoter constraints are assumed to be fully specified, consistent, and known before the request window closes. Contradictory or incomplete constraints are not modeled.
5. **No bot or fraud modeling**: All fan requests are assumed to be genuine. Sybil attacks, bot-generated requests, and identity fraud are not modeled in Phase 0.
6. **Static pricing**: Prices are fixed by the promoter before the request window opens and do not change during or after allocation. Dynamic pricing is out of scope.
7. **Atomic request window**: All requests arrive within a single window. There is no modeling of early vs. late submission timing effects within the window.
8. **No secondary market**: Resale behavior, aftermarket pricing, and post-allocation transfers are not modeled.
9. **No payment or checkout friction**: If a fan is allocated tickets, the transaction is assumed to complete. Cart abandonment, payment failure, and hold expiration are not modeled.
10. **Demand exceeds supply**: The prototype focuses on oversubscribed events where allocation is non-trivial. Undersubscribed events (where all requests can be fulfilled) are a degenerate case that requires no solver.

---

## 5. Non-Goals

The following are explicitly **not** objectives of this prototype:

1. **Production readiness**: This is an internal prototype for simulation and analysis. It is not intended to handle real transactions, real inventory, or real fan data.
2. **Price optimization or dynamic pricing**: The platform does not set prices. The system allocates within promoter-defined price tiers. Any exploration of pricing is strictly simulation of promoter-defined scenarios.
3. **Resale market optimization**: The system does not model, predict, or optimize for secondary-market outcomes.
4. **Seat-level assignment**: Mapping allocations to specific seats (row, section, seat number) is a downstream problem not addressed here.
5. **Fan identity verification or anti-fraud**: Verifying that requestors are real, unique individuals is an operational concern outside this prototype's scope.
6. **User interface or fan-facing experience design**: No UI, UX, or front-end design is in scope.
7. **Regulatory compliance certification**: While the design is informed by regulatory awareness, this prototype does not constitute a compliance assessment.
8. **Recommendation of a "best" or "fairest" system**: The prototype enumerates feasible approaches and their tradeoffs. Normative claims require explicit metric definitions and stakeholder agreement.
9. **Real-time allocation**: The model assumes a batch-processing paradigm (collect requests, then allocate). Streaming or real-time allocation is not in scope.
10. **Integration with existing Ticketmaster systems**: No APIs, databases, or infrastructure dependencies are assumed or designed for.

---

## 6. Open Questions for Subsequent Phases

These questions are surfaced here and deferred for explicit resolution:

- Which objective function (or combination) should the prototype optimize? This requires stakeholder input.
- How should willingness-to-pay be elicited from fans without creating adverse incentive structures (e.g., fans inflating stated WTP)?
- What fairness definition is appropriate, and who decides?
- Should the prototype model phased releases (multiple allocation rounds) or a single batch?
- What sensitivity analyses are most informative for rights owners evaluating this model vs. FCFS?
