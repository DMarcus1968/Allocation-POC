"""Phase 2B — Streamlit promoter tradeoff dashboard.

Launch with:  streamlit run ui/dashboard.py

Language rules:
- No "optimize / recommend / best / fair" in labels or text.
- Conditional framing only.
"""

from __future__ import annotations

import streamlit as st
import httpx
import plotly.graph_objects as go

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Promoter Tradeoff Dashboard", layout="wide")
st.title("Promoter Tradeoff Dashboard (Phase 2B)")
st.caption(
    "Define event tiers, set constraints, and compare allocation outcomes. "
    "All prices are promoter-controlled."
)

# ---- Sidebar: scenario setup -----------------------------------------------
with st.sidebar:
    st.header("Scenario Setup")
    event_name = st.text_input("Event name", value="Summer Concert")
    num_tiers = st.number_input("Number of tiers", 1, 5, 2)
    tiers = []
    for i in range(int(num_tiers)):
        st.subheader(f"Tier {i+1}")
        name = st.text_input(f"Name##t{i}", value="GA" if i == 0 else "VIP")
        cap = st.number_input(f"Capacity##t{i}", 1, 100_000, 500 if i == 0 else 100)
        price = st.number_input(
            f"Price (promoter-set)##t{i}", 0.0, 100_000.0,
            75.0 if i == 0 else 200.0, step=5.0,
        )
        tiers.append({"name": name, "capacity": int(cap), "price": float(price)})

    max_per_req = st.number_input("Max tickets per request", 1, 20, 4)
    partial = st.checkbox("Allow partial fill", value=False)
    num_fans = st.number_input("Simulated fan count", 10, 10_000, 300)
    seed = st.number_input("Seed (for determinism)", 0, 999_999, 42)

    run_clicked = st.button("Run Tradeoff Analysis")

# ---- Main area: run and display ---------------------------------------------
if run_clicked:
    # 1. Create scenario
    scenario_payload = {
        "event_name": event_name,
        "tiers": tiers,
        "max_tickets_per_request": int(max_per_req),
        "allow_partial_fill": partial,
        "num_fans": int(num_fans),
        "objectives": ["fill_capacity", "revenue_at_face_value"],
    }
    try:
        resp = httpx.post(f"{API_BASE}/scenarios", json=scenario_payload, timeout=10)
        resp.raise_for_status()
        scenario = resp.json()
        sid = scenario["scenario_id"]
        st.success(f"Scenario created: {sid}")
    except httpx.HTTPError as e:
        st.error(f"Failed to create scenario: {e}")
        st.stop()

    # 2. Execute run
    run_payload = {"scenario_id": sid, "use_common_seed": True, "seed": int(seed)}
    try:
        resp = httpx.post(f"{API_BASE}/runs", json=run_payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
    except httpx.HTTPError as e:
        st.error(f"Run failed: {e}")
        st.stop()

    comparison = result["comparison"]
    scenarios = comparison["scenarios"]

    # 3. Summary table
    st.subheader("Scenario Comparison (dimensional)")
    cols = st.columns(len(scenarios))
    for idx, sc in enumerate(scenarios):
        with cols[idx]:
            label = sc["allocator_name"]
            if sc["objective_used"]:
                label += f" ({sc['objective_used']})"
            st.metric("Allocator", label)
            st.metric("Total allocated", sc["total_allocated"])
            st.metric("Fill rate", f"{sc['overall_fill_rate']:.2%}")
            st.metric("Revenue at face value", f"${sc['total_revenue_at_face_value']:,.0f}")
            st.metric("Requests rejected", sc["requests_rejected"])

    # 4. Dimensional deltas
    deltas = comparison.get("dimension_deltas", {})
    if deltas:
        st.subheader("Dimensional Deltas")
        for dim, pairs in deltas.items():
            for pair_label, val in pairs.items():
                sign = "+" if val > 0 else ""
                st.write(f"**{dim}** ({pair_label}): {sign}{val}")

    # 5. Per-tier bar chart
    st.subheader("Per-Tier Allocation Breakdown")
    for sc in scenarios:
        label = sc["allocator_name"]
        if sc["objective_used"]:
            label += f" / {sc['objective_used']}"
        fig = go.Figure()
        tier_names = [t["tier_name"] for t in sc["tier_metrics"]]
        fig.add_trace(go.Bar(
            name="Capacity",
            x=tier_names,
            y=[t["capacity"] for t in sc["tier_metrics"]],
        ))
        fig.add_trace(go.Bar(
            name="Allocated",
            x=tier_names,
            y=[t["total_allocated"] for t in sc["tier_metrics"]],
        ))
        fig.add_trace(go.Bar(
            name="Requested",
            x=tier_names,
            y=[t["total_requested"] for t in sc["tier_metrics"]],
        ))
        fig.update_layout(
            title=f"Allocator: {label}",
            barmode="group",
            yaxis_title="Tickets",
        )
        st.plotly_chart(fig, use_container_width=True)

    # 6. Explainability
    st.subheader("Explainability")
    for sc in scenarios:
        label = sc["allocator_name"]
        with st.expander(f"{label} — constraints and objective"):
            st.write("**Constraints applied:**")
            for c in sc["constraints_applied"]:
                st.write(f"- {c}")
            st.write(f"**Objective used:** {sc['objective_used']}")
