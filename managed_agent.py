"""Managed Agent — Anthropic SDK v0.92.0+

Bridge between the managed agent and Corporate HQ's DuckDB warehouse.

One-time setup: creates agent + environment with custom warehouse tools.
Per-run: creates session, streams events, executes tool calls locally against
DuckDB, sends results back, and loops until the agent is done.

Correct SDK method paths (beta namespace):
  client.beta.environments.create()
  client.beta.agents.create()
  client.beta.sessions.create(agent=AGENT_ID, environment_id=ENV_ID)
  client.beta.sessions.events.send(session_id=..., events=[...])
  client.beta.sessions.events.stream(session_id=...)
"""

import json
import os
import traceback
import logging
import anthropic

log = logging.getLogger("managed_agent")


# ════════════════════════════════════════════════════════════════════════
#  WAREHOUSE TOOL DEFINITIONS — custom tools the agent can call
# ════════════════════════════════════════════════════════════════════════

WAREHOUSE_TABLES = [
    "competitors", "competitor_moves", "competitor_social", "competitor_products",
    "competitor_financials", "competitor_scores", "price_history", "review_snapshots",
    "barbers", "barber_specialties", "neighborhoods", "platform_profiles",
    "platform_solo_barbers", "alerts_log", "agent_runs",
]

CUSTOM_TOOLS = [
    {
        "type": "custom",
        "name": "query_warehouse",
        "description": (
            "Run a read-only SQL query against the Corporate HQ DuckDB warehouse. "
            "Contains competitor data, pricing, reviews, social media, barber profiles, "
            "agent logs, and alert history. Use DuckDB SQL syntax. Only SELECT/WITH queries allowed. "
            "Results are capped at 50 rows."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A SQL SELECT or WITH query using DuckDB syntax"
                }
            },
            "required": ["sql"]
        },
    },
    {
        "type": "custom",
        "name": "list_tables",
        "description": (
            "List all warehouse tables with their current row counts. "
            "Call this first to see what data is available before writing queries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "type": "custom",
        "name": "read_agent_logs",
        "description": (
            "Read recent agent run logs. Shows which agents ran, when they ran, "
            "their completion status, and how many records they processed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Filter by agent name (optional, uses fuzzy ILIKE match)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max rows to return (default 10)"
                },
            },
        },
    },
    {
        "type": "custom",
        "name": "run_agent_pipeline",
        "description": (
            "Run a local agent tier pipeline against the warehouse. "
            "tier1=scouts (pricing, reviews, social, shops, platforms), "
            "tier2=processing (normalize, enrich, detect changes), "
            "tier3=analytics (scorecards, threat levels), "
            "tier4=alerts (price wars, reputation, talent movement), "
            "digest=weekly summary report. "
            "Returns the list of agents that ran and their results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tier": {
                    "type": "string",
                    "enum": ["tier1", "tier2", "tier3", "tier4", "digest"],
                    "description": "Which agent tier to run"
                }
            },
            "required": ["tier"]
        },
    },
]


# ════════════════════════════════════════════════════════════════════════
#  LOCAL TOOL EXECUTION — runs against DuckDB on our server
# ════════════════════════════════════════════════════════════════════════

def _execute_tool(tool_name, tool_input):
    """Execute a custom tool locally and return a result dict."""
    from warehouse.db import get_connection

    if tool_name == "query_warehouse":
        sql = (tool_input.get("sql") or "").strip()
        upper = sql.upper()
        if not upper.startswith("SELECT") and not upper.startswith("WITH"):
            return {"error": "Only SELECT/WITH queries are allowed."}
        try:
            con = get_connection()
            cur = con.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            con.close()
            if len(rows) > 50:
                return {"rows": rows[:50], "total": len(rows), "note": "Truncated to 50 rows."}
            return {"rows": rows, "count": len(rows)}
        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}

    elif tool_name == "list_tables":
        try:
            con = get_connection()
            results = []
            for table in WAREHOUSE_TABLES:
                try:
                    count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                except Exception:
                    count = 0
                results.append({"table": table, "rows": count})
            con.close()
            return {"tables": results}
        except Exception as e:
            return {"error": f"Failed to list tables: {str(e)}"}

    elif tool_name == "read_agent_logs":
        agent_name = tool_input.get("agent_name", "")
        limit = tool_input.get("limit", 10)
        try:
            con = get_connection()
            if agent_name:
                cur = con.execute(
                    "SELECT * FROM agent_runs WHERE agent_name ILIKE ? ORDER BY started_at DESC LIMIT ?",
                    [f"%{agent_name}%", limit],
                )
            else:
                cur = con.execute(
                    "SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT ?", [limit]
                )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            con.close()
            return {"runs": rows, "count": len(rows)}
        except Exception as e:
            return {"runs": [], "count": 0, "error": str(e)}

    elif tool_name == "run_agent_pipeline":
        tier = tool_input.get("tier", "")
        try:
            from agents.runner import run_tier, run_agents
            if tier == "digest":
                results = run_agents(["weekly_digest"])
            else:
                results = run_tier(tier)
            return {
                "tier": tier,
                "agents_run": list(results.keys()),
                "results": {k: str(v) for k, v in results.items()},
            }
        except Exception as e:
            return {"error": f"Pipeline '{tier}' failed: {str(e)}"}

    return {"error": f"Unknown tool: {tool_name}"}


# ════════════════════════════════════════════════════════════════════════
#  AGENT SYSTEM PROMPT — includes full warehouse schema
# ════════════════════════════════════════════════════════════════════════

AGENT_SYSTEM_PROMPT = """You are the Corporate HQ Intelligence Agent for a Charlotte, NC barbershop operation.

You are talking to William, the owner. He charges $40-65 per cut and is building a competitive intelligence operation to prepare for expanding from a suite to a full shop.

YOUR ROLE:
- Answer questions about his business using real data from the warehouse
- Speak in plain, direct business language — no developer jargon, no corporate buzzwords
- If the data does not exist yet, say so honestly. Never make up numbers.
- Keep answers concise and actionable
- Always use your warehouse tools to pull real data before answering data questions

YOUR OPERATOR:
- Solo barber, South Park suite (zip 28210), 10 years experience
- Current pricing: Fade $45, Skin Fade $55, Combo $65
- Annual gross: ~$42,000 — transitioning to full shop ownership
- Goal: Open a full barbershop with chair rentals targeting $75K-$120K/year

PRIORITY ZIP CODES (minority-serving Charlotte neighborhoods):
28216 (Beatties Ford), 28208 (West Charlotte), 28206 (North Charlotte),
28215 (Eastway/Shamrock), 28212 (East Charlotte), 28202 (Uptown),
28203 (South End), 28205 (Plaza Midwood/NoDa), 28217 (Steele Creek), 28269 (University)

WAREHOUSE SCHEMA (DuckDB — use query_warehouse tool):
- competitors: competitor_id, company_name, industry, hq_location, zip_code, neighborhood, ownership_type, primary_clientele, founded_year, employee_count, business_model, status
- price_history: id, competitor_id, service_name, price, recorded_at, source
- review_snapshots: id, competitor_id, platform, rating, review_text, reviewer_name, review_date, sentiment_score, keywords, collected_at
- competitor_social: id, competitor_id, platform, followers, engagement_rate, snapshot_date
- competitor_moves: move_id, competitor_id, move_date, move_type, description, source_url, impact_rating
- competitor_scores: id, competitor_id, score_type, score, components, scored_at
- competitor_products: product_id, competitor_id, product_name, category, pricing_model, price_range
- competitor_financials: id, competitor_id, period, revenue_estimate, funding_total
- barbers: barber_id, competitor_id, name, instagram_handle, specialties, seniority, status, first_seen, last_seen
- barber_specialties: id, barber_id, specialty, skill_level, source
- neighborhoods: neighborhood_id, name, zip_code, demographics_notes, market_saturation
- platform_profiles: id, competitor_id, platform, profile_url, rating, review_count, is_verified, accepts_online_booking
- platform_solo_barbers: id, barber_name, platform, profile_url, zip_code, neighborhood, rating, review_count, fade_price, haircut_price, beard_price, combo_price, ownership_type, status
- alerts_log: alert_id, alert_type, severity, competitor_id, title, detail, data_json, acknowledged, created_at
- agent_runs: run_id, agent_name, started_at, finished_at, status, records_processed, notes

SQL TIPS:
- Use QUALIFY ROW_NUMBER() OVER (...) = 1 for latest records per group
- Use ILIKE for case-insensitive text matching
- Common service names: Fade, Skin Fade, Beard Trim, Haircut, Combo, Line Up, Kids Cut, Hot Towel Shave
- score_type values: 'threat', 'hotness', 'neighborhood_rank'
- move_type values: 'New Location', 'Closure', 'Expansion', 'Rebrand', 'Talent Movement', 'data_sync'
- Always call list_tables first if you are unsure what data exists"""


# ════════════════════════════════════════════════════════════════════════
#  STREAM HELPER — handles requires_action loop for custom tools
# ════════════════════════════════════════════════════════════════════════

def _stream_with_tools(client, session_id, initial_events, max_rounds=10):
    """Stream a managed agent session, executing custom tools locally.

    Custom tool calls arrive as standalone `agent.custom_tool_use` events
    (NOT as blocks inside agent.message — those are text-only). When the
    session goes idle with stop_reason `requires_action`, we:
      1. Execute each pending tool locally against DuckDB
      2. Send results back as `user.custom_tool_result` events, referencing
         the custom_tool_use event id, with content as a list of text blocks
      3. Open a new stream to collect the agent's next response
    Repeats until the session idles with end_turn or hits max_rounds.
    """
    reply_parts = []
    events_to_send = initial_events

    for round_num in range(max_rounds):
        pending_tool_calls = []
        needs_another_round = False

        with client.beta.sessions.events.stream(session_id=session_id) as stream:
            client.beta.sessions.events.send(
                session_id=session_id,
                events=events_to_send,
            )

            for event in stream:
                etype = getattr(event, "type", "")

                if etype == "agent.message":
                    # Content is a list of text blocks only
                    for block in (event.content or []):
                        if getattr(block, "text", None):
                            reply_parts.append(block.text)

                elif etype == "agent.custom_tool_use":
                    pending_tool_calls.append({
                        "event_id": event.id,
                        "name": event.name,
                        "input": event.input or {},
                    })

                elif etype == "session.status_idle":
                    sr = getattr(event, "stop_reason", None)
                    if getattr(sr, "type", "") == "requires_action" and pending_tool_calls:
                        needs_another_round = True
                    break

                elif etype == "session.status_terminated":
                    break

                elif etype == "session.error":
                    err = getattr(event, "error", None)
                    log.error(f"Session error: {err}")
                    break

        if not needs_another_round:
            break

        result_events = []
        for tc in pending_tool_calls:
            log.info(f"Tool call [{round_num+1}]: {tc['name']}")
            result = _execute_tool(tc["name"], tc["input"])
            result_events.append({
                "type": "user.custom_tool_result",
                "custom_tool_use_id": tc["event_id"],
                "content": [{"type": "text", "text": json.dumps(result, default=str)}],
                "is_error": isinstance(result, dict) and "error" in result,
            })
        events_to_send = result_events

    return "".join(reply_parts)


# ════════════════════════════════════════════════════════════════════════
#  ONE-TIME SETUP — run once, save the IDs to Railway env vars
# ════════════════════════════════════════════════════════════════════════

def setup_managed_agent():
    """Create the agent and environment once. Returns (agent_id, env_id, error).

    Run this once, then save the IDs as Railway env vars:
      CORPORATE_HQ_AGENT_ID=agent_...
      CORPORATE_HQ_ENV_ID=env_...
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None, None, "ANTHROPIC_API_KEY not set"

    client = anthropic.Anthropic(api_key=api_key)

    try:
        environment = client.beta.environments.create(
            name="corporate-hq-env",
            config={
                "type": "cloud",
                "networking": {"type": "unrestricted"},
            },
        )
        env_id = environment.id

        agent = client.beta.agents.create(
            name="Corporate HQ Agent",
            model="claude-sonnet-4-6",
            system=AGENT_SYSTEM_PROMPT,
            tools=[
                {"type": "agent_toolset_20260401", "default_config": {"enabled": True}},
            ] + CUSTOM_TOOLS,
        )
        agent_id = agent.id

        return agent_id, env_id, None

    except Exception as e:
        traceback.print_exc()
        return None, None, str(e)


def update_managed_agent(agent_id: str = None):
    """Apply the current system prompt + custom tools to an existing agent.

    Agents are persistent, versioned objects — tools set at creation stick
    until updated. Run this after changing AGENT_SYSTEM_PROMPT or CUSTOM_TOOLS
    so the live agent picks up the new config. New sessions then use the
    updated version automatically.

    Returns (new_version, error).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    agent_id = agent_id or os.environ.get("CORPORATE_HQ_AGENT_ID", "")

    if not api_key:
        return None, "ANTHROPIC_API_KEY not set"
    if not agent_id:
        return None, "CORPORATE_HQ_AGENT_ID not set"

    client = anthropic.Anthropic(api_key=api_key)

    try:
        current = client.beta.agents.retrieve(agent_id)
        updated = client.beta.agents.update(
            agent_id=agent_id,
            version=current.version,
            system=AGENT_SYSTEM_PROMPT,
            tools=[
                {"type": "agent_toolset_20260401", "default_config": {"enabled": True}},
            ] + CUSTOM_TOOLS,
        )
        return updated.version, None

    except Exception as e:
        traceback.print_exc()
        return None, str(e)


# ════════════════════════════════════════════════════════════════════════
#  PER-RUN — called each time an agent task is triggered
# ════════════════════════════════════════════════════════════════════════

def run_agent_task(task: str, agent_id: str = None, env_id: str = None) -> dict:
    """Create a session, send the task, handle tool calls, return the result.

    Args:
        task: The user message / task description to send.
        agent_id: Agent ID (falls back to CORPORATE_HQ_AGENT_ID env var).
        env_id: Environment ID (falls back to CORPORATE_HQ_ENV_ID env var).

    Returns:
        {"reply": "...", "mode": "managed", "session_id": "..."} on success
        {"error": "..."} on failure
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    agent_id = agent_id or os.environ.get("CORPORATE_HQ_AGENT_ID", "")
    env_id = env_id or os.environ.get("CORPORATE_HQ_ENV_ID", "")

    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not configured."}
    if not agent_id:
        return {"error": "CORPORATE_HQ_AGENT_ID not set. Run /api/setup-agent first."}
    if not env_id:
        return {"error": "CORPORATE_HQ_ENV_ID not set. Run /api/setup-agent first."}

    client = anthropic.Anthropic(api_key=api_key)

    try:
        session = client.beta.sessions.create(
            agent=agent_id,
            environment_id=env_id,
        )

        reply = _stream_with_tools(client, session.id, [{
            "type": "user.message",
            "content": [{"type": "text", "text": task}],
        }])

        if not reply:
            reply = "Agent completed the task but produced no text output."

        return {"reply": reply, "mode": "managed", "session_id": session.id}

    except Exception as e:
        traceback.print_exc()
        return {"error": f"Managed agent failed: {str(e)}"}


# ════════════════════════════════════════════════════════════════════════
#  CHAT SESSION — for the embedded chat widget (persistent session)
# ════════════════════════════════════════════════════════════════════════

def create_chat_session(agent_id: str = None, env_id: str = None) -> dict:
    """Create a managed agent session for the chat widget.

    Returns:
        {"session_id": "sess_...", "mode": "managed"} on success
        {"session_id": "local", "mode": "messages", "note": "..."} on fallback
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    agent_id = agent_id or os.environ.get("CORPORATE_HQ_AGENT_ID", "")
    env_id = env_id or os.environ.get("CORPORATE_HQ_ENV_ID", "")

    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not configured."}

    if not agent_id or not env_id:
        reason = []
        if not agent_id:
            reason.append("CORPORATE_HQ_AGENT_ID not set")
        if not env_id:
            reason.append("CORPORATE_HQ_ENV_ID not set")
        return {"session_id": "local", "mode": "messages", "note": "; ".join(reason)}

    client = anthropic.Anthropic(api_key=api_key)

    try:
        session = client.beta.sessions.create(
            agent=agent_id,
            environment_id=env_id,
        )
        return {"session_id": session.id, "mode": "managed"}

    except AttributeError as e:
        return {"session_id": "local", "mode": "messages",
                "note": f"SDK lacks managed agents API: {str(e)}"}
    except Exception as e:
        traceback.print_exc()
        return {"session_id": "local", "mode": "messages",
                "note": f"Managed agent failed: {str(e)}"}


def send_chat_message(session_id: str, user_message: str) -> dict:
    """Send a message to an existing managed agent chat session.

    Uses stream-first pattern with custom tool handling:
    opens SSE stream, sends message, executes any custom tool calls
    locally against DuckDB, sends results back, and loops until done.

    Returns:
        {"reply": "...", "mode": "managed"} on success
        {"error": "..."} on failure
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not configured."}

    client = anthropic.Anthropic(api_key=api_key)

    try:
        reply = _stream_with_tools(client, session_id, [{
            "type": "user.message",
            "content": [{"type": "text", "text": user_message}],
        }])

        if not reply:
            reply = "I processed your request but had no text response. Try asking again."

        return {"reply": reply, "mode": "managed"}

    except Exception as e:
        traceback.print_exc()
        return {"error": f"Managed agent chat failed: {str(e)}"}


# ════════════════════════════════════════════════════════════════════════
#  SCHEDULER INTERFACE — used by scheduler.py
# ════════════════════════════════════════════════════════════════════════

def _load_agent_id():
    """Load agent ID from environment. Used by the scheduler for status checks."""
    return os.environ.get("CORPORATE_HQ_AGENT_ID", "")


TIER_TASKS = {
    "tier1": (
        "Run a Tier 1 scout cycle. Use list_tables to check data availability, "
        "then query_warehouse to assess current competitor coverage — how many "
        "competitors are tracked, latest pricing data age, review counts, and "
        "social follower data. Identify any gaps or stale data. Report findings."
    ),
    "tier2": (
        "Run a Tier 2 processing cycle. Use run_agent_pipeline with tier2 to "
        "normalize service names, enrich barber profiles, detect competitor "
        "changes, and analyze platform adoption. Then query the warehouse to "
        "confirm what was processed. Report results."
    ),
    "tier3": (
        "Run a Tier 3 analytics cycle. Use run_agent_pipeline with tier3 to "
        "calculate competitor scorecards and threat levels. Then use "
        "query_warehouse to pull updated scores from competitor_scores and "
        "report the top threats and any significant score changes."
    ),
    "tier4": (
        "Run a Tier 4 alert scan. Use run_agent_pipeline with tier4 to check "
        "for price wars, reputation shifts, and talent movement. Then query "
        "alerts_log for any new alerts generated today and summarize what "
        "needs William's attention."
    ),
    "digest": (
        "Generate the weekly intelligence digest. Use run_agent_pipeline with "
        "digest to create the full weekly summary. Then use query_warehouse to "
        "pull this week's key metrics: price changes, new competitors, review "
        "trends, social changes, and alert counts. Format a clear briefing "
        "for William."
    ),
}


def launch_session(tier: str) -> str:
    """Launch a managed agent session for a scheduled tier run.

    Called by scheduler.py on each cron trigger. Creates a new session,
    sends the tier-specific task, handles all tool calls, and returns
    the session ID on success or None on failure.
    """
    task = TIER_TASKS.get(tier)
    if not task:
        log.warning(f"Unknown tier requested: {tier}")
        return None

    log.info(f"Launching session for {tier}...")
    result = run_agent_task(task)

    if "error" in result:
        log.error(f"Session failed for {tier}: {result['error']}")
        return None

    session_id = result.get("session_id")
    log.info(f"Session completed for {tier}: {session_id}")
    return session_id
