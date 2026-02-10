# Phase 1A — Demand Model

## 1. Purpose

Generate a synthetic fan population and a set of ticket requests to serve as input to both the FCFS Baseline (Phase 1B) and the Allocation Solver (Phase 1C). The demand model is a simulation tool, not a predictive model.

## 2. Event Configuration (Promoter Inputs)

The following parameters are provided by the rights owner. They are hard constraints on the demand model's output.

| Parameter | Type | Example |
|---|---|---|
| **Tiers** | List of `{name, capacity, price}` | `[{GA, 500, $75}, {VIP, 100, $200}]` |
| **Per-Request Limit** | Integer | `4` |
| **Singles Policy** | Enum: `allowed`, `filler_only`, `rejected` | `filler_only` |
| **Request Window** | Duration | `72 hours` |

### 2.1 Tier Definition

Each tier has:
- A **name** (label only, no allocation semantics).
- A **capacity** (integer, hard ceiling on allocations).
- A **price** (set by the promoter; used only if revenue is part of the objective function).

### 2.2 Per-Request Limit

The maximum number of tickets any single request may ask for. Requests exceeding this limit are rejected at submission time before entering the allocation pipeline.

### 2.3 Singles Policy

The promoter selects one of three modes:

| Mode | Meaning |
|---|---|
| `allowed` | Single-ticket requests compete equally with group requests. |
| `filler_only` | Single-ticket requests are processed only after all group requests have been resolved, and only to fill remaining capacity. |
| `rejected` | Single-ticket requests are not accepted. |

## 3. Fan Population

### 3.1 Population Size

A configurable parameter `N` representing the total number of fans who may submit requests. Default: `N = 2000`.

### 3.2 Request Generation

Each fan generates at most one request with the following attributes:

| Attribute | Distribution | Notes |
|---|---|---|
| **Tier Preference** | Categorical, weighted by tier capacity | Larger tiers attract proportionally more demand. |
| **Group Size** | Discrete uniform over `[1, per_request_limit]` | Bounded by the promoter's per-request limit. |
| **Submission Time** | Uniform over the request window | Used **only** in Phase 1B (FCFS). Ignored in Phase 1C. |

### 3.3 Group vs. Single Requests

A request with `group_size = 1` is classified as a **single request**. All other requests are **group requests**. This classification determines processing order under certain singles policies (see Phase 1B §4 and Phase 1C §4).

### 3.4 What the Demand Model Does NOT Include

- **Willingness-to-pay variation.** All fans requesting a tier are assumed to accept the promoter's stated price. WTP modeling is deferred to future phases.
- **Fan loyalty or history.** No fan attributes beyond tier preference and group size.
- **Strategic behavior.** Fans do not adjust requests based on expected allocation outcomes.
- **Multiple requests per fan.** Each fan submits exactly one request.

## 4. Output Schema

The demand model produces a list of requests:

```
Request {
  id:              unique identifier
  fan_id:          unique fan identifier
  tier:            target tier name
  group_size:      integer in [1, per_request_limit]
  submission_time: timestamp within request window
  type:            "group" | "single"  (derived: group if group_size > 1)
}
```

## 5. Oversubscription Ratio

To produce meaningful allocation scenarios, the demand model is configured so that total requested tickets **exceed** available capacity. The oversubscription ratio is configurable:

- `oversubscription_ratio = total_requested / total_capacity`
- Default: `1.5` (50% more tickets requested than available).

This is adjusted per tier to ensure each tier independently faces oversubscription.

## 6. Reproducibility

All random generation uses a configurable seed. Identical seeds produce identical request sets, enabling direct comparison between Phase 1B and Phase 1C outcomes on the same demand.
