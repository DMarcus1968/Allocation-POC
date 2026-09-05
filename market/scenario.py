from __future__ import annotations
import json
from pathlib import Path
from .engine import DEFAULT_ZONES, synthetic_summary, zone_dicts

def baseline(seed=2026, fans=500_000):
    summary = synthetic_summary(seed, fans)
    demand = summary["tickets_requested"]
    supply = summary["available_supply"]
    async_alloc = min(supply, int(supply*.992))
    conventional = int(supply*.91)
    return {"event": "Nova Rae — One Night at Meridian Stadium", "status": "Synthetic modeled estimate",
        "summary": summary, "zones": zone_dicts(),
        "proof": {"early_advantage": False, "timestamp_match_rate": 1.0, "registration_peak": 7100, "onsale_peak": 286000},
        "allocation": {"allocated": async_alloc, "exact_requests": 23840, "negotiated_tickets": 6840, "remaining_inventory": supply-async_alloc, "unfulfilled_demand": demand-async_alloc},
        "comparison": [
          {"metric":"Revenue", "async":"$22.8M", "race":"$20.1M"}, {"metric":"Sell-through", "async":"99.2%", "race":"91.0%"},
          {"metric":"Exact request fulfillment", "async":"34.8%", "race":"27.1%"}, {"metric":"Negotiated fulfillment", "async":"6,840", "race":"—"},
          {"metric":"Fan active time", "async":"6 min", "race":"94 min"}, {"metric":"Peak concurrent users", "async":"7,100", "race":"286,000"},
          {"metric":"Normalized capacity", "async":"1.0×", "race":"40.3×"}, {"metric":"Bot speed advantage", "async":"None in allocation", "race":"Material"},
          {"metric":"Intervention window", "async":"4 days", "race":"Minutes"}, {"metric":"Payment failures", "async":"1,420 re-cleared", "race":"5,180 lost/returned"}],
        "negotiations": [
          {"fan":"Maya Chen", "request":"4 × Front Floor", "reply":"I can keep your group together in Rear Floor at $325 each, or allocate 2 Front Floor at $625 each.", "status":"Accepted Rear Floor"},
          {"fan":"Jordan Brooks", "request":"2 × Front Lower Bowl", "reply":"Mid Lower Bowl is available at the approved $325 price; same quantity, adjacent.", "status":"Pre-authorized"},
          {"fan":"Sofia Martinez", "request":"2 × Premium Upper", "reply":"A second-show option could preserve Premium Upper at $175 each.", "status":"Awaiting response"}]}

if __name__ == "__main__":
    path = Path("data/baseline.json"); path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(baseline(), indent=2))
    print(path)
