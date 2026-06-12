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
    {
        "type": "custom",
        "name": "record_prices",
        "description": (
            "Write competitor service prices into the warehouse (price_history table). "
            "Use this after web-searching current barbershop prices in Charlotte NC. "
            "The competitor is matched by name (created if new). One call per shop. "
            "Automatically flags undercuts and premium tiers, and logs a pricing_scout "
            "run to agent_runs. Only record real prices you actually found — never invent numbers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "competitor_name": {
                    "type": "string",
                    "description": "Barbershop name as found in the search results"
                },
                "zip_code": {
                    "type": "string",
                    "description": "Shop zip code if known (used when creating a new competitor)"
                },
                "prices": {
                    "type": "object",
                    "description": "Map of service name to price in USD, e.g. {\"Fade\": 45, \"Beard Trim\": 20}",
                    "additionalProperties": {"type": "number"}
                },
                "source": {
                    "type": "string",
                    "description": "Where the prices came from (e.g. 'Booksy', 'Google', a website URL)"
                },
            },
            "required": ["competitor_name", "prices"]
        },
    },
    {
        "type": "custom",
        "name": "record_reviews",
        "description": (
            "Write customer reviews into the warehouse (review_snapshots table). "
            "Use this after web-searching recent Charlotte barbershop reviews. "
            "The competitor is matched by name (created if new). Sentiment and intel "
            "keywords are scored automatically, and a review_harvester run is logged "
            "to agent_runs. Only record real reviews you actually found."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "competitor_name": {
                    "type": "string",
                    "description": "Barbershop name the reviews belong to"
                },
                "zip_code": {
                    "type": "string",
                    "description": "Shop zip code if known"
                },
                "reviews": {
                    "type": "array",
                    "description": "Reviews found via web search",
                    "items": {
                        "type": "object",
                        "properties": {
                            "platform": {"type": "string", "description": "Google, Yelp, Facebook, or Booksy"},
                            "rating": {"type": "number", "description": "Star rating 1-5"},
                            "review_text": {"type": "string"},
                            "reviewer_name": {"type": "string"},
                            "review_date": {"type": "string", "description": "YYYY-MM-DD if known"},
                        },
                        "required": ["platform", "review_text"]
                    }
                },
            },
            "required": ["competitor_name", "reviews"]
        },
    },
    {
        "type": "custom",
        "name": "record_social",
        "description": (
            "Write social media follower snapshots into the warehouse (competitor_social "
            "table). Use this after web-searching Instagram/TikTok/Facebook presence of "
            "Charlotte barbershops. Logs a social_listener run to agent_runs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "competitor_name": {
                    "type": "string",
                    "description": "Barbershop name the snapshots belong to"
                },
                "snapshots": {
                    "type": "array",
                    "description": "One entry per platform",
                    "items": {
                        "type": "object",
                        "properties": {
                            "platform": {"type": "string", "description": "Instagram, TikTok, Facebook, or X/Twitter"},
                            "followers": {"type": "integer"},
                            "engagement_rate": {"type": "number", "description": "Optional, as a percentage"},
                        },
                        "required": ["platform", "followers"]
                    }
                },
            },
            "required": ["competitor_name", "snapshots"]
        },
    },
    {
        "type": "custom",
        "name": "record_shop_intel",
        "description": (
            "Record shop status intel: a newly discovered competitor, or a status change "
            "(opening, closure, expansion, remodel, rebrand) for a known one. Writes to "
            "competitors / competitor_moves and raises an alert. Logs a shop_watcher run "
            "to agent_runs. Use after web-searching Charlotte barbershop news."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["new_competitor", "status_change"],
                    "description": "new_competitor = shop not yet tracked; status_change = update on a tracked shop"
                },
                "company_name": {"type": "string"},
                "change_type": {
                    "type": "string",
                    "description": "For status_change: New Location, Closure, Remodel, Hours Change, Ownership Change, Rebrand, or Expansion"
                },
                "description": {"type": "string", "description": "What happened, with specifics"},
                "zip_code": {"type": "string"},
                "neighborhood": {"type": "string"},
                "shop_type": {"type": "string", "description": "e.g. Full Shop, Suite, Mobile"},
                "source_url": {"type": "string"},
            },
            "required": ["kind", "company_name"]
        },
    },
    {
        "type": "custom",
        "name": "record_platform_presence",
        "description": (
            "Write booking-platform presence into the warehouse: shop profiles go to "
            "platform_profiles, solo barbers in target zips go to platform_solo_barbers. "
            "Use after web-searching Booksy/Vagaro/StyleSeat/TheCut/Squire for Charlotte "
            "barbers. Logs a platform_scout run to agent_runs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "profiles": {
                    "type": "array",
                    "description": "Shop profiles found on booking platforms",
                    "items": {
                        "type": "object",
                        "properties": {
                            "competitor_name": {"type": "string"},
                            "platform": {"type": "string", "description": "Booksy, Vagaro, StyleSeat, TheCut, or Squire"},
                            "rating": {"type": "number"},
                            "review_count": {"type": "integer"},
                            "profile_url": {"type": "string"},
                            "accepts_online_booking": {"type": "boolean"},
                        },
                        "required": ["competitor_name", "platform"]
                    }
                },
                "solo_barbers": {
                    "type": "array",
                    "description": "Independent solo barbers found in target zip codes",
                    "items": {
                        "type": "object",
                        "properties": {
                            "barber_name": {"type": "string"},
                            "platform": {"type": "string"},
                            "zip_code": {"type": "string"},
                            "neighborhood": {"type": "string"},
                            "rating": {"type": "number"},
                            "review_count": {"type": "integer"},
                            "profile_url": {"type": "string"},
                            "fade_price": {"type": "number"},
                            "haircut_price": {"type": "number"},
                            "beard_price": {"type": "number"},
                            "combo_price": {"type": "number"},
                            "instagram_handle": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                        "required": ["barber_name", "platform", "zip_code"]
                    }
                },
            },
        },
    },
]


# ════════════════════════════════════════════════════════════════════════
#  LOCAL TOOL EXECUTION — runs against DuckDB on our server
# ════════════════════════════════════════════════════════════════════════

# William's own prices and location — feed scout alert logic
# (undercut detection in PricingScout, proximity warnings in ShopWatcher)
YOUR_PRICES = {"Fade": 45.0, "Skin Fade": 55.0, "Haircut + Beard Combo": 65.0}
YOUR_ZIP = "28210"


def _resolve_competitor(name, zip_code=None, neighborhood=None):
    """Match a competitor by name (ILIKE), creating a record if not found."""
    from warehouse.db import get_connection
    con = get_connection()
    row = con.execute(
        "SELECT competitor_id FROM competitors WHERE company_name ILIKE ?",
        [f"%{name}%"],
    ).fetchone()
    con.close()
    if row:
        return row[0]
    from warehouse.competitors import add_competitor
    return add_competitor(
        name,
        industry="Barbershop",
        zip_code=zip_code,
        neighborhood=neighborhood,
        business_model="Service",
        notes="Discovered by managed agent web search",
    )


def _record_with_scout(scout_cls, work):
    """Run `work(scout)` inside a full run lifecycle so agent_runs gets a row.

    The scout's records_processed counter tracks every row written, and
    _finish_run persists it to agent_runs together with a summary note —
    this is the audit trail proving the scout actually collected data.
    """
    scout = scout_cls()
    scout._start_run()
    try:
        summary = work(scout)
        scout._finish_run("completed", summary)
        return {
            "status": "completed",
            "run_id": scout.run_id,
            "records_written": scout.records_processed,
            "summary": summary,
        }
    except Exception as e:
        scout._finish_run("failed", str(e))
        return {
            "error": str(e),
            "run_id": scout.run_id,
            "records_written": scout.records_processed,
        }


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

    elif tool_name == "record_prices":
        from agents.pricing_scout import PricingScout
        name = (tool_input.get("competitor_name") or "").strip()
        prices = tool_input.get("prices") or {}
        if not name or not prices:
            return {"error": "competitor_name and a non-empty prices object are required."}

        def work(scout):
            cid = _resolve_competitor(name, tool_input.get("zip_code"))
            clean = {}
            for svc, price in prices.items():
                try:
                    clean[svc] = float(price)
                except (TypeError, ValueError):
                    continue
            scout.bulk_record_prices(
                cid, clean, source=tool_input.get("source") or "managed agent web search"
            )
            return f"Recorded {len(clean)} prices for {name}"

        return _record_with_scout(lambda: PricingScout(your_prices=YOUR_PRICES), work)

    elif tool_name == "record_reviews":
        from agents.review_harvester import ReviewHarvester
        name = (tool_input.get("competitor_name") or "").strip()
        reviews = tool_input.get("reviews") or []
        if not name or not reviews:
            return {"error": "competitor_name and a non-empty reviews list are required."}

        def work(scout):
            cid = _resolve_competitor(name, tool_input.get("zip_code"))
            for r in reviews:
                r.setdefault("platform", "Google")
                if r.get("rating") is not None:
                    try:
                        r["rating"] = float(r["rating"])
                    except (TypeError, ValueError):
                        r["rating"] = None
            scout.bulk_ingest(cid, reviews)
            return f"Ingested {len(reviews)} reviews for {name}"

        return _record_with_scout(ReviewHarvester, work)

    elif tool_name == "record_social":
        from agents.social_listener import SocialListener
        name = (tool_input.get("competitor_name") or "").strip()
        snapshots = tool_input.get("snapshots") or []
        if not name or not snapshots:
            return {"error": "competitor_name and a non-empty snapshots list are required."}

        def work(scout):
            cid = _resolve_competitor(name)
            for snap in snapshots:
                try:
                    followers = int(snap.get("followers") or 0)
                except (TypeError, ValueError):
                    followers = 0
                scout.record_social_snapshot(
                    cid,
                    snap.get("platform") or "Instagram",
                    followers,
                    snap.get("engagement_rate"),
                )
            return f"Recorded {len(snapshots)} social snapshots for {name}"

        return _record_with_scout(SocialListener, work)

    elif tool_name == "record_shop_intel":
        from agents.shop_watcher import ShopWatcher
        kind = tool_input.get("kind")
        name = (tool_input.get("company_name") or "").strip()
        if not name:
            return {"error": "company_name is required."}

        def work(scout):
            if kind == "new_competitor":
                con = get_connection()
                existing = con.execute(
                    "SELECT competitor_id FROM competitors WHERE company_name ILIKE ?",
                    [f"%{name}%"],
                ).fetchone()
                con.close()
                if existing:
                    return f"{name} is already tracked (competitor_id={existing[0]}); nothing recorded"
                cid = scout.record_new_competitor(
                    name,
                    zip_code=tool_input.get("zip_code"),
                    neighborhood=tool_input.get("neighborhood"),
                    shop_type=tool_input.get("shop_type"),
                    source_url=tool_input.get("source_url"),
                )
                return f"New competitor recorded: {name} (competitor_id={cid})"
            else:
                cid = _resolve_competitor(
                    name, tool_input.get("zip_code"), tool_input.get("neighborhood")
                )
                scout.record_status_change(
                    cid,
                    tool_input.get("change_type") or "Expansion",
                    tool_input.get("description") or "",
                    source_url=tool_input.get("source_url"),
                )
                return f"Status change recorded for {name}: {tool_input.get('change_type')}"

        return _record_with_scout(lambda: ShopWatcher(your_zip=YOUR_ZIP), work)

    elif tool_name == "record_platform_presence":
        from agents.platform_scout import PlatformScout
        profiles = tool_input.get("profiles") or []
        solo_barbers = tool_input.get("solo_barbers") or []
        if not profiles and not solo_barbers:
            return {"error": "Provide at least one of profiles or solo_barbers."}

        def work(scout):
            for p in profiles:
                cid = _resolve_competitor(p.get("competitor_name") or "Unknown")
                scout.record_platform_profile(
                    competitor_id=cid,
                    platform=p.get("platform") or "Booksy",
                    rating=p.get("rating"),
                    review_count=p.get("review_count") or 0,
                    profile_url=p.get("profile_url"),
                    accepts_online_booking=p.get("accepts_online_booking", True),
                )
            for b in solo_barbers:
                scout.record_solo_barber(
                    barber_name=b.get("barber_name") or "Unknown",
                    platform=b.get("platform") or "Booksy",
                    zip_code=b.get("zip_code") or "",
                    neighborhood=b.get("neighborhood"),
                    rating=b.get("rating"),
                    review_count=b.get("review_count") or 0,
                    profile_url=b.get("profile_url"),
                    fade_price=b.get("fade_price"),
                    haircut_price=b.get("haircut_price"),
                    beard_price=b.get("beard_price"),
                    combo_price=b.get("combo_price"),
                    instagram_handle=b.get("instagram_handle"),
                    notes=b.get("notes"),
                )
            return (
                f"Recorded {len(profiles)} platform profiles and "
                f"{len(solo_barbers)} solo barbers"
            )

        return _record_with_scout(PlatformScout, work)

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
- Always call list_tables first if you are unsure what data exists

DATA COLLECTION (Tier 1 scout cycles):
You are the data collector. Use your web search tool to find current, real
Charlotte barbershop intel, then write it to the warehouse with these tools:
- record_prices — service prices found on Booksy/Google/shop sites
- record_reviews — customer reviews with rating, text, and platform
- record_social — Instagram/TikTok/Facebook follower snapshots
- record_shop_intel — new shops, closures, expansions, relocations
- record_platform_presence — booking-platform profiles and solo barbers
Each call logs an agent run with the row count, so the audit trail in
agent_runs proves what was collected. Record ONLY data you actually found
in search results. If a search comes up empty, say so — never fabricate."""


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
        "Run a Tier 1 scout cycle: collect FRESH competitive data with web search "
        "and write it to the warehouse with the record tools.\n"
        "1. PRICING: web-search current service prices at Charlotte NC barbershops "
        "(Booksy listings, Google Business, shop websites — fades, haircuts, beard "
        "trims, combos). Record every real price you find via record_prices, one "
        "call per shop. Target at least 10-20 price observations total.\n"
        "2. REVIEWS: web-search recent customer reviews of Charlotte barbershops "
        "(Google, Yelp, Booksy). Record them via record_reviews with rating, text, "
        "and platform.\n"
        "3. SOCIAL: web-search Instagram/TikTok presence of Charlotte barbershops "
        "and record follower counts via record_social.\n"
        "4. SHOPS: web-search for newly opened, closed, relocating, or expanding "
        "Charlotte barbershops and record findings via record_shop_intel.\n"
        "5. PLATFORMS: web-search Booksy/StyleSeat/Vagaro for Charlotte barber "
        "profiles and solo barbers in the priority zips; record via "
        "record_platform_presence.\n"
        "Prioritize the priority zip codes. Only record data you actually found in "
        "search results — never invent numbers. Finish with read_agent_logs and "
        "query_warehouse to confirm rows were written, then report what was "
        "collected and any gaps."
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
