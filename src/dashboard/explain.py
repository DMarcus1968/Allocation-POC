"""Phase 2B Step 3 — Rule-based explainability.

All explanations are deterministic and based on concrete counts
from the allocator debug output.  No ML attribution is used.
"""

from __future__ import annotations

from src.models.allocation import AllocationResult
from src.models.scenario import Scenario


def explain_run(
    batch_result: AllocationResult,
    scenario: Scenario,
) -> dict:
    """Generate an explainability payload for a single preview run.

    Examines the batch allocator's debug output for constraint-binding
    indicators and produces human-readable bullet notes with counts.

    Returns:
        {"bindings": {...}, "notes": [...]}
    """
    debug = batch_result.debug or {}
    bc = debug.get("binding_counts", {})

    bindings = {
        "per_account_cap_binds": bc.get("per_account_cap", 0),
        "group_size_cap_binds": bc.get("group_size_cap", 0),
        "section_eligibility_exclusions": bc.get("section_eligibility", 0),
        "holdback_tickets": bc.get("holdback", 0),
        "insufficient_inventory_rejections": bc.get("insufficient_inventory", 0),
        "singles_stranded": bc.get("singles_stranded", 0),
    }

    notes = _build_notes(bindings, scenario.knobs, debug)

    return {"bindings": bindings, "notes": notes}


def explain_delta(
    base_preview: dict,
    alt_preview: dict,
    base_scenario: Scenario,
    alt_scenario: Scenario,
) -> dict:
    """Generate explainability for the difference between two scenarios.

    Identifies which knobs changed and how binding indicators shifted.

    Returns:
        {"knob_changes": [...], "binding_shifts": {...}, "notes": [...]}
    """
    # Identify knob differences
    knob_changes = _diff_knobs(base_scenario.knobs, alt_scenario.knobs)

    # Binding shifts
    base_bindings = base_preview.get("explainability", {}).get("bindings", {})
    alt_bindings = alt_preview.get("explainability", {}).get("bindings", {})
    binding_shifts = {}
    all_keys = set(base_bindings) | set(alt_bindings)
    for key in sorted(all_keys):
        bv = base_bindings.get(key, 0)
        av = alt_bindings.get(key, 0)
        if bv != av:
            binding_shifts[key] = {"base": bv, "alt": av, "change": av - bv}

    # Metric shifts
    base_batch = base_preview.get("metrics", {}).get("batch", {})
    alt_batch = alt_preview.get("metrics", {}).get("batch", {})

    notes = _build_delta_notes(
        knob_changes, binding_shifts, base_batch, alt_batch,
        base_scenario, alt_scenario,
    )

    return {
        "knob_changes": knob_changes,
        "binding_shifts": binding_shifts,
        "notes": notes,
    }


# ── internal helpers ────────────────────────────────────────────────

def _build_notes(bindings: dict, knobs: dict, debug: dict) -> list[str]:
    """Build human-readable bullet strings from binding data."""
    notes: list[str] = []

    cap_binds = bindings.get("per_account_cap_binds", 0)
    if cap_binds > 0:
        cap_val = knobs.get("per_account_cap", "unknown")
        notes.append(
            f"Per-account cap ({cap_val}) was binding for {cap_binds} request(s)."
        )

    gs_binds = bindings.get("group_size_cap_binds", 0)
    if gs_binds > 0:
        gs_val = knobs.get("group_size_cap", "unknown")
        notes.append(
            f"Group size cap ({gs_val}) was binding for {gs_binds} request(s)."
        )

    elig = bindings.get("section_eligibility_exclusions", 0)
    if elig > 0:
        notes.append(
            f"Section eligibility constraints excluded {elig} section attempt(s)."
        )

    holdback = bindings.get("holdback_tickets", 0)
    if holdback > 0:
        pct = debug.get("holdback_pct", 0)
        notes.append(
            f"Holdback ({pct:.0%}) withheld {holdback} ticket(s) from allocation."
        )

    insuff = bindings.get("insufficient_inventory_rejections", 0)
    if insuff > 0:
        notes.append(
            f"{insuff} request(s) could not be fulfilled due to insufficient inventory."
        )

    stranded = bindings.get("singles_stranded", 0)
    if stranded > 0:
        notes.append(
            f"{stranded} section(s) left with exactly 1 unsold seat (stranded single)."
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


def _build_delta_notes(
    knob_changes: list[dict],
    binding_shifts: dict,
    base_batch: dict,
    alt_batch: dict,
    base_scenario: Scenario,
    alt_scenario: Scenario,
) -> list[str]:
    """Build human-readable notes for a scenario comparison."""
    notes: list[str] = []

    if not knob_changes:
        notes.append(
            f"Scenarios '{base_scenario.name}' and '{alt_scenario.name}' "
            "have identical knob settings."
        )
    else:
        for ch in knob_changes:
            notes.append(
                f"Knob '{ch['knob']}' changed from {ch['base']} to {ch['alt']}."
            )

    for key, shift in binding_shifts.items():
        direction = "increased" if shift["change"] > 0 else "decreased"
        notes.append(
            f"{key} {direction} by {abs(shift['change'])} "
            f"(from {shift['base']} to {shift['alt']})."
        )

    # Revenue shift
    base_rev = base_batch.get("gross_revenue_fixed_pricebook", 0)
    alt_rev = alt_batch.get("gross_revenue_fixed_pricebook", 0)
    rev_delta = alt_rev - base_rev
    if rev_delta != 0:
        direction = "higher" if rev_delta > 0 else "lower"
        notes.append(
            f"Gross revenue (fixed pricebook) is ${abs(rev_delta):,.2f} {direction} "
            f"in '{alt_scenario.name}' vs '{base_scenario.name}'."
        )

    # Access shift
    base_access = base_batch.get("accounts_fulfilled_pct", 0)
    alt_access = alt_batch.get("accounts_fulfilled_pct", 0)
    access_delta = alt_access - base_access
    if access_delta != 0:
        direction = "higher" if access_delta > 0 else "lower"
        notes.append(
            f"Accounts fulfilled is {abs(access_delta):.2f}pp {direction} "
            f"in '{alt_scenario.name}' vs '{base_scenario.name}'."
        )

    return notes
