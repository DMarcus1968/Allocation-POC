# DemandMatch Market Lab

DemandMatch is a runnable, non-production experiment comparing a four-day ticket request market with a generic high-demand ecommerce race. A fictional 70,000-seat stadium event, 500,000 synthetic fans, deterministic clearing, approved-price negotiation, and a conventional-onsale benchmark form one end-to-end vertical slice.

## Run

Requires Python 3.11+; no third-party runtime packages or API keys are required.

```bash
python3 -m market.scenario   # regenerate the seeded full-scale baseline
python3 server.py
```

Open **http://127.0.0.1:8000**. Use the four top navigation tabs or follow `DEMO_SCRIPT.md`.

## Test

```bash
python3 -m pytest -q
```

The package boundaries are `market/engine.py` (catalog, aggregate generator, pricing validation, deterministic allocation, negotiation), `market/scenario.py` (saved scenario and benchmark), `server.py` (standard-library JSON/static server), and `web/` (responsive SPA and interactive SVG).

## Scope and interpretation

All people, venue, event, results, and economics are synthetic. Dashboard projections are labeled modeled estimates. The generic queue is not a reconstruction of a specific company's platform. This prototype intentionally aggregates the 500,000-fan browser view and uses small request pools in invariant tests; the production-scale aggregate is generated in constant memory. It is not production-ready: there is no authentication, persistent database, payment processor, accessible-seat workflow, or production seat map.

