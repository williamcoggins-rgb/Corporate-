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
    setup_managed_agent, run_agent_task,
    create_chat_session, send_chat_message,
)

app = Flask(__name__)
_scheduler = None

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
        "os_features": YOUR_SHOP.get("booking_os", {}).get("features", []),
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

    # Neighborhoods
    d["neighborhoods"] = _q("""
        SELECT c.neighborhood, COUNT(DISTINCT c.competitor_id) as shops,
               ROUND(AVG(ph.price), 2) as avg_fade
        FROM competitors c
        LEFT JOIN price_history ph ON ph.competitor_id = c.competitor_id
            AND ph.service_name = 'Fade'
        WHERE c.status = 'Active'
        GROUP BY c.neighborhood
        ORDER BY shops ASC
    """)

    # Recent moves
    d["recent_moves"] = _q("""
        SELECT c.company_name, cm.move_type, cm.description,
               cm.move_date
        FROM competitor_moves cm
        JOIN competitors c ON c.competitor_id = cm.competitor_id
        ORDER BY cm.move_date DESC LIMIT 6
    """)

    # Social leaders
    d["social_leaders"] = _q("""
        SELECT c.company_name, cs.followers, cs.engagement_rate, cs.platform
        FROM competitor_social cs
        JOIN competitors c ON c.competitor_id = cs.competitor_id
        ORDER BY cs.followers DESC LIMIT 5
    """)

    # Barber talent pool
    d["barber_count"] = _q("SELECT COUNT(*) as n FROM barbers")[0]["n"]

    # Scores
    d["score_count"] = _q("SELECT COUNT(*) as n FROM competitor_scores")[0]["n"]

    # Review avg
    d["review_avg"] = float(_q(
        "SELECT COALESCE(ROUND(AVG(rating), 1), 0) as avg FROM review_snapshots"
    )[0]["avg"])

    # Top competitors by threat
    d["top_threats"] = _q("""
        SELECT c.company_name, c.neighborhood, c.ownership_type,
               cs.score as threat_score
        FROM competitor_scores cs
        JOIN competitors c ON c.competitor_id = cs.competitor_id
        WHERE cs.score_type = 'threat'
        ORDER BY cs.score DESC LIMIT 8
    """)

    # Agent runs
    d["agent_runs"] = _q("""
        SELECT agent_name, status, started_at, records_processed
        FROM agent_runs
        ORDER BY started_at DESC LIMIT 8
    """)

    # Alerts
    d["alerts"] = _q("""
        SELECT alert_type, severity, title, detail, created_at
        FROM alerts_log
        ORDER BY created_at DESC LIMIT 6
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
                   execution_quality, token_efficiency, version, connected_to
            FROM skills
            WHERE status != 'retired'
            ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                     WHEN 'medium' THEN 2 ELSE 3 END, skill_id ASC
        """)
    except Exception:
        d["skills"] = []

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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
/* ═══════════════════════════════════════════════════════════════
   CSS CUSTOM PROPERTIES — THE BARBER POLE PALETTE
   ═══════════════════════════════════════════════════════════════ */
@property --angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}
@property --holo-angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}
@property --grid-scroll {
  syntax: "<number>";
  inherits: false;
  initial-value: 0;
}

:root {
  --white: #FAFAFA;
  --red: #E63946;
  --red-soft: #FF6B6B;
  --teal: #2EC4B6;
  --teal-soft: #5EEADB;

  --bg-base: #030308;
  --bg-surface: #0A0A12;
  --bg-elevated: #12121C;
  --bg-hover: #1A1A26;
  --bg-card: rgba(10, 10, 18, 0.75);

  --text-primary: #FAFAFA;
  --text-secondary: #9CA3AF;
  --text-muted: #5C6370;

  --border-subtle: rgba(250, 250, 250, 0.05);
  --border-glow: rgba(46, 196, 182, 0.15);

  --shadow-glow-red: 0 0 30px rgba(230, 57, 70, 0.12);
  --shadow-glow-teal: 0 0 30px rgba(46, 196, 182, 0.12);

  --radius: 20px;
  --radius-sm: 12px;
  --radius-xs: 8px;

  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', monospace;

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
  font-size: 14px;
  line-height: 1.5;
  overflow-x: hidden;
  min-height: 100vh;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

/* ═══════════════════════════════════════════════════════════════
   4D BACKGROUND — PERSPECTIVE GRID + DEPTH LAYERS
   ═══════════════════════════════════════════════════════════════ */
.bg-4d {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  perspective: 800px;
  perspective-origin: 50% 30%;
  overflow: hidden;
}

/* Infinite perspective grid floor */
.grid-floor {
  position: absolute;
  width: 200vw;
  height: 200vh;
  left: -50vw;
  top: 10%;
  transform: rotateX(65deg) translateZ(0px);
  transform-style: preserve-3d;
  background-image:
    linear-gradient(rgba(46,196,182,0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(46,196,182,0.08) 1px, transparent 1px);
  background-size: 80px 80px;
  animation: grid-scroll 20s linear infinite;
  mask-image: radial-gradient(ellipse 60% 50% at 50% 20%, black, transparent);
  -webkit-mask-image: radial-gradient(ellipse 60% 50% at 50% 20%, black, transparent);
}
@keyframes grid-scroll {
  from { background-position: 0 0; }
  to { background-position: 0 80px; }
}

/* Depth orbs — floating at different Z layers */
.depth-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
}
.depth-orb-1 {
  width: 40vmax; height: 40vmax;
  background: radial-gradient(circle, rgba(230,57,70,0.3), transparent 70%);
  top: -10%; left: -5%;
  transform: translateZ(-200px);
  animation: float-z1 25s ease-in-out infinite alternate;
  opacity: 0.2;
}
.depth-orb-2 {
  width: 35vmax; height: 35vmax;
  background: radial-gradient(circle, rgba(46,196,182,0.3), transparent 70%);
  bottom: -15%; right: -5%;
  transform: translateZ(-400px);
  animation: float-z2 30s ease-in-out infinite alternate;
  opacity: 0.15;
}
.depth-orb-3 {
  width: 20vmax; height: 20vmax;
  background: radial-gradient(circle, rgba(250,250,250,0.2), transparent 70%);
  top: 30%; left: 40%;
  transform: translateZ(-100px);
  animation: float-z3 18s ease-in-out infinite alternate;
  opacity: 0.06;
}
@keyframes float-z1 {
  0% { transform: translateZ(-200px) translate(0, 0); }
  50% { transform: translateZ(-150px) translate(8vw, 5vh); }
  100% { transform: translateZ(-250px) translate(-5vw, 10vh); }
}
@keyframes float-z2 {
  0% { transform: translateZ(-400px) translate(0, 0); }
  50% { transform: translateZ(-300px) translate(-10vw, -5vh); }
  100% { transform: translateZ(-350px) translate(5vw, -8vh); }
}
@keyframes float-z3 {
  0% { transform: translateZ(-100px) translate(0, 0) scale(1); }
  100% { transform: translateZ(-50px) translate(-8vw, 6vh) scale(1.3); }
}

/* Horizon glow line */
.horizon-glow {
  position: absolute;
  width: 100%;
  height: 2px;
  top: 38%;
  left: 0;
  background: linear-gradient(90deg, transparent, rgba(46,196,182,0.15) 20%, rgba(230,57,70,0.1) 50%, rgba(46,196,182,0.15) 80%, transparent);
  box-shadow: 0 0 60px 20px rgba(46,196,182,0.04), 0 0 120px 40px rgba(230,57,70,0.02);
  animation: horizon-pulse 8s ease-in-out infinite;
}
@keyframes horizon-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* Star particles at various depths */
.stars {
  position: absolute;
  inset: 0;
}
.star {
  position: absolute;
  width: 2px;
  height: 2px;
  background: var(--white);
  border-radius: 50%;
  animation: twinkle var(--dur) ease-in-out infinite;
  opacity: 0;
}
@keyframes twinkle {
  0%, 100% { opacity: 0; transform: scale(0.5); }
  50% { opacity: var(--brightness); transform: scale(1); }
}

/* Noise texture overlay */
.noise-overlay {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  opacity: 0.02;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* Scanline effect for that extra dimension */
.scanlines {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0,0,0,0.03) 2px,
    rgba(0,0,0,0.03) 4px
  );
  animation: scan-drift 0.1s steps(2) infinite;
}
@keyframes scan-drift {
  to { background-position: 0 4px; }
}

/* ═══════════════════════════════════════════════════════════════
   LAYOUT — SHELL WITH DEPTH
   ═══════════════════════════════════════════════════════════════ */
.shell {
  position: relative;
  z-index: 2;
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px 28px 60px;
  transform-style: preserve-3d;
}

/* ═══════════════════════════════════════════════════════════════
   TOP BAR — POWER HEADER
   ═══════════════════════════════════════════════════════════════ */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px;
  border-radius: var(--radius);
  position: relative;
  background: linear-gradient(135deg, rgba(10,10,18,0.95), rgba(15,15,24,0.9));
  border: 1px solid rgba(250,250,250,0.06);
  margin-bottom: 28px;
  overflow: hidden;
  backdrop-filter: blur(20px);
}

/* Spinning conic border — barber pole energy ring */
.topbar::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: var(--radius);
  padding: 1.5px;
  background: conic-gradient(from var(--angle), var(--red), var(--teal), var(--white), var(--red));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: spin-border 3s linear infinite;
  opacity: 0.8;
}

/* Inner energy sweep — horizontal power pulse */
.topbar::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 50%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(46,196,182,0.06) 30%, rgba(230,57,70,0.04) 50%, rgba(46,196,182,0.06) 70%, transparent);
  animation: power-sweep 4s ease-in-out infinite;
  pointer-events: none;
}
@keyframes spin-border { to { --angle: 360deg; } }
@keyframes power-sweep {
  0% { left: -50%; }
  100% { left: 100%; }
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* Logo — pulsing power core */
.topbar-logo {
  width: 48px; height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--red), var(--teal));
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 18px;
  color: var(--white);
  position: relative;
  animation: logo-breathe 3s ease-in-out infinite;
  box-shadow:
    0 0 20px rgba(230,57,70,0.3),
    0 0 40px rgba(46,196,182,0.2),
    inset 0 0 10px rgba(255,255,255,0.1);
}
.topbar-logo::before {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 14px;
  background: conic-gradient(from var(--angle), var(--red), transparent 40%, var(--teal), transparent 80%, var(--red));
  animation: spin-border 3s linear infinite;
  opacity: 0.5;
  filter: blur(4px);
  z-index: -1;
}
@keyframes logo-breathe {
  0%, 100% {
    box-shadow: 0 0 20px rgba(230,57,70,0.3), 0 0 40px rgba(46,196,182,0.2), inset 0 0 10px rgba(255,255,255,0.1);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 30px rgba(230,57,70,0.5), 0 0 60px rgba(46,196,182,0.3), inset 0 0 15px rgba(255,255,255,0.15);
    transform: scale(1.04);
  }
}

/* Title — chromatic power text */
.topbar-title {
  font-size: clamp(1.1rem, 1.5vw + 0.5rem, 1.4rem);
  font-weight: 900;
  letter-spacing: 5px;
  text-transform: uppercase;
  background: linear-gradient(
    var(--holo-angle),
    var(--white) 0%,
    var(--red-soft) 20%,
    var(--white) 40%,
    var(--teal-soft) 60%,
    var(--white) 80%,
    var(--red-soft) 100%
  );
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: title-power 4s linear infinite;
  filter: drop-shadow(0 0 12px rgba(250,250,250,0.15));
}
@keyframes title-power {
  from { background-position: 200% center; }
  to { background-position: 0% center; }
}

.topbar-subtitle {
  font-size: 10px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  letter-spacing: 2px;
  text-transform: uppercase;
  animation: subtitle-flicker 6s ease-in-out infinite;
}
@keyframes subtitle-flicker {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; color: var(--teal); }
}

.topbar-status {
  display: flex;
  align-items: center;
  gap: 18px;
}
.status-dot {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
  letter-spacing: 0.5px;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(250,250,250,0.02);
  border: 1px solid rgba(250,250,250,0.04);
  transition: all 0.3s;
}
.status-dot:hover {
  background: rgba(250,250,250,0.05);
  border-color: rgba(250,250,250,0.1);
}
.status-dot .dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
  position: relative;
}
.status-dot .dot::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  background: inherit;
  opacity: 0.3;
  filter: blur(4px);
  animation: pulse-dot 2s ease-in-out infinite;
}
.dot-green { background: #34D399; box-shadow: 0 0 10px rgba(52,211,153,0.5); }
.dot-red { background: var(--red); box-shadow: 0 0 10px rgba(230,57,70,0.5); }
.dot-teal { background: var(--teal); box-shadow: 0 0 10px rgba(46,196,182,0.5); }
.dot-yellow { background: #FBBF24; box-shadow: 0 0 10px rgba(251,191,36,0.5); }
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.8); }
}

@media (max-width: 768px) {
  .topbar { flex-direction: column; gap: 14px; padding: 16px 20px; }
  .topbar-status { flex-wrap: wrap; justify-content: center; }
}
@media (max-width: 640px) {
  .topbar { padding: 14px 16px; gap: 10px; }
  .topbar-brand { flex-direction: column; text-align: center; gap: 6px; }
  .topbar-logo { margin: 0 auto; }
  .topbar-title { font-size: 16px; }
  .topbar-subtitle { font-size: 9px; letter-spacing: 2px; }
  .topbar-status { gap: 6px; justify-content: center; }
  .status-dot { font-size: 9px; padding: 3px 8px; letter-spacing: 0.5px; }
}

/* ═══════════════════════════════════════════════════════════════
   MIGRATION BANNER — persistent until Booksy is done
   ═══════════════════════════════════════════════════════════════ */
.migration-banner {
  background: linear-gradient(90deg, rgba(230,57,70,0.1), rgba(46,196,182,0.08));
  border: 1px solid rgba(230,57,70,0.2);
  border-radius: var(--radius-sm);
  padding: 12px 20px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.migration-banner .label {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--red-soft);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-weight: 600;
}
.migration-banner .bar-track {
  flex: 1;
  height: 4px;
  background: rgba(250,250,250,0.06);
  border-radius: 4px;
  overflow: hidden;
  max-width: 400px;
}
.migration-banner .bar-fill {
  height: 100%;
  width: 35%;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--red), var(--teal));
  animation: shimmer 2s ease-in-out infinite;
}
@keyframes shimmer {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.migration-banner .pct {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--red-soft);
}

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

  /* Migration banner */
  .migration-banner { flex-direction: column; padding: 10px 14px; gap: 8px; text-align: center; }
  .migration-banner .label { font-size: 10px; }

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
  background: rgba(15, 15, 20, 0.65);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(250,250,250,0.07);
  border-radius: var(--radius);
  padding: 24px 26px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              box-shadow 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              background 0.4s;
  box-shadow: 0 4px 24px rgba(0,0,0,0.2),
              inset 0 1px 0 rgba(250,250,250,0.04);
  container-type: inline-size;
}
.card:hover {
  border-color: rgba(250,250,250,0.12);
  background: rgba(10, 10, 18, 0.85);
  box-shadow: 0 12px 48px rgba(0,0,0,0.4),
              inset 0 1px 0 rgba(250,250,250,0.06),
              0 0 40px rgba(46,196,182,0.04);
}
/* Stripe flashlight hover — radial gradient follows cursor */
.card .spotlight {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: radial-gradient(
    500px circle at var(--mx) var(--my),
    rgba(46, 196, 182, 0.08),
    transparent 40%
  );
  opacity: 0;
  transition: opacity 0.4s;
  pointer-events: none;
  z-index: 0;
}
.card:hover .spotlight { opacity: 1; }
.card > *:not(.spotlight) { position: relative; z-index: 1; }
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
.badge-red { background: rgba(230,57,70,0.15); color: var(--red-soft); border: 1px solid rgba(230,57,70,0.2); }
.badge-teal { background: rgba(46,196,182,0.15); color: var(--teal-soft); border: 1px solid rgba(46,196,182,0.2); }
.badge-yellow { background: rgba(251,191,36,0.15); color: #FBBF24; border: 1px solid rgba(251,191,36,0.2); }
.badge-green { background: rgba(52,211,153,0.12); color: #34D399; border: 1px solid rgba(52,211,153,0.2); }

/* ═══════════════════════════════════════════════════════════════
   GLOW CARD VARIANT — animated border
   ═══════════════════════════════════════════════════════════════ */
.card-glow::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: var(--radius);
  padding: 1px;
  background: conic-gradient(from var(--angle), var(--red), transparent 25%, var(--teal), transparent 65%, var(--red));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: spin-border 5s linear infinite;
  opacity: 0;
  transition: opacity 0.5s;
  z-index: 2;
}
/* Blur halo behind the rotating border */
.card-glow::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: var(--radius);
  background: conic-gradient(from var(--angle), var(--red), transparent 25%, var(--teal), transparent 65%, var(--red));
  filter: blur(18px);
  opacity: 0;
  transition: opacity 0.5s;
  z-index: -1;
  animation: spin-border 5s linear infinite;
}
.card-glow:hover::before { opacity: 0.6; }
.card-glow:hover::after { opacity: 0.2; }

/* ═══════════════════════════════════════════════════════════════
   STAT NUMBERS — big metric display
   ═══════════════════════════════════════════════════════════════ */
.stat-big {
  font-size: var(--text-hero);
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.04em;
  margin: 6px 0;
  font-variant-numeric: tabular-nums;
}
.stat-big.red {
  background: linear-gradient(135deg, var(--red), var(--red-soft));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 20px rgba(230,57,70,0.25));
}
.stat-big.teal {
  background: linear-gradient(135deg, var(--teal), var(--teal-soft));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 20px rgba(46,196,182,0.25));
}
.stat-big.white {
  background: linear-gradient(135deg, #fff 0%, rgba(255,255,255,0.7) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

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
.delta-up { background: rgba(52,211,153,0.12); color: #34D399; }
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
  background: rgba(250,250,250,0.03);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 16px 18px;
  text-align: center;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  box-shadow: inset 0 1px 0 rgba(250,250,250,0.03);
}
.metric-cell:hover {
  background: rgba(250,250,250,0.06);
  border-color: rgba(46,196,182,0.2);
  box-shadow: inset 0 1px 0 rgba(250,250,250,0.05), 0 0 16px rgba(46,196,182,0.06);
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
  background: rgba(250,250,250,0.02);
  border: 1px solid var(--border-subtle);
  transition: all 0.2s;
}
.council-row:hover { background: rgba(250,250,250,0.04); }
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
.vote-yes { background: rgba(52,211,153,0.15); color: #34D399; border: 1px solid rgba(52,211,153,0.25); }
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
  background: rgba(250,250,250,0.02);
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}
.intel-table td:first-child { border-left: 1px solid var(--border-subtle); border-radius: 8px 0 0 8px; }
.intel-table td:last-child { border-right: 1px solid var(--border-subtle); border-radius: 0 8px 8px 0; }
.intel-table tr:hover td { background: rgba(250,250,250,0.04); }

.threat-bar {
  height: 4px;
  border-radius: 2px;
  background: rgba(250,250,250,0.06);
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
  background: rgba(250,250,250,0.04);
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
  background: rgba(250,250,250,0.02);
  border: 1px solid var(--border-subtle);
  margin-bottom: 6px;
  transition: all 0.2s;
}
.pipeline-row:hover { background: rgba(250,250,250,0.04); }
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
  background: rgba(250,250,250,0.05);
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
  background: rgba(250,250,250,0.02);
  border: 1px solid var(--border-subtle);
  font-size: 11px;
  transition: all 0.2s;
}
.agent-cell:hover { background: rgba(250,250,250,0.04); }
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
   HOLOGRAPHIC TITLE
   ═══════════════════════════════════════════════════════════════ */
.holo-text {
  background: linear-gradient(
    var(--holo-angle),
    var(--red) 0%, var(--white) 25%, var(--teal) 50%, var(--white) 75%, var(--red) 100%
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: holo 5s linear infinite;
  font-weight: 900;
}
@keyframes holo { from { --holo-angle: 0deg; } to { --holo-angle: 360deg; } }

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
::-webkit-scrollbar-thumb { background: rgba(250,250,250,0.08); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(250,250,250,0.14); }

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
  background: rgba(250,250,250,0.03);
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
.lab-tab[data-lab="os"] { --lab-color: #a78bfa; }
.lab-tab[data-lab="market"] { --lab-color: #FBBF24; }
.lab-tab[data-lab="business"] { --lab-color: var(--red-soft); }
.lab-tab[data-lab="product"] { --lab-color: #34D399; }
.lab-tab.active[data-lab="service"] { background: rgba(46,196,182,0.12); border-color: rgba(46,196,182,0.3); color: var(--teal-soft); }
.lab-tab.active[data-lab="os"] { background: rgba(167,139,250,0.12); border-color: rgba(167,139,250,0.3); color: #a78bfa; }
.lab-tab.active[data-lab="market"] { background: rgba(251,191,36,0.12); border-color: rgba(251,191,36,0.3); color: #FBBF24; }
.lab-tab.active[data-lab="business"] { background: rgba(255,107,107,0.12); border-color: rgba(255,107,107,0.3); color: var(--red-soft); }
.lab-tab.active[data-lab="product"] { background: rgba(52,211,153,0.12); border-color: rgba(52,211,153,0.3); color: #34D399; }

.rnd-project {
  padding: 14px 16px;
  border-radius: var(--radius-xs);
  background: rgba(250,250,250,0.02);
  border: 1px solid var(--border-subtle);
  margin-bottom: 8px;
  transition: all 0.2s;
}
.rnd-project:hover {
  background: rgba(250,250,250,0.04);
  border-color: rgba(250,250,250,0.1);
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
  color: #34D399;
  margin-left: auto;
}

/* ═══════════════════════════════════════════════════════════════
   SKILLS DEPARTMENT CARDS
   ═══════════════════════════════════════════════════════════════ */
.skill-card {
  padding: 14px 16px;
  border-radius: var(--radius-xs);
  background: rgba(250,250,250,0.02);
  border: 1px solid var(--border-subtle);
  margin-bottom: 8px;
  transition: all 0.2s;
}
.skill-card:hover {
  background: rgba(250,250,250,0.04);
  border-color: rgba(250,250,250,0.1);
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
  background: rgba(250,250,250,0.06);
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
.section-header {
  grid-column: span 12;
  padding: 36px 0 16px;
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.section-num {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--teal);
  letter-spacing: 2px;
  opacity: 0.5;
}
.section-title {
  font-size: 11px;
  font-family: var(--font-mono);
  letter-spacing: 4px;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
}
.section-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--border-subtle), transparent);
}

/* ═══════════════════════════════════════════════════════════════
   4D CARD TILT
   ═══════════════════════════════════════════════════════════════ */
.card-3d {
  transform-style: preserve-3d;
  transition: transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

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
  background: rgba(250,250,250,0.02);
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
</style>
</head>
<body>

<!-- 4D BACKGROUND SYSTEM -->
<div class="bg-4d">
  <div class="grid-floor"></div>
  <div class="depth-orb depth-orb-1"></div>
  <div class="depth-orb depth-orb-2"></div>
  <div class="depth-orb depth-orb-3"></div>
  <div class="horizon-glow"></div>
  <div class="stars" id="starfield"></div>
</div>
<div class="noise-overlay"></div>
<div class="scanlines"></div>

<!-- DASHBOARD SHELL -->
<div class="shell">

  <!-- ═══ POWER HEADER ═══ -->
  <div class="topbar">
    <div class="topbar-brand">
      <div class="topbar-logo">HQ</div>
      <div>
        <div class="topbar-title">Corporate HQ</div>
        <div class="topbar-subtitle">Business Intelligence Dashboard</div>
      </div>
    </div>
    <div class="topbar-status">
      <div class="status-dot">
        <span class="dot dot-green"></span>
        Booking System Live
      </div>
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
  </div>

  <!-- ═══ BOOKSY MIGRATION BANNER ═══ -->
  {% if data.shop.migrating_from %}
  <div class="migration-banner">
    <div class="label">Moving Clients from Booksy to Our System</div>
    <div class="bar-track"><div class="bar-fill"></div></div>
    <div class="pct">In Progress</div>
  </div>
  {% endif %}

  <!-- ═══ BENTO GRID ═══ -->
  <div class="bento">

    <!-- ════════════════════════════════════════════════════════
         SECTION 01: COMMAND CENTER
         ════════════════════════════════════════════════════════ -->

    <!-- HERO CARD — Revenue Command -->
    <div class="card card-glow card-3d b-hero">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Revenue Overview</span>
        <span class="card-badge badge-teal">LIVE</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5;">
        Your current monthly income from the shop. Target is $4,500/month. All data is pulled live from your booking system.
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
        The bars show how your price compares to the market average. Green bar = market average. Red bar = market high. Your price is shown at the right.
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
        <span class="card-badge badge-teal">{{ data.neighborhoods|length }} ZONES</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5;">
        Each row is a Charlotte neighborhood your agents are monitoring. Shows how many competing shops are there and what the average fade price is.
      </div>
      <table class="intel-table">
        <thead>
          <tr>
            <th>Neighborhood</th>
            <th>Shops</th>
            <th>Avg Fade</th>
            <th>How Crowded</th>
          </tr>
        </thead>
        <tbody>
          {% for n in data.neighborhoods[:10] %}
          <tr>
            <td style="font-weight: 500;">{{ n.neighborhood or 'Unknown' }}</td>
            <td>
              <span style="font-family: var(--font-mono); {% if n.shops <= 1 %}color: var(--teal);{% elif n.shops >= 4 %}color: var(--red-soft);{% endif %}">
                {{ n.shops }}
              </span>
            </td>
            <td>
              {% if n.avg_fade %}
              <span style="font-family: var(--font-mono);">${{ "%.0f"|format(n.avg_fade) }}</span>
              {% else %}
              <span style="color: var(--text-muted);">--</span>
              {% endif %}
            </td>
            <td>
              <div style="height:4px; border-radius:2px; background:rgba(250,250,250,0.06); min-width:40px;">
                <div style="height:100%; border-radius:2px; width:{{ (n.shops / 6 * 100)|int }}%; background: linear-gradient(90deg, var(--teal), {% if n.shops >= 4 %}var(--red){% else %}var(--teal-soft){% endif %});"></div>
              </div>
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
        <span class="card-badge badge-red">{% if data.top_threats|length %}{{ data.top_threats|length }} Tracked{% else %}None Being Tracked Yet{% endif %}</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5;">
        Competitors flagged by the Scorecard agent as high-threat based on ratings, growth, and pricing. Run the Scorecard agent to populate this.
      </div>
      {% if data.top_threats %}
      <table class="intel-table">
        <thead>
          <tr>
            <th>Competitor</th>
            <th>Area</th>
            <th>Type</th>
            <th>Threat Level</th>
          </tr>
        </thead>
        <tbody>
          {% for t in data.top_threats %}
          <tr>
            <td style="font-weight: 500;">{{ t.company_name }}</td>
            <td style="font-size: 11px; color: var(--text-secondary);">{{ t.neighborhood or '--' }}</td>
            <td><span style="font-family: var(--font-mono); font-size: 10px;">{{ t.ownership_type or '--' }}</span></td>
            <td>
              <div class="threat-bar">
                <div class="threat-fill" style="width: {{ ((t.threat_score or 0) / 10 * 100)|int }}%;"></div>
              </div>
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
        Events collected by your agents — new shop openings, expansions, franchise deals, and controversies in your market.
      </div>
      {% if data.recent_moves %}
        {% for move in data.recent_moves %}
        <div class="move-row">
          <div>
            <span class="move-who">{{ move.company_name }}</span>
            <span class="move-type">{{ move.move_type }}</span>
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

    <!-- ════════════════════════════════════════════════════════
         SECTION 03: OPERATIONS & SYSTEMS
         ════════════════════════════════════════════════════════ -->
    <div class="section-header">
      <span class="section-num">03</span>
      <span class="section-title">Operations &amp; Tools</span>
      <span class="section-line"></span>
    </div>
    <div style="grid-column: span 12; font-size: 11px; color: var(--text-muted); line-height: 1.5; margin-top: -8px; margin-bottom: 4px;">
      Your proprietary tech stack. This is what separates you from every other shop using off-the-shelf booking software.
    </div>

    <!-- OS STATUS -->
    <div class="card card-glow card-3d b-third">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Our Booking System</span>
        <span class="card-badge {% if data.shop.has_proprietary_os %}badge-green{% else %}badge-red{% endif %}">
          {% if data.shop.has_proprietary_os %}DEPLOYED{% else %}PENDING{% endif %}
        </span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.4;">
        Your custom booking and operations platform. Built specifically for this shop. Not Booksy, not Vagaro &mdash; yours.
      </div>
      {% for feat in data.shop.os_features %}
      <div class="os-feat">
        <div class="check">&#10003;</div>
        <span>{{ feat }}</span>
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
        <span class="card-badge badge-teal">13 Agents Running</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.4;">
        13 AI agents running in the background, continuously collecting data on competitors, pricing, reviews, and social media.
      </div>
      <div class="agent-grid">
        {% set agents = ['PricingScout', 'ReviewHarvester', 'SocialListener', 'ShopWatcher', 'PlatformScout', 'Normalizer', 'BarberEnricher', 'DeltaSpotter', 'PlatformAnalyzer', 'Scorecard', 'PriceWarAlert', 'ReputationRadar', 'WeeklyDigest'] %}
        {% for agent in agents %}
        <div class="agent-cell">
          <span class="dot {% if loop.index <= 1 %}dot-green{% else %}dot-yellow{% endif %}" style="width:6px;height:6px;border-radius:50%;flex-shrink:0;"></span>
          <span class="agent-name">{{ agent }}</span>
          <span class="agent-status" style="{% if loop.index <= 1 %}color: #34D399; background: rgba(52,211,153,0.1);{% else %}color: var(--text-muted); background: rgba(250,250,250,0.04);{% endif %}">
            {% if loop.index <= 1 %}LIVE{% else %}BUILT{% endif %}
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
        Real-time notifications triggered by your agents when something important changes in your market.
      </div>
      {% if data.alerts %}
        {% for alert in data.alerts %}
        <div class="alert-row">
          <div class="alert-icon" style="background: {% if alert.severity == 'critical' %}var(--red){% elif alert.severity == 'warning' %}#FBBF24{% else %}var(--teal){% endif %};
               box-shadow: 0 0 6px {% if alert.severity == 'critical' %}rgba(230,57,70,0.4){% elif alert.severity == 'warning' %}rgba(251,191,36,0.4){% else %}rgba(46,196,182,0.4){% endif %};"></div>
          <div>
            <div class="alert-title">{{ alert.title }}</div>
            {% if alert.detail %}
            <div class="alert-detail">{{ alert.detail[:80] }}</div>
            {% endif %}
          </div>
        </div>
        {% endfor %}
      {% else %}
        <div class="empty">Everything looks good. No alerts right now.</div>
      {% endif %}
    </div>

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
        {% set lab_colors = {'service': 'var(--teal)', 'os': '#a78bfa', 'market': '#FBBF24', 'business': 'var(--red-soft)', 'product': '#34D399'} %}
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
      ('os', 'Booking System Lab', 'Building new features into your proprietary booking and ops platform.', '#a78bfa', 'rgba(167,139,250,0.08)'),
      ('market', 'Market Research Lab', 'Studying market trends, competitor strategies, and customer behavior.', '#FBBF24', 'rgba(251,191,36,0.08)'),
      ('business', 'Business Strategy Lab', 'Exploring expansion models, partnerships, and revenue strategies.', 'var(--red-soft)', 'rgba(255,107,107,0.08)'),
      ('product', 'Product Development Lab', 'Developing physical or digital products tied to the brand.', '#34D399', 'rgba(52,211,153,0.08)')
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
            {% elif p.status == 'research' %}background: rgba(251,191,36,0.1); color: #FBBF24;
            {% elif p.status == 'complete' %}background: rgba(52,211,153,0.1); color: #34D399;
            {% else %}background: rgba(250,250,250,0.04); color: var(--text-muted);
            {% endif %}
          ">{{ p.status|replace('_', ' ')|upper }}</span>
          <span class="rnd-tag" style="
            {% if p.priority == 'critical' %}background: rgba(230,57,70,0.12); color: var(--red-soft);
            {% elif p.priority == 'high' %}background: rgba(251,191,36,0.1); color: #FBBF24;
            {% else %}background: rgba(250,250,250,0.04); color: var(--text-muted);
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
        {% set cat_configs = {'document': 'Document', 'workflow': 'Workflow', 'mcp': 'MCP Enhancement'} %}
        {% set cat_colors = {'document': '#60A5FA', 'workflow': '#F472B6', 'mcp': '#A78BFA'} %}
        {% for cat_key, cat_label in cat_configs.items() %}
        <div class="stat-chip">
          <div class="stat-chip-value" style="color: {{ cat_colors.get(cat_key, 'var(--white)') }};">{{ data.skills_by_cat.get(cat_key, {}).get('count', 0) }}</div>
          <div class="stat-chip-label">{{ cat_label }}</div>
        </div>
        {% endfor %}
        <div class="stat-chip">
          <div class="stat-chip-value" style="color: var(--teal);">{{ data.skills|selectattr('status', 'equalto', 'active')|list|length }}</div>
          <div class="stat-chip-label">Live</div>
        </div>
        <div class="stat-chip">
          <div class="stat-chip-value" style="color: #FBBF24;">{{ data.skills_by_phase.get('test', 0) + data.skills_by_phase.get('build', 0) }}</div>
          <div class="stat-chip-label">Testing</div>
        </div>
      </div>
    </div>

    <!-- SKILLS BY CATEGORY -->
    {% set skill_cat_configs = [
      ('document', 'Document / Asset Creation', 'Generate reports, briefs, analysis docs from warehouse data. Templates + style guides.', '#60A5FA', 'rgba(96,165,250,0.08)'),
      ('workflow', 'Workflow Automation', 'Multi-step processes with validation. Coordinates agents, enforces quality gates.', '#F472B6', 'rgba(244,114,182,0.08)'),
      ('mcp', 'MCP Enhancement', 'Guides Claude tool usage. Embeds domain expertise, optimizes API coordination.', '#A78BFA', 'rgba(167,139,250,0.08)')
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
          {% if s.status == 'active' %}
          <span class="skill-tag" style="background: rgba(46,196,182,0.12); color: var(--teal-soft);">ACTIVE</span>
          {% elif s.status == 'testing' %}
          <span class="skill-tag" style="background: rgba(251,191,36,0.1); color: #FBBF24;">TESTING</span>
          {% endif %}
        </div>
        {% if s.description %}
        <div class="skill-card-desc">{{ s.description|e|truncate(160) }}</div>
        {% endif %}

        <!-- What you get -->
        {% set skill_outputs = {
          "competitive-brief": "A formatted report showing exactly how your prices, services, and ratings compare to every competitor being tracked.",
          "pricing-analysis": "A side-by-side breakdown of your prices vs the market so you can see where you are over or underpriced.",
          "council-brief": "A formal document ready to present to your advisory board showing your progress toward the 5 expansion goals.",
          "competitor-onboarding": "A fully tracked competitor entry with pricing, reviews, social profiles, and a threat score — all set up automatically.",
          "weekly-intel-cycle": "A complete weekly intelligence sweep — updated prices, new reviews, social changes, and alerts across your entire market.",
          "rnd-project-setup": "A structured project plan with hypothesis, success metrics, and a concept paper ready to begin research.",
          "warehouse-query-guide": "Optimized data queries that pull exactly the right information from your warehouse without errors.",
          "agent-orchestrator": "Coordinated agent runs in the right order with proper error handling — no manual work needed.",
          "expansion-readiness-check": "A live readiness check against all 5 expansion goals showing exactly what is met and what is still needed.",
          "site-selection-analysis": "A multi-factor analysis of potential shop locations comparing demographics, competition, pricing, and demand."
        } %}
        {% if s.name in skill_outputs %}
        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 8px; line-height: 1.5;">
          <span style="color: var(--teal-soft); font-weight: 600;">What you get:</span> {{ skill_outputs[s.name] }}
        </div>
        {% endif %}

        <!-- Live status: Last run, Output, Fed by -->
        <div style="margin-top: 10px; font-size: 11px; line-height: 1.8;">
          <div>
            <span style="color: var(--text-muted);">Last run:</span>
            <span style="color: var(--white);">—</span>
          </div>
          <div>
            <span style="color: var(--text-muted);">Output:</span>
            <span style="color: var(--white);">—</span>
          </div>
          {% set skill_feeds = {
            "competitive-brief": "Scorecard Agent · Data Warehouse",
            "pricing-analysis": "Pricing Intelligence · Pricing Scout",
            "council-brief": "Advisory Council · Data Warehouse",
            "competitor-onboarding": "Pricing Scout · Review Harvester · Scorecard Agent",
            "weekly-intel-cycle": "All 13 Agents · Alert System",
            "rnd-project-setup": "R&D System · Data Warehouse",
            "warehouse-query-guide": "Data Warehouse (all 21 tables)",
            "agent-orchestrator": "All 13 Agents",
            "expansion-readiness-check": "Advisory Council · Business Strategy",
            "site-selection-analysis": "Market Research · Demand Forecasting"
          } %}
          {% if s.name in skill_feeds %}
          <div>
            <span style="color: var(--text-muted);">Fed by:</span>
            <span style="color: var(--white);">{{ skill_feeds[s.name] }}</span>
          </div>
          {% endif %}
        </div>
      </div>
      {% endfor %}
    </div>
    {% endif %}
    {% endfor %}

  </div><!-- /bento -->

  <!-- FOOTER -->
  <div style="text-align: center; padding: 48px 0 0; color: var(--text-muted); font-family: var(--font-mono); font-size: 10px; letter-spacing: 2px;">
    CORPORATE HQ &middot; BUSINESS INTELLIGENCE DASHBOARD &middot; POWERED BY THE DOCTRINE
  </div>

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
  background: linear-gradient(135deg, var(--teal), #1a8a7f);
  border: 2px solid rgba(46,196,182,0.3);
  color: #fff;
  font-size: 24px;
  cursor: pointer;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 24px rgba(46,196,182,0.3), 0 0 0 0 rgba(46,196,182,0.4);
  transition: all 0.3s;
  animation: chat-pulse 3s ease-in-out infinite;
}
.chat-fab:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 32px rgba(46,196,182,0.5);
}
.chat-fab.open { animation: none; }
@keyframes chat-pulse {
  0%, 100% { box-shadow: 0 4px 24px rgba(46,196,182,0.3), 0 0 0 0 rgba(46,196,182,0.4); }
  50% { box-shadow: 0 4px 24px rgba(46,196,182,0.3), 0 0 0 8px rgba(46,196,182,0); }
}

/* Chat Panel */
.chat-panel {
  position: fixed;
  bottom: 96px;
  right: 28px;
  width: 400px;
  max-height: 560px;
  background: rgba(14,14,16,0.97);
  border: 1px solid rgba(250,250,250,0.08);
  border-radius: 16px;
  z-index: 9998;
  display: none;
  flex-direction: column;
  overflow: hidden;
  backdrop-filter: blur(24px);
  box-shadow: 0 16px 64px rgba(0,0,0,0.6), 0 0 1px rgba(250,250,250,0.1);
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
  border-bottom: 1px solid rgba(250,250,250,0.06);
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
  background: rgba(250,250,250,0.04);
  border: 1px solid rgba(250,250,250,0.06);
  color: var(--text-secondary);
}
.chat-msg.assistant .msg-actions {
  margin-top: 8px;
  display: flex;
  gap: 6px;
}
.chat-msg .speaker-btn {
  background: rgba(250,250,250,0.06);
  border: 1px solid rgba(250,250,250,0.1);
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
  border-top: 1px solid rgba(250,250,250,0.06);
  display: flex;
  gap: 8px;
  align-items: center;
}
.chat-input {
  flex: 1;
  background: rgba(250,250,250,0.04);
  border: 1px solid rgba(250,250,250,0.08);
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
  border: 1px solid rgba(250,250,250,0.08);
  background: rgba(250,250,250,0.04);
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
.chat-messages::-webkit-scrollbar-thumb { background: rgba(250,250,250,0.1); border-radius: 2px; }

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

  // ═══ GENERATE STAR PARTICLES AT VARIOUS DEPTHS ═══
  const starfield = document.getElementById('starfield');
  for (let i = 0; i < 60; i++) {
    const star = document.createElement('div');
    star.className = 'star';
    star.style.left = Math.random() * 100 + '%';
    star.style.top = Math.random() * 100 + '%';
    star.style.setProperty('--dur', (3 + Math.random() * 6) + 's');
    star.style.setProperty('--brightness', (0.2 + Math.random() * 0.5).toString());
    star.style.animationDelay = (Math.random() * 5) + 's';
    star.style.width = (1 + Math.random() * 2) + 'px';
    star.style.height = star.style.width;
    starfield.appendChild(star);
  }

  // ═══ STRIPE FLASHLIGHT — cursor-tracking radial glow ═══
  const cards = document.querySelectorAll('.card');
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty('--mx', `${e.clientX - rect.left}px`);
      card.style.setProperty('--my', `${e.clientY - rect.top}px`);
    });
  });

  // ═══ 3D CARD TILT ON HOVER ═══
  document.querySelectorAll('.card-3d').forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      card.style.transform = `perspective(1000px) rotateY(${x * 4}deg) rotateX(${-y * 4}deg) scale(1.01)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg) scale(1)';
    });
  });

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

  // ═══ PARALLAX ON SCROLL — depth orbs move at different rates ═══
  window.addEventListener('scroll', () => {
    const sy = window.scrollY;
    document.querySelectorAll('.depth-orb-1').forEach(el => {
      el.style.transform = `translateZ(-200px) translateY(${sy * 0.05}px)`;
    });
    document.querySelectorAll('.depth-orb-2').forEach(el => {
      el.style.transform = `translateZ(-400px) translateY(${sy * 0.02}px)`;
    });
    document.querySelectorAll('.depth-orb-3').forEach(el => {
      el.style.transform = `translateZ(-100px) translateY(${sy * 0.08}px)`;
    });
  });

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

  // Toggle panel — create session on first open
  chatFab.addEventListener('click', () => {
    const open = chatPanel.classList.toggle('visible');
    chatFab.classList.toggle('open', open);
    chatFab.innerHTML = open ? '&#10005;' : '&#9993;';
    if (open) {
      chatInput.focus();
      if (!chatSessionId) initSession();
    }
  });

  // Initialize managed agent session
  function initSession() {
    fetch('/api/chat/session', {method: 'POST', headers: {'Content-Type': 'application/json'}})
    .then(r => r.json())
    .then(data => {
      chatSessionId = data.session_id;
      chatMode = data.mode || 'messages';
      const modeLabel = chatMode === 'managed' ? 'Connected to HQ Agent' : 'Ask anything about your business';
      document.querySelector('.chat-header-sub').textContent = modeLabel;
      if (data.note) console.log('Chat session note:', data.note);
    })
    .catch(() => {
      chatSessionId = 'local';
      chatMode = 'messages';
    });
  }

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

    fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        message: text,
        history: chatHistory.slice(0, -1),
        session_id: chatSessionId,
        mode: chatMode
      })
    })
    .then(r => r.json())
    .then(data => {
      loader.remove();
      if (data.error) {
        appendMsg('assistant', 'Error: ' + data.error);
      } else {
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
