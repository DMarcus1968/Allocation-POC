"""
Allocation POC - Web Interface

A password-protected web application for interacting with the
ticket allocation proof of concept.

Usage:
    python app.py

Then open http://localhost:5000 in your browser.
Default password: allocation2024 (change via ALLOC_PASSWORD env var)
"""

import os
import json
import secrets
import tempfile
import time
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)

from allocation_engine import (
    Event, generate_synthetic_demand, run_comparison,
    allocate_fcfs, allocate_lottery, allocate_tiered_priority,
    allocate_access_maximizing,
)

app = Flask(__name__)

# Use a stable secret key that survives debug reloader restarts.
# secrets.token_hex(32) would generate a NEW key each restart, silently
# invalidating all session cookies and breaking authentication.
_key_path = os.path.join(tempfile.gettempdir(), "allocation_poc_secret_key")
try:
    with open(_key_path) as _f:
        _stable_key = _f.read().strip()
except FileNotFoundError:
    _stable_key = secrets.token_hex(32)
    with open(_key_path, "w") as _f:
        _f.write(_stable_key)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", _stable_key)

# Password for accessing the interface
APP_PASSWORD = os.environ.get("ALLOC_PASSWORD", "allocation2024")

# File-based result storage (survives debug reloader restarts)
_RESULTS_DIR = os.path.join(tempfile.gettempdir(), "allocation_poc_results")
os.makedirs(_RESULTS_DIR, exist_ok=True)


def _save_results(result_id, data):
    path = os.path.join(_RESULTS_DIR, f"{result_id}.json")
    with open(path, "w") as f:
        json.dump(data, f)


def _load_results(result_id):
    if not result_id:
        return None
    path = os.path.join(_RESULTS_DIR, f"{result_id}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# --- Authentication ---

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if secrets.compare_digest(password, APP_PASSWORD):
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("Incorrect password. Please try again.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# --- Main Pages ---

@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/run", methods=["POST"])
@login_required
def run_allocation():
    """Run the allocation simulation with user-provided parameters."""
    t_start = time.time()
    try:
        # Parse event configuration from form
        event_name = request.form.get("event_name", "Concert Event")
        venue_name = request.form.get("venue_name", "Main Venue")
        max_per_person = int(request.form.get("max_per_person", 4))

        # Parse sections
        section_names = request.form.getlist("section_name[]")
        section_capacities = request.form.getlist("section_capacity[]")
        section_prices = request.form.getlist("section_price[]")

        if not section_names or not section_names[0]:
            flash("Please add at least one section.", "error")
            return redirect(url_for("dashboard"))

        sections = []
        for i in range(len(section_names)):
            if section_names[i].strip():
                sections.append({
                    "name": section_names[i].strip(),
                    "capacity": int(section_capacities[i]),
                    "price": float(section_prices[i]),
                })

        if not sections:
            flash("Please add at least one valid section.", "error")
            return redirect(url_for("dashboard"))

        event = Event(
            name=event_name,
            venue=venue_name,
            sections=sections,
            max_tickets_per_person=max_per_person,
        )

        # Generate demand
        demand_multiplier = float(request.form.get("demand_multiplier", 1.5))
        seed = int(request.form.get("seed", 42))

        t0 = time.time()
        requests_list = generate_synthetic_demand(event, demand_multiplier, seed)
        print(f"  [timing] generate_synthetic_demand: {time.time()-t0:.2f}s ({len(requests_list)} requests)")

        # Run selected strategies
        selected = request.form.getlist("strategies[]")
        if not selected:
            selected = ["fcfs", "lottery", "tiered", "access"]

        strategy_map = {
            "fcfs": ("First-Come-First-Served", allocate_fcfs),
            "lottery": ("Random Lottery", allocate_lottery),
            "tiered": ("Tiered Priority", allocate_tiered_priority),
            "access": ("Access Maximizing", allocate_access_maximizing),
        }

        comparison = {}
        for key in selected:
            if key in strategy_map:
                name, func = strategy_map[key]
                t0 = time.time()
                if key == "fcfs":
                    results, explanation = func(event, requests_list)
                else:
                    results, explanation = func(event, requests_list, seed=seed)
                print(f"  [timing] {name}: {time.time()-t0:.2f}s")
                comparison[key] = {
                    "name": name,
                    "explanation": explanation,
                }

        # Store results to disk (survives debug reloader restarts)
        result_id = secrets.token_hex(8)
        _save_results(result_id, {
            "comparison": json.dumps(comparison, default=str),
            "event": json.dumps({
                "name": event_name,
                "venue": venue_name,
                "sections": sections,
                "max_per_person": max_per_person,
                "demand_multiplier": demand_multiplier,
                "total_requests": len(requests_list),
            }),
        })
        session["result_id"] = result_id

        print(f"  [timing] TOTAL: {time.time()-t_start:.2f}s — result_id={result_id}")
        return redirect(url_for("results"))

    except Exception as e:
        print(f"  [ERROR] Allocation failed after {time.time()-t_start:.2f}s: {type(e).__name__}: {e}")
        flash(f"Allocation error: {e}", "error")
        return redirect(url_for("dashboard"))


@app.route("/results")
@login_required
def results():
    result_id = session.get("result_id")
    stored = _load_results(result_id)

    if not stored:
        flash("No results to display. Please run a simulation first.", "info")
        return redirect(url_for("dashboard"))

    comparison = json.loads(stored["comparison"])
    event_info = json.loads(stored["event"])

    return render_template("results.html", comparison=comparison, event=event_info)


@app.route("/api/results")
@login_required
def api_results():
    """JSON endpoint for results (used by charts)."""
    result_id = session.get("result_id")
    stored = _load_results(result_id)

    if not stored:
        return jsonify({"error": "No results available"}), 404

    return jsonify({
        "comparison": json.loads(stored["comparison"]),
        "event": json.loads(stored["event"]),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n{'='*60}")
    print(f"  Allocation POC - Web Interface")
    print(f"  Open http://localhost:{port} in your browser")
    print(f"  Default password: allocation2024")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
