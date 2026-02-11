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
    new_knobs_raw = st.text_area(
        "Knobs (JSON)",
        value=json.dumps(
            {
                "per_account_cap": 4,
                "group_size_cap": 6,
                "holdback_pct": 0.0,
                "priority_mode": "random",
                "singles_avoidance": True,
            },
            indent=2,
        ),
    )
    new_seed = st.number_input("Seed", value=42, step=1)
    new_seed_mode = st.selectbox("Seed mode", ["common", "per_scenario"])

    if st.button("Create"):
        try:
            knobs = json.loads(new_knobs_raw)
        except json.JSONDecodeError:
            st.error("Invalid JSON for knobs")
            knobs = None

        if knobs is not None:
            sc = scenario_store.create_scenario(
                {
                    "name": new_name,
                    "description": new_desc or None,
                    "knobs": knobs,
                    "seed_policy": {"mode": new_seed_mode, "seed": int(new_seed)},
                }
            )
            st.success(f"Created: {sc.name} ({sc.id[:8]}…)")
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
                st.sidebar.success(f"Cloned → {cloned.id[:8]}…")
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


# ── main area: scenario editor ──────────────────────────────────────

tabs = st.tabs(["Scenario Editor", "Preview", "Compare"])

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
            st.markdown(f"**Checksum:** `{sc.checksum[:16]}…`")

            edit_name = st.text_input("Name", value=sc.name, key="edit_name")
            edit_desc = st.text_input(
                "Description", value=sc.description or "", key="edit_desc"
            )
            edit_knobs_raw = st.text_area(
                "Knobs (JSON)",
                value=json.dumps(sc.knobs, indent=2),
                height=200,
                key="edit_knobs",
            )

            if st.button("Save changes"):
                if sc.locked:
                    st.error("This scenario is locked and cannot be updated.")
                else:
                    try:
                        knobs = json.loads(edit_knobs_raw)
                    except json.JSONDecodeError:
                        st.error("Invalid JSON for knobs")
                        knobs = None

                    if knobs is not None:
                        try:
                            updated = scenario_store.update_scenario(
                                sc.id,
                                {
                                    "name": edit_name,
                                    "description": edit_desc or None,
                                    "knobs": knobs,
                                },
                            )
                            st.success(f"Saved. Checksum: {updated.checksum[:16]}…")
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
            with st.spinner("Running allocation preview…"):
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

                with st.expander("Raw bindings"):
                    st.json(expl.get("bindings", {}))

# ── compare tab ─────────────────────────────────────────────────────

with tabs[2]:
    st.subheader("Scenario Comparison")
    if len(scenarios) < 2:
        st.info("Create at least 2 scenarios to compare.")
    else:
        compare_ids = st.multiselect(
            "Select 2–4 scenarios to compare",
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
                with st.spinner("Running comparison…"):
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
                    # Table view
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

                    st.markdown("### Explainability")
                    for ed in result.get("explainability_deltas", []):
                        st.markdown(
                            f"**vs scenario {ed['base_scenario_id'][:8]}…**"
                        )
                        for note in ed["delta"].get("notes", []):
                            st.markdown(f"- {note}")

# ── footer ──────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Phase 2B Tradeoff Dashboard — allocation knobs only. "
    "Pricing control is promoter-side (read-only pricebook). "
    "Phase 3 (pricing guidance) is deferred."
)
