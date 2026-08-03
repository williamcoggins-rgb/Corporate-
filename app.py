"""CORPORATE HQ — The Dashboard

Futuristic command center for the barbershop empire.
Flask backend serving live DuckDB warehouse data.

Run:  python app.py
      Then open http://localhost:5000
"""

import json
import os
import traceback
import requests as http_requests
from flask import Flask, jsonify, render_template_string, request, Response
from warehouse.db import get_connection, init_schema
from strategy import YOUR_SHOP
from rnd import init_rnd_schema, _seed_assets, _seed_projects
from skills import init_skills_schema, _seed_skills
import anthropic
from managed_agent import (
    setup_managed_agent, update_managed_agent, run_agent_task,
    create_chat_session, send_chat_message,
)

app = Flask(__name__)
_scheduler = None

# Cowork -> Corporate HQ ingestion endpoints (write-only, bearer-auth)
from ingest import ingest_bp
app.register_blueprint(ingest_bp)

# Auto-initialize DB + seed data if empty (needed for Railway/fresh deploys)
def _ensure_db():
    init_schema()
    con = get_connection()
    try:
        count = con.execute("SELECT COUNT(*) FROM competitors").fetchone()[0]
        if count == 0:
            con.close()
            from seed_charlotte import seed
            seed()
            try:
                from seed_platforms import seed_platforms
                seed_platforms()
            except Exception:
                pass  # Optional seed
    except Exception:
        con.close()
        raise
    else:
        con.close()

    # Ensure R&D schema and seed data
    try:
        init_rnd_schema()
        _seed_assets()
        _seed_projects()
    except Exception:
        pass  # R&D is optional

    # Ensure Skills schema and seed data
    try:
        init_skills_schema()
        _seed_skills()
    except Exception:
        pass  # Skills is optional

    # Backfill blank neighborhoods from ZIP / name signals (web-search
    # discovered shops used to land with neighborhood empty)
    try:
        from warehouse.competitors import backfill_neighborhoods
        backfill_neighborhoods()
    except Exception:
        pass

_ensure_db()

# Start the scheduler (APScheduler cron jobs for agent tiers)
try:
    from scheduler import init_scheduler, get_schedule_status
    _scheduler = init_scheduler(app)
except Exception:
    pass  # Scheduler is optional — runs without APScheduler


# ════════════════════════════════════════════════════════════════════════
#  DATA LAYER — pulls from the warehouse
# ════════════════════════════════════════════════════════════════════════

def _q(query, params=None):
    con = get_connection()
    try:
        cur = con.execute(query, params or [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        con.close()


def _shop_threat_reason(row):
    """Build a plain-English reason why this shop is a threat, sourced from
    actual per-shop research (competitor notes + hotness scorecard components),
    NOT from the generic threat-formula sub-scores."""
    import re as _re

    notes = (row.get("notes") or "").strip()
    neighborhood = row.get("neighborhood") or ""

    hotness_json = row.get("hotness_components")
    try:
        h = json.loads(hotness_json) if isinstance(hotness_json, str) else dict(hotness_json or {})
    except (ValueError, TypeError):
        h = {}

    avg_rating = h.get("avg_rating")
    total_reviews = h.get("total_reviews") or 0
    avg_price = h.get("avg_service_price")
    total_followers = h.get("total_followers") or 0
    active_barbers = h.get("active_barbers") or 0

    parts = []

    # Established / founded — extract just the year from notes
    year_match = _re.search(
        r'(?:Est\.?\s*|Founded\s+(?:in\s+)?|Since\s+|Opened\s+(?:in\s+)?)'
        r'(\w+\.?\s*\d{4}|\d{4})',
        notes, _re.IGNORECASE,
    )
    if year_match:
        parts.append(f"in business since {year_match.group(1).strip()}")
    elif row.get("founded_year"):
        parts.append(f"in business since {row['founded_year']}")

    # Barber count — prefer hotness data, fall back to notes
    if active_barbers and active_barbers > 1:
        parts.append(f"{active_barbers} barbers on staff")
    else:
        m = _re.search(r'(\d+)\s*barber', notes, _re.IGNORECASE)
        if m and int(m.group(1)) > 1:
            parts.append(f"{m.group(1)} barbers on staff")

    # Rating + reviews
    if avg_rating and total_reviews:
        parts.append(f"{avg_rating:.1f}-star rating across {total_reviews:,} reviews")
    elif avg_rating:
        parts.append(f"{avg_rating:.1f}-star rating")

    # Pricing
    if avg_price and avg_price > 0:
        parts.append(f"average service price around ${avg_price:.0f}")

    # Social following
    if total_followers >= 500:
        parts.append(f"{total_followers:,} social media followers")

    # Standout detail from notes
    note_lower = notes.lower()
    standout = None
    if "franchise" in note_lower or "14 locations" in note_lower or "locations in" in note_lower:
        standout = "part of a multi-location franchise"
    elif "oldest" in note_lower:
        standout = "a historic institution in Charlotte"
    elif "cash only" in note_lower:
        standout = "cash-only shop"
    elif "beer" in note_lower:
        standout = "offers beer on-site"
    elif "warm towel" in note_lower or "steam towel" in note_lower:
        standout = "complimentary hot towel service"
    elif "walk-in" in note_lower:
        standout = "accepts walk-ins"

    if not parts and not standout:
        if notes:
            clean = notes.split(".")[0].strip()
            if len(clean) > 10:
                return f"{clean}. Limited intel so far — agents are still gathering pricing and review data."
        return "Limited intel collected so far — agents are still gathering data on this shop."

    sentence = ", ".join(parts[:3])
    if sentence:
        sentence = sentence[0].upper() + sentence[1:]
        if standout:
            sentence += " — " + standout
    else:
        sentence = standout[0].upper() + standout[1:]
    sentence += "."

    if len(parts) <= 1:
        sentence += " Agents are still gathering more details."

    return sentence


def get_dashboard_data():
    """Pull all data the dashboard needs in one pass."""
    d = {}

    # Shop basics
    d["shop"] = {
        "name": YOUR_SHOP.get("name", "HQ"),
        "neighborhood": YOUR_SHOP.get("neighborhood", ""),
        "setup": YOUR_SHOP.get("setup", ""),
        "goal": YOUR_SHOP.get("goal", ""),
        "years_experience": YOUR_SHOP.get("years_experience", 0),
        "annual_gross": YOUR_SHOP.get("annual_gross", 0),
        "monthly_gross": YOUR_SHOP.get("monthly_gross", 0),
        "barbers": YOUR_SHOP.get("barbers", 1),
        "deposits": YOUR_SHOP.get("deposits", False),
        "booking_platform": YOUR_SHOP.get("booking_platform", ""),
        "has_proprietary_os": YOUR_SHOP.get("booking_os", {}).get("type") == "proprietary",
        "migrating_from": YOUR_SHOP.get("booking_os", {}).get("migrating_from"),
        "os_features_live": YOUR_SHOP.get("booking_os", {}).get("features_live", []),
        "os_features_planned": YOUR_SHOP.get("booking_os", {}).get("features_planned", []),
        "wholesale": YOUR_SHOP.get("revenue_model", {}).get("wholesale_membership", False),
    }
    d["prices"] = YOUR_SHOP.get("prices", {})

    # Competitor counts
    d["competitor_count"] = _q(
        "SELECT COUNT(*) as n FROM competitors WHERE status = 'Active'"
    )[0]["n"]

    d["franchise_count"] = _q("""
        SELECT COUNT(DISTINCT competitor_id) as n FROM competitors
        WHERE company_name LIKE 'No Grease%' OR company_name LIKE 'Da Lucky Spot%'
    """)[0]["n"]

    d["independent_count"] = d["competitor_count"] - d["franchise_count"]

    # Pricing
    d["avg_fade"] = float(_q(
        "SELECT COALESCE(ROUND(AVG(price), 2), 0) as avg FROM price_history WHERE service_name = 'Fade'"
    )[0]["avg"])

    d["max_fade"] = float(_q(
        "SELECT COALESCE(ROUND(MAX(price), 2), 0) as mx FROM price_history WHERE service_name = 'Fade'"
    )[0]["mx"])

    # Neighborhoods — with real shop counts, avg fade, and density context.
    # Each shop's neighborhood is resolved from its record, ZIP, or name so
    # web-search-discovered shops land in their real area, never "Unknown".
    from warehouse.competitors import resolve_neighborhood
    PENDING_ZONE = "Location pending — agents still verifying"
    your_neighborhood = YOUR_SHOP.get("neighborhood", "")
    your_fade = YOUR_SHOP.get("prices", {}).get("Fade", 0)
    _shop_rows = _q("""
        SELECT c.competitor_id, c.neighborhood, c.zip_code, c.company_name,
               c.hq_location, AVG(ph.price) as fade_price
        FROM competitors c
        LEFT JOIN price_history ph ON ph.competitor_id = c.competitor_id
            AND ph.service_name = 'Fade'
        WHERE c.status = 'Active'
        GROUP BY c.competitor_id, c.neighborhood, c.zip_code, c.company_name,
                 c.hq_location
    """)
    _zones = {}
    for r in _shop_rows:
        hood = resolve_neighborhood(
            r["neighborhood"], r["zip_code"], r["company_name"], r["hq_location"]
        ) or PENDING_ZONE
        z = _zones.setdefault(hood, {"neighborhood": hood, "shops": 0, "_fades": []})
        z["shops"] += 1
        if r["fade_price"]:
            z["_fades"].append(float(r["fade_price"]))
    d["neighborhoods"] = []
    for z in _zones.values():
        z["avg_fade"] = round(sum(z["_fades"]) / len(z["_fades"]), 2) if z["_fades"] else None
        z["pending"] = z["neighborhood"] == PENDING_ZONE
        del z["_fades"]
        d["neighborhoods"].append(z)
    d["neighborhoods"].sort(key=lambda z: (z["pending"], -z["shops"]))
    for n in d["neighborhoods"]:
        s = n["shops"]
        if n["pending"]:
            n["density"] = "Verifying"
        elif s == 0:
            n["density"] = "Empty"
        elif s <= 2:
            n["density"] = "Low"
        elif s <= 4:
            n["density"] = "Medium"
        elif s <= 6:
            n["density"] = "Busy"
        else:
            n["density"] = "Packed"
        n["is_yours"] = (not n["pending"]) and (
            (n["neighborhood"] or "").lower().replace(" ", "")
            == your_neighborhood.lower().replace(" ", "")
        )
        if n["avg_fade"] and your_fade:
            diff = your_fade - float(n["avg_fade"])
            if diff > 5:
                n["price_note"] = f"${abs(diff):.0f} above avg"
            elif diff < -5:
                n["price_note"] = f"${abs(diff):.0f} below avg"
            else:
                n["price_note"] = "Near your price"
        else:
            n["price_note"] = ""
    # Show the busiest zones plus the pending bucket (always visible so the
    # collection gap stays on the radar); badge shows the true total
    d["neighborhood_zones_total"] = len(d["neighborhoods"])
    d["neighborhoods"] = (
        [z for z in d["neighborhoods"] if not z["pending"]][:11]
        + [z for z in d["neighborhoods"] if z["pending"]]
    )

    # Recent moves
    d["recent_moves"] = _q("""
        SELECT c.company_name, cm.move_type, cm.description,
               cm.move_date
        FROM competitor_moves cm
        JOIN competitors c ON c.competitor_id = cm.competitor_id
        ORDER BY cm.move_date DESC LIMIT 6
    """)

    # Social leaders — one row per distinct brand (latest snapshot, highest followers)
    d["social_leaders"] = _q("""
        WITH per_competitor AS (
            SELECT cs.competitor_id, c.company_name, cs.platform,
                   cs.followers, cs.engagement_rate,
                   ROW_NUMBER() OVER (
                       PARTITION BY cs.competitor_id
                       ORDER BY cs.followers DESC, cs.snapshot_date DESC
                   ) AS rn
            FROM competitor_social cs
            JOIN competitors c ON c.competitor_id = cs.competitor_id
        ),
        best AS (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY LEFT(company_name, 10)
                ORDER BY followers DESC
            ) AS brand_rn
            FROM per_competitor WHERE rn = 1
        )
        SELECT company_name, platform, followers, engagement_rate
        FROM best WHERE brand_rn = 1
        ORDER BY followers DESC
        LIMIT 5
    """)

    # Barber talent pool
    d["barber_count"] = _q("SELECT COUNT(*) as n FROM barbers")[0]["n"]

    # Scores
    d["score_count"] = _q("SELECT COUNT(*) as n FROM competitor_scores")[0]["n"]

    # Review avg
    d["review_avg"] = float(_q(
        "SELECT COALESCE(ROUND(AVG(rating), 1), 0) as avg FROM review_snapshots"
    )[0]["avg"])

    # Top competitors by threat — latest score per competitor, deduped,
    # joined with competitor notes + hotness scorecard for real per-shop facts
    d["top_threats"] = _q("""
        WITH latest_threat AS (
            SELECT cs.competitor_id, cs.score, cs.scored_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY cs.competitor_id
                       ORDER BY cs.scored_at DESC
                   ) AS rn
            FROM competitor_scores cs
            WHERE cs.score_type = 'threat'
        ),
        latest_hotness AS (
            SELECT cs.competitor_id, cs.components,
                   ROW_NUMBER() OVER (
                       PARTITION BY cs.competitor_id
                       ORDER BY cs.scored_at DESC
                   ) AS rn
            FROM competitor_scores cs
            WHERE cs.score_type = 'hotness'
        )
        SELECT c.company_name, c.neighborhood, c.zip_code, c.notes,
               c.ownership_type, c.founded_year, c.business_model,
               lt.score as threat_score,
               lh.components as hotness_components
        FROM latest_threat lt
        JOIN competitors c ON c.competitor_id = lt.competitor_id
        LEFT JOIN latest_hotness lh ON lh.competitor_id = lt.competitor_id AND lh.rn = 1
        WHERE lt.rn = 1
        ORDER BY lt.score DESC LIMIT 8
    """)
    for t in d["top_threats"]:
        t["neighborhood"] = resolve_neighborhood(
            t.get("neighborhood"), t.get("zip_code"), t.get("company_name"), None
        )
        t["reason"] = _shop_threat_reason(t)

    # Agent runs
    d["agent_runs"] = _q("""
        SELECT agent_name, status, started_at, records_processed
        FROM agent_runs
        ORDER BY started_at DESC LIMIT 8
    """)

    # Agent fleet — real run history per registered agent, from agent_runs
    fleet_registry = [
        ("pricing_scout", "PricingScout"), ("review_harvester", "ReviewHarvester"),
        ("social_listener", "SocialListener"), ("shop_watcher", "ShopWatcher"),
        ("platform_scout", "PlatformScout"), ("normalizer", "Normalizer"),
        ("barber_enricher", "BarberEnricher"), ("delta_spotter", "DeltaSpotter"),
        ("platform_analyzer", "PlatformAnalyzer"), ("scorecard", "Scorecard"),
        ("skill_runner", "SkillRunner"), ("price_war_alert", "PriceWarAlert"),
        ("reputation_radar", "ReputationRadar"), ("talent_tracker", "TalentTracker"),
        ("weekly_digest", "WeeklyDigest"),
    ]
    run_stats = {r["agent_name"]: r for r in _q("""
        SELECT agent_name, MAX(started_at) AS last_run, COUNT(*) AS run_count
        FROM agent_runs GROUP BY agent_name
    """)}
    d["agent_fleet"] = [{
        "display": display,
        "last_run": run_stats.get(name, {}).get("last_run"),
        "run_count": run_stats.get(name, {}).get("run_count", 0),
    } for name, display in fleet_registry]
    d["agents_executed"] = sum(1 for a in d["agent_fleet"] if a["run_count"])
    fleet_last_runs = [a["last_run"] for a in d["agent_fleet"] if a["last_run"]]
    d["last_agent_cycle"] = max(fleet_last_runs) if fleet_last_runs else None

    # Alerts — from alerts_log, with competitor names
    d["alerts"] = _q("""
        SELECT a.alert_type, a.severity, a.title, a.detail, a.created_at,
               c.company_name
        FROM alerts_log a
        LEFT JOIN competitors c ON c.competitor_id = a.competitor_id
        ORDER BY a.created_at DESC LIMIT 8
    """)

    # R&D projects — full data for organized display
    try:
        d["rnd_projects"] = _q("""
            SELECT project_id, lab, title, description, status, priority,
                   revenue_potential, hypothesis, assets_used
            FROM rnd_projects
            ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                     WHEN 'medium' THEN 2 ELSE 3 END, project_id ASC
        """)
    except Exception:
        d["rnd_projects"] = []

    # Skills data — full data for organized display
    try:
        d["skills"] = _q("""
            SELECT skill_id, name, display_name, category, description,
                   status, phase, pattern, priority, trigger_accuracy,
                   execution_quality, token_efficiency, version, connected_to,
                   last_run, last_output
            FROM skills
            WHERE status != 'retired'
            ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                     WHEN 'medium' THEN 2 ELSE 3 END, skill_id ASC
        """)
    except Exception:
        d["skills"] = []
    d["skills_executed"] = sum(1 for s in d.get("skills", []) if s.get("last_run"))

    # Skills summary stats
    d["skills_by_cat"] = {}
    d["skills_by_phase"] = {}
    for s in d.get("skills", []):
        cat = s.get("category", "unknown")
        phase = s.get("phase", "identify")
        if cat not in d["skills_by_cat"]:
            d["skills_by_cat"][cat] = {"count": 0, "active": 0, "testing": 0}
        d["skills_by_cat"][cat]["count"] += 1
        st = s.get("status", "draft")
        if st in ("active",):
            d["skills_by_cat"][cat]["active"] += 1
        elif st in ("testing",):
            d["skills_by_cat"][cat]["testing"] += 1

        if phase not in d["skills_by_phase"]:
            d["skills_by_phase"][phase] = 0
        d["skills_by_phase"][phase] += 1

    # R&D summary stats
    d["rnd_labs"] = {}
    for p in d["rnd_projects"]:
        lab = p.get("lab", "unknown")
        if lab not in d["rnd_labs"]:
            d["rnd_labs"][lab] = {"count": 0, "in_progress": 0, "research": 0, "idea": 0}
        d["rnd_labs"][lab]["count"] += 1
        st = p.get("status", "idea")
        if st in d["rnd_labs"][lab]:
            d["rnd_labs"][lab][st] += 1

    # Council vote conditions
    monthly = d["shop"]["monthly_gross"]
    d["council"] = {
        "strategist": {"ready": monthly >= 4000, "condition": "Earning $4K/month with multiple income streams"},
        "comptroller": {"ready": monthly >= 4000 and d["shop"]["deposits"], "condition": "Earning $4K/month with deposits turned on"},
        "intel": {"ready": d["competitor_count"] >= 15, "condition": "Tracking 15+ competitors with real data"},
        "operator": {"ready": d["shop"]["has_proprietary_os"] and d["shop"]["migrating_from"] is None, "condition": "Booking system live and clients moved over"},
        "brand": {"ready": d["shop"]["name"] != "Your Shop", "condition": "Shop has a name and brand identity"},
    }

    return d


# ════════════════════════════════════════════════════════════════════════
#  API ROUTES
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(get_dashboard_data())


@app.route("/api/competitors")
def api_competitors():
    rows = _q("""
        SELECT c.*, cs.score as threat_score
        FROM competitors c
        LEFT JOIN competitor_scores cs ON c.competitor_id = cs.competitor_id
            AND cs.score_type = 'threat'
        WHERE c.status = 'Active'
        ORDER BY cs.score DESC NULLS LAST
    """)
    return jsonify(rows)


@app.route("/api/prices/by-zip")
def api_prices_by_zip():
    """Zip code pricing rankings — most to least expensive."""
    service = request.args.get("service")
    try:
        from agents.pricing_scout import PricingScout
        scout = PricingScout()
        data = scout.prices_by_zip(service_name=service)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/prices/by-zip/<zip_code>")
def api_prices_by_zip_detail(zip_code):
    """Per-shop pricing detail for a specific zip code."""
    service = request.args.get("service")
    try:
        from agents.pricing_scout import PricingScout
        scout = PricingScout()
        data = scout.zip_price_detail(zip_code, service_name=service)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/prices/zip-spread")
def api_prices_zip_spread():
    """Price spread across zips — which services vary most by location."""
    try:
        from agents.pricing_scout import PricingScout
        scout = PricingScout()
        data = scout.zip_price_spread()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/prices/zip-report")
def api_prices_zip_report():
    """Full zip pricing report — rankings, breakdowns, opportunities."""
    try:
        from agents.warehouse_divisions.pricing_intelligence import PricingIntelZipAnalyst
        analyst = PricingIntelZipAnalyst()
        report = analyst.full_zip_report()
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/skills/run/<skill_name>", methods=["POST"])
def api_skill_run(skill_name):
    """Run a skill's agent pipeline."""
    try:
        from agents.skill_executor import SkillExecutor
        executor = SkillExecutor()
        result = executor.run_skill(skill_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "skill": skill_name}), 500


@app.route("/api/skills/preview/<skill_name>")
def api_skill_preview(skill_name):
    """Preview what agents a skill will run."""
    try:
        from agents.skill_executor import SKILL_PIPELINES
        pipeline = SKILL_PIPELINES.get(skill_name)
        if not pipeline:
            return jsonify({"error": f"No pipeline for: {skill_name}"}), 404
        return jsonify({
            "skill": skill_name,
            "description": pipeline["description"],
            "stages": pipeline["stages"],
            "total_agents": sum(len(s["agents"]) for s in pipeline.get("stages", [])),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/skills")
def api_skills():
    try:
        rows = _q("""
            SELECT s.*, COUNT(st.test_id) as test_count,
                   SUM(CASE WHEN st.passed THEN 1 ELSE 0 END) as tests_passed
            FROM skills s
            LEFT JOIN skill_tests st ON s.skill_id = st.skill_id
            WHERE s.status != 'retired'
            GROUP BY s.skill_id, s.name, s.display_name, s.category,
                     s.description, s.trigger_phrases, s.status, s.phase,
                     s.pattern, s.priority, s.doctrine_alignment,
                     s.trigger_accuracy, s.execution_quality, s.token_efficiency,
                     s.connected_to, s.version, s.created_at, s.updated_at
            ORDER BY s.skill_id
        """)
    except Exception:
        rows = []
    return jsonify(rows)


@app.route("/api/pricing")
def api_pricing():
    rows = _q("""
        SELECT ph.service_name, c.company_name, ph.price, ph.recorded_at
        FROM price_history ph
        JOIN competitors c ON c.competitor_id = ph.competitor_id
        ORDER BY ph.service_name, ph.price DESC
    """)
    return jsonify(rows)


@app.route("/api/schedule")
def api_schedule():
    """Return the current scheduler status and upcoming jobs."""
    if _scheduler:
        return jsonify(get_schedule_status(_scheduler))
    return jsonify({"status": "not_running", "jobs": [], "note": "APScheduler not initialized"})


# ════════════════════════════════════════════════════════════════════════
#  WAREHOUSE API — full table access for external consumers
# ════════════════════════════════════════════════════════════════════════

# Tables available via the warehouse API
WAREHOUSE_TABLES = [
    "competitors", "competitor_moves", "competitor_social", "competitor_products",
    "competitor_financials", "competitor_scores", "price_history", "review_snapshots",
    "barbers", "barber_specialties", "neighborhoods", "platform_profiles",
    "platform_solo_barbers", "rnd_projects", "rnd_assets", "rnd_experiments",
    "skills", "skill_deployments", "skill_tests", "alerts_log", "agent_runs",
]


@app.route("/api/warehouse")
def api_warehouse_index():
    """List all available tables and their row counts."""
    results = []
    for table in WAREHOUSE_TABLES:
        try:
            count = _q(f"SELECT COUNT(*) AS cnt FROM {table}")[0]["cnt"]
        except Exception:
            count = 0
        results.append({"table": table, "rows": count})
    return jsonify({"tables": results})


@app.route("/api/warehouse/<table_name>")
def api_warehouse_table(table_name):
    """Return all rows from a warehouse table. Supports ?limit=N&offset=N."""
    if table_name not in WAREHOUSE_TABLES:
        return jsonify({"error": f"Unknown table: {table_name}"}), 404

    limit = request.args.get("limit", 1000, type=int)
    offset = request.args.get("offset", 0, type=int)
    limit = min(limit, 10000)  # cap at 10k rows per request

    rows = _q(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", [limit, offset])
    # Serialize non-JSON-safe types
    for row in rows:
        for k, v in row.items():
            if not isinstance(v, (str, int, float, bool, type(None))):
                row[k] = str(v)

    return jsonify({"table": table_name, "count": len(rows), "rows": rows})


# ════════════════════════════════════════════════════════════════════════
#  AI CHAT ASSISTANT — Claude Managed Agent + Messages API fallback
# ════════════════════════════════════════════════════════════════════════

def _execute_chat_tool(tool_name, tool_input):
    """Execute a tool call for the Messages API fallback."""
    if tool_name == "query_warehouse":
        sql = tool_input.get("sql", "")
        stripped = sql.strip().upper()
        if not stripped.startswith("SELECT") and not stripped.startswith("WITH") and not stripped.startswith("FROM"):
            return {"error": "Only SELECT queries are allowed."}
        try:
            rows = _q(sql)
            if len(rows) > 50:
                rows = rows[:50]
                return {"rows": rows, "note": "Showing first 50 rows."}
            return {"rows": rows, "count": len(rows)}
        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}

    elif tool_name == "read_agent_logs":
        agent_name = tool_input.get("agent_name", "")
        limit = tool_input.get("limit", 10)
        try:
            if agent_name:
                rows = _q(
                    "SELECT * FROM agent_runs WHERE agent_name ILIKE ? ORDER BY started_at DESC LIMIT ?",
                    [f"%{agent_name}%", limit]
                )
            else:
                rows = _q("SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT ?", [limit])
            return {"runs": rows, "count": len(rows)}
        except Exception:
            return {"runs": [], "count": 0, "note": "No agent run logs found yet."}

    return {"error": f"Unknown tool: {tool_name}"}


@app.route("/api/setup-agent", methods=["POST"])
def api_setup_agent():
    """One-time setup: create agent + environment, return IDs for Railway env vars."""
    agent_id, env_id, error = setup_managed_agent()
    if error:
        return jsonify({"error": error}), 500
    return jsonify({
        "agent_id": agent_id,
        "env_id": env_id,
        "note": "Save these as CORPORATE_HQ_AGENT_ID and CORPORATE_HQ_ENV_ID in Railway."
    })


@app.route("/api/update-agent", methods=["POST"])
def api_update_agent():
    """Push the current system prompt + custom tools to the existing agent.

    Run this after deploying code that changes CUSTOM_TOOLS or the system
    prompt — the live agent keeps its old config until updated.
    """
    version, error = update_managed_agent()
    if error:
        return jsonify({"error": error}), 500
    return jsonify({
        "agent_version": version,
        "note": "Agent updated. New sessions will have the warehouse tools."
    })


@app.route("/api/run-agent", methods=["POST"])
def api_run_agent():
    """Run a managed agent task. POST {task: "..."}."""
    body = request.get_json(silent=True) or {}
    task = body.get("task", "").strip()
    if not task:
        return jsonify({"error": "No task provided."}), 400
    result = run_agent_task(task)
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/chat/session", methods=["POST"])
def api_chat_session():
    """Create a managed agent session for the chat widget."""
    result = create_chat_session()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """AI chat endpoint — managed agent session or Messages API fallback."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured."}), 500

    body = request.get_json(silent=True) or {}
    user_message = body.get("message", "").strip()
    session_id = body.get("session_id", "")
    mode = body.get("mode", "messages")
    history = body.get("history", [])

    if not user_message:
        return jsonify({"error": "No message provided."}), 400

    # ── MANAGED AGENT MODE ──
    # Uses correct SDK paths: client.beta.sessions.events.stream() / events.send()
    if mode == "managed" and session_id and session_id != "local":
        result = send_chat_message(session_id, user_message)
        if "error" not in result:
            return jsonify(result)
        # Fall through to Messages API on error
        mode = "messages"

    # ── MESSAGES API FALLBACK ──
    system_prompt = """You are the Corporate HQ AI Assistant for a barbershop business in Charlotte, NC (South Park area, zip 28210).

You are talking to William, the owner. He charges $40-65 per cut and is building a competitive intelligence operation to prepare for expanding from a suite to a full shop.

YOUR ROLE:
- Answer questions about his business using real data from the warehouse
- Speak in plain, direct business language — no developer jargon, no corporate buzzwords
- If the data does not exist yet, say so honestly. Never make up numbers.
- Keep answers concise and actionable

WHAT YOU HAVE ACCESS TO:
1. A DuckDB warehouse with competitor data, pricing, reviews, social media, and agent logs
2. Key tables: competitors, price_history, review_snapshots, competitor_social, competitor_moves, barbers, neighborhoods, alerts_log, agent_runs, rnd_projects, skills

WAREHOUSE SCHEMA HIGHLIGHTS:
- competitors: competitor_id, company_name, industry, hq_location, neighborhood, zip_code, ownership_type, status
- price_history: competitor_id, service_name, price, recorded_at
- review_snapshots: competitor_id, platform, rating, review_count, sentiment_score
- competitor_social: competitor_id, platform, followers, engagement_rate
- competitor_moves: competitor_id, move_type, description, move_date, impact_level
- agent_runs: agent_name, started_at, finished_at, status, records_processed

When querying, always use DuckDB SQL syntax. Use QUALIFY ROW_NUMBER() for latest records. Use single quotes for string literals."""

    fallback_tools = [
        {
            "name": "query_warehouse",
            "description": "Execute a read-only SQL query against the DuckDB warehouse.",
            "input_schema": {
                "type": "object",
                "properties": {"sql": {"type": "string", "description": "The SQL SELECT query"}},
                "required": ["sql"]
            }
        },
        {
            "name": "read_agent_logs",
            "description": "Read recent agent run logs.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Optional agent name filter"},
                    "limit": {"type": "integer", "description": "Number of runs (default 10)"}
                },
                "required": []
            }
        }
    ]

    client = anthropic.Anthropic(api_key=api_key)
    messages = []
    for h in history[-20:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            tools=fallback_tools,
            messages=messages,
        )

        for _ in range(5):
            if response.stop_reason != "tool_use":
                break
            tool_results = []
            assistant_content = []
            for block in response.content:
                if block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                    result = _execute_chat_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })
                elif block.type == "text":
                    assistant_content.append({
                        "type": "text",
                        "text": block.text,
                    })
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=system_prompt,
                tools=fallback_tools,
                messages=messages,
            )

        reply = ""
        for block in response.content:
            if block.type == "text":
                reply += block.text

        if not reply:
            reply = "I processed your request but could not generate a text response. Try rephrasing your question."

        return jsonify({"reply": reply, "mode": "messages"})

    except anthropic.APIError as e:
        return jsonify({"error": f"Claude API error: {str(e)}"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Chat failed: {str(e)}"}), 500


@app.route("/api/tts", methods=["POST"])
def api_tts():
    """ElevenLabs TTS proxy — converts text to speech audio."""
    el_key = os.environ.get("ELEVENLABS_API_KEY", "")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "")

    if not el_key or not voice_id:
        return jsonify({"error": "ElevenLabs not configured. Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID."}), 500

    body = request.get_json(silent=True) or {}
    text = body.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided."}), 400

    try:
        resp = http_requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": el_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return jsonify({"error": f"ElevenLabs error: {resp.status_code}"}), 502

        return Response(resp.content, mimetype="audio/mpeg")

    except Exception as e:
        return jsonify({"error": f"TTS failed: {str(e)}"}), 500


# ════════════════════════════════════════════════════════════════════════
#  MAIN ROUTE — serves the dashboard
# ════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    data = get_dashboard_data()
    return render_template_string(DASHBOARD_HTML, data=data, data_json=json.dumps(data, default=str))


# ════════════════════════════════════════════════════════════════════════
#  THE DASHBOARD — HTML + CSS + JS (all inline, zero dependencies)
# ════════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CORPORATE HQ</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
/* ═══════════════════════════════════════════════════════════════
   CSS CUSTOM PROPERTIES — NIKE-STYLE LIGHT SYSTEM
   White canvas, near-black ink, light-grey panels,
   one accent (teal) used sparingly.
   NOTE: --white is the legacy emphasis-text var used throughout
   the template; on the light theme it maps to near-black ink.
   ═══════════════════════════════════════════════════════════════ */
@property --angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}

:root {
  --white: #111111;
  --red: #D6293A;
  --red-soft: #C1121F;
  --teal: #00796B;
  --teal-soft: #00665C;

  --bg-base: #FFFFFF;
  --bg-surface: #F5F5F5;
  --bg-elevated: #EFEFEF;
  --bg-hover: #E9E9E9;
  --bg-card: #F5F5F5;

  --text-primary: #111111;
  --text-secondary: #4B4B4B;
  --text-muted: #757575;

  --border-subtle: rgba(17,17,17,0.08);
  --border-glow: rgba(17,17,17,0.12);

  --shadow-glow-red: none;
  --shadow-glow-teal: none;

  --radius: 8px;
  --radius-sm: 6px;
  --radius-xs: 4px;

  --font-sans: 'Helvetica Neue', Helvetica, 'Inter', Arial, sans-serif;
  --font-mono: 'Helvetica Neue', Helvetica, 'Inter', Arial, sans-serif;
  --font-display: 'Anton', 'Arial Narrow', 'Helvetica Neue', sans-serif;

  --text-xs: clamp(0.6875rem, 0.5vw + 0.5rem, 0.75rem);
  --text-sm: clamp(0.8125rem, 0.6vw + 0.6rem, 0.875rem);
  --text-base: clamp(0.875rem, 0.8vw + 0.6rem, 1rem);
  --text-lg: clamp(1.125rem, 1vw + 0.75rem, 1.25rem);
  --text-xl: clamp(1.5rem, 2vw + 0.75rem, 2rem);
  --text-2xl: clamp(2rem, 3vw + 1rem, 3rem);
  --text-hero: clamp(2.5rem, 4vw + 1rem, 3.5rem);
}

/* ═══════════════════════════════════════════════════════════════
   RESET + BASE
   ═══════════════════════════════════════════════════════════════ */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
html { overflow-x: hidden; }

body {
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.5;
  overflow-x: hidden;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

/* ═══════════════════════════════════════════════════════════════
   LAYOUT — CLEAN WHITE CANVAS
   ═══════════════════════════════════════════════════════════════ */
.shell {
  position: relative;
  z-index: 2;
  max-width: 1440px;
  margin: 0 auto;
  padding: 36px 48px 80px;
}
@media (max-width: 768px) {
  .shell { padding: 20px 20px 60px; }
}

/* ═══════════════════════════════════════════════════════════════
   NIKE-STYLE HEADER — utility strip + white sticky nav
   ═══════════════════════════════════════════════════════════════ */
.utility-strip {
  background: var(--bg-surface);
  padding: 6px 48px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 20px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-primary);
}
.utility-strip span { cursor: default; }
.utility-strip .sep { color: var(--border-subtle); }

.site-header {
  position: sticky;
  top: 0;
  z-index: 600;
  background: var(--bg-base);
  border-bottom: 1px solid rgba(17,17,17,0.06);
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 48px;
  height: 64px;
  background: var(--bg-base);
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.topbar-logo {
  width: 38px; height: 38px;
  border-radius: 4px;
  background: var(--white);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 15px;
  color: var(--bg-base);
  letter-spacing: 0;
}
.topbar-title {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 400;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-primary);
  line-height: 1;
}
.topbar-subtitle {
  font-size: 9px;
  color: var(--text-muted);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-top: 3px;
}

/* Status dots — now a strip inside the Overview tab */
.topbar-status {
  display: flex;
  align-items: center;
  gap: 18px;
}
.status-dot {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.5px;
  padding: 8px 14px;
  border-radius: 4px;
  background: var(--bg-surface);
  transition: background 0.2s;
}
.status-dot:hover { background: var(--bg-elevated); }
.status-dot .dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
  position: relative;
}
.dot-green { background: #0E9F6E; }
.dot-red { background: var(--red); }
.dot-teal { background: var(--teal); }
.dot-yellow { background: #B45309; }
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.8); }
}

/* ── TAB NAVIGATION — Nike Men/Women/Kids bar ── */
.topbar-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1;
  flex-wrap: wrap;
}
.nav-tab {
  position: relative;
  padding: 20px 14px;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-primary);
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  transition: opacity 0.15s;
}
.nav-tab::after {
  content: '';
  position: absolute;
  left: 14px; right: 14px; bottom: 12px;
  height: 2px;
  background: var(--white);
  transform: scaleX(0);
  transition: transform 0.2s ease;
}
.nav-tab:hover::after { transform: scaleX(1); }
.nav-tab.active::after { transform: scaleX(1); }

.topbar-assistant {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
  border-radius: 30px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--bg-base);
  background: var(--white);
  border: none;
  cursor: pointer;
  font-family: inherit;
  transition: opacity 0.2s;
  white-space: nowrap;
  flex-shrink: 0;
}
.topbar-assistant:hover { opacity: 0.75; }

.tab-panel { display: none; }
.tab-panel.active { display: block; animation: tab-fade 0.3s ease; }
@keyframes tab-fade {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 920px) {
  .topbar { flex-wrap: wrap; height: auto; padding: 12px 20px; row-gap: 0; }
  .topbar-nav { order: 3; flex-basis: 100%; justify-content: center; gap: 0; }
  .nav-tab { padding: 12px 10px; font-size: 12px; letter-spacing: 1px; }
  .utility-strip { padding: 6px 20px; }
  .topbar-status { flex-wrap: wrap; }
}
@media (max-width: 640px) {
  .topbar-subtitle { display: none; }
  .topbar-title { font-size: 17px; }
  .topbar-assistant { padding: 8px 12px; font-size: 11px; }
  .topbar-status { gap: 6px; }
  .status-dot { font-size: 10px; padding: 6px 10px; }
}

/* Migration banner removed — Booksy/Emporium OS is roadmap, not live status. */

/* ═══════════════════════════════════════════════════════════════
   BENTO GRID
   ═══════════════════════════════════════════════════════════════ */
.bento {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: minmax(80px, auto);
}

/* Card sizes */
.b-hero    { grid-column: span 8; grid-row: span 4; }
.b-side    { grid-column: span 4; grid-row: span 4; }
.b-wide    { grid-column: span 6; grid-row: span 4; }
.b-third   { grid-column: span 4; grid-row: span 4; }
.b-full    { grid-column: span 12; grid-row: span 3; }
.b-half    { grid-column: span 6; grid-row: span 3; }

@media (max-width: 1024px) {
  .bento { grid-template-columns: repeat(6, 1fr); }
  .b-hero, .b-full { grid-column: span 6; }
  .b-side, .b-third { grid-column: span 6; }
  .b-wide, .b-half { grid-column: span 6; }
}
@media (max-width: 640px) {
  .bento { grid-template-columns: 1fr; gap: 12px; }
  .b-hero, .b-side, .b-wide, .b-third, .b-full, .b-half { grid-column: span 1; grid-row: auto; }
  .shell { padding: 10px 12px 40px; }

  /* Cards — tighter padding on mobile */
  .card { padding: 16px 14px; border-radius: 12px; }

  /* Revenue hero — scale down */
  .stat-row { flex-wrap: wrap; }
  .stat-sub { font-size: 11px; line-height: 1.5; }

  /* Metric grid — 2 columns */
  .metric-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .metric-cell { padding: 8px 6px; }

  /* Council grid — full width */
  .council-grid { gap: 6px; }
  .council-row { flex-wrap: wrap; gap: 4px; }
  .council-cond { font-size: 10px; flex-basis: 100%; padding-left: 28px; }

  /* Tables — horizontal scroll */
  .intel-table { display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .intel-table th { font-size: 8px; padding: 4px 8px; white-space: nowrap; }
  .intel-table td { font-size: 11px; padding: 8px; white-space: nowrap; }

  /* Agent grid — single column */
  .agent-grid { grid-template-columns: 1fr; }
  .agent-cell { padding: 6px 8px; }

  /* Stat strip (lab counts) — wrap and smaller */
  .stat-strip { flex-wrap: wrap; gap: 6px; }
  .stat-chip { min-width: calc(33% - 6px); padding: 8px 6px; }
  .stat-chip-value { font-size: 16px; }
  .stat-chip-label { font-size: 8px; letter-spacing: 0.5px; }

  /* Section headers */
  .section-header { padding: 24px 0 10px; gap: 8px; }
  .section-title { font-size: 10px; letter-spacing: 2px; }

  /* Price rows */
  .price-row { gap: 6px; }
  .price-name { font-size: 11px; min-width: 60px; }
  .price-val { font-size: 12px; }

  /* Move rows */
  .move-row { padding: 8px 0; }
  .move-who { font-size: 11px; }
  .move-desc { font-size: 10px; }

  /* R&D project cards */
  .rnd-project-header { flex-wrap: wrap; gap: 4px; }
  .rnd-project-title { font-size: 12px; }
  .rnd-project-desc { font-size: 10px; }
  .rnd-tag { font-size: 8px; }

  /* Skill cards */
  .skill-card { padding: 12px; }
  .skill-card-header { flex-wrap: wrap; gap: 4px; }
  .skill-card-title { font-size: 12px; }
  .skill-card-desc { font-size: 10px; }

  /* Force all bento children to single column — override inline span 12 */
  .bento > * { grid-column: 1 / -1 !important; grid-row: auto !important; }
  .section-header { grid-column: 1 / -1 !important; }

  /* Footer */
  .shell > div:last-child { font-size: 8px !important; letter-spacing: 1px !important; }
}

/* ═══════════════════════════════════════════════════════════════
   GLASS CARD — base component
   ═══════════════════════════════════════════════════════════════ */
.card {
  background: var(--bg-card);
  border: none;
  border-radius: var(--radius);
  padding: 28px 30px;
  position: relative;
  overflow: hidden;
  transition: background 0.2s;
  container-type: inline-size;
}
.card:hover { background: var(--bg-elevated); }
.card .spotlight { display: none; }
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.card-label {
  font-size: 10px;
  font-family: var(--font-mono);
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
}
.card-badge {
  font-size: 10px;
  font-family: var(--font-mono);
  padding: 3px 8px;
  border-radius: 4px;
  letter-spacing: 1px;
  font-weight: 600;
}
.badge-red { background: #FCE8EA; color: #B3202C; border: none; }
.badge-teal { background: #DDF0EE; color: var(--teal-soft); border: none; }
.badge-yellow { background: #FBF0D9; color: #8A5600; border: none; }
.badge-green { background: #DEF2E9; color: #0B7350; border: none; }

/* Glow/3D card variants — flattened for the light theme.
   Classes remain in markup; no visual effect. */
.card-glow::before, .card-glow::after { display: none; }
.card-3d { transform: none !important; }
@keyframes spin-border { to { --angle: 360deg; } }

/* ═══════════════════════════════════════════════════════════════
   STAT NUMBERS — big metric display
   ═══════════════════════════════════════════════════════════════ */
.stat-big {
  font-size: var(--text-hero);
  font-family: var(--font-display);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0;
  margin: 6px 0;
  font-variant-numeric: tabular-nums;
}
.stat-big.red { color: var(--red); }
.stat-big.teal { color: var(--teal); }
.stat-big.white { color: var(--text-primary); }

.stat-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.stat-unit {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-secondary);
}
.stat-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  font-family: var(--font-mono);
}
.stat-delta {
  font-size: 11px;
  font-family: var(--font-mono);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}
.delta-up { background: rgba(52,211,153,0.12); color: #0E9F6E; }
.delta-down { background: rgba(230,57,70,0.12); color: var(--red-soft); }

/* ═══════════════════════════════════════════════════════════════
   METRIC GRID — small stat cards inside hero
   ═══════════════════════════════════════════════════════════════ */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 12px;
}
.metric-cell {
  background: rgba(17,17,17,0.03);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 16px 18px;
  text-align: center;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  box-shadow: inset 0 1px 0 rgba(17,17,17,0.03);
}
.metric-cell:hover {
  background: rgba(17,17,17,0.06);
  border-color: rgba(46,196,182,0.2);
  box-shadow: inset 0 1px 0 rgba(17,17,17,0.05), 0 0 16px rgba(46,196,182,0.06);
  transform: translateY(-1px);
}
.metric-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--white);
  font-variant-numeric: tabular-nums;
}
.metric-label {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-top: 4px;
}

@media (max-width: 640px) {
  .metric-grid { grid-template-columns: repeat(2, 1fr); }
}

/* ═══════════════════════════════════════════════════════════════
   COUNCIL VOTE PANEL
   ═══════════════════════════════════════════════════════════════ */
.council-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.council-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-xs);
  background: rgba(17,17,17,0.02);
  border: 1px solid var(--border-subtle);
  transition: all 0.2s;
}
.council-row:hover { background: rgba(17,17,17,0.04); }
.council-vote {
  width: 28px; height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  flex-shrink: 0;
}
.vote-yes { background: rgba(52,211,153,0.15); color: #0E9F6E; border: 1px solid rgba(52,211,153,0.25); }
.vote-no { background: rgba(230,57,70,0.12); color: var(--red-soft); border: 1px solid rgba(230,57,70,0.2); }
.council-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 100px;
}
.council-cond {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  flex: 1;
}

/* ═══════════════════════════════════════════════════════════════
   COMPETITOR TABLE
   ═══════════════════════════════════════════════════════════════ */
.intel-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 4px;
}
.intel-table th {
  font-size: 9px;
  font-family: var(--font-mono);
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-muted);
  text-align: left;
  padding: 6px 12px;
  font-weight: 600;
}
.intel-table td {
  padding: 10px 12px;
  font-size: 12px;
  background: rgba(17,17,17,0.02);
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}
.intel-table td:first-child { border-left: 1px solid var(--border-subtle); border-radius: 8px 0 0 8px; }
.intel-table td:last-child { border-right: 1px solid var(--border-subtle); border-radius: 0 8px 8px 0; }
.intel-table tr:hover td { background: rgba(17,17,17,0.04); }

.threat-bar {
  height: 4px;
  border-radius: 2px;
  background: rgba(17,17,17,0.06);
  min-width: 60px;
}
.threat-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--teal), var(--red));
}

/* ═══════════════════════════════════════════════════════════════
   PRICE SERVICE BARS
   ═══════════════════════════════════════════════════════════════ */
.price-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.price-row:last-child { border-bottom: none; }
.price-name {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 120px;
  font-weight: 500;
}
.price-bar-wrap {
  flex: 1;
  height: 6px;
  background: rgba(17,17,17,0.04);
  border-radius: 3px;
  overflow: hidden;
}
.price-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1);
}
.price-val {
  font-size: 13px;
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--white);
  min-width: 40px;
  text-align: right;
}

/* ═══════════════════════════════════════════════════════════════
   R&D PIPELINE PILLS
   ═══════════════════════════════════════════════════════════════ */
.pipeline-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-xs);
  background: rgba(17,17,17,0.02);
  border: 1px solid var(--border-subtle);
  margin-bottom: 6px;
  transition: all 0.2s;
}
.pipeline-row:hover { background: rgba(17,17,17,0.04); }
.pipeline-id {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  min-width: 24px;
}
.pipeline-title {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
}
.pipeline-lab {
  font-size: 9px;
  font-family: var(--font-mono);
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(17,17,17,0.05);
  color: var(--text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}
.pipeline-status {
  font-size: 9px;
  font-family: var(--font-mono);
  padding: 2px 8px;
  border-radius: 3px;
  letter-spacing: 1px;
  text-transform: uppercase;
  font-weight: 600;
}

/* ═══════════════════════════════════════════════════════════════
   ALERT FEED
   ═══════════════════════════════════════════════════════════════ */
.alert-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.alert-row:last-child { border-bottom: none; }
.alert-icon {
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-top: 4px;
  flex-shrink: 0;
}
.alert-title { font-size: 12px; font-weight: 500; color: var(--text-primary); }
.alert-detail { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* ═══════════════════════════════════════════════════════════════
   MOVE FEED — competitive moves
   ═══════════════════════════════════════════════════════════════ */
.move-row {
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.move-row:last-child { border-bottom: none; }
.move-who {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}
.move-type {
  font-size: 9px;
  font-family: var(--font-mono);
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(46,196,182,0.1);
  color: var(--teal-soft);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-left: 6px;
}
.move-desc {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 3px;
  line-height: 1.4;
}

/* ═══════════════════════════════════════════════════════════════
   AGENT STATUS GRID
   ═══════════════════════════════════════════════════════════════ */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}
.agent-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--radius-xs);
  background: rgba(17,17,17,0.02);
  border: 1px solid var(--border-subtle);
  font-size: 11px;
  transition: all 0.2s;
}
.agent-cell:hover { background: rgba(17,17,17,0.04); }
.agent-name {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-secondary);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.agent-status {
  font-size: 9px;
  font-family: var(--font-mono);
  padding: 1px 5px;
  border-radius: 3px;
  letter-spacing: 0.5px;
  font-weight: 600;
}

/* ═══════════════════════════════════════════════════════════════
   SECTION DIVIDERS
   ═══════════════════════════════════════════════════════════════ */
.section-label {
  font-size: 10px;
  font-family: var(--font-mono);
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 28px 0 12px;
  grid-column: span 12;
}

/* ═══════════════════════════════════════════════════════════════
   OS FEATURES LIST
   ═══════════════════════════════════════════════════════════════ */
.os-feat {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 12px;
  color: var(--text-secondary);
}
.os-feat .check {
  width: 16px; height: 16px;
  border-radius: 4px;
  background: rgba(46,196,182,0.12);
  border: 1px solid rgba(46,196,182,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--teal);
  font-size: 10px;
  flex-shrink: 0;
}

/* ═══════════════════════════════════════════════════════════════
   SCROLLBAR
   ═══════════════════════════════════════════════════════════════ */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(17,17,17,0.08); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(17,17,17,0.14); }

/* ═══════════════════════════════════════════════════════════════
   EMPTY STATES
   ═══════════════════════════════════════════════════════════════ */
.empty {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--font-mono);
}

/* ═══════════════════════════════════════════════════════════════
   R&D LAB TABS + CARDS
   ═══════════════════════════════════════════════════════════════ */
.lab-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.lab-tab {
  font-size: 10px;
  font-family: var(--font-mono);
  padding: 5px 12px;
  border-radius: 6px;
  background: rgba(17,17,17,0.03);
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  cursor: pointer;
  letter-spacing: 1px;
  text-transform: uppercase;
  font-weight: 600;
  transition: all 0.2s;
}
.lab-tab:hover, .lab-tab.active {
  background: rgba(46,196,182,0.1);
  border-color: rgba(46,196,182,0.25);
  color: var(--teal-soft);
}
.lab-tab[data-lab="service"] { --lab-color: var(--teal); }
.lab-tab[data-lab="os"] { --lab-color: #7C3AED; }
.lab-tab[data-lab="market"] { --lab-color: #B45309; }
.lab-tab[data-lab="business"] { --lab-color: var(--red-soft); }
.lab-tab[data-lab="product"] { --lab-color: #0E9F6E; }
.lab-tab.active[data-lab="service"] { background: rgba(46,196,182,0.12); border-color: rgba(46,196,182,0.3); color: var(--teal-soft); }
.lab-tab.active[data-lab="os"] { background: rgba(167,139,250,0.12); border-color: rgba(167,139,250,0.3); color: #7C3AED; }
.lab-tab.active[data-lab="market"] { background: rgba(251,191,36,0.12); border-color: rgba(251,191,36,0.3); color: #B45309; }
.lab-tab.active[data-lab="business"] { background: rgba(255,107,107,0.12); border-color: rgba(255,107,107,0.3); color: var(--red-soft); }
.lab-tab.active[data-lab="product"] { background: rgba(52,211,153,0.12); border-color: rgba(52,211,153,0.3); color: #0E9F6E; }

.rnd-project {
  padding: 14px 16px;
  border-radius: var(--radius-xs);
  background: rgba(17,17,17,0.02);
  border: 1px solid var(--border-subtle);
  margin-bottom: 8px;
  transition: all 0.2s;
}
.rnd-project:hover {
  background: rgba(17,17,17,0.04);
  border-color: rgba(17,17,17,0.1);
}
.rnd-project-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.rnd-project-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}
.rnd-project-desc {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 8px;
}
.rnd-project-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.rnd-tag {
  font-size: 9px;
  font-family: var(--font-mono);
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  font-weight: 600;
}
.rnd-revenue {
  font-size: 10px;
  font-family: var(--font-mono);
  color: #0E9F6E;
  margin-left: auto;
}

/* ═══════════════════════════════════════════════════════════════
   SKILLS DEPARTMENT CARDS
   ═══════════════════════════════════════════════════════════════ */
.skill-card {
  padding: 14px 16px;
  border-radius: var(--radius-xs);
  background: rgba(17,17,17,0.02);
  border: 1px solid var(--border-subtle);
  margin-bottom: 8px;
  transition: all 0.2s;
}
.skill-card:hover {
  background: rgba(17,17,17,0.04);
  border-color: rgba(17,17,17,0.1);
}
.skill-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.skill-card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}
.skill-card-desc {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 8px;
}
.skill-card-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.skill-tag {
  font-size: 9px;
  font-family: var(--font-mono);
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  font-weight: 600;
}
.skill-version {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  margin-left: auto;
}
.skill-metrics {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}
.skill-metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.skill-metric-value {
  font-size: 14px;
  font-family: var(--font-mono);
  font-weight: 700;
}
.skill-metric-label {
  font-size: 8px;
  font-family: var(--font-mono);
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-muted);
}
.skill-phase-bar {
  display: flex;
  gap: 2px;
  margin-top: 6px;
}
.skill-phase-pip {
  width: 18px;
  height: 4px;
  border-radius: 2px;
  background: rgba(17,17,17,0.06);
}
.skill-phase-pip.filled {
  background: var(--teal);
  opacity: 0.8;
}
.skill-links {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 6px;
  font-family: var(--font-mono);
}

/* ═══════════════════════════════════════════════════════════════
   SECTION HEADERS — functional grouping
   ═══════════════════════════════════════════════════════════════ */
/* Nike signature: huge condensed all-caps display headline as divider */
.section-header {
  grid-column: span 12;
  padding: 28px 0 8px;
  display: flex;
  align-items: baseline;
  gap: 16px;
  flex-wrap: wrap;
}
.section-num {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 2px;
}
.section-title {
  font-family: var(--font-display);
  font-size: clamp(2.75rem, 6.5vw, 5.5rem);
  font-weight: 400;
  letter-spacing: 0;
  text-transform: uppercase;
  color: var(--text-primary);
  line-height: 0.95;
  flex-basis: 100%;
}
.section-line { display: none; }

/* ═══════════════════════════════════════════════════════════════
   SUMMARY STAT ROW — compact horizontal stats
   ═══════════════════════════════════════════════════════════════ */
.stat-strip {
  display: flex;
  gap: 4px;
}
.stat-chip {
  flex: 1;
  padding: 10px 12px;
  background: rgba(17,17,17,0.02);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xs);
  text-align: center;
}
.stat-chip-value {
  font-size: var(--text-lg);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.stat-chip-label {
  font-size: 9px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-top: 2px;
}

/* ═══════════════════════════════════════════════════════════════
   NIKE-STYLE FOOTER
   ═══════════════════════════════════════════════════════════════ */
.site-footer {
  margin-top: 72px;
  border-top: 1px solid rgba(17,17,17,0.1);
  padding: 48px 0 24px;
}
.footer-cols {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 32px;
}
.footer-col { display: flex; flex-direction: column; gap: 10px; align-items: flex-start; }
.footer-head {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.foot-link {
  background: none;
  border: none;
  padding: 0;
  font-family: inherit;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.15s;
  text-align: left;
}
.foot-link:hover { color: var(--text-primary); }
.foot-item { font-size: 12px; color: var(--text-muted); }
.footer-base {
  margin-top: 48px;
  padding-top: 20px;
  border-top: 1px solid rgba(17,17,17,0.06);
  font-size: 11px;
  color: var(--text-muted);
}
@media (max-width: 768px) {
  .footer-cols { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>
<body>

<!-- ═══ NIKE-STYLE HEADER — utility strip + sticky white nav ═══ -->
<div class="utility-strip">
  <span>Charlotte, NC</span>
  <span class="sep">|</span>
  <span>{{ data.shop.neighborhood }}</span>
  <span class="sep">|</span>
  <span>Powered by the Doctrine</span>
</div>
<header class="site-header">
  <div class="topbar">
    <div class="topbar-brand">
      <div class="topbar-logo">HQ</div>
      <div>
        <div class="topbar-title">Corporate HQ</div>
        <div class="topbar-subtitle">Business Intelligence</div>
      </div>
    </div>
    <nav class="topbar-nav" id="topbarNav">
      <button class="nav-tab active" data-tab="overview">Overview</button>
      <button class="nav-tab" data-tab="competitors">Competitors</button>
      <button class="nav-tab" data-tab="operations">Operations</button>
      <button class="nav-tab" data-tab="projects">Projects</button>
      <button class="nav-tab" data-tab="skills">Skills</button>
    </nav>
    <button class="topbar-assistant" id="topbarAssistant" title="Open the HQ Assistant chat">&#9993; HQ Assistant</button>
  </div>
</header>

<!-- DASHBOARD SHELL -->
<div class="shell">

  <!-- Booksy migration banner removed — shelved feature, not a tracked initiative.
       The planned booking platform is documented in the "Our Booking System" card
       (Tech Stack tab), which is the roadmap home for Emporium OS. -->

  <!-- ═══ TAB: OVERVIEW ═══ -->
  <div class="tab-panel active" id="tab-overview">
  <div class="bento">

    <!-- ════════════════════════════════════════════════════════
         SECTION 01: COMMAND CENTER
         ════════════════════════════════════════════════════════ -->

    <!-- STATUS STRIP (moved from topbar) -->
    <div class="topbar-status" style="grid-column: span 12; flex-wrap: wrap;">
      <!-- "Booking System: Planned" status dot removed — static placeholder with no
           data binding. The planned platform lives in the Tech Stack roadmap card. -->
      <div class="status-dot">
        <span class="dot {% if data.shop.migrating_from %}dot-yellow{% else %}dot-green{% endif %}"></span>
        {% if data.shop.migrating_from %}Moving Clients from Booksy{% else %}BOOKSY CLEAR{% endif %}
      </div>
      <div class="status-dot">
        <span class="dot dot-teal"></span>
        {{ data.competitor_count }} Competitors Tracked
      </div>
      <div class="status-dot">
        <span class="dot {% if data.council.strategist.ready %}dot-green{% else %}dot-red{% endif %}"></span>
        {{ [data.council.strategist.ready, data.council.comptroller.ready, data.council.intel.ready, data.council.operator.ready, data.council.brand.ready]|select|list|length }} of 5 Goals Met
      </div>
    </div>

    <!-- HERO CARD — Revenue Command -->
    <div class="card card-glow card-3d b-hero">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Revenue Overview</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5;">
        Current monthly income (manually entered). Target is $4,500/month.
      </div>
      <div class="stat-row">
        <div class="stat-big white">${{ "{:,.0f}".format(data.shop.monthly_gross) }}</div>
        <div class="stat-unit">/month</div>
        {% if data.shop.monthly_gross < 4500 %}
        <span class="stat-delta delta-down">TARGET $4,500</span>
        {% else %}
        <span class="stat-delta delta-up">ON TARGET</span>
        {% endif %}
      </div>
      <div class="stat-sub">${{ "{:,}".format(data.shop.annual_gross) }}/yr gross &middot; {{ data.shop.setup }} &middot; {{ data.shop.neighborhood }} &middot; {{ data.shop.years_experience }}yr experience</div>

      <div class="metric-grid">
        <div class="metric-cell" title="Barbershops in your market being tracked by the intelligence agents">
          <div class="metric-value" style="color: var(--teal);">{{ data.competitor_count }}</div>
          <div class="metric-label">Competing Shops</div>
          <div style="font-size: 9px; color: var(--text-muted); margin-top: 2px;">Tracked by intel agents</div>
        </div>
        <div class="metric-cell" title="Franchise chains with multiple locations (e.g. No Grease)">
          <div class="metric-value" style="color: var(--red);">{{ data.franchise_count }}</div>
          <div class="metric-label">Franchise Locations</div>
          <div style="font-size: 9px; color: var(--text-muted); margin-top: 2px;">Chains like No Grease</div>
        </div>
        <div class="metric-cell" title="Solo barbers operating without a chain affiliation">
          <div class="metric-value">{{ data.independent_count }}</div>
          <div class="metric-label">Independent Barbers</div>
          <div style="font-size: 9px; color: var(--text-muted); margin-top: 2px;">Solo, no chain</div>
        </div>
        <div class="metric-cell" title="R&D experiments currently running in your labs">
          <div class="metric-value">{{ data.rnd_projects|length }}</div>
          <div class="metric-label">Active Projects</div>
          <div style="font-size: 9px; color: var(--text-muted); margin-top: 2px;">Running in your labs</div>
        </div>
      </div>
    </div>

    <!-- COUNCIL CARD -->
    <div class="card card-glow card-3d b-side">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Business Goals</span>
        {% set yes_votes = data.council.values()|selectattr('ready')|list|length %}
        <span class="card-badge {% if yes_votes >= 3 %}badge-green{% elif yes_votes >= 1 %}badge-yellow{% else %}badge-red{% endif %}">{{ yes_votes }} of 5 Goals Reached</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5;">
        These are the 5 milestones your advisory board requires before voting to expand from a suite to a full shop. Green = complete, Red = not yet met.
      </div>
      <div class="council-grid">
        {% for name, info in data.council.items() %}
        <div class="council-row">
          <div class="council-vote {% if info.ready %}vote-yes{% else %}vote-no{% endif %}">
            {% if info.ready %}Y{% else %}N{% endif %}
          </div>
          <div class="council-name">{{ name|title }}</div>
          <div class="council-cond">{{ info.condition }}</div>
        </div>
        {% endfor %}
      </div>
    </div>

  </div><!-- /bento -->
  </div><!-- /tab-overview -->

  <!-- ═══ TAB: COMPETITORS ═══ -->
  <div class="tab-panel" id="tab-competitors">
  <div class="bento">

    <!-- ════════════════════════════════════════════════════════
         SECTION 02: INTELLIGENCE
         ════════════════════════════════════════════════════════ -->
    <div class="section-header">
      <span class="section-num">02</span>
      <span class="section-title">Competitor Research</span>
      <span class="section-line"></span>
    </div>
    <div style="grid-column: span 12; font-size: 11px; color: var(--text-muted); line-height: 1.5; margin-top: -8px; margin-bottom: 4px;">
      Data collected automatically by your intelligence agents from Booksy, Google, and social media.
    </div>

    <!-- PRICING CARD -->
    <div class="card card-glow card-3d b-wide">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Your Prices vs. The Market</span>
        <span class="card-badge badge-teal">{{ data.prices|length }} SERVICES</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5;">
        Your menu prices compared to the Charlotte market. Prices collected from {{ data.competitor_count }} competing shops by your PricingScout agent.
      </div>
      {% set max_price = data.prices.values()|max if data.prices else 80 %}
      {% for name, price in data.prices.items() %}
      <div class="price-row">
        <div class="price-name">{{ name }}</div>
        <div class="price-bar-wrap">
          <div class="price-bar-fill" style="width: {{ (price / (max_price * 1.2) * 100)|int }}%; background: linear-gradient(90deg, var(--teal), {% if price >= 55 %}var(--red){% elif price >= 35 %}var(--teal-soft){% else %}var(--teal){% endif %});"></div>
        </div>
        <div class="price-val">${{ price }}</div>
      </div>
      {% endfor %}
      {% if data.avg_fade > 0 %}
      <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle); display: flex; gap: 16px; flex-wrap: wrap;">
        <div style="font-size: 11px; font-family: var(--font-mono);">
          <span style="color: var(--text-muted);">Market Average Fade Price</span>
          <span style="color: var(--white); font-weight: 600; margin-left: 4px;">${{ "%.0f"|format(data.avg_fade) }}</span>
        </div>
        <div style="font-size: 11px; font-family: var(--font-mono);">
          <span style="color: var(--text-muted);">Market Highest Price</span>
          <span style="color: var(--red-soft); font-weight: 600; margin-left: 4px;">${{ "%.0f"|format(data.max_fade) }}</span>
        </div>
        <div style="font-size: 11px; font-family: var(--font-mono);">
          <span style="color: var(--text-muted);">Your Fade Price</span>
          <span style="color: var(--teal-soft); font-weight: 600; margin-left: 4px;">${{ data.prices.get('Fade', 0) }}</span>
        </div>
      </div>
      {% endif %}
    </div>

    <!-- TERRITORY + COMPETITIVE MOVES -->
    <div class="card card-glow card-3d b-wide">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Neighborhood Breakdown</span>
        <span class="card-badge badge-teal">{{ data.neighborhood_zones_total }} ZONES</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5;">
        Every Charlotte neighborhood where your agents found competing barbershops, ranked by shop count. Your neighborhood ({{ data.shop.neighborhood }}) is highlighted.
      </div>
      <table class="intel-table">
        <thead>
          <tr>
            <th>Neighborhood</th>
            <th>Shops</th>
            <th>Avg Fade</th>
            <th>Density</th>
            <th>vs. Your Price</th>
          </tr>
        </thead>
        <tbody>
          {% for n in data.neighborhoods %}
          <tr{% if n.is_yours %} style="background: rgba(0,121,107,0.06);"{% endif %}>
            <td style="font-weight: 500;">
              {{ n.neighborhood or 'Unknown' }}{% if n.is_yours %} <span style="font-size: 9px; color: var(--teal); font-weight: 700;">YOU</span>{% endif %}
            </td>
            <td>
              <span style="font-family: var(--font-mono); font-weight: 600; {% if n.shops <= 1 %}color: var(--teal);{% elif n.shops >= 5 %}color: var(--red);{% else %}color: var(--text-primary);{% endif %}">
                {{ n.shops }}
              </span>
            </td>
            <td>
              {% if n.avg_fade %}
              <span style="font-family: var(--font-mono);">${{ "%.0f"|format(n.avg_fade) }}</span>
              {% else %}
              <span style="color: var(--text-muted);">No data</span>
              {% endif %}
            </td>
            <td>
              <span class="{% if n.density == 'Packed' %}badge-red{% elif n.density == 'Busy' or n.density == 'Verifying' %}badge-yellow{% elif n.density == 'Low' or n.density == 'Empty' %}badge-green{% else %}badge-teal{% endif %}" style="font-size: 10px; padding: 2px 8px; border-radius: 4px; font-weight: 500;">
                {{ n.density }}
              </span>
            </td>
            <td style="font-size: 11px; font-family: var(--font-mono); color: var(--text-secondary);">
              {{ n.price_note or '' }}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <!-- THREAT BOARD -->
    <div class="card card-glow card-3d b-wide">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Shops to Watch</span>
        <span class="card-badge badge-red">{% if data.top_threats|length %}{{ data.top_threats|length }} Tracked{% else %}0 Tracked{% endif %}</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5;">
        Your biggest competitors ranked by threat score. Higher score = more direct competition to your shop. Scores calculated from ratings, growth, pricing, and proximity.
      </div>
      {% if data.top_threats %}
      <table class="intel-table">
        <thead>
          <tr>
            <th>Competitor</th>
            <th>Location</th>
            <th>Score</th>
            <th>Why They're a Threat</th>
          </tr>
        </thead>
        <tbody>
          {% for t in data.top_threats %}
          <tr>
            <td style="font-weight: 500;">{{ t.company_name }}</td>
            <td style="font-size: 11px; color: var(--text-secondary);">{{ t.neighborhood or t.zip_code or 'Charlotte' }}</td>
            <td>
              <span style="font-family: var(--font-mono); font-weight: 600; {% if (t.threat_score or 0) >= 7 %}color: var(--red);{% elif (t.threat_score or 0) >= 4 %}color: #B45309;{% else %}color: var(--teal);{% endif %}">{{ "%.1f"|format(t.threat_score or 0) }}/10</span>
            </td>
            <td style="font-size: 11px; line-height: 1.4;">
              {{ t.reason }}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
        <div class="empty">No threat scores yet. Run the Scorecard agent to calculate.</div>
      {% endif %}
    </div>

    <!-- COMPETITIVE MOVES + SOCIAL -->
    <div class="card card-glow card-3d b-wide">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Recent Competitor Activity</span>
        <span class="card-badge badge-red">Live Updates</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5;">
        Changes detected by your agents — price moves, rating shifts, review spikes, new openings, expansions, and more.
      </div>
      {% if data.recent_moves %}
        {% for move in data.recent_moves %}
        <div class="move-row">
          <div>
            <span class="move-who">{{ move.company_name }}</span>
            <span class="move-type">{{ move.move_type }}</span>
            {% if move.move_date %}
            <span style="font-size: 10px; color: var(--text-muted); margin-left: 6px;">{{ move.move_date }}</span>
            {% endif %}
          </div>
          <div class="move-desc">{{ move.description|e }}</div>
        </div>
        {% endfor %}
      {% else %}
        <div class="empty">No moves logged. Deploy agents to start tracking.</div>
      {% endif %}
    </div>

    <!-- SOCIAL LEADERS -->
    <div class="card card-glow card-3d b-wide">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Social Landscape</span>
        <span class="card-badge badge-red">TOP 5</span>
      </div>
      {% if data.social_leaders %}
      <table class="intel-table">
        <thead>
          <tr>
            <th>Shop</th>
            <th>Platform</th>
            <th>Followers</th>
            <th>Engagement</th>
          </tr>
        </thead>
        <tbody>
          {% for s in data.social_leaders %}
          <tr>
            <td style="font-weight: 500;">{{ s.company_name }}</td>
            <td><span style="font-family: var(--font-mono); font-size: 10px; color: var(--text-muted);">{{ s.platform or 'N/A' }}</span></td>
            <td style="font-family: var(--font-mono);">{{ "{:,}".format(s.followers) }}</td>
            <td style="font-family: var(--font-mono);">{% if s.engagement_rate %}{{ "%.1f"|format(s.engagement_rate) }}%{% else %}--{% endif %}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
        <div class="empty">No social data. Deploy SocialListener agent.</div>
      {% endif %}
    </div>

  </div><!-- /bento -->
  </div><!-- /tab-competitors -->

  <!-- ═══ TAB: OPERATIONS ═══ -->
  <div class="tab-panel" id="tab-operations">
  <div class="bento">

    <!-- ════════════════════════════════════════════════════════
         SECTION 03: OPERATIONS & SYSTEMS
         ════════════════════════════════════════════════════════ -->
    <div class="section-header">
      <span class="section-num">03</span>
      <span class="section-title">Operations &amp; Tools</span>
      <span class="section-line"></span>
    </div>
    <div style="grid-column: span 12; font-size: 11px; color: var(--text-muted); line-height: 1.5; margin-top: -8px; margin-bottom: 4px;">
      Your tech stack: the intelligence warehouse and agents are live; the proprietary booking platform is planned.
    </div>

    <!-- OS STATUS -->
    <div class="card card-glow card-3d b-third">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Our Booking System</span>
        <span class="card-badge badge-yellow">PLANNED</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.4;">
        Your custom booking and operations platform &mdash; not yet built. The intelligence warehouse behind it is live; the booking features below are planned.
      </div>
      {% for feat in data.shop.os_features_live %}
      <div class="os-feat">
        <div class="check">&#10003;</div>
        <span>{{ feat }}</span>
      </div>
      {% endfor %}
      {% for feat in data.shop.os_features_planned %}
      <div class="os-feat" style="opacity: 0.55;">
        <div class="check" style="background: rgba(251,191,36,0.12); color: #B45309;">&#9675;</div>
        <span>{{ feat }} <span style="font-family: var(--font-mono); font-size: 9px; color: #B45309; letter-spacing: 1px;">PLANNED</span></span>
      </div>
      {% endfor %}
      {% if data.shop.migrating_from %}
      <div style="margin-top: 10px; padding: 8px 10px; border-radius: 6px; background: rgba(230,57,70,0.08); border: 1px solid rgba(230,57,70,0.15);">
        <div style="font-size: 10px; font-family: var(--font-mono); color: var(--red-soft); letter-spacing: 1px;">MIGRATING FROM {{ data.shop.migrating_from|upper }}</div>
      </div>
      {% endif %}
    </div>

    <!-- AGENT FLEET -->
    <div class="card card-glow card-3d b-third">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Automated Agents</span>
        <span class="card-badge badge-teal">{{ data.agents_executed }} of {{ data.agent_fleet|length }} Have Run</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.4;">
        {{ data.agent_fleet|length }} agents registered. Each row below shows that agent's real last run, read from the agent log &mdash; &ldquo;NO RUNS YET&rdquo; until it has actually executed.
        {% if data.last_agent_cycle %}Last cycle: {{ data.last_agent_cycle.strftime('%b %d, %I:%M %p') if data.last_agent_cycle.strftime else data.last_agent_cycle }}.{% endif %}
      </div>
      <div class="agent-grid">
        {% for agent in data.agent_fleet %}
        <div class="agent-cell">
          <span class="dot {% if agent.run_count %}dot-green{% else %}dot-yellow{% endif %}" style="width:6px;height:6px;border-radius:50%;flex-shrink:0;"></span>
          <span class="agent-name">{{ agent.display }}</span>
          <span class="agent-status" style="{% if agent.run_count %}color: #0E9F6E; background: rgba(52,211,153,0.1);{% else %}color: var(--text-muted); background: rgba(17,17,17,0.04);{% endif %}">
            {% if agent.last_run %}RAN {{ agent.last_run.strftime('%b %d') if agent.last_run.strftime else agent.last_run }}{% else %}NO RUNS YET{% endif %}
          </span>
        </div>
        {% endfor %}
      </div>
    </div>

    <!-- ALERTS -->
    <div class="card card-glow card-3d b-third">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Alerts</span>
        <span class="card-badge badge-yellow">{% if data.alerts|length %}{{ data.alerts|length }} Alerts{% else %}No Alerts{% endif %}</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.4;">
        Notifications written to the alert log by your agents when something changes in your market.
      </div>
      {% if data.alerts %}
        {% for alert in data.alerts %}
        <div class="alert-row">
          <div class="alert-icon" style="background: {% if alert.severity == 'critical' %}var(--red){% elif alert.severity == 'warning' %}#B45309{% else %}var(--teal){% endif %};
               box-shadow: 0 0 6px {% if alert.severity == 'critical' %}rgba(230,57,70,0.4){% elif alert.severity == 'warning' %}rgba(251,191,36,0.4){% else %}rgba(46,196,182,0.4){% endif %};"></div>
          <div>
            <div class="alert-title">{{ alert.title }}</div>
            <div style="font-size: 9px; font-family: var(--font-mono); color: var(--text-muted); letter-spacing: 0.5px;">
              {{ alert.alert_type }}{% if alert.company_name %} &middot; {{ alert.company_name }}{% endif %}{% if alert.created_at %} &middot; {{ alert.created_at.strftime('%b %d, %I:%M %p') if alert.created_at.strftime else alert.created_at }}{% endif %}
            </div>
            {% if alert.detail %}
            <div class="alert-detail">{{ alert.detail[:80] }}</div>
            {% endif %}
          </div>
        </div>
        {% endfor %}
      {% else %}
        <div class="empty">Alert log is empty &mdash; no alerts have been generated yet.</div>
      {% endif %}
    </div>

  </div><!-- /bento -->
  </div><!-- /tab-operations -->

  <!-- ═══ TAB: PROJECTS ═══ -->
  <div class="tab-panel" id="tab-projects">
  <div class="bento">

    <!-- ════════════════════════════════════════════════════════
         SECTION 04: R&D LABS
         ════════════════════════════════════════════════════════ -->
    <div class="section-header">
      <span class="section-num">04</span>
      <span class="section-title">Projects &amp; Experiments</span>
      <span class="section-line"></span>
    </div>
    <div style="grid-column: span 12; font-size: 11px; color: var(--text-muted); line-height: 1.5; margin-top: -8px; margin-bottom: 4px;">
      Active R&amp;D initiatives organized into 5 labs. Each lab focuses on a different area of the business.
    </div>

    <!-- R&D OVERVIEW STRIP -->
    <div class="card card-glow card-3d" style="grid-column: span 12; grid-row: span 2;">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Project Pipeline Overview</span>
        <span class="card-badge badge-teal">{{ data.rnd_projects|length }} PROJECTS &middot; 5 LABS</span>
      </div>
      <div class="stat-strip">
        {% set lab_names = {'service': 'New Services Lab', 'os': 'Booking System Lab', 'market': 'Market Research Lab', 'business': 'Business Strategy Lab', 'product': 'Product Development Lab'} %}
        {% set lab_colors = {'service': 'var(--teal)', 'os': '#7C3AED', 'market': '#B45309', 'business': 'var(--red-soft)', 'product': '#0E9F6E'} %}
        {% for lab_key, lab_label in lab_names.items() %}
        <div class="stat-chip">
          <div class="stat-chip-value" style="color: {{ lab_colors.get(lab_key, 'var(--white)') }};">{{ data.rnd_labs.get(lab_key, {}).get('count', 0) }}</div>
          <div class="stat-chip-label">{{ lab_label }}</div>
        </div>
        {% endfor %}
      </div>
    </div>

    <!-- R&D PROJECT CARDS BY LAB -->
    {% set lab_configs = [
      ('service', 'New Services Lab', 'Testing new service offerings, pricing models, and service bundles.', 'var(--teal)', 'rgba(46,196,182,0.08)'),
      ('os', 'Booking System Lab', 'Building new features into your proprietary booking and ops platform.', '#7C3AED', 'rgba(167,139,250,0.08)'),
      ('market', 'Market Research Lab', 'Studying market trends, competitor strategies, and customer behavior.', '#B45309', 'rgba(251,191,36,0.08)'),
      ('business', 'Business Strategy Lab', 'Exploring expansion models, partnerships, and revenue strategies.', 'var(--red-soft)', 'rgba(255,107,107,0.08)'),
      ('product', 'Product Development Lab', 'Developing physical or digital products tied to the brand.', '#0E9F6E', 'rgba(52,211,153,0.08)')
    ] %}

    {% for lab_key, lab_label, lab_desc, lab_color, lab_bg in lab_configs %}
    {% set lab_projects = data.rnd_projects|selectattr('lab', 'equalto', lab_key)|list %}
    {% if lab_projects %}
    <div class="card card-glow card-3d b-wide" style="border-top: 2px solid {{ lab_color }}20;">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label" style="color: {{ lab_color }};">{{ lab_label }}</span>
        <span class="card-badge" style="background: {{ lab_bg }}; color: {{ lab_color }}; border: 1px solid {{ lab_color }}30;">{{ lab_projects|length }} PROJECTS</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.4;">{{ lab_desc }}</div>

      {% for p in lab_projects %}
      <div class="rnd-project">
        <div class="rnd-project-header">
          <span class="pipeline-id">#{{ p.project_id }}</span>
          <span class="rnd-project-title">{{ p.title }}</span>
          <span class="rnd-tag" style="
            {% if p.status == 'in_progress' %}background: rgba(46,196,182,0.12); color: var(--teal-soft);
            {% elif p.status == 'research' %}background: rgba(251,191,36,0.1); color: #B45309;
            {% elif p.status == 'complete' %}background: rgba(52,211,153,0.1); color: #0E9F6E;
            {% else %}background: rgba(17,17,17,0.04); color: var(--text-muted);
            {% endif %}
          ">{{ p.status|replace('_', ' ')|upper }}</span>
          <span class="rnd-tag" style="
            {% if p.priority == 'critical' %}background: rgba(230,57,70,0.12); color: var(--red-soft);
            {% elif p.priority == 'high' %}background: rgba(251,191,36,0.1); color: #B45309;
            {% else %}background: rgba(17,17,17,0.04); color: var(--text-muted);
            {% endif %}
          ">{{ p.priority|upper }}</span>
        </div>
        {% if p.description %}
        <div class="rnd-project-desc">{{ p.description|e }}</div>
        {% endif %}
        <div class="rnd-project-meta">
          {% if p.hypothesis %}
          <span style="font-size: 10px; color: var(--text-muted); font-style: italic;">"{{ p.hypothesis|e|truncate(100) }}"</span>
          {% endif %}
          {% if p.revenue_potential %}
          <span class="rnd-revenue">{{ p.revenue_potential }}</span>
          {% endif %}
        </div>
      </div>
      {% endfor %}
    </div>
    {% endif %}
    {% endfor %}

  </div><!-- /bento -->
  </div><!-- /tab-projects -->

  <!-- ═══ TAB: SKILLS ═══ -->
  <div class="tab-panel" id="tab-skills">
  <div class="bento">

    <!-- ════════════════════════════════════════════════════════
         SECTION 05: SKILLS DEPARTMENT
         ════════════════════════════════════════════════════════ -->
    <div class="section-header">
      <span class="section-num">05</span>
      <span class="section-title">Skills Department</span>
      <span class="section-line"></span>
    </div>

    <!-- SKILLS OVERVIEW STRIP -->
    <div class="card card-glow card-3d" style="grid-column: span 12; grid-row: span 2;">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Skills Pipeline Overview</span>
        <span class="card-badge badge-teal">{{ data.skills|length }} SKILLS &middot; 3 CATEGORIES</span>
      </div>
      <div class="stat-strip">
        {% set cat_configs = {'document': 'Reports', 'workflow': 'Automated', 'mcp': 'Smart Assistant'} %}
        {% set cat_colors = {'document': '#2563EB', 'workflow': '#DB2777', 'mcp': '#7C3AED'} %}
        {% for cat_key, cat_label in cat_configs.items() %}
        <div class="stat-chip">
          <div class="stat-chip-value" style="color: {{ cat_colors.get(cat_key, 'var(--white)') }};">{{ data.skills_by_cat.get(cat_key, {}).get('count', 0) }}</div>
          <div class="stat-chip-label">{{ cat_label }}</div>
        </div>
        {% endfor %}
        <div class="stat-chip">
          <div class="stat-chip-value" style="color: var(--teal);">{{ data.skills_executed }}</div>
          <div class="stat-chip-label">Have Run</div>
        </div>
        <div class="stat-chip">
          <div class="stat-chip-value" style="color: #B45309;">{{ (data.skills|selectattr('status', 'equalto', 'design')|list|length) + (data.skills|selectattr('status', 'equalto', 'testing')|list|length) }}</div>
          <div class="stat-chip-label">Planned / Testing</div>
        </div>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-top: 10px; line-height: 1.5;">
        These are the things HQ can do for you. <strong style="color: var(--text-secondary);">Reports</strong> generate written analysis.
        <strong style="color: var(--text-secondary);">Automated</strong> processes run multi-step tasks on their own.
        <strong style="color: var(--text-secondary);">Smart Assistant</strong> skills make the HQ chat smarter when you ask it questions.
      </div>
    </div>

    <!-- SKILLS BY CATEGORY -->
    {% set skill_cat_configs = [
      ('document', 'Reports & Analysis', 'Written reports that summarize your competitive data — pricing comparisons, competitor threat levels, and market trends.', '#2563EB', 'rgba(96,165,250,0.08)'),
      ('workflow', 'Automated Processes', 'Multi-step tasks that run on their own — onboarding new competitors, weekly market sweeps, and research project setup.', '#DB2777', 'rgba(244,114,182,0.08)'),
      ('mcp', 'Smart Assistant Skills', 'These make the HQ Assistant smarter when you ask it questions — better data lookups, coordinated agent runs, and expansion readiness checks.', '#7C3AED', 'rgba(167,139,250,0.08)')
    ] %}

    {% for cat_key, cat_label, cat_desc, cat_color, cat_bg in skill_cat_configs %}
    {% set cat_skills = data.skills|selectattr('category', 'equalto', cat_key)|list %}
    {% if cat_skills %}
    <div class="card card-glow card-3d b-wide" style="border-top: 2px solid {{ cat_color }}20;">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label" style="color: {{ cat_color }};">{{ cat_label }}</span>
        <span class="card-badge" style="background: {{ cat_bg }}; color: {{ cat_color }}; border: 1px solid {{ cat_color }}30;">{{ cat_skills|length }} SKILLS</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.4;">{{ cat_desc }}</div>

      {% for s in cat_skills %}
      <div class="skill-card">
        <div class="skill-card-header">
          <span class="pipeline-id">#{{ s.skill_id }}</span>
          <span class="skill-card-title">{{ s.display_name }}</span>
          {% if s.last_run %}
          <span class="skill-tag" style="background: rgba(46,196,182,0.12); color: var(--teal-soft);">WORKING</span>
          {% elif s.status == 'active' %}
          <span class="skill-tag" style="background: rgba(96,165,250,0.1); color: #2563EB;">READY</span>
          {% elif s.status == 'testing' %}
          <span class="skill-tag" style="background: rgba(251,191,36,0.1); color: #B45309;">TESTING</span>
          {% else %}
          <span class="skill-tag" style="background: rgba(17,17,17,0.06); color: var(--text-muted);">PLANNED</span>
          {% endif %}
        </div>
        {% if s.description %}
        <div class="skill-card-desc">{{ s.description|e }}</div>
        {% endif %}

        <!-- What you get -->
        {% set skill_outputs = {
          "competitive-brief": "A plain-English report showing who your biggest threats are, how your prices compare, and what changed this week.",
          "pricing-analysis": "A service-by-service breakdown showing where you're priced above or below the market average, and by how much.",
          "council-brief": "A progress report for your advisory board showing which expansion goals are met and which still need work.",
          "competitor-onboarding": "A fully set-up competitor profile with their prices, reviews, social accounts, and a threat score — done automatically.",
          "weekly-intel-cycle": "A full weekly update — fresh prices, new reviews, social changes, and any alerts — across your whole market.",
          "rnd-project-setup": "A structured project plan with a hypothesis, success metrics, and a concept paper ready before any work begins.",
          "warehouse-query-guide": "Faster, more accurate answers when you ask the HQ Assistant questions about your data.",
          "agent-orchestrator": "All your automated agents run in the right order without you having to manage anything.",
          "expansion-readiness-check": "A clear yes/no on each of the 5 expansion goals, showing exactly what's met and what's still needed.",
          "site-selection-analysis": "A comparison of potential new shop locations looking at local population, nearby competition, pricing, and demand."
        } %}
        {% if s.name in skill_outputs %}
        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 8px; line-height: 1.5;">
          <span style="color: var(--teal-soft); font-weight: 600;">What you get:</span> {{ skill_outputs[s.name] }}
        </div>
        {% endif %}

        <!-- Run status: Last run, Output, Fed by — from the skills table -->
        <div style="margin-top: 10px; font-size: 11px; line-height: 1.8;">
          <div>
            <span style="color: var(--text-muted);">Last run:</span>
            {% if s.last_run %}
            <span style="color: var(--white);">{{ s.last_run.strftime('%b %d, %I:%M %p') if s.last_run.strftime else s.last_run }}</span>
            {% else %}
            <span style="color: var(--text-muted);">never run</span>
            {% endif %}
          </div>
          <div>
            <span style="color: var(--text-muted);">Latest findings:</span>
            {% if s.last_output %}
            <span style="color: var(--white);">{{ s.last_output|e|truncate(300, False, '') }}</span>
            {% else %}
            <span style="color: var(--text-muted);">Hasn't been run yet — ask the HQ Assistant to generate it</span>
            {% endif %}
          </div>
          {% set skill_sources = {
            "competitive-brief": "Your live competitor scores and pricing data",
            "pricing-analysis": "Your tracked competitor prices, updated each collection cycle",
            "council-brief": "Your advisory board goals and live business metrics",
            "competitor-onboarding": "Price, review, and social data collectors plus the scoring system",
            "weekly-intel-cycle": "All automated data collectors and the alert system",
            "rnd-project-setup": "Your R&D project tracker and business data",
            "warehouse-query-guide": "Your full business database (all tables)",
            "agent-orchestrator": "All 15 automated agents",
            "expansion-readiness-check": "Your advisory board criteria and live business data",
            "site-selection-analysis": "Market research data and demand estimates"
          } %}
          {% if s.name in skill_sources %}
          <div>
            <span style="color: var(--text-muted);">Data source:</span>
            <span style="color: var(--white);">{{ skill_sources[s.name] }}</span>
          </div>
          {% endif %}
        </div>
      </div>
      {% endfor %}
    </div>
    {% endif %}
    {% endfor %}

  </div><!-- /bento -->
  </div><!-- /tab-skills -->

  <!-- ═══ NIKE-STYLE FOOTER — multi-column ═══ -->
  <footer class="site-footer">
    <div class="footer-cols">
      <div class="footer-col">
        <div class="footer-head">Dashboard</div>
        <button class="foot-link" data-tab="overview">Overview</button>
        <button class="foot-link" data-tab="competitors">Competitors</button>
        <button class="foot-link" data-tab="operations">Operations</button>
        <button class="foot-link" data-tab="projects">Projects</button>
        <button class="foot-link" data-tab="skills">Skills</button>
      </div>
      <div class="footer-col">
        <div class="footer-head">Intelligence</div>
        <span class="foot-item">{{ data.competitor_count }} Competitors Tracked</span>
        <span class="foot-item">{{ data.agent_fleet|length }} Automated Agents</span>
        <span class="foot-item">{{ data.agents_executed }} Agents Have Run</span>
        <span class="foot-item">Weekly Digest Sundays</span>
      </div>
      <div class="footer-col">
        <div class="footer-head">Systems</div>
        <span class="foot-item">Intelligence Warehouse</span>
        <span class="foot-item">HQ Assistant</span>
        <span class="foot-item">Alert Log</span>
      </div>
      <div class="footer-col">
        <div class="footer-head">Corporate HQ</div>
        <span class="foot-item">{{ data.shop.neighborhood }}</span>
        <span class="foot-item">Charlotte, NC</span>
        <span class="foot-item">{{ data.shop.years_experience }} Years Experience</span>
        <span class="foot-item">Powered by the Doctrine</span>
      </div>
    </div>
    <div class="footer-base">
      &copy; Corporate HQ &middot; Business Intelligence Dashboard
    </div>
  </footer>

</div><!-- /shell -->

<!-- ═══════════════════════════════════════════════════════════════
     AI CHAT ASSISTANT — Floating widget
     ═══════════════════════════════════════════════════════════════ -->
<style>
/* Chat FAB */
.chat-fab {
  position: fixed;
  bottom: 28px;
  right: 28px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--white);
  border: none;
  color: var(--bg-base);
  font-size: 24px;
  cursor: pointer;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(17,17,17,0.25);
  transition: all 0.3s;
}
.chat-fab:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(17,17,17,0.35);
}

/* Chat Panel */
.chat-panel {
  position: fixed;
  bottom: 96px;
  right: 28px;
  width: 400px;
  max-height: 560px;
  background: var(--bg-base);
  border: 1px solid rgba(17,17,17,0.1);
  border-radius: 16px;
  z-index: 9998;
  display: none;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 16px 48px rgba(17,17,17,0.18);
}
.chat-panel.visible {
  display: flex;
  animation: chat-slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes chat-slide-up {
  from { opacity: 0; transform: translateY(16px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* Chat Header */
.chat-header {
  padding: 16px 18px;
  border-bottom: 1px solid rgba(17,17,17,0.06);
  display: flex;
  align-items: center;
  gap: 10px;
}
.chat-header-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--teal);
  box-shadow: 0 0 6px rgba(46,196,182,0.5);
}
.chat-header-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}
.chat-header-sub {
  font-size: 10px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 300px;
  max-height: 380px;
}
.chat-msg {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  word-wrap: break-word;
}
.chat-msg.user {
  align-self: flex-end;
  background: rgba(46,196,182,0.15);
  border: 1px solid rgba(46,196,182,0.2);
  color: var(--text-primary);
}
.chat-msg.assistant {
  align-self: flex-start;
  background: rgba(17,17,17,0.04);
  border: 1px solid rgba(17,17,17,0.06);
  color: var(--text-secondary);
}
.chat-msg.assistant .msg-actions {
  margin-top: 8px;
  display: flex;
  gap: 6px;
}
.chat-msg .speaker-btn {
  background: rgba(17,17,17,0.06);
  border: 1px solid rgba(17,17,17,0.1);
  color: var(--text-muted);
  border-radius: 6px;
  padding: 3px 8px;
  font-size: 10px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: var(--font-mono);
}
.chat-msg .speaker-btn:hover {
  background: rgba(46,196,182,0.15);
  color: var(--teal-soft);
  border-color: rgba(46,196,182,0.3);
}
.chat-msg .speaker-btn.playing {
  background: rgba(46,196,182,0.2);
  color: var(--teal);
}

/* Loading dots */
.chat-loading {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
  align-self: flex-start;
}
.chat-loading span {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--teal);
  opacity: 0.4;
  animation: chat-dot 1.2s ease-in-out infinite;
}
.chat-loading span:nth-child(2) { animation-delay: 0.2s; }
.chat-loading span:nth-child(3) { animation-delay: 0.4s; }
@keyframes chat-dot {
  0%, 80%, 100% { opacity: 0.4; transform: scale(1); }
  40% { opacity: 1; transform: scale(1.3); }
}

/* Input */
.chat-input-area {
  padding: 12px 14px;
  border-top: 1px solid rgba(17,17,17,0.06);
  display: flex;
  gap: 8px;
  align-items: center;
}
.chat-input {
  flex: 1;
  background: rgba(17,17,17,0.04);
  border: 1px solid rgba(17,17,17,0.08);
  border-radius: 10px;
  padding: 10px 14px;
  color: var(--text-primary);
  font-size: 13px;
  font-family: var(--font-body);
  outline: none;
  transition: border-color 0.2s;
}
.chat-input:focus {
  border-color: rgba(46,196,182,0.4);
}
.chat-input::placeholder {
  color: var(--text-muted);
}
.chat-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: 1px solid rgba(17,17,17,0.08);
  background: rgba(17,17,17,0.04);
  color: var(--text-muted);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}
.chat-btn:hover {
  background: rgba(46,196,182,0.15);
  color: var(--teal);
  border-color: rgba(46,196,182,0.3);
}
.chat-btn.recording {
  background: rgba(230,57,70,0.2);
  color: var(--red-soft);
  border-color: rgba(230,57,70,0.3);
  animation: rec-pulse 1s ease-in-out infinite;
}
@keyframes rec-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(230,57,70,0.3); }
  50% { box-shadow: 0 0 0 6px rgba(230,57,70,0); }
}
.chat-btn.sending {
  opacity: 0.5;
  pointer-events: none;
}

/* Scrollbar */
.chat-messages::-webkit-scrollbar { width: 4px; }
.chat-messages::-webkit-scrollbar-track { background: transparent; }
.chat-messages::-webkit-scrollbar-thumb { background: rgba(17,17,17,0.1); border-radius: 2px; }

/* Mobile */
@media (max-width: 480px) {
  .chat-panel { right: 8px; left: 8px; width: auto; bottom: 80px; }
  .chat-fab { bottom: 16px; right: 16px; }
}
</style>

<!-- Chat FAB -->
<button class="chat-fab" id="chatFab" title="Ask your AI assistant">&#9993;</button>

<!-- Chat Panel -->
<div class="chat-panel" id="chatPanel">
  <div class="chat-header">
    <div class="chat-header-dot"></div>
    <div class="chat-header-title">HQ Assistant</div>
    <div class="chat-header-sub">Ask anything about your business</div>
  </div>
  <div class="chat-messages" id="chatMessages">
    <div class="chat-msg assistant">
      Hey William. I have access to your full warehouse — competitors, pricing, reviews, social data, and agent logs. Ask me anything about your market.
    </div>
  </div>
  <div class="chat-input-area">
    <button class="chat-btn" id="chatMic" title="Voice input">&#9834;</button>
    <input type="text" class="chat-input" id="chatInput" placeholder="Ask about your business..." autocomplete="off">
    <button class="chat-btn" id="chatSend" title="Send">&#10148;</button>
  </div>
</div>

<script>
const DATA = {{ data_json|safe }};

document.addEventListener('DOMContentLoaded', () => {

  // ═══ TAB NAVIGATION ═══
  const navTabs = document.querySelectorAll('.nav-tab');
  const tabPanels = document.querySelectorAll('.tab-panel');
  function activateTab(name) {
    navTabs.forEach(t => t.classList.toggle('active', t.dataset.tab === name));
    tabPanels.forEach(p => p.classList.toggle('active', p.id === 'tab-' + name));
    window.scrollTo({top: 0});
  }
  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      activateTab(tab.dataset.tab);
      history.replaceState(null, '', '#' + tab.dataset.tab);
    });
  });
  // Footer links switch tabs too
  document.querySelectorAll('.foot-link').forEach(link => {
    link.addEventListener('click', () => {
      activateTab(link.dataset.tab);
      history.replaceState(null, '', '#' + link.dataset.tab);
    });
  });
  // Deep-link support: /#competitors opens that tab on load
  const initialTab = location.hash.replace('#', '');
  if (initialTab && document.getElementById('tab-' + initialTab)) {
    activateTab(initialTab);
  }

  // ═══ TOPBAR ASSISTANT BUTTON — same toggle as the chat FAB ═══
  document.getElementById('topbarAssistant').addEventListener('click', () => {
    document.getElementById('chatFab').click();
  });

  const cards = document.querySelectorAll('.card');

  // ═══ STAGGERED CARD ENTRANCE ═══
  cards.forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px) scale(0.97)';
    card.style.transition = `opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1) ${80 + i * 60}ms, transform 0.7s cubic-bezier(0.16, 1, 0.3, 1) ${80 + i * 60}ms`;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        card.style.opacity = '1';
        card.style.transform = 'translateY(0) scale(1)';
      });
    });
  });

  // ═══ ANIMATE PRICE BARS ═══
  const bars = document.querySelectorAll('.price-bar-fill');
  bars.forEach((bar, i) => {
    const w = bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = w; }, 200 + i * 100);
  });

  // ═══ COUNT-UP ANIMATION ═══
  const metrics = document.querySelectorAll('.metric-value');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const text = el.textContent.trim();
      const val = parseInt(text);
      if (isNaN(val) || el.dataset.counted) return;
      el.dataset.counted = 'true';
      let current = 0;
      const duration = 800;
      const start = performance.now();
      const step = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        current = Math.round(val * eased);
        el.textContent = current;
        if (progress < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
      observer.unobserve(el);
    });
  }, { threshold: 0.5 });
  metrics.forEach(el => observer.observe(el));

  // ═══ LIVE PULSE — topbar status dots ═══
  const dots = document.querySelectorAll('.status-dot .dot');
  dots.forEach((dot, i) => {
    dot.style.animationDelay = `${i * 0.3}s`;
  });

  // ═══════════════════════════════════════════════════════════════
  //  AI CHAT ASSISTANT
  // ═══════════════════════════════════════════════════════════════
  const chatFab = document.getElementById('chatFab');
  const chatPanel = document.getElementById('chatPanel');
  const chatInput = document.getElementById('chatInput');
  const chatSend = document.getElementById('chatSend');
  const chatMic = document.getElementById('chatMic');
  const chatMessages = document.getElementById('chatMessages');
  let chatHistory = [];
  let chatBusy = false;
  let currentAudio = null;
  let chatSessionId = null;
  let chatMode = 'messages';

  // Toggle panel — session is warmed at page load; retry here if it failed
  chatFab.addEventListener('click', () => {
    const open = chatPanel.classList.toggle('visible');
    chatFab.classList.toggle('open', open);
    chatFab.innerHTML = open ? '&#10005;' : '&#9993;';
    if (open) {
      chatInput.focus();
      if (!chatSessionId) initSession();
    }
  });

  let sessionReady = null;

  function updateModeLabel(mode) {
    const label = mode === 'managed' ? 'Connected to HQ Agent' : 'Ask anything about your business';
    document.querySelector('.chat-header-sub').textContent = label;
  }

  // Initialize managed agent session — returns a promise sendMessage can await
  function initSession() {
    sessionReady = fetch('/api/chat/session', {method: 'POST', headers: {'Content-Type': 'application/json'}})
    .then(r => r.json())
    .then(data => {
      chatSessionId = data.session_id;
      chatMode = data.mode || 'messages';
      updateModeLabel(chatMode);
      if (data.note) console.log('Chat session note:', data.note);
    })
    .catch(() => {
      chatSessionId = 'local';
      chatMode = 'messages';
    });
    return sessionReady;
  }

  // Warm the session at page load so the first message uses the managed agent
  initSession();

  // Send message
  function sendMessage(text) {
    if (!text.trim() || chatBusy) return;
    chatBusy = true;
    chatSend.classList.add('sending');

    // Add user message
    appendMsg('user', text);
    chatHistory.push({role: 'user', content: text});
    chatInput.value = '';

    // Show loading
    const loader = document.createElement('div');
    loader.className = 'chat-loading';
    loader.innerHTML = '<span></span><span></span><span></span>';
    chatMessages.appendChild(loader);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Wait for session init so the first message doesn't race past it
    (sessionReady || initSession()).then(() => fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        message: text,
        history: chatHistory.slice(0, -1),
        session_id: chatSessionId,
        mode: chatMode
      })
    }))
    .then(r => r.json())
    .then(data => {
      loader.remove();
      if (data.error) {
        appendMsg('assistant', 'Error: ' + data.error);
      } else {
        if (data.mode && data.mode !== chatMode) {
          console.log('Reply served by ' + data.mode + ' fallback (session mode: ' + chatMode + ')');
        }
        appendMsg('assistant', data.reply, true);
        chatHistory.push({role: 'assistant', content: data.reply});
      }
    })
    .catch(err => {
      loader.remove();
      appendMsg('assistant', 'Connection error. Make sure the server is running.');
    })
    .finally(() => {
      chatBusy = false;
      chatSend.classList.remove('sending');
    });
  }

  function appendMsg(role, text, showSpeaker) {
    const div = document.createElement('div');
    div.className = 'chat-msg ' + role;

    // Simple markdown-like formatting
    let html = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
    div.innerHTML = html;

    if (showSpeaker && role === 'assistant') {
      const actions = document.createElement('div');
      actions.className = 'msg-actions';
      const btn = document.createElement('button');
      btn.className = 'speaker-btn';
      btn.innerHTML = '&#9835; Listen';
      btn.addEventListener('click', () => playTTS(text, btn));
      actions.appendChild(btn);
      div.appendChild(actions);
    }

    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // TTS via ElevenLabs
  function playTTS(text, btn) {
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    btn.classList.add('playing');
    btn.innerHTML = '&#9835; Loading...';

    fetch('/api/tts', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: text.substring(0, 1000)})
    })
    .then(r => {
      if (!r.ok) throw new Error('TTS unavailable');
      return r.blob();
    })
    .then(blob => {
      const url = URL.createObjectURL(blob);
      currentAudio = new Audio(url);
      currentAudio.play();
      btn.innerHTML = '&#9835; Playing...';
      currentAudio.addEventListener('ended', () => {
        btn.classList.remove('playing');
        btn.innerHTML = '&#9835; Listen';
        currentAudio = null;
      });
    })
    .catch(() => {
      btn.classList.remove('playing');
      btn.innerHTML = '&#9835; Unavailable';
      setTimeout(() => { btn.innerHTML = '&#9835; Listen'; }, 2000);
    });
  }

  // Voice input via Web Speech API
  let recognition = null;
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      chatInput.value = transcript;
      chatMic.classList.remove('recording');
      chatMic.innerHTML = '&#9834;';
      sendMessage(transcript);
    };
    recognition.onerror = () => {
      chatMic.classList.remove('recording');
      chatMic.innerHTML = '&#9834;';
    };
    recognition.onend = () => {
      chatMic.classList.remove('recording');
      chatMic.innerHTML = '&#9834;';
    };
  }

  chatMic.addEventListener('click', () => {
    if (!recognition) {
      alert('Voice input not supported in this browser. Use Chrome for best results.');
      return;
    }
    if (chatMic.classList.contains('recording')) {
      recognition.stop();
    } else {
      chatMic.classList.add('recording');
      chatMic.innerHTML = '&#9679;';
      recognition.start();
    }
  });

  // Send on click or Enter
  chatSend.addEventListener('click', () => sendMessage(chatInput.value));
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(chatInput.value);
    }
  });

});
</script>
</body>
</html>'''


# ════════════════════════════════════════════════════════════════════════
#  RUN
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  CORPORATE HQ — Dashboard launching on port {port}...")
    print(f"  Open: http://localhost:{port}\n")
    app.run(debug=False, host="0.0.0.0", port=port)
