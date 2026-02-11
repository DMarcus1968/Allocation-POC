"""Phase 2B — Streamlit tradeoff dashboard.

UI copy rules: use "Scenario", "Preview", "Impact", "Tradeoff".
Avoid "optimize/recommend/best/fair".

Pricing control is promoter-side and read-only here.
Phase 3 features (fan-facing price guidance) are deferred.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on the path
_project_root = str(Path(__file__).resolve().parents[1])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from src.dashboard import scenario_store
from src.dashboard.scenario_store import ScenarioLocked
from src.dashboard.tradeoff_engine import run_preview, run_compare


# ── page config ─────────────────────────────────────────────────────

st.set_page_config(page_title="Allocation Tradeoff Dashboard", layout="wide")
st.title("Allocation Tradeoff Dashboard")

# Ensure DB
scenario_store.init_db()


# ── sidebar: scenario management ────────────────────────────────────

st.sidebar.header("Scenarios")

if st.sidebar.button("Refresh list"):
    st.rerun()

scenarios = scenario_store.list_scenarios()
scenario_names = {s.id: s.name or s.id for s in scenarios}

# Create new scenario
with st.sidebar.expander("Create scenario"):
    new_name = st.text_input("Name", value="New scenario")
    new_desc = st.text_input("Description", value="")

    col_pc, col_ap = st.columns(2)
    with col_pc:
        st.caption("Constraints reflect promoter-set rules.")
        new_pc_raw = st.text_area(
            "Promoter constraints (JSON)",
            value=json.dumps(
                {
                    "per_account_cap": 4,
                    "group_size_cap": 6,
                    "holdback_pct": 0.0,
                },
                indent=2,
            ),
            key="new_pc",
        )
    with col_ap:
        st.caption("Policy controls how requests are processed within constraints.")
        new_ap_raw = st.text_area(
            "Allocation policy (JSON)",
            value=json.dumps(
                {
                    "priority_mode": "random",
                    "singles_avoidance": True,
                },
                indent=2,
            ),
            key="new_ap",
        )

    new_seed = st.number_input("Seed", value=42, step=1)
    new_seed_mode = st.selectbox("Seed mode", ["common", "per_scenario"])

    if st.button("Create"):
        try:
            pc = json.loads(new_pc_raw)
            ap = json.loads(new_ap_raw)
        except json.JSONDecodeError:
            st.error("Invalid JSON in knob editors")
            pc, ap = None, None

        if pc is not None and ap is not None:
            sc = scenario_store.create_scenario(
                {
                    "name": new_name,
                    "description": new_desc or None,
                    "knobs_promoter_constraints": pc,
                    "knobs_allocation_policy": ap,
                    "seed_policy": {"mode": new_seed_mode, "seed": int(new_seed)},
                }
            )
            st.success(f"Created: {sc.name} ({sc.id[:8]}...)")
            st.rerun()

# Per-scenario actions
if scenarios:
    st.sidebar.markdown("---")
    selected_id = st.sidebar.selectbox(
        "Select scenario",
        options=[s.id for s in scenarios],
        format_func=lambda sid: scenario_names.get(sid, sid),
    )

    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        if st.button("Clone"):
            try:
                cloned = scenario_store.clone_scenario(selected_id)
                st.sidebar.success(f"Cloned -> {cloned.id[:8]}...")
                st.rerun()
            except ValueError as e:
                st.sidebar.error(str(e))
    with col2:
        if st.button("Lock"):
            try:
                scenario_store.lock_scenario(selected_id)
                st.sidebar.success("Locked")
                st.rerun()
            except ValueError as e:
                st.sidebar.error(str(e))
    with col3:
        if st.button("Delete"):
            scenario_store.delete_scenario(selected_id)
            st.sidebar.success("Deleted")
            st.rerun()


# ── main area: tabs ─────────────────────────────────────────────────

tabs = st.tabs(["Scenario Editor", "Preview", "Compare"])

# ── scenario editor tab ─────────────────────────────────────────────

with tabs[0]:
    st.subheader("Scenario Editor")
    if not scenarios:
        st.info("No scenarios yet. Create one in the sidebar.")
    else:
        sc = scenario_store.get_scenario(selected_id)
        if sc is None:
            st.warning("Scenario not found.")
        else:
            st.markdown(f"**ID:** `{sc.id}`")
            st.markdown(f"**Locked:** {sc.locked}")
            st.markdown(f"**Checksum:** `{sc.checksum[:16]}...`")

            edit_name = st.text_input("Name", value=sc.name, key="edit_name")
            edit_desc = st.text_input(
                "Description", value=sc.description or "", key="edit_desc"
            )

            col_epc, col_eap = st.columns(2)
            with col_epc:
                st.caption("Constraints reflect promoter-set rules.")
                edit_pc_raw = st.text_area(
                    "Promoter constraints (JSON)",
                    value=json.dumps(sc.knobs_promoter_constraints, indent=2),
                    height=180,
                    key="edit_pc",
                )
            with col_eap:
                st.caption(
                    "Policy controls how requests are processed within constraints."
                )
                edit_ap_raw = st.text_area(
                    "Allocation policy (JSON)",
                    value=json.dumps(sc.knobs_allocation_policy, indent=2),
                    height=180,
                    key="edit_ap",
                )

            if st.button("Save changes"):
                if sc.locked:
                    st.error("This scenario is locked and cannot be updated.")
                else:
                    try:
                        pc = json.loads(edit_pc_raw)
                        ap = json.loads(edit_ap_raw)
                    except json.JSONDecodeError:
                        st.error("Invalid JSON in knob editors")
                        pc, ap = None, None

                    if pc is not None and ap is not None:
                        try:
                            updated = scenario_store.update_scenario(
                                sc.id,
                                {
                                    "name": edit_name,
                                    "description": edit_desc or None,
                                    "knobs_promoter_constraints": pc,
                                    "knobs_allocation_policy": ap,
                                },
                            )
                            st.success(
                                f"Saved. Checksum: {updated.checksum[:16]}..."
                            )
                            st.rerun()
                        except ScenarioLocked:
                            st.error("Scenario is locked.")

# ── preview tab ─────────────────────────────────────────────────────

with tabs[1]:
    st.subheader("Preview")
    if not scenarios:
        st.info("Create a scenario first.")
    else:
        preview_id = st.selectbox(
            "Scenario to preview",
            options=[s.id for s in scenarios],
            format_func=lambda sid: scenario_names.get(sid, sid),
            key="preview_select",
        )
        use_common = st.checkbox("Use common seed", value=True, key="preview_common")
        seed_override = st.number_input(
            "Seed override (0 = use scenario policy)",
            value=0,
            step=1,
            key="preview_seed",
        )

        if st.button("Run preview"):
            seed_val = int(seed_override) if seed_override != 0 else None
            with st.spinner("Running allocation preview..."):
                try:
                    result = run_preview(
                        preview_id,
                        seed=seed_val,
                        use_common_seed=use_common,
                    )
                except ValueError as e:
                    st.error(str(e))
                    result = None

            if result:
                st.markdown("### Manifest")
                st.json(result["manifest"])

                st.markdown("### Metrics")
                col_f, col_b = st.columns(2)
                with col_f:
                    st.markdown("**FCFS**")
                    st.json(result["metrics"]["fcfs"])
                with col_b:
                    st.markdown("**Batch**")
                    st.json(result["metrics"]["batch"])

                st.markdown("### Impact (Batch vs FCFS)")
                st.json(result["metrics"]["delta_batch_vs_fcfs"])

                st.markdown("### Explainability")
                expl = result.get("explainability", {})
                for note in expl.get("notes", []):
                    st.markdown(f"- {note}")

                with st.expander("Bindings (section-aware)"):
                    st.json(expl.get("bindings", {}))
                with st.expander("Lost ticket estimates"):
                    st.json(expl.get("lost_tickets_estimates", {}))

# ── compare tab ─────────────────────────────────────────────────────

with tabs[2]:
    st.subheader("Scenario Comparison")
    if len(scenarios) < 2:
        st.info("Create at least 2 scenarios to compare.")
    else:
        compare_ids = st.multiselect(
            "Select 2-4 scenarios to compare",
            options=[s.id for s in scenarios],
            format_func=lambda sid: scenario_names.get(sid, sid),
            max_selections=4,
            key="compare_select",
        )
        compare_common = st.checkbox(
            "Use common seed", value=True, key="compare_common"
        )
        compare_seed = st.number_input(
            "Seed override (0 = use scenario policy)",
            value=0,
            step=1,
            key="compare_seed",
        )

        if st.button("Run comparison"):
            if len(compare_ids) < 2:
                st.warning("Select at least 2 scenarios.")
            else:
                seed_val = int(compare_seed) if compare_seed != 0 else None
                with st.spinner("Running comparison..."):
                    try:
                        result = run_compare(
                            compare_ids,
                            seed=seed_val,
                            use_common_seed=compare_common,
                        )
                    except ValueError as e:
                        st.error(str(e))
                        result = None

                if result:
                    st.markdown("### FCFS Baseline")
                    st.json(result["fcfs_baseline"])

                    st.markdown("### Scenario Metrics (Batch)")
                    table_data = []
                    for sm in result["scenario_metrics"]:
                        row = {"Scenario": sm["scenario_name"]}
                        row.update(sm["metrics"])
                        table_data.append(row)
                    st.table(table_data)

                    st.markdown("### Tradeoff Points")
                    st.markdown(
                        "x = Accounts Fulfilled %, "
                        "y = Gross Revenue (fixed pricebook)"
                    )
                    pareto_table = []
                    for pt in result["pareto_points"]:
                        pareto_table.append(
                            {
                                "Scenario": pt["scenario_name"],
                                "Accounts Fulfilled %": pt[
                                    "x_accounts_fulfilled_pct"
                                ],
                                "Gross Revenue": pt["y_gross_revenue"],
                            }
                        )
                    st.table(pareto_table)

                    # "Why results changed" panel
                    st.markdown("### Why Results Changed")
                    for ed in result.get("explainability_deltas", []):
                        base_name = scenario_names.get(
                            ed["base_scenario_id"],
                            ed["base_scenario_id"][:8],
                        )
                        alt_name = scenario_names.get(
                            ed["alt_scenario_id"],
                            ed["alt_scenario_id"][:8],
                        )
                        st.markdown(f"**{alt_name} vs {base_name}:**")

                        delta = ed["delta"]

                        # Knob diffs
                        if delta.get("knob_changes_promoter_constraints"):
                            st.markdown("*Promoter constraint changes:*")
                            for ch in delta["knob_changes_promoter_constraints"]:
                                st.markdown(
                                    f"- `{ch['knob']}`: "
                                    f"{ch['base']} -> {ch['alt']}"
                                )
                        if delta.get("knob_changes_allocation_policy"):
                            st.markdown("*Allocation policy changes:*")
                            for ch in delta["knob_changes_allocation_policy"]:
                                st.markdown(
                                    f"- `{ch['knob']}`: "
                                    f"{ch['base']} -> {ch['alt']}"
                                )

                        # Binding deltas
                        if delta.get("binding_shifts"):
                            st.markdown("*Binding shifts:*")
                            for cname, shift in delta["binding_shifts"].items():
                                st.markdown(
                                    f"- {cname}: {shift['base']} -> "
                                    f"{shift['alt']} ({shift['change']:+d})"
                                )

                        # Outcome deltas
                        if delta.get("outcome_deltas"):
                            st.markdown("*Outcome impact:*")
                            od = delta["outcome_deltas"]
                            for key, val in od.items():
                                if val != 0:
                                    st.markdown(f"- {key}: {val:+}")

                        # Notes
                        for note in delta.get("notes", []):
                            st.markdown(f"- {note}")

                        st.markdown("---")

# ── footer ──────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Phase 2B Tradeoff Dashboard -- allocation knobs only. "
    "Pricing control is promoter-side (read-only pricebook). "
    "Phase 3 (pricing guidance) is deferred."
)
