"""CORPORATE HQ — Claude Managed Agents Integration

This module defines Corporate HQ as a Claude Managed Agent.
One agent definition. Persistent sessions. 24/7 autonomous operation.

Each tier runs as its own scheduled session:
  - Tier 1 (Scout)     → Daily + weekends
  - Tier 2 (Process)   → After each Tier 1 run
  - Tier 3 (Analytics) → Nightly
  - Tier 4 (Alerts)    → Every 4 hours
  - Council            → On demand

Usage:
    python managed_agent.py create          # Create agent definition
    python managed_agent.py run <tier>      # Launch a session for a tier
    python managed_agent.py status          # Check agent + recent sessions
    python managed_agent.py council         # Trigger council session
    python managed_agent.py digest          # Trigger weekly digest session
"""

import os
import sys
import json
import time
import requests

# ── CONFIG ────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MANAGED_AGENTS_BASE = "https://api.anthropic.com/v1/managed-agents"
SESSIONS_BASE = "https://api.anthropic.com/v1/managed-agents/sessions"

BETA_HEADER = "managed-agents-2026-04-01"
MODEL = "claude-sonnet-4-6"

# Agent ID stored after first create — set via env or auto-saved
AGENT_ID_FILE = ".managed_agent_id"

# ── YOUR SHOP BASELINE (imported from strategy) ────────────────────────
try:
    from strategy import YOUR_SHOP
except ImportError:
    YOUR_SHOP = {
        "name": "Corporate HQ",
        "neighborhood": "South Park",
        "zip_code": "28210",
        "prices": {"Fade": 45, "Skin Fade": 55, "Haircut + Beard Combo": 65},
        "annual_gross": 42000,
    }

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────
CORPORATE_HQ_SYSTEM_PROMPT = f"""You are the Corporate HQ Intelligence Agent for a Charlotte, NC barbershop operation.

YOUR MISSION:
You are a 24/7 autonomous competitive intelligence system tracking the Charlotte barber market.
Your job is to gather data, detect threats, surface opportunities, and protect your operator's market position.

YOUR OPERATOR:
- Solo barber, South Park suite (zip 28210), 10 years experience
- Current pricing: Fade $45, Skin Fade $55, Combo $65
- Annual gross: ~$42,000 — transitioning to full shop ownership
- Goal: Open a full barbershop with chair rentals targeting $75K-$120K/year

YOUR PRIORITY ZIP CODES (minority-serving Charlotte neighborhoods):
28216 (Beatties Ford), 28208 (West Charlotte), 28206 (North Charlotte),
28215 (Eastway/Shamrock), 28212 (East Charlotte), 28202 (Uptown),
28203 (South End), 28205 (Plaza Midwood/NoDa), 28217 (Steele Creek), 28269 (University)

YOUR INTELLIGENCE DIRECTIVES:
1. Track competitor pricing for: Regular Haircut, Fade, Skin Fade, Taper Fade, Beard Trim,
   Hot Towel Shave, Line-Up, Haircut+Beard Combo, Kids Haircut
2. Monitor competitor ratings, review volume, and sentiment signals
3. Detect talent movements (barbers joining/leaving shops)
4. Flag price wars, flash promos, new shop openings
5. Generate weekly digest every Sunday
6. Surface site selection intelligence for the upcoming shop search

YOUR ETHICAL BOUNDARIES:
- Public data only (Google Business, Booksy, Yelp, public social)
- Never fabricate data — every data point must trace to a real source
- Community first: this intelligence informs strategy, not hostility
- Focus on Black-owned shops as primary competitive set

YOUR TOOLS:
You have access to web search for real-time market data. When you collect pricing or
review data, format it as structured JSON for warehouse ingestion. Always include
source URLs and timestamps.

OUTPUT FORMAT FOR DATA COLLECTION:
When collecting pricing data, output structured JSON:
{{
  "agent": "pricing_scout",
  "timestamp": "ISO-8601",
  "competitor": "Shop Name",
  "zip_code": "28XXX",
  "services": {{
    "Fade": 35.00,
    "Skin Fade": 45.00
  }},
  "source_url": "https://...",
  "confidence": "high|medium|low"
}}

When generating alerts, output:
{{
  "alert_type": "price_undercut|new_shop|talent_movement|reputation_shift|promo_detected",
  "severity": "critical|warning|info",
  "competitor": "Shop Name",
  "detail": "...",
  "recommended_action": "..."
}}

CURRENT COMPETITOR WATCHLIST (priority targets):
- No Grease (multiple CLT locations) — franchise benchmark
- Goodfellas Barbershop (28216) — 8 barbers, 302 reviews
- Gordon's Historic Barbershop (28204) — legacy shop, 478 reviews
- Da Lucky Spot (28208/28206) — expanding chain
- The Man Cave Barbershop (28208) — 12+ years, strong reviews
- Modern Classics, Fade Factory, Major League Barber Lounge

You are disciplined, thorough, and efficient. You deliver intelligence, not noise.
"""

# ── TIER TASK PROMPTS ──────────────────────────────────────────────────
TIER_TASKS = {
    "tier1": """Run the Tier 1 extraction cycle. Your tasks:

1. PRICING SCOUT: Search Google Business and Booksy for current fade prices at the top 10
   Charlotte barbershops on the watchlist. For each shop, collect all service prices you can find.
   Output structured JSON for each shop.

2. REVIEW HARVESTER: Check current Google ratings for the watchlist shops.
   Note any shops with recent rating changes, high review velocity (10+ new reviews this week),
   or clusters of negative reviews. Flag any reviews mentioning barber departures or new hires.

3. SHOP WATCHER: Check for any new barbershop openings in the priority zip codes (28208, 28215,
   28206, 28216). Search "new barbershop Charlotte [current month/year]" and scan Google Maps
   for recent listings. Flag anything within 2 miles of South Park (28210).

Output all findings as structured JSON. End with a summary of records collected and any
alerts generated.""",

    "tier2": """Run the Tier 2 processing cycle on data collected in the last 24 hours.

1. NORMALIZER: Review the pricing data collected in Tier 1. Standardize service names
   (e.g., "Taper" → "Taper Fade", "Lineup" → "Line-Up / Edge-Up"). Identify any
   obvious data errors (prices outside $10-$150 range). Output clean normalized records.

2. DELTA SPOTTER: Compare current prices to the baseline. Flag any price changes >10%.
   Calculate the current market average for Fade ($X) and Skin Fade ($X) across all
   tracked shops. Identify which shops are below market average (undercut risk) and
   above (premium positioning).

3. THREAT SCORER: Score each competitor on a 1-10 threat scale based on:
   - Price competitiveness (vs operator's $45 fade)
   - Review momentum (rating + velocity)
   - Proximity to operator's suite (28210)
   - Expansion signals

Output normalized data + threat scores + market averages.""",

    "tier3": """Run the Tier 3 analytics cycle.

1. COMPETITOR SCORECARDS: Generate a full scorecard for each watchlist shop:
   - Average pricing vs market
   - Rating + review count
   - Social presence score
   - Overall threat level (1-10)
   - Key intelligence notes

2. NEIGHBORHOOD RANKER: Rank the 10 priority zip codes by:
   - Average fade price (highest to lowest)
   - Market saturation (shops per sq mile estimate)
   - Growth signals (new shops, review velocity)
   - Opportunity score for potential shop location

3. SITE SELECTION INTELLIGENCE: Based on all collected data, identify the top 3 zip
   codes where opening a new shop would face the least direct competition while serving
   an underserved market. The operator's goal is to serve lower-income barbers in
   underserved neighborhoods while building sustainable revenue.

Output full analytics report in structured format.""",

    "tier4": """Run the Tier 4 alert cycle.

1. PRICE WAR SCAN: Check if any watchlist competitor is currently pricing their
   Fade below $40 or Skin Fade below $50. If yes, generate a critical alert with
   recommended counter-move (bundle deals, loyalty pricing, value-add services).

2. REPUTATION RADAR: Search for any Charlotte barbershop in the priority zips
   with 3+ negative Google reviews in the past 48 hours mentioning the same issue
   (wait times, no-shows, quality). This signals a vulnerability the operator can
   exploit by promoting reliability and appointment availability.

3. TALENT TRACKER: Search Instagram and Google for any Charlotte barber announcements
   about moving shops, "now booking at...", or shop closure signals. Flag any talent
   that serves the priority zip codes.

4. PROMO DETECTOR: Search for any current flash deals or promotions from watchlist
   shops ("first cut free", "% off", "walk-in special"). Assess threat level.

Output all alerts with severity ratings and recommended operator actions.""",

    "council": """Convene the Corporate HQ Council for a full strategic session.

You are five advisors, each with a distinct perspective. Review all available market
intelligence and give your assessment. The operator is preparing to sign a commercial
lease for their first full barbershop. The council vote will determine readiness.

STRATEGIST: Assess market positioning. Is now the right time to open? What does the
competitive landscape look like in the target zip codes?

COMPTROLLER: Review the financial position. At $42K current gross, what lease payment
can the operator afford? What revenue does the new shop need to generate in month 1
to be viable? Model three scenarios (conservative/moderate/optimistic).

INTEL OFFICER: What does the competitive intelligence tell us about the best location?
Which zip codes have the least saturation and most opportunity?

OPERATOR: What are the execution risks? What needs to be in place before signing a
lease? Flag the top 3 operational blockers.

BRAND ARCHITECT: How should the new shop be positioned vs existing competition?
What's the differentiated value proposition that justifies premium pricing?

END WITH A COUNCIL VOTE: Ready to sign a lease? Yes / No / More data needed.
Each advisor votes and gives a one-sentence rationale.""",

    "digest": """Generate the weekly intelligence digest for Corporate HQ.

Format as a professional briefing document:

## CORPORATE HQ — WEEKLY INTELLIGENCE DIGEST
### Week of [Current Date]

**MARKET PULSE**
- Charlotte barber market current average fade price: $X
- Market direction: Rising / Stable / Falling
- Key movement this week:

**TOP THREATS THIS WEEK**
(List top 3 competitive threats with severity and recommended response)

**OPPORTUNITIES SPOTTED**
(List 2-3 actionable opportunities: underserved areas, vulnerable competitors, talent available)

**PRICE INTELLIGENCE**
(Table: Top 10 shops, their fade price, rating, trend vs last week)

**TALENT MOVEMENTS**
(Any barber hires/departures detected)

**SITE SELECTION UPDATE**
(Top 3 recommended zip codes for new shop, with reasoning)

**COUNCIL STATUS**
(Are we closer to or further from lease-signing readiness vs last week?)

**NEXT WEEK WATCHLIST**
(3 things to monitor closely)

Keep it sharp. Bloomberg standard — facts, numbers, sources. No fluff."""
}

# ── API HELPERS ────────────────────────────────────────────────────────

def _headers():
    return {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": BETA_HEADER,
        "content-type": "application/json",
    }


def _save_agent_id(agent_id):
    with open(AGENT_ID_FILE, "w") as f:
        f.write(agent_id)
    print(f"Agent ID saved: {agent_id}")


def _load_agent_id():
    env_id = os.environ.get("CORPORATE_HQ_AGENT_ID")
    if env_id:
        return env_id
    if os.path.exists(AGENT_ID_FILE):
        with open(AGENT_ID_FILE) as f:
            return f.read().strip()
    return None


# ── AGENT MANAGEMENT ──────────────────────────────────────────────────

def create_agent():
    """Create the Corporate HQ agent definition on the Managed Agents platform."""
    print("Creating Corporate HQ Managed Agent...")

    payload = {
        "name": "Corporate HQ — Charlotte Barber Intelligence",
        "model": MODEL,
        "system_prompt": CORPORATE_HQ_SYSTEM_PROMPT,
        "tools": [
            {
                "type": "web_search_20250305",
                "name": "web_search"
            }
        ],
        "metadata": {
            "operator": "Will Coggins",
            "business": "Corporate HQ",
            "city": "Charlotte NC",
            "version": "1.0"
        }
    }

    resp = requests.post(
        f"{MANAGED_AGENTS_BASE}/agents",
        headers=_headers(),
        json=payload,
        timeout=30
    )

    if resp.status_code in (200, 201):
        data = resp.json()
        agent_id = data.get("id") or data.get("agent_id")
        if agent_id:
            _save_agent_id(agent_id)
            print(f"✓ Agent created: {agent_id}")
            return agent_id
        else:
            print(f"Response: {json.dumps(data, indent=2)}")
            return data
    else:
        print(f"Error {resp.status_code}: {resp.text}")
        return None


def get_agent_status(agent_id=None):
    """Get current agent status and recent sessions."""
    agent_id = agent_id or _load_agent_id()
    if not agent_id:
        print("No agent ID found. Run: python managed_agent.py create")
        return None

    resp = requests.get(
        f"{MANAGED_AGENTS_BASE}/agents/{agent_id}",
        headers=_headers(),
        timeout=15
    )

    if resp.status_code == 200:
        data = resp.json()
        print(f"\n{'═' * 60}")
        print(f"  CORPORATE HQ — AGENT STATUS")
        print(f"{'═' * 60}")
        print(f"  Agent ID:  {agent_id}")
        print(f"  Model:     {data.get('model', MODEL)}")
        print(f"  Status:    {data.get('status', 'Active')}")
        print(f"{'═' * 60}\n")
        return data
    else:
        print(f"Error {resp.status_code}: {resp.text}")
        return None


# ── SESSION LAUNCHER ───────────────────────────────────────────────────

def launch_session(tier, agent_id=None, wait_for_result=False):
    """Launch a Managed Agent session for a specific tier."""
    agent_id = agent_id or _load_agent_id()
    if not agent_id:
        print("No agent ID. Run: python managed_agent.py create")
        return None

    task = TIER_TASKS.get(tier)
    if not task:
        print(f"Unknown tier: {tier}. Valid: {list(TIER_TASKS.keys())}")
        return None

    print(f"\n{'─' * 60}")
    print(f"  Launching {tier.upper()} session...")
    print(f"  Agent: {agent_id}")
    print(f"{'─' * 60}")

    payload = {
        "agent_id": agent_id,
        "messages": [
            {"role": "user", "content": task}
        ],
        "metadata": {
            "tier": tier,
            "launched_by": "scheduler",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    }

    resp = requests.post(
        SESSIONS_BASE,
        headers=_headers(),
        json=payload,
        timeout=30
    )

    if resp.status_code in (200, 201, 202):
        data = resp.json()
        session_id = data.get("id") or data.get("session_id")
        print(f"  ✓ Session launched: {session_id}")
        print(f"  Status: {data.get('status', 'running')}")

        if wait_for_result:
            return poll_session(session_id)
        return session_id
    else:
        print(f"  Error {resp.status_code}: {resp.text}")
        return None


def poll_session(session_id, max_wait=300, interval=10):
    """Poll a session until it completes."""
    print(f"\nPolling session {session_id}...")
    waited = 0

    while waited < max_wait:
        resp = requests.get(
            f"{SESSIONS_BASE}/{session_id}",
            headers=_headers(),
            timeout=15
        )

        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "")

            if status in ("completed", "done", "succeeded"):
                print(f"✓ Session completed after {waited}s")
                messages = data.get("messages", [])
                for msg in reversed(messages):
                    if msg.get("role") == "assistant":
                        content = msg.get("content", "")
                        if isinstance(content, list):
                            return " ".join(
                                c.get("text", "") for c in content
                                if c.get("type") == "text"
                            )
                        return str(content)
                return str(data)

            elif status in ("failed", "error", "cancelled"):
                print(f"✗ Session {status}: {data.get('error', '')}")
                return None

            else:
                print(f"  [{waited}s] Status: {status}...")
                time.sleep(interval)
                waited += interval
        else:
            print(f"Poll error {resp.status_code}")
            time.sleep(interval)
            waited += interval

    print(f"Timed out after {max_wait}s")
    return None


def list_sessions(agent_id=None, limit=10):
    """List recent sessions for the agent."""
    agent_id = agent_id or _load_agent_id()
    if not agent_id:
        print("No agent ID found.")
        return []

    resp = requests.get(
        f"{SESSIONS_BASE}?agent_id={agent_id}&limit={limit}",
        headers=_headers(),
        timeout=15
    )

    if resp.status_code == 200:
        sessions = resp.json().get("sessions", [])
        print(f"\n{'─' * 70}")
        print(f"  RECENT SESSIONS ({len(sessions)} shown)")
        print(f"{'─' * 70}")
        print(f"  {'ID':36s} {'TIER':10s} {'STATUS':12s} {'STARTED':20s}")
        print(f"{'─' * 70}")
        for s in sessions:
            meta = s.get("metadata", {})
            tier = meta.get("tier", "unknown")
            started = s.get("created_at", "")[:19]
            print(f"  {s.get('id','')[:36]:36s} {tier:10s} {s.get('status',''):12s} {started}")
        print(f"{'─' * 70}\n")
        return sessions
    else:
        print(f"Error {resp.status_code}: {resp.text}")
        return []


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("""
Corporate HQ — Managed Agent CLI
══════════════════════════════════
Commands:
  create              Create the agent definition
  status              Check agent status + recent sessions
  run <tier>          Launch a session (tier1/tier2/tier3/tier4/council/digest)
  poll <session_id>   Poll a session until it completes
  sessions            List recent sessions

Examples:
  python managed_agent.py create
  python managed_agent.py run tier1
  python managed_agent.py run council
  python managed_agent.py status
        """)
        return

    cmd = sys.argv[1].lower()

    if cmd == "create":
        create_agent()
    elif cmd == "status":
        get_agent_status()
        list_sessions()
    elif cmd == "run":
        if len(sys.argv) < 3:
            print("Usage: python managed_agent.py run <tier>")
            print(f"Valid tiers: {list(TIER_TASKS.keys())}")
            return
        tier = sys.argv[2].lower()
        wait = "--wait" in sys.argv
        result = launch_session(tier, wait_for_result=wait)
        if wait and result:
            print(f"\n{'═' * 60}")
            print("SESSION RESULT:")
            print('═' * 60)
            print(result)
    elif cmd == "poll":
        if len(sys.argv) < 3:
            print("Usage: python managed_agent.py poll <session_id>")
            return
        result = poll_session(sys.argv[2])
        if result:
            print(result)
    elif cmd == "sessions":
        list_sessions()
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
