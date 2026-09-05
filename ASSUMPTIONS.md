# Assumptions

## Market and supply
- One fictional performance at Meridian Stadium has 74,000 gross ticketable seats, with 5,500 initial production, sponsor, artist, and operational holds; the baseline exposes 68,500 seats. Zones use coarse 20-seat blocks as an adjacency proxy.
- The artist/promoter owns every price, bound, hold, inventory, VIP, and access-policy decision. Front-to-back rank is explicit; overlapping bands are permitted, while a worse adjacent tier priced over 120% of the better tier is flagged.
- VIP is transparent merchandise, hospitality, premium-entry, and collectible packaging at a configurable 3× underlying face price. It shares—and therefore consumes—the underlying zone pool.

## Synthetic demand and behavior
- Seed 2026 generates 500,000 fans. Quantity sampling is 12.5% one, 50% two, 12.5% three, and 25% four tickets, yielding about 1.25M requested tickets. Preferences use a beta distribution biased toward more desirable zones.
- Cohorts overlap independently: fan club 22%, past buyer 31%, merchandise 18%, engaged streaming 42%, new fan 27%, sponsor/cardholder 12%, local 38%, and VIP-oriented 8%. These are scenario assumptions, not observed facts.
- Latent willingness-to-pay exists only inside a future elasticity response model. It never enters priority or individual price. Product price is common to every recipient in a scenario.
- Negotiation acceptance, conventional failure, and infrastructure metrics are modeled illustrative estimates. A new date is assumed acceptable to 58% of flexible fans; it does not duplicate demand.

## Clearing and benchmark
- Default policy is balanced access: cohort scores followed by a SHA-256 seeded lottery; timestamp and input order are excluded. Selecting extra zones expands feasible matches but cannot improve priority for a preferred zone.
- Household identity is represented by unique `fan_id`; the first duplicate request is retained. Limit is four tickets. Failed payment inventory is assumed eligible for a later deterministic re-clear.
- The generic onsale includes concentrated arrival, abandonment, contention, and payment failures. Normalized capacity is relative, not a dollar estimate.
