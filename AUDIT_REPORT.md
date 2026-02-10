# Consistency Audit Report

**Scope:** PHASE_0_PROBLEM_DEFINITION.md, PHASE_1A_DEMAND_MODEL.md, PHASE_1B_FCFS_BASELINE.md, PHASE_1C_ALLOCATION_SOLVER.md

**Date:** 2026-02-10

**Rule:** This report only states what exists or what is missing. No new features are proposed. No improvements are suggested.

---

## 1. Hard Constraints Verification

Phase 0 §4 defines five promoter-defined hard constraints (HC-1 through HC-5). The table below traces each constraint through Phase 1B and Phase 1C.

### HC-1: Tier Capacity

| Document | Where | How Enforced |
|---|---|---|
| Phase 0 §4 | Definition | "Each pricing tier has a fixed seat count. The system must never allocate more tickets in a tier than the capacity allows." |
| Phase 1B §4.1 | Enforcement | Checked on every allocation: request rejected if `remaining_capacity < group_size`. Capacity decremented atomically per request. |
| Phase 1C §5 | Enforcement | Modeled as a capacity constraint in the solver. Verified post-solve as an assertion (§5.1, assertion 1). |

**Status:** Enforced in both phases. No gap.

### HC-2: Per-Request Limit

| Document | Where | How Enforced |
|---|---|---|
| Phase 0 §4 | Definition | "Maximum number of tickets a single request may receive." |
| Phase 1B §4.1 | Enforcement | Deferred to Phase 1A §2.2. Requests exceeding the limit never enter the FCFS queue. |
| Phase 1C §5 | Enforcement | Validated at input. Requests exceeding the limit are rejected before the solver runs, with reason `exceeds_per_request_limit`. |

**Status:** Enforced in both phases via input validation. Both phases rely on Phase 1A to generate conforming requests, plus their own pre-processing rejection. No gap.

### HC-3: Group Integrity

| Document | Where | How Enforced |
|---|---|---|
| Phase 0 §4 | Definition | "A group request must be fulfilled entirely or not at all. Partial fills are not permitted." |
| Phase 1B §4.1 | Enforcement | All-or-nothing check: `remaining_capacity >= group_size`. No partial fills. |
| Phase 1C §5 | Enforcement | Each request is an atomic unit in the solver's solution space. Verified post-solve as an assertion (§5.1, assertion 2). |

**Status:** Enforced in both phases. No gap.

### HC-4: Tier Eligibility

| Document | Where | How Enforced |
|---|---|---|
| Phase 0 §4 | Definition | "A request targets a specific tier. The system does not reassign requests across tiers **unless explicitly configured by the promoter**." |
| Phase 1B §4.1 | Enforcement | "Each request targets exactly one tier. FCFS does not reassign across tiers." |
| Phase 1C §5 | Enforcement | "Each request is associated with exactly one tier. The solver does not move requests across tiers." |

**Status:** Enforced in both phases. **Finding:** Phase 0 includes the clause "unless explicitly configured by the promoter," which leaves open a promoter-configured cross-tier reassignment mode. Neither Phase 1B nor Phase 1C implements or acknowledges this clause. This is not a violation — the current phases simply do not implement the optional mode — but the conditional clause in Phase 0 has no corresponding mechanism in either downstream document.

### HC-5: Singles Policy

| Document | Where | How Enforced |
|---|---|---|
| Phase 0 §4 | Definition | "The promoter defines whether single-ticket requests are accepted and under what conditions." |
| Phase 1A §2.3 | Configuration | Three modes defined: `allowed`, `filler_only`, `rejected`. |
| Phase 1B §4.2 | Enforcement | `allowed`: interleaved by submission time. `filler_only`: two-pass processing (groups first, then singles). `rejected`: singles excluded before processing. |
| Phase 1C §4.1 | Enforcement | `allowed`: single allocation phase, no distinction. `filler_only`: two-phase allocation (Phase A groups, Phase B singles). `rejected`: singles excluded before solver runs. |

**Status:** Enforced in both phases across all three modes. No gap.

### Summary

| Constraint | Phase 1B | Phase 1C | Finding |
|---|---|---|---|
| HC-1 Tier Capacity | Enforced | Enforced + post-solve assertion | Consistent |
| HC-2 Per-Request Limit | Enforced via input validation | Enforced via input validation | Consistent |
| HC-3 Group Integrity | Enforced | Enforced + post-solve assertion | Consistent |
| HC-4 Tier Eligibility | Enforced | Enforced | Phase 0's "unless explicitly configured" clause is unimplemented |
| HC-5 Singles Policy | Enforced (3 modes) | Enforced (3 modes) | Consistent |

---

## 2. Singles Policy Verification

### 2.1 Does the system ever prefer single-ticket requests?

**No.** Under no documented configuration does the system give singles priority over group requests.

- Under `allowed`: singles and groups compete equally. No preference in either direction.
- Under `filler_only`: groups are explicitly processed first. Singles are structurally subordinate.
- Under `rejected`: singles are excluded entirely.

**However, one interaction exists that is not explicitly addressed in the documents:**

Under `allowed` mode combined with the **Maximize Access** objective (Phase 1C §3), the solver maximizes the number of distinct requests fulfilled. A single-ticket request consumes 1 seat and counts as 1 fulfilled request. A group request of 4 consumes 4 seats and counts as 1 fulfilled request. The solver would therefore allocate capacity to singles over groups because singles are four times more "efficient" per seat for the access-count objective. This is not a preference embedded in the allocation order — it is a mathematical consequence of the objective function formulation. The documents do not explicitly acknowledge this interaction.

### 2.2 Allocation order

**(a) Group requests:**

| Phase | Order |
|---|---|
| Phase 1B | Submission-time order (ascending). Under `filler_only`, groups are processed in Pass 1 before any singles. |
| Phase 1C | Selected by objective function optimization. Ties broken by random lottery. Under `filler_only`, groups are processed in Phase A before any singles. |

**(b) Single requests:**

| Phase | Order |
|---|---|
| Phase 1B, `allowed` | Interleaved with groups by submission-time order. No distinction from groups. |
| Phase 1C, `allowed` | Compete in a single allocation phase with groups. No sequencing distinction. |

**(c) Singles-as-filler:**

| Phase | Order |
|---|---|
| Phase 1B, `filler_only` | Pass 2: processed in submission-time order against remaining capacity after all groups. |
| Phase 1C, `filler_only` | Phase B: selected by random lottery against remaining capacity after Phase A is finalized. |

**Finding:** Phase 1B uses **submission-time order** for singles-as-filler. Phase 1C uses **random lottery**. This is a deliberate design difference, not an inconsistency — Phase 1B is an arrival-time baseline and Phase 1C is a lottery-based system. Both are internally consistent with their own design principles.

### 2.3 Can singles ever displace a feasible group allocation?

| Phase | Answer | Where Stated |
|---|---|---|
| Phase 1B | **No.** | §4.2: "A single request **never displaces** a group request, even if the group request arrives later in submission time." |
| Phase 1C | **No.** | §4.2: "A single-ticket request can never displace a feasible group allocation. Phase B only runs after Phase A is finalized." |

**Status:** Both phases explicitly confirm that singles cannot displace groups under `filler_only`. Phase 1C includes a post-solve assertion (§5.1, assertion 4) to verify this property.

Under `allowed` mode, the question is inapplicable — the promoter has explicitly chosen to let singles compete on equal terms with groups. There is no displacement because there is no sequencing.

---

## 3. Explainability Verification

### 3.1 Phase 1C Fulfilled Request Explanation Categories

Phase 1C §6.2 defines three categories:

| # | Category | Template Present | Human-Readable |
|---|---|---|---|
| 1 | **Selected by objective** | Yes | Yes — "Your request for {n} tickets in {tier} was fulfilled. The allocation optimized for {objective} across all eligible requests." |
| 2 | **Selected by lottery** | Yes | Yes — "Your request for {n} tickets in {tier} was fulfilled. Among equally eligible requests, yours was selected by random lottery." |
| 3 | **Singles filler** | Yes | Yes — "Your request for 1 ticket in {tier} was fulfilled as a filler allocation after group requests were processed." |

### 3.2 Phase 1C Rejected Request Explanation Categories

Phase 1C §6.3 defines seven categories:

| # | Reason Code | Template Present | Human-Readable |
|---|---|---|---|
| 1 | `capacity_exhausted` | Yes | Yes |
| 2 | `group_exceeds_remaining` | Yes | Yes |
| 3 | `displaced_by_objective` | Yes | Yes |
| 4 | `lottery_not_selected` | Yes | Yes |
| 5 | `singles_policy_rejected` | Yes | Yes |
| 6 | `singles_filler_no_capacity` | Yes | Yes |
| 7 | `exceeds_per_request_limit` | Yes | Yes |

### 3.3 Rejection Path Coverage Analysis

The following table maps every documented rejection path in Phase 1C to its corresponding reason code:

| Rejection Path | Where It Occurs | Reason Code |
|---|---|---|
| Request exceeds per-request limit | §5 (input validation) | `exceeds_per_request_limit` |
| Singles policy is `rejected` and request is single | §4.1 (pre-solver exclusion) | `singles_policy_rejected` |
| Tier fully consumed, 0 seats remaining | §4.1 Phase A / Phase B | `capacity_exhausted` |
| Group size exceeds remaining capacity (remaining > 0 but < group_size) | §4.1 Phase A | `group_exceeds_remaining` |
| Objective function selected other requests over this one | §4.1 Phase A | `displaced_by_objective` |
| Equally ranked but lost random lottery | §4.3 | `lottery_not_selected` |
| Single under `filler_only`, no capacity after groups | §4.1 Phase B | `singles_filler_no_capacity` |

**Status:** Every identifiable rejection path maps to exactly one reason code and human-readable template. The coverage guarantee in §6.4 is substantiated.

### 3.4 Phase 1B Explainability

Phase 1B defines three rejection reason codes (§5.2): `insufficient_capacity`, `singles_policy_rejected`, `exceeds_per_request_limit`. These are **reason codes only** — no human-readable explanation templates are provided.

Phase 1B §6 item 4 explicitly documents this as a limitation: "No explainability beyond queue position."

Phase 0 §9 criterion 3 requires "a human-readable explanation for every allocation and rejection" but applies this criterion to "request-based allocation" — which is Phase 1C, not Phase 1B. Phase 1B is framed as the comparison baseline, not the system under evaluation. This is consistent.

### 3.5 Finding: `capacity_exhausted` vs. `group_exceeds_remaining` boundary

Phase 1C defines two separate rejection codes for capacity-related rejections: `capacity_exhausted` (all seats allocated) and `group_exceeds_remaining` (some seats remain but fewer than group_size). The distinction is meaningful for explainability. However, the documents do not specify the **decision boundary** — i.e., at what point during the solve process a rejection is classified as one vs. the other. If the solver evaluates all requests simultaneously (as an optimization problem), the distinction between "tier was full" and "tier had some seats but not enough" depends on which other requests were selected, which is determined by the solver, not by a sequential process. The mapping from solver output to these two codes is not formally specified.

---

## 4. Drift Check

### 4.1 Arrival Time

| Document | Status |
|---|---|
| Phase 0 §5 | "Does not use arrival time as an allocation factor." |
| Phase 1A §3.2 | `submission_time` is generated but marked as "Used **only** in Phase 1B (FCFS). Ignored in Phase 1C." |
| Phase 1B §3 | Uses `submission_time` as the primary ordering. This is **by design** — Phase 1B is the FCFS baseline. Not drift. |
| Phase 1C §2 | "`submission_time` field is **ignored**; all requests are treated as simultaneous." |
| Phase 1C §8 | "Does not use arrival time." |

**Finding:** No arrival-time drift in Phase 1C. Phase 1B's use of arrival time is intentional and documented as the baseline it is designed to be.

**However:** Phase 1B's `filler_only` mode uses submission-time order for singles in Pass 2. This means even in the filler pass, arrival time determines which singles are filled first. This is consistent with FCFS design but means Phase 1B never fully eliminates arrival-time dependence, even for the subordinate singles pass. This is documented behavior, not drift.

### 4.2 Revenue Optimization

| Document | Status |
|---|---|
| Phase 0 §5 | "Does not optimize revenue by default. Revenue optimization requires explicit promoter selection." |
| Phase 0 §6 | "If no objective is specified, the system must halt and request clarification rather than assuming one." |
| Phase 1A §2.1 | Price is "set by the promoter; used only if revenue is part of the objective function." |
| Phase 1C §3 | Solver "does not assume a default." Revenue is one of three explicit choices. "It never defaults to revenue maximization." |
| Phase 1C §3 | Revenue formula: `sum(request.group_size * tier.price)`. Uses promoter-set `tier.price`, no platform price modification. |

**Finding:** No revenue optimization drift. Revenue is never assumed. The revenue formula uses only promoter-defined prices.

### 4.3 Implicit Fairness Assumptions

| Document | Status |
|---|---|
| Phase 0 §7 | Lottery-based fairness. "All requests submitted within the request window are treated equally regardless of submission time." |
| Phase 1A §3.4 | "No fan loyalty or history. No strategic behavior." |
| Phase 1C §4.3 | Lottery is "uniform random." "No fan attribute (submission time, loyalty, history) influences the lottery." |

**Finding:** No implicit fairness assumptions in Phase 1C. The lottery mechanism is documented as uniform random with no fan-attribute influence.

**One interaction to note:** Phase 1A §3.2 generates group sizes as "discrete uniform over `[1, per_request_limit]`." This distribution means that if `per_request_limit = 4`, then 25% of generated requests are singles (group_size = 1). This is an explicit modeling choice, not hidden drift. However, the uniform distribution of group sizes is itself a fairness-relevant assumption about the fan population — it determines the ratio of singles to groups entering the system. This assumption is documented.

### 4.4 Pricing Control

| Document | Status |
|---|---|
| Phase 0 §5 | "Does not set prices. Prices are promoter inputs." |
| claude.md §1 | "Ticketmaster does NOT control pricing." |
| Phase 1A §2.1 | Price is "set by the promoter." |
| Phase 1C §3 | Revenue formula uses `tier.price`, a promoter input. No price modification occurs. |
| Phase 1C §8 | No mention of price adjustment, dynamic pricing, or price optimization. |

**Finding:** No pricing control drift. The platform never sets, modifies, or suggests prices in any document.

### 4.5 Drift Summary

| Drift Category | Phase 1B | Phase 1C |
|---|---|---|
| Arrival time | Used by design (baseline) | Not present |
| Revenue optimization | Not present (no objective) | Not present (requires explicit selection) |
| Implicit fairness | Tie-breaking by `request.id` is arbitrary but deterministic | Not present (uniform lottery) |
| Pricing control | Not present | Not present |

**No accidental drift detected in Phase 1C.**

Phase 1B's use of arrival time and `request.id` tie-breaking is intentional baseline behavior, not drift.

---

## Appendix: Cross-Document Consistency Matrix

| Property | Phase 0 | Phase 1A | Phase 1B | Phase 1C | Consistent? |
|---|---|---|---|---|---|
| Promoter defines constraints | §4 | §2 | §4.1 | §5 | Yes |
| No default objective | §6 | — | §7 (no objective at all) | §3 (halts if missing) | Yes |
| Lottery fairness | §7 | — | N/A (uses arrival time) | §4.3 | Yes (1B is baseline) |
| Explainability | §9.3 | — | Limited (by design) | §6 (full coverage) | Yes |
| No arrival time in allocation | §5 | §3.2 (1B only) | Uses it (by design) | §2 (ignored) | Yes |
| No platform pricing | §5 | §2.1 | — | §3 (promoter price only) | Yes |
| Singles cannot displace groups | §4 HC-5 | §2.3 | §4.2 | §4.2 | Yes (under `filler_only`) |
| Group integrity | §4 HC-3 | — | §4.1 | §5 + §5.1 | Yes |
| Cross-tier reassignment option | §4 HC-4 "unless configured" | — | Not implemented | Not implemented | Unimplemented option |
