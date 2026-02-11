# Phase 2B Contract — Promoter Tradeoff Dashboard

## Scope

Phase 2B previews allocation outcomes under promoter-set constraints and chosen allocation policies. It does not change pricing, does not produce fan-facing guidance, and does not infer or prescribe willingness-to-pay.

## Non-negotiables

- Pricing remains promoter-controlled; pricebook is read-only.
- Allocation and pricing are architecturally separated.
- Determinism: identical inputs + seed => identical outputs.
- Explainability: every delta shown must be attributable to knob changes and binding constraints.
- Promoter constraints are enforced as hard constraints.

## Inputs

### Scenario

- `knobs_promoter_constraints` (promoter-set rules)
- `knobs_allocation_policy` (processing policy within constraints)
- `seed_policy`
- `references` (event config, demand config, pricebook ref)

### Demand

- Demand generation is seeded and produces `TicketRequest[]`.
- Any tier fields (e.g., `promoter_provided_tier`) are supplied by the promoter/artist team, not inferred.

### Pricebook

- Read-only, promoter-set. Used only for revenue accounting on allocations.

## Outputs

### Preview output

- `manifest` includes: run_id, scenario_id, seed, checksum, git_commit, config hashes
- `results`: raw fcfs + raw batch allocation outputs (internal)
- `metrics`: normalized summaries for fcfs, batch, and delta batch vs fcfs
- `explainability`: binding counts + knob diffs + sanitized notes

### Compare output

- Pinned FCFS baseline metrics
- Per-scenario pareto points (x=accounts_fulfilled_pct, y=gross_revenue_fixed_pricebook)
- Deltas vs FCFS and vs base scenario
- Storyboard: What changed / Why / What it costs (neutral, non-directive)

## Forbidden in Phase 2B

- Any price modification, dynamic pricing, price suggestions, or nudges.
- Any fan-facing outputs.
- Any WTP-driven decision logic (WTP remains diagnostic only and must not influence allocation).
- Words in UI/logs/exports: "optimize", "recommend", "best", "fair".
- Raw request data, demand draws, or fan-identifiable information in exports or audit payloads.

## Metric semantics

- `accounts_fulfilled_pct`: fulfilled accounts / total requesting accounts (input-side denominator).
- `gross_revenue_fixed_pricebook`: the sole revenue metric; no aliases (`gross_revenue`, `revenue_delta_vs_fcfs`).
- All metric columns in CSV exports are sorted alphabetically.

## Audit trail

- Immutable append-only entries with canonical payload schema:
  `{event, scenario_id, actor, timestamp, entity: {type, id}, summary, details}`
- For run events, `entity.id` = run_id (not scenario_id).
- Actor emails are redacted (`a***@corp.com`).
- Payloads bounded to 8KB; strings capped at 500 chars; lists at 20 items.

## Locked scenarios

- Frozen at lock time with reference hashes (event_config_hash, demand_config_hash, pricebook_hash).
- Run manifests include git_commit, code_version, and config_hashes.
- If config hashes drift post-lock, manifest includes `repro_warning`.

## Export hygiene

- Three modes: `metrics_csv` (wide), `long_csv` (long form), `summary_json`.
- Explainability notes sanitized: UUIDs, hex tokens, and internal identifiers stripped; max 300 chars in CSV.
- Config hashes and git_commit included in all export formats.
- No raw requests, demand draws, or fan-identifiable data.

## Terminology

- `"loyalty"` is mapped to `"promoter_provided_tier"` in UI, presets, and explainability.
- Internal model fields (`loyalty_score`) are annotated as promoter-provided tier scores.
- Priority mode labels use safe display names via `_PRIORITY_MODE_LABELS`.
