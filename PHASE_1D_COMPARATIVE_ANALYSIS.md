# Phase 1D — Comparative Analysis: FCFS vs. Batch Allocation

## Purpose

This document presents a side-by-side comparison of outcomes from the Phase 1B FCFS baseline and the Phase 1C allocation solver, operating under identical demand inputs and constraint conditions. The analysis is descriptive and comparative. It does not recommend one mechanism over the other.

---

## 1. Experimental Setup

### 1.1 Shared Demand Inputs

Both mechanisms process the identical demand population defined in Phase 1A:

| Parameter | Value |
|---|---|
| Total requests | 4,000 |
| Total tickets requested | ~18,000 |
| Oversubscription ratio | 1.8:1 |
| Fan archetypes | 4 (Diehard 15%, Enthusiast 30%, Casual 40%, Budget-Seeker 15%) |
| Group size range | 1–6 (weighted avg ~2.5) |
| WTP range | $20–$300 |

No requests are added, removed, or modified between simulations. The same 4,000 request objects — with identical group sizes, WTP values, tier preferences, and archetype labels — are used in both.

### 1.2 Shared Constraints

| Constraint | Specification |
|---|---|
| Total inventory | 10,000 tickets |
| Tier structure | Premium (1,000 @ $250), Standard (5,000 @ $100), Upper (4,000 @ $50) |
| Pricing | Fixed by rights owner; identical across mechanisms |
| Fulfillment rule | All-or-nothing (no partial group fills) |
| WTP feasibility | Fans cannot be placed in tiers priced above their WTP |
| Tier preference | Fans can only be placed in tiers on their preference list |

### 1.3 What Differs Between Mechanisms

| Dimension | FCFS (Phase 1B) | Allocation Solver (Phase 1C) |
|---|---|---|
| Processing mode | Sequential (one request at a time) | Batch (all requests simultaneously) |
| Ordering | Arrival order (uniform random) | None (arrival order ignored) |
| Optimization | Greedy (first available preferred tier) | Global (maximize weighted objective) |
| Demand visibility | None (future requests unseen) | Full (all requests visible before allocation) |
| Objective function | Implicit: serve the next fan in line | Explicit: 60% revenue + 40% access (weighted hybrid) |
| Backtracking | Not possible | Possible (solver explores alternative assignments) |

### 1.4 Fixed Parameters

- Arrival order is generated once and used by FCFS; the solver ignores it
- WTP values are drawn once and held constant
- No parameter tuning was performed to favor either mechanism
- The allocation solver's 60/40 weight split is a stated starting point, not an optimized value

---

## 2. Core Outcome Comparison

### 2.1 Aggregate Metrics

| Metric | FCFS | Allocation | Δ (Alloc − FCFS) | Δ % |
|---|---|---|---|---|
| Total tickets allocated | 8,742 | 9,614 | +872 | +10.0% |
| Total requests fulfilled | 3,196 | 3,471 | +275 | +8.6% |
| Total requests rejected | 804 | 529 | −275 | −34.2% |
| Fulfillment rate (by requests) | 79.9% | 86.8% | +6.9 pp | — |
| Fulfillment rate (by tickets) | 87.4% | 96.1% | +8.7 pp | — |
| Gross revenue | $867,450 | $927,400 | +$59,950 | +6.9% |
| Unsold inventory | 1,258 | 386 | −872 | −69.3% |

The allocation solver fulfills 275 more requests and allocates 872 more tickets from the same inventory pool, while simultaneously generating $59,950 more in gross revenue.

### 2.2 Fulfillment Rate by Fan Archetype

| Archetype | FCFS | Allocation | Δ (pp) |
|---|---|---|---|
| Diehards | 79.7% | 95.2% | +15.5 |
| Enthusiasts | 79.3% | 89.8% | +10.5 |
| Casual Fans | 80.2% | 83.9% | +3.7 |
| Budget-Seekers | 80.5% | 80.0% | −0.5 |

**FCFS pattern:** Approximately uniform across archetypes (~79–81%). Archetype has no influence on outcome.

**Allocation pattern:** Monotonically decreasing from Diehards (95.2%) to Budget-Seekers (80.0%). The gradient reflects the revenue component of the objective function: archetypes with higher WTP and more tier flexibility receive preferential allocation.

**Notable:** Budget-Seekers are the only archetype with a (marginally) lower fulfillment rate under allocation than under FCFS. The difference is −0.5 pp — within the noise range of a single simulation run. All other archetypes see gains ranging from +3.7 to +15.5 pp.

### 2.3 Fulfillment Rate by Request Size

| Group Size | FCFS | Allocation | Δ (pp) |
|---|---|---|---|
| 1 | 87.3% | 91.9% | +4.6 |
| 2 | 82.6% | 88.1% | +5.5 |
| 3 | 78.1% | 86.7% | +8.6 |
| 4+ | 70.0% | 79.5% | +9.5 |

Both mechanisms show decreasing fulfillment for larger groups. However, the penalty is substantially smaller under allocation:

- **FCFS group-size spread:** 17.3 pp (87.3% for singles vs. 70.0% for 4+)
- **Allocation group-size spread:** 12.4 pp (91.9% for singles vs. 79.5% for 4+)

The allocation solver reduces the group-size penalty by 4.9 pp because it can consider all group sizes simultaneously and pack inventory more efficiently, rather than processing requests in sequence and leaving fragmented capacity.

### 2.4 Distribution of Fulfillment by WTP Decile

| WTP Decile | FCFS Rate | Allocation Rate | Δ (pp) |
|---|---|---|---|
| D1 (lowest) | 80.5% | 76.0% | −4.5 |
| D2 | 79.8% | 79.0% | −0.8 |
| D3 | 79.0% | 82.3% | +3.3 |
| D4 | 80.3% | 85.0% | +4.7 |
| D5 | 79.5% | 87.3% | +7.8 |
| D6 | 80.8% | 89.0% | +8.2 |
| D7 | 79.3% | 91.3% | +12.0 |
| D8 | 80.5% | 92.8% | +12.3 |
| D9 | 80.0% | 93.5% | +13.5 |
| D10 (highest) | 79.5% | 91.8% | +12.3 |

**FCFS pattern:** Effectively flat across all deciles. WTP has no correlation with outcome.

**Allocation pattern:** Monotonically increasing from D1 (76.0%) through D9 (93.5%), with a slight flattening at D10 due to Premium capacity constraints.

**Crossover point:** The allocation solver produces lower fulfillment than FCFS for deciles D1 and D2 (fans with WTP $20–$55), approximately equal fulfillment at D3, and higher fulfillment for D4–D10. This crossover is a direct and expected consequence of including revenue weight in the objective function.

---

## 3. Rights-Owner Outcomes

### 3.1 Gross Revenue Comparison

| Metric | FCFS | Allocation | Δ |
|---|---|---|---|
| Gross revenue | $867,450 | $927,400 | +$59,950 (+6.9%) |
| Premium revenue | $233,500 | $248,000 | +$14,500 (+6.2%) |
| Standard revenue | $487,100 | $496,600 | +$9,500 (+2.0%) |
| Upper revenue | $146,850 | $182,800 | +$35,950 (+24.5%) |

Revenue gains come from two sources:
1. **Higher utilization of Premium and Standard tiers** (+$24,000 combined) — the solver packs these high-value tiers more tightly
2. **Substantially higher Upper-tier utilization** (+$35,950) — the solver allocates 719 more Upper-tier tickets by fitting groups more efficiently

### 3.2 Inventory Utilization by Tier

| Tier | FCFS Utilization | Allocation Utilization | Δ (pp) |
|---|---|---|---|
| Premium | 93.4% | 99.2% | +5.8 |
| Standard | 97.4% | 99.3% | +1.9 |
| Upper | 73.4% | 91.4% | +18.0 |
| **Overall** | **87.4%** | **96.1%** | **+8.7** |

The largest utilization gain is in the Upper tier (+18.0 pp), where FCFS leaves 1,063 seats unsold compared to allocation's 344. Both mechanisms have residual unsold Upper seats due to the all-or-nothing constraint, but the solver minimizes this fragmentation by globally optimizing group placement.

### 3.3 Unsold Inventory

| Tier | FCFS Unsold | Allocation Unsold | Δ |
|---|---|---|---|
| Premium | 66 | 8 | −58 |
| Standard | 129 | 34 | −95 |
| Upper | 1,063 | 344 | −719 |
| **Total** | **1,258** | **386** | **−872** |

Under FCFS, 12.6% of inventory goes unsold despite 1.8:1 oversubscription. Under allocation, unsold inventory drops to 3.9%. The 872-ticket difference represents demand that exists but is structurally unreachable by a sequential mechanism due to group-size fragmentation.

### 3.4 Visibility and Predictability

| Dimension | FCFS | Allocation |
|---|---|---|
| Revenue known before sale | No (depends on queue order) | Yes (computed before release) |
| Demand shape visible | No (revealed sequentially) | Yes (all requests observed) |
| Unsold inventory predictable | No (depends on arrival sequence) | Yes (identified during optimization) |
| Outcome variance across runs | High (different arrival orders → different results) | Zero (deterministic given same inputs) |

FCFS produces variable outcomes depending on the random arrival order. Running the same demand through FCFS with a different random seed would change total revenue, fulfillment rates, and per-archetype outcomes. The allocation solver produces the same output for the same input regardless of submission order.

---

## 4. Fan Experience Signals

### 4.1 Probability of Fulfillment by Archetype

| Archetype | FCFS | Allocation | Interpretation |
|---|---|---|---|
| Diehards | 79.7% | 95.2% | Allocation strongly favors high-WTP, flexible fans |
| Enthusiasts | 79.3% | 89.8% | Moderate gain from mid-range WTP and tier flexibility |
| Casual Fans | 80.2% | 83.9% | Small gain; lower WTP partially offset by access weight |
| Budget-Seekers | 80.5% | 80.0% | Approximately neutral; lowest WTP, single-tier preference |

Under FCFS, a fan's archetype provides no information about their likelihood of fulfillment. Under allocation, archetype is correlated with outcome. Whether this correlation is desirable depends on the rights owner's objectives — it is not inherently positive or negative.

### 4.2 Variance of Outcomes Within Similar Requests

**FCFS:** Two fans with identical archetypes, group sizes, WTP, and tier preferences can have opposite outcomes (one fulfilled, one rejected) based solely on arrival order. The within-group variance is driven entirely by the random queue position. Near the inventory-exhaustion boundary, outcome is effectively a coin flip for identically-situated fans.

**Allocation:** Two fans with identical attributes will always receive the same outcome. When ties exist (multiple requests with the same objective score competing for the last available capacity), the solver applies a deterministic tiebreaker. Outcome variance for identically-situated fans is zero.

### 4.3 Incidence of Arbitrary Cutoffs

**FCFS exhibits sharp binary cutoffs.** There exists a queue position (approximately request #3,200 in this simulation, varying by tier) beyond which fulfillment probability drops sharply. Fans at position 3,195 and 3,205 may have a 10-to-1 difference in fulfillment odds, despite having made their request within seconds of each other. This is the "cliff" effect inherent in sequential processing under capacity constraints.

**Allocation does not have position-based cutoffs.** Rejection is determined by a fan's objective score relative to competing requests, not by submission timing. The boundary between fulfilled and unfulfilled requests is defined by the constraint set and objective function, not by an arbitrary point in a queue.

However, allocation introduces a **different type of boundary:** the WTP threshold below which fulfillment probability declines. This boundary is continuous (not binary) and is visible in the D1–D3 fulfillment rates. Whether a score-based gradient is preferable to a position-based cliff is a value judgment, not a factual determination.

---

## 5. Structural Differences Observed

### 5.1 Mechanism-Design Differences (Not Objective Differences)

The following outcome differences arise from *how* each mechanism processes requests, not from *what* it optimizes for:

| Observation | Root Cause |
|---|---|
| Allocation fills 872 more seats from the same demand | Global group-size packing vs. sequential greedy allocation |
| FCFS leaves 1,063 Upper-tier seats unsold despite oversubscription | Late-arriving large groups cannot fit in fragmented remaining capacity |
| FCFS fulfillment is uncorrelated with WTP | Arrival order is random and WTP is invisible to the mechanism |
| Allocation fulfillment is monotonically correlated with WTP | Revenue weight in objective function prioritizes higher-WTP requests |
| FCFS outcomes vary across random seeds | Sequential processing is path-dependent |
| Allocation outcomes are deterministic | Batch optimization has a unique solution for these inputs |

### 5.2 Connection to Known FCFS Failure Modes

Phase 0 identified six failure modes of FCFS under excess demand. The simulation results confirm or qualify each:

| Failure Mode | Observed in Phase 1B? | Phase 1C Comparison |
|---|---|---|
| **Race-condition dynamics** | Confirmed: arrival order is the sole determinant of differential outcomes among identical fans | Eliminated: arrival order is not used |
| **Binary success/failure cliffs** | Confirmed: sharp fulfillment drop-off near queue position ~3,200 | Replaced by continuous WTP-based gradient |
| **No demand visibility** | Confirmed: FCFS cannot see the shape of demand before allocating | Addressed: solver observes full demand before any allocation |
| **Suboptimal revenue capture** | Partially confirmed: FCFS leaves $59,950 on the table relative to allocation, but FCFS still achieves >100% of the uniform-sellout benchmark | Solver captures +6.9% revenue through better tier packing |
| **Poor fan experience** | Not directly measurable in simulation (requires behavioral modeling) | Not directly measurable in simulation |
| **Inventory fragmentation** | Confirmed: 1,258 unsold tickets (12.6%) despite oversubscription | Reduced to 386 unsold (3.9%); 69.3% reduction in waste |

### 5.3 What Both Mechanisms Share

Both mechanisms produce the same outcomes on the following dimensions:

- Neither adjusts prices (fixed by rights owner)
- Both respect all-or-nothing fulfillment (no partial groups)
- Both reject requests for tiers priced above WTP
- Both operate within identical tier capacity limits
- Both leave some inventory unsold (the all-or-nothing constraint guarantees this under heterogeneous group sizes)
- Neither models secondary-market behavior

---

## 6. Known Tradeoffs and Limitations

### 6.1 Limitations of the Phase 1C Objective Function

The allocation solver's results are conditional on the 60/40 revenue-access weight split:

- A **higher revenue weight** would increase the WTP-fulfillment gradient, improving revenue but reducing fulfillment for low-WTP fans further
- A **higher access weight** would flatten the gradient toward FCFS-like uniformity, increasing total fulfillment but reducing revenue
- The 60/40 split is **not claimed to be optimal** — it is a parameter chosen to demonstrate the tradeoff surface

The solver also assumes:
- WTP is truthfully reported (no strategic behavior)
- All requests arrive in a single batch (no dynamic arrivals)
- The objective function is the correct one to use (a policy assumption, not a technical fact)

### 6.2 Scenarios Where FCFS Performs Comparably or Better

| Scenario | Why FCFS May Be Comparable or Preferable |
|---|---|
| **Low oversubscription** (demand ≤ capacity) | Both mechanisms can fulfill all requests; allocation's advantages diminish |
| **Homogeneous demand** (similar group sizes, similar WTP) | Less fragmentation and less scope for optimization; gains from batch processing shrink |
| **Budget-Seeker-heavy populations** | The allocation solver's revenue weight penalizes low-WTP fans; FCFS treats them equally |
| **Simplicity and transparency** | FCFS has a trivially explainable allocation rule ("first in line gets served"); batch allocation requires explaining an objective function and solver |
| **Speed of resolution** | FCFS resolves outcomes in real time; batch allocation requires a request window and processing delay |
| **No WTP information available** | If WTP cannot be inferred or collected, the revenue component of the objective function has no signal to optimize against |

### 6.3 What Conclusions Should NOT Be Drawn

1. **"Allocation is always better than FCFS."** The results are conditional on this specific demand population, oversubscription ratio, and objective function. Different conditions could produce different relative outcomes.

2. **"The 60/40 weight is the right balance."** The weight is a parameter, not a finding. Rights owners with different priorities would choose different weights and observe different outcomes.

3. **"FCFS is unfair."** FCFS treats all fans identically conditional on arrival order. Whether arrival-order-based allocation is "fair" or "unfair" is a normative question outside the scope of this analysis.

4. **"Allocation solves the ticketing problem."** This comparison addresses one dimension (allocation mechanism) under simplified conditions. Real-world ticketing involves bot mitigation, dynamic pricing decisions, multi-event strategies, seat-level optimization, and behavioral responses to mechanism design — none of which are modeled here.

5. **"Low-WTP fans are harmed by allocation."** D1 and D2 fulfillment rates are 4.5 and 0.8 pp lower under allocation than FCFS, respectively. Whether this constitutes "harm" depends on whether the comparison baseline (FCFS) is considered the normative default — a framing choice, not a factual determination.

6. **"Revenue gains justify the mechanism switch."** The $59,950 revenue difference (6.9%) is a simulation output, not a business case. Implementation costs, fan behavioral responses, and rights-owner preferences are not modeled.

---

## Appendix: Summary Statistics

| Metric | FCFS (1B) | Allocation (1C) | Δ |
|---|---|---|---|
| Tickets allocated | 8,742 | 9,614 | +872 |
| Requests fulfilled | 3,196 | 3,471 | +275 |
| Fulfillment rate (requests) | 79.9% | 86.8% | +6.9 pp |
| Fulfillment rate (tickets) | 87.4% | 96.1% | +8.7 pp |
| Gross revenue | $867,450 | $927,400 | +$59,950 |
| Unsold tickets | 1,258 | 386 | −872 |
| Premium utilization | 93.4% | 99.2% | +5.8 pp |
| Standard utilization | 97.4% | 99.3% | +1.9 pp |
| Upper utilization | 73.4% | 91.4% | +18.0 pp |
| Archetype fulfillment range | 79.3–80.5% | 80.0–95.2% | — |
| WTP decile fulfillment range | 79.0–80.8% | 76.0–93.5% | — |
| Group-size fulfillment spread | 17.3 pp | 12.4 pp | −4.9 pp |
| Outcome determinism | Stochastic (path-dependent) | Deterministic | — |
| Revenue visibility pre-sale | None | Full | — |
