"""Phase 2B — Streamlit tradeoff dashboard.

UI copy rules: use "Scenario", "Preview", "Impact", "Tradeoff",
"Template", "Export", "Audit trail", "Lock scenario".
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
from src.dashboard import preset_store
from src.dashboard.audit_store import list_audits


# ── page config ─────────────────────────────────────────────────────

st.set_page_config(page_title="Allocation Tradeoff Dashboard", layout="wide")
st.title("Allocation Tradeoff Dashboard")

# Static disclaimer panel
st.info(
    "This dashboard previews allocation outcomes under promoter-set "
    "constraints and policies. Pricing is not changed here and remains "
    "promoter-controlled. No fan-facing guidance is generated in this phase."
)

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
        if st.button("Lock scenario"):
            st.session_state["confirm_lock"] = selected_id
    with col3:
        if st.button("Delete"):
            scenario_store.delete_scenario(selected_id)
            st.sidebar.success("Deleted")
            st.rerun()

    # Lock confirmation modal
    if st.session_state.get("confirm_lock") == selected_id:
        st.sidebar.warning(
            "Locking makes this scenario immutable. "
            "Create an editable clone to iterate."
        )
        lock_cols = st.sidebar.columns(2)
        with lock_cols[0]:
            if st.button("Confirm Lock"):
                try:
                    scenario_store.lock_scenario(selected_id)
                    st.sidebar.success("Locked")
                    st.session_state.pop("confirm_lock", None)
                    st.rerun()
                except ValueError as e:
                    st.sidebar.error(str(e))
        with lock_cols[1]:
            if st.button("Cancel"):
                st.session_state.pop("confirm_lock", None)
                st.rerun()


# ── main area: tabs ─────────────────────────────────────────────────

tabs = st.tabs(["Templates", "Scenario Editor", "Preview", "Compare", "Audit Trail"])

# ── templates tab ──────────────────────────────────────────────────

with tabs[0]:
    st.subheader("Templates")
    st.caption("Pre-configured scenario templates. Select one to create a new scenario with those settings.")

    presets = preset_store.list_presets()
    if not presets:
        st.info("No templates available.")
    else:
        for preset in presets:
            with st.expander(f"{preset['name']} — {preset['description']}"):
                st.markdown(f"**Creator:** {preset['creator']}")
                col_tpc, col_tap = st.columns(2)
                with col_tpc:
                    st.markdown("**Promoter constraints:**")
                    st.json(preset["knobs_promoter_constraints"])
                with col_tap:
                    st.markdown("**Allocation policy:**")
                    st.json(preset["knobs_allocation_policy"])

                if st.button(
                    f"Create scenario from template",
                    key=f"apply_{preset['id']}",
                ):
                    sc = preset_store.apply_preset_to_new_scenario(
                        preset["id"], created_by="dashboard_user"
                    )
                    st.success(
                        f"Created scenario '{sc.name}' ({sc.id[:8]}...) "
                        f"from template '{preset['name']}'."
                    )
                    st.rerun()

# ── scenario editor tab ─────────────────────────────────────────────

with tabs[1]:
    st.subheader("Scenario Editor")
    if not scenarios:
        st.info("No scenarios yet. Create one in the sidebar or from a template.")
    else:
        sc = scenario_store.get_scenario(selected_id)
        if sc is None:
            st.warning("Scenario not found.")
        else:
            st.markdown(f"**ID:** `{sc.id}`")
            st.markdown(f"**Locked:** {sc.locked}")
            st.markdown(f"**Checksum:** `{sc.checksum[:16]}...`")

            if sc.locked:
                st.info(
                    "This scenario is locked and cannot be edited. "
                    "Use Clone to create an editable copy."
                )

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
                    disabled=sc.locked,
                )
            with col_eap:
                st.caption(
                    "Policy controls how requests are processed within constraints. "
                    "If using priority_mode, the field uses a promoter-provided tier; "
                    "it does not infer willingness to pay."
                )
                edit_ap_raw = st.text_area(
                    "Allocation policy (JSON)",
                    value=json.dumps(sc.knobs_allocation_policy, indent=2),
                    height=180,
                    key="edit_ap",
                    disabled=sc.locked,
                )

            if st.button("Save changes", disabled=sc.locked):
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

with tabs[2]:
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

                # Export controls
                st.markdown("### Export")
                exp_cols = st.columns(2)
                with exp_cols[0]:
                    exp_fmt = st.selectbox(
                        "Format", ["csv", "json"], key="preview_export_fmt"
                    )
                with exp_cols[1]:
                    exp_expl = st.checkbox(
                        "Include explainability", value=True, key="preview_export_expl"
                    )
                if st.button("Export this run"):
                    st.info(
                        f"POST /scenarios/{preview_id}/export "
                        f"with format={exp_fmt}, include_explainability={exp_expl}"
                    )

# ── compare tab ─────────────────────────────────────────────────────

with tabs[3]:
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
                    # ── Section 1: What changed ──────────────────────
                    st.markdown("### 1. What changed")
                    st.caption(
                        "Side-by-side metrics for each scenario under "
                        "identical demand. FCFS baseline is pinned."
                    )

                    st.markdown("**FCFS Baseline**")
                    st.json(result["fcfs_baseline"]["metrics"])

                    st.markdown("**Scenario Metrics (Batch)**")
                    table_data = []
                    for sm in result["scenario_metrics"]:
                        row = {"Scenario": sm["scenario_name"]}
                        row.update(sm["metrics"])
                        table_data.append(row)
                    st.table(table_data)

                    st.markdown("**Tradeoff Points**")
                    st.caption(
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
                                "Gross Revenue (fixed pricebook)": pt["y_gross_revenue"],
                            }
                        )
                    st.table(pareto_table)

                    # ── Section 2: Why it changed ────────────────────
                    st.markdown("### 2. Why it changed")
                    st.caption(
                        "Knob differences and constraint-binding shifts "
                        "that explain the outcome deltas above."
                    )
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

                        st.markdown("---")

                    # ── Section 3: What it costs ─────────────────────
                    st.markdown("### 3. What it costs")
                    st.caption(
                        "Revenue, access, and inventory impact of each "
                        "scenario relative to the baseline."
                    )
                    for ed in result.get("explainability_deltas", []):
                        alt_name = scenario_names.get(
                            ed["alt_scenario_id"],
                            ed["alt_scenario_id"][:8],
                        )
                        base_name = scenario_names.get(
                            ed["base_scenario_id"],
                            ed["base_scenario_id"][:8],
                        )
                        delta = ed["delta"]

                        if delta.get("outcome_deltas"):
                            st.markdown(f"**{alt_name} vs {base_name}:**")
                            od = delta["outcome_deltas"]
                            for key, val in sorted(od.items()):
                                if val != 0:
                                    label = key.replace("_", " ").capitalize()
                                    st.markdown(f"- {label}: {val:+}")

                        # Notes
                        for note in delta.get("notes", []):
                            st.markdown(f"- {note}")

                        st.markdown("---")

# ── audit trail tab ─────────────────────────────────────────────────

with tabs[4]:
    st.subheader("Audit Trail")
    if not scenarios:
        st.info("No scenarios yet.")
    else:
        audit_scenario_id = st.selectbox(
            "Scenario",
            options=[s.id for s in scenarios],
            format_func=lambda sid: scenario_names.get(sid, sid),
            key="audit_select",
        )
        audit_limit = st.number_input(
            "Max entries", value=50, step=10, key="audit_limit"
        )

        if st.button("Load audit trail"):
            audits = list_audits(
                scenario_id=audit_scenario_id,
                limit=int(audit_limit),
            )
            if not audits:
                st.info("No audit entries for this scenario.")
            else:
                for entry in audits:
                    ts = entry["created_at"]
                    ev = entry["event"]
                    actor = entry["actor"]
                    payload_str = json.dumps(entry["payload"], indent=2)
                    st.markdown(
                        f"**{ts}** | `{ev}` | actor: {actor}"
                    )
                    with st.expander("Payload"):
                        st.code(payload_str, language="json")

        if st.button("Download audit as CSV"):
            audits = list_audits(
                scenario_id=audit_scenario_id,
                limit=1000,
            )
            if audits:
                import csv as csv_mod
                import io

                buf = io.StringIO()
                columns = ["id", "scenario_id", "event", "actor", "payload", "created_at"]
                writer = csv_mod.DictWriter(buf, fieldnames=columns)
                writer.writeheader()
                for a in audits:
                    writer.writerow({
                        "id": a["id"],
                        "scenario_id": a["scenario_id"],
                        "event": a["event"],
                        "actor": a["actor"],
                        "payload": json.dumps(a["payload"]),
                        "created_at": a["created_at"],
                    })
                st.download_button(
                    label="Download CSV",
                    data=buf.getvalue(),
                    file_name=f"{audit_scenario_id}_audits.csv",
                    mime="text/csv",
                )
            else:
                st.info("No audit entries to export.")


# ── footer ──────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Phase 2B Tradeoff Dashboard -- allocation knobs only. "
    "Pricing control is promoter-side (read-only pricebook). "
    "Phase 3 (pricing guidance) is deferred."
)
