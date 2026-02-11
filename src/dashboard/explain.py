"""Phase 2B Step 3 — Rule-based explainability.

All explanations are deterministic and based on concrete counts
from the allocator debug output.  No ML attribution is used.

Bindings are now section-aware, and delta explanations group knob
changes by promoter constraints vs allocation policy.
"""

from __future__ import annotations

from src.models.allocation import AllocationResult
from src.models.scenario import Scenario, PROMOTER_CONSTRAINT_KEYS

# Promoter-safe label mapping for priority_mode values
_PRIORITY_MODE_LABELS: dict[str, str] = {
    "loyalty": "promoter-provided tier",
    "promoter_provided_tier": "promoter-provided tier",
    "price_tier": "promoter-provided tier",
    "tier_then_time": "tier-then-time",
    "random": "random",
}


def _safe_value_label(knob: str, value) -> str:
    """Return a promoter-safe display label for a knob value."""
    if knob == "priority_mode" and isinstance(value, str):
        return _PRIORITY_MODE_LABELS.get(value, value)
    return str(value)


def explain_run(
    batch_result: AllocationResult,
    scenario: Scenario,
) -> dict:
    """Generate an explainability payload for a single preview run.

    Examines the batch allocator's section-aware debug output for
    constraint-binding indicators and produces human-readable bullet
    notes with concrete counts.

    Returns:
        {
          "bindings": { constraint -> {total, by_section} },
          "lost_tickets_estimates": { constraint -> {total, by_section} },
          "notes": [str, ...]
        }
    """
    debug = batch_result.debug or {}
    bindings = debug.get("bindings", {})
    lost = debug.get("lost_tickets_estimates", {})

    notes = _build_notes(bindings, lost, scenario.knobs, debug)

    return {
        "bindings": bindings,
        "lost_tickets_estimates": lost,
        "notes": notes,
    }


def explain_delta(
    base_preview: dict,
    alt_preview: dict,
    base_scenario: Scenario,
    alt_scenario: Scenario,
) -> dict:
    """Generate explainability for the difference between two scenarios.

    Groups knob changes into promoter constraints vs allocation policy,
    computes binding deltas (per constraint, totals + top 2 sections
    by absolute delta), and outcome deltas.

    Returns:
        {
          "knob_changes_promoter_constraints": [...],
          "knob_changes_allocation_policy": [...],
          "knob_changes": [...],   (all, for backward compat)
          "binding_shifts": {...},
          "outcome_deltas": {...},
          "notes": [str, ...]
        }
    """
    # Identify knob differences, split by category
    all_changes = _diff_knobs(base_scenario.knobs, alt_scenario.knobs)
    pc_changes = [c for c in all_changes if c["knob"] in PROMOTER_CONSTRAINT_KEYS]
    ap_changes = [c for c in all_changes if c["knob"] not in PROMOTER_CONSTRAINT_KEYS]

    # Binding shifts (section-aware)
    base_bindings = base_preview.get("explainability", {}).get("bindings", {})
    alt_bindings = alt_preview.get("explainability", {}).get("bindings", {})
    binding_shifts = _compute_binding_shifts(base_bindings, alt_bindings)

    # Outcome deltas
    base_batch = base_preview.get("metrics", {}).get("batch", {})
    alt_batch = alt_preview.get("metrics", {}).get("batch", {})
    outcome_deltas = {
        "tickets_fulfilled": (
            alt_batch.get("tickets_fulfilled", 0)
            - base_batch.get("tickets_fulfilled", 0)
        ),
        "singles_stranded_count": (
            alt_batch.get("singles_stranded_count", 0)
            - base_batch.get("singles_stranded_count", 0)
        ),
        "unsold_inventory_count": (
            alt_batch.get("unsold_inventory_count", 0)
            - base_batch.get("unsold_inventory_count", 0)
        ),
        "gross_revenue_fixed_pricebook": round(
            alt_batch.get("gross_revenue_fixed_pricebook", 0)
            - base_batch.get("gross_revenue_fixed_pricebook", 0),
            2,
        ),
        "accounts_fulfilled_pct": round(
            alt_batch.get("accounts_fulfilled_pct", 0)
            - base_batch.get("accounts_fulfilled_pct", 0),
            2,
        ),
    }

    notes = _build_delta_notes(
        pc_changes, ap_changes, binding_shifts, outcome_deltas,
        base_scenario, alt_scenario,
    )

    return {
        "knob_changes_promoter_constraints": pc_changes,
        "knob_changes_allocation_policy": ap_changes,
        "knob_changes": all_changes,
        "binding_shifts": binding_shifts,
        "outcome_deltas": outcome_deltas,
        "notes": notes,
    }


# ── internal helpers ────────────────────────────────────────────────

def _build_notes(
    bindings: dict,
    lost: dict,
    knobs: dict,
    debug: dict,
) -> list[str]:
    """Build human-readable bullet strings from section-aware binding data."""
    notes: list[str] = []

    for constraint in sorted(bindings.keys()):
        entry = bindings[constraint]
        total = entry.get("total", 0) if isinstance(entry, dict) else entry
        if total <= 0:
            continue

        by_section = entry.get("by_section", {}) if isinstance(entry, dict) else {}
        lost_entry = lost.get(constraint, {})
        lost_total = lost_entry.get("total", 0) if isinstance(lost_entry, dict) else 0

        section_detail = ""
        if by_section:
            top_sections = sorted(
                by_section.items(), key=lambda x: -x[1]
            )[:3]
            parts = [f"{sid}: {cnt}" for sid, cnt in top_sections]
            section_detail = f" [by section: {', '.join(parts)}]"

        lost_detail = ""
        if lost_total > 0:
            lost_detail = f" (~{lost_total} ticket(s) lost)"

        label = constraint.replace("_", " ")
        knob_val = knobs.get(constraint)
        val_str = f" ({knob_val})" if knob_val is not None else ""

        notes.append(
            f"{label.capitalize()}{val_str}: {total} binding(s){lost_detail}{section_detail}."
        )

    if not notes:
        notes.append("No binding constraints detected in this allocation run.")

    return notes


def _diff_knobs(base: dict, alt: dict) -> list[dict]:
    """Identify which knobs changed between two scenarios."""
    changes: list[dict] = []
    all_keys = sorted(set(base) | set(alt))
    for key in all_keys:
        bv = base.get(key)
        av = alt.get(key)
        if bv != av:
            changes.append({"knob": key, "base": bv, "alt": av})
    return changes


def _compute_binding_shifts(
    base_bindings: dict,
    alt_bindings: dict,
) -> dict:
    """Compute per-constraint binding shifts with top sections."""
    shifts: dict = {}
    all_constraints = sorted(set(base_bindings) | set(alt_bindings))

    for constraint in all_constraints:
        b_entry = base_bindings.get(constraint, {"total": 0, "by_section": {}})
        a_entry = alt_bindings.get(constraint, {"total": 0, "by_section": {}})

        b_total = b_entry.get("total", 0) if isinstance(b_entry, dict) else b_entry
        a_total = a_entry.get("total", 0) if isinstance(a_entry, dict) else a_entry

        if b_total == a_total:
            continue

        b_by_sec = b_entry.get("by_section", {}) if isinstance(b_entry, dict) else {}
        a_by_sec = a_entry.get("by_section", {}) if isinstance(a_entry, dict) else {}

        # Section-level deltas
        all_secs = sorted(set(b_by_sec) | set(a_by_sec))
        section_deltas = {}
        for sid in all_secs:
            d = a_by_sec.get(sid, 0) - b_by_sec.get(sid, 0)
            if d != 0:
                section_deltas[sid] = d

        # Top 2 sections by absolute delta
        top_sections = sorted(
            section_deltas.items(), key=lambda x: -abs(x[1])
        )[:2]

        shifts[constraint] = {
            "base": b_total,
            "alt": a_total,
            "change": a_total - b_total,
            "top_sections": dict(top_sections),
        }

    return shifts


def _build_delta_notes(
    pc_changes: list[dict],
    ap_changes: list[dict],
    binding_shifts: dict,
    outcome_deltas: dict,
    base_scenario: Scenario,
    alt_scenario: Scenario,
) -> list[str]:
    """Build human-readable notes for a scenario comparison."""
    notes: list[str] = []

    # Knob changes by category
    if pc_changes:
        notes.append("Promoter constraint changes:")
        for ch in pc_changes:
            base_label = _safe_value_label(ch["knob"], ch["base"])
            alt_label = _safe_value_label(ch["knob"], ch["alt"])
            notes.append(
                f"  '{ch['knob']}' changed from {base_label} to {alt_label}."
            )
    if ap_changes:
        notes.append("Allocation policy changes:")
        for ch in ap_changes:
            base_label = _safe_value_label(ch["knob"], ch["base"])
            alt_label = _safe_value_label(ch["knob"], ch["alt"])
            notes.append(
                f"  '{ch['knob']}' changed from {base_label} to {alt_label}."
            )
    if not pc_changes and not ap_changes:
        notes.append(
            f"Scenarios '{base_scenario.name}' and '{alt_scenario.name}' "
            "have identical knob settings."
        )

    # Binding shifts
    for constraint, shift in sorted(binding_shifts.items()):
        direction = "increased" if shift["change"] > 0 else "decreased"
        section_info = ""
        if shift["top_sections"]:
            parts = [f"{s}: {d:+d}" for s, d in shift["top_sections"].items()]
            section_info = f" (top sections: {', '.join(parts)})"
        notes.append(
            f"{constraint.replace('_', ' ').capitalize()} {direction} "
            f"by {abs(shift['change'])} "
            f"(from {shift['base']} to {shift['alt']}){section_info}."
        )

    # Outcome deltas
    rev_d = outcome_deltas.get("gross_revenue_fixed_pricebook", 0)
    if rev_d != 0:
        direction = "higher" if rev_d > 0 else "lower"
        notes.append(
            f"Gross revenue (fixed pricebook) is ${abs(rev_d):,.2f} {direction} "
            f"in '{alt_scenario.name}' vs '{base_scenario.name}'."
        )

    access_d = outcome_deltas.get("accounts_fulfilled_pct", 0)
    if access_d != 0:
        direction = "higher" if access_d > 0 else "lower"
        notes.append(
            f"Accounts fulfilled is {abs(access_d):.2f}pp {direction} "
            f"in '{alt_scenario.name}' vs '{base_scenario.name}'."
        )

    tickets_d = outcome_deltas.get("tickets_fulfilled", 0)
    if tickets_d != 0:
        direction = "more" if tickets_d > 0 else "fewer"
        notes.append(
            f"{abs(tickets_d)} {direction} ticket(s) fulfilled "
            f"in '{alt_scenario.name}' vs '{base_scenario.name}'."
        )

    unsold_d = outcome_deltas.get("unsold_inventory_count", 0)
    if unsold_d != 0:
        direction = "more" if unsold_d > 0 else "fewer"
        notes.append(
            f"{abs(unsold_d)} {direction} unsold seat(s) "
            f"in '{alt_scenario.name}' vs '{base_scenario.name}'."
        )

    return notes
