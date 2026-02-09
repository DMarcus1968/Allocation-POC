# Phase 1A — Demand Model

## Overview

This document defines the static demand model used for ticket allocation.
It describes the structure of a fan, a request, and the rules governing
single-seat allocations.

---

## Fan

A fan represents the identity unit submitting one or more requests.

| Attribute   | Type   | Required | Description                                              |
|-------------|--------|----------|----------------------------------------------------------|
| entity_id   | string | yes      | Unique identity used for enforcing promoter ticket limits |

Promoter-defined per-fan ticket limits are enforced against `entity_id`.
All requests sharing the same `entity_id` count toward that fan's limit.

---

## Request

A request is a single allocation ask submitted by a fan.

| Attribute            | Type    | Required | Default | Description                                                        |
|----------------------|---------|----------|---------|--------------------------------------------------------------------|
| quantity_requested   | integer | yes      | —       | Number of seats the fan is requesting                              |
| price_level          | string  | yes      | —       | The price level or tier the fan is willing to pay                   |
| together_required    | boolean | yes      | —       | Whether all requested seats must be contiguous                     |
| allow_singles_fill   | boolean | no       | false   | Fan is willing to accept single seats (non-contiguous) as a fallback |

### Field semantics

- **together_required** — When `true`, the solver must allocate all
  `quantity_requested` seats as a contiguous block or reject the request
  entirely.  When `false`, seats may be split across non-contiguous
  locations.

- **allow_singles_fill** — When `true`, the fan opts in to receiving
  individual (non-contiguous) seats as a last-resort fallback even when
  `quantity_requested > 1`.  This flag is only meaningful when
  `together_required` is also `true`; it gives the solver permission to
  break the contiguity requirement rather than fully rejecting the request.

---

## Single-Seat Allocation Rule

A request may be fulfilled with individual (non-contiguous) single-seat
placements **only** when at least one of the following is true:

1. `quantity_requested == 1` — the fan asked for exactly one seat.
2. `allow_singles_fill == true` — the fan explicitly opted in to
   single-seat fallback.

In all other cases the solver must honor the contiguity or grouping
requirements implied by `together_required` and `quantity_requested`.
