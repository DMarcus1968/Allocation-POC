# Phase 0: Problem Definition

## 1. Context

This document defines the problem space for a ticket allocation and yield optimization system that replaces real-time, first-come-first-served (FCFS) ticket sales with a request-based allocation model. The system operates within constraints set by rights owners (promoters, artists, teams), and the platform's role is allocation and optimization within those constraints only.

## 2. Core Assumptions

- **Demand exceeds supply** for the events under consideration.
- **Fan preferences are heterogeneous**: fans differ in willingness-to-pay, tier preference, and sensitivity to allocation outcome.
- **Rights owners define hard constraints**: pricing bands, inventory caps, hold-backs, and release timing are inputs, not decision variables.
- **Perfect information is not assumed**: the system operates on estimated demand distributions, not realized demand.
- **No resale optimization**: the system does not account for or optimize secondary-market outcomes.

## 3. Candidate Objective Functions

The allocation system requires an explicit objective function. Below are five candidate objectives, each with a formal definition, key metric, and description of tradeoffs against the other candidates.

### 3.1 Maximize Total Revenue

**Formulation:** Allocate tickets to maximize the sum of ticket prices paid across all allocated tickets, subject to inventory and pricing-band constraints set by the rights owner.

**Key Metric:** Total gross revenue (sum of face-value prices for all allocated tickets).

**Tradeoffs:** Prioritizing revenue tends to favor higher-priced tiers and fans with greater willingness-to-pay. This can reduce the number of fans served at lower price points and concentrate access among higher-spending segments. It may conflict with access breadth and perceived fairness objectives.

#### Pathological Outcome If Overweighted

When revenue maximization is pursued in isolation, the allocator systematically routes all inventory toward the highest willingness-to-pay segments, effectively pricing out the majority of the fan population. In a concrete scenario, a general-admission concert with 20,000 seats could see 90%+ of tickets allocated to premium-tier buyers while thousands of fans willing to pay face value in standard tiers receive nothing. This produces an allocation that resembles an auction outcome rather than a managed-access system, eroding the predictability and broad-access properties that distinguish the request-based model from FCFS. Over repeated events, the fan population that engages with the request system narrows to high-spend segments, reducing the platform's demand signal quality for events where rights owners prioritize reach over yield.

### 3.2 Maximize the Number of Fans Served

**Formulation:** Allocate tickets to maximize the total count of distinct fans who receive at least one ticket, subject to inventory and per-fan quantity constraints.

**Key Metric:** Total number of unique fans receiving an allocation.

**Tradeoffs:** Maximizing fan count tends to favor single-ticket allocations and lower-priced tiers. This can reduce per-fan satisfaction (e.g., splitting groups), lower total revenue, and may not reflect fan preference for specific tiers or quantities. It treats all allocations as equally valuable regardless of fan willingness-to-pay or preference strength.

#### Pathological Outcome If Overweighted

When fan count maximization is the sole objective, the allocator fragments group requests into single-ticket allocations to serve the maximum number of distinct individuals. A fan requesting four adjacent seats for a family outing receives one ticket, while three unrelated individuals each receive one ticket from the remaining inventory. Across the event, the majority of attendees arrive alone despite having requested group seating, producing a measurably worse experience that the allocation system is not instrumented to detect. The resulting dissatisfaction drives down future participation in the request system, as fans learn that the mechanism penalizes group attendance in favor of headcount.

### 3.3 Maximize Aggregate Fan Utility

**Formulation:** Allocate tickets to maximize the sum of individual fan utility scores, where each fan's utility is a function of the tier received, quantity received, and the difference between their willingness-to-pay and the price paid (consumer surplus).

**Key Metric:** Sum of fan utility scores across all allocations (utility function must be defined explicitly per scenario).

**Tradeoffs:** Utility maximization requires modeling fan preferences, which introduces estimation error and assumptions about utility functional form. It can favor fans with more intense preferences (higher reported willingness-to-pay), potentially reducing access breadth. Results are sensitive to how utility is defined and calibrated.

#### Pathological Outcome If Overweighted

When aggregate utility maximization dominates, the allocator becomes highly sensitive to the utility model's assumptions, and misspecification in that model drives systematic misallocation. If the utility function overweights consumer surplus, fans who understate their willingness-to-pay receive disproportionate allocations because the gap between their reported ceiling and the tier price appears large. This creates an incentive for strategic misreporting, where fans learn to deflate stated willingness-to-pay to increase their surplus score. Over successive events, the demand signal degrades as reported preferences diverge from actual preferences, and the allocator optimizes against a distorted input distribution rather than genuine fan demand.

### 3.4 Minimize Allocation Inequality

**Formulation:** Allocate tickets to minimize dispersion in allocation outcomes across the fan population, measured by the Gini coefficient or similar inequality metric over a defined outcome variable (e.g., consumer surplus, probability of receiving any ticket).

**Key Metric:** Gini coefficient (or analogous dispersion metric) of the chosen outcome variable across the fan population.

**Tradeoffs:** Inequality minimization can produce allocations that ignore fan preference intensity, compressing variation in outcomes. This may reduce total revenue and aggregate utility by constraining the allocator from matching high-value fans to high-value inventory. It also requires a normative choice about which outcome variable to equalize.

#### Pathological Outcome If Overweighted

When inequality minimization is applied aggressively, the allocator converges on uniform-probability random lottery behavior, disregarding all preference and willingness-to-pay signals. In a scenario with tiered inventory (e.g., floor, lower bowl, upper deck), the system distributes each tier proportionally across the entire fan population rather than matching fans to tiers they prefer. Fans with strong tier preferences—and the willingness to pay for them—receive random tier assignments at the same rate as indifferent fans. The resulting allocation leaves high-value inventory underutilized relative to demand while generating revenue substantially below the rights owner's floor, triggering constraint violations that the inequality metric does not capture.

### 3.5 Maximize Rights-Owner Objective Compliance

**Formulation:** Allocate tickets to maximize the degree to which the allocation satisfies a composite set of rights-owner-specified targets, including revenue floors, demographic reach goals, hold-back utilization rates, and promotional allocation quotas.

**Key Metric:** Weighted compliance score across rights-owner-defined targets (weights and targets defined per event).

**Tradeoffs:** This objective subordinates fan-side outcomes to rights-owner preferences, which may reduce fan utility, access breadth, or perceived fairness. The composite score can obscure which sub-objectives are being sacrificed. It also requires the rights owner to specify well-defined, non-contradictory targets, which may not always be feasible.

#### Pathological Outcome If Overweighted

When rights-owner compliance is maximized without balancing fan-side objectives, the allocator treats contradictory or poorly calibrated owner targets as binding, producing allocations that satisfy the composite score while delivering poor fan outcomes. For example, if a rights owner specifies both a high revenue floor and a promotional hold-back of 30% of inventory for a sponsor's customer list, the system may allocate the remaining 70% exclusively to premium tiers to meet the revenue target, leaving standard-tier fans entirely unserved. The composite compliance score registers as high because both sub-targets are met, but the allocation excludes the majority of the requesting fan population. This failure mode is difficult to detect through the compliance metric alone, since the metric is designed to reflect owner satisfaction rather than allocation quality from the fan perspective.

## 4. Tradeoff Summary

No single objective dominates across all evaluation criteria. Selecting an objective function—or a weighted combination—requires explicit input from stakeholders. The system must be capable of evaluating allocations under any of the above objectives and reporting comparative outcomes transparently.

## 5. Next Steps

- Define a synthetic event scenario with concrete inventory, pricing, and demand parameters.
- Implement allocation solvers for each candidate objective.
- Run comparative simulations and report outcome distributions across all five metrics.
