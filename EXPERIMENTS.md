# Experiments

## Baseline (seed 2026)
The 500,000-fan run produced 1,250,621 requested tickets against 68,500 initially available seats. The saved dashboard scenario estimates 99.2% asynchronous sell-through versus 91.0% in the illustrative race benchmark. These are synthetic outputs, not forecasts.

## Timing permutation
Thirty identical requests competed for ten two-seat allocations. Input order and every registration timestamp were changed; the allocated fan/zone set matched 100% under the same lottery seed. This validates the implementation invariant, not fan perception.

## Constraint battery
Tests deliberately constrained capacity, block size, VIP pools, catalog ranges, product consent, sponsor/loyal cohorts, ticket limits, duplicate identities, seeds, negotiation prices, and latent WTP. All thirteen invariants passed.

## Supply release and second-show interventions
The demo models release of 3,000 held seats as +2,976 fulfilled and +$0.92M gross. A second show adds 70,000 seats, but only flexible fans are eligible to switch; it is not a cloned demand curve. Both require real promoter feasibility validation before use.

## WHERE THE THESIS BREAKS
- Waiting several days for certainty may feel worse than an immediate purchase, especially for low-demand events where a queue is brief.
- Fans may select every band strategically, overstating genuine flexibility; rankings and withdrawal penalties require careful testing. Added selections must never improve preferred-product priority.
- Publishing ranges and then raising offered prices during registration risks backlash. A safer production rule is to lock each submitted fan's maximum exposure or require renewed consent.
- Cohort proofs and household identity can be gamed. Aggregation creates duplicate-request, account-rental, and synthetic-identity attacks even while reducing the value of speed bots.
- Weighted access is contestable: loyalty can entrench incumbents; new-fan goals can frustrate longstanding fans; sponsor reservations can lower general fulfillment. Objectives require explicit rights-owner governance and reporting.
- A greedy allocation is explainable and fast but can be dominated by a global integer solution when group-size fragmentation is severe.
- Payment authorization days before clearing may expire; authorization at clearing can fail. Re-clearing improves use but delays finality and can create cascades.
- Aggregation reveals market demand to the operator. Post-registration price increases, excessive added dates, or selective disclosures could undermine trust.
- Outages have lower priority impact but still exclude fans who cannot return before close. Extensions and offline/accessibility support are needed.
- A request market does not eliminate fraud; it changes fraud from speed to identity multiplication and eligibility manipulation.
