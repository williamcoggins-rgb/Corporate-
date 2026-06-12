"""THE DOCTRINE OF STRATEGIC INTELLIGENCE

A Unified System for Strategy, Power, and Execution.

This is the operating doctrine that governs the strategy section.
Three disciplines fused into one machine:

  1. Strategic Management     — how organizations decide direction
  2. Strategic Business Mgmt  — how strategy is analyzed, chosen, executed
  3. Competitive Intelligence — how information becomes advantage

Every move in strategy.py flows from this doctrine.
Every agent in the warehouse serves this doctrine.
Every decision you make should be tested against this doctrine.

Run:  python doctrine.py                  # Full doctrine + live audit
      python doctrine.py --audit          # Audit your position against the doctrine
      python doctrine.py --framework      # Print the doctrine framework only
"""

import sys
from warehouse.db import get_connection


# ════════════════════════════════════════════════════════════════════════
#  THE DOCTRINE
# ════════════════════════════════════════════════════════════════════════

DOCTRINE = {
    "prime_law": {
        "title": "THE PRIME LAW: Survival Through Strategic Adaptation",
        "principle": (
            "Every organization exists in an environment that is constantly changing.\n"
            "Success depends on the ability to win today while preparing for tomorrow.\n"
            "\n"
            "This creates the fundamental tension of strategy:\n"
            "\n"
            "    PRESENT SURVIVAL  vs  FUTURE DOMINANCE\n"
            "\n"
            "Organizations that focus only on the present become obsolete.\n"
            "Organizations that focus only on the future collapse before reaching it.\n"
            "\n"
            "Strategic leadership must do both simultaneously."
        ),
    },

    "core_mission": {
        "title": "THE CORE MISSION STRUCTURE",
        "principle": (
            "All strategy begins with purpose.\n"
            "\n"
            "An organization must clearly define:\n"
            "\n"
            "  1. MISSION          — Why it exists\n"
            "  2. VISION           — The future it intends to create\n"
            "  3. STRATEGIC INTENT — The position it seeks to dominate\n"
            "  4. OBJECTIVES       — Measurable outcomes that move toward the vision\n"
            "\n"
            "Mission provides direction. Objectives provide measurement.\n"
            "\n"
            "Objectives must be SMART:\n"
            "  Specific · Measurable · Achievable · Relevant · Time-bound\n"
            "\n"
            "Without measurable objectives, strategy becomes philosophy instead of action."
        ),
    },

    "strategic_trinity": {
        "title": "THE STRATEGIC TRINITY",
        "principle": (
            "Every strategic system operates across three domains:\n"
            "\n"
            "  ┌─────────────────────────────────────────────────────────────┐\n"
            "  │                                                             │\n"
            "  │              ┌──────────────────┐                           │\n"
            "  │              │   ENVIRONMENT    │                           │\n"
            "  │              │   competitors    │                           │\n"
            "  │              │   markets        │                           │\n"
            "  │              │   technology     │                           │\n"
            "  │              │   regulation     │                           │\n"
            "  │              └────────┬─────────┘                           │\n"
            "  │                       │                                     │\n"
            "  │              ┌────────┴─────────┐                           │\n"
            "  │              │  INTELLIGENCE   │                           │\n"
            "  │              │  the bridge     │                           │\n"
            "  │              │  Data →         │                           │\n"
            "  │              │  Information →  │                           │\n"
            "  │              │  Knowledge →    │                           │\n"
            "  │              │  Intelligence   │                           │\n"
            "  │              └────────┬─────────┘                           │\n"
            "  │                       │                                     │\n"
            "  │              ┌────────┴─────────┐                           │\n"
            "  │              │  ORGANIZATION   │                           │\n"
            "  │              │  resources      │                           │\n"
            "  │              │  capabilities   │                           │\n"
            "  │              │  culture        │                           │\n"
            "  │              │  leadership     │                           │\n"
            "  │              └──────────────────┘                           │\n"
            "  │                                                             │\n"
            "  └─────────────────────────────────────────────────────────────┘\n"
            "\n"
            "Without intelligence, strategy is blind."
        ),
    },

    "strategic_process": {
        "title": "THE STRATEGIC PROCESS",
        "principle": (
            "All strategy follows four continuous stages:\n"
            "\n"
            "  1. STRATEGIC ANALYSIS    — Understand reality\n"
            "     External: industry, economy, technology, politics\n"
            "     Internal: capabilities, competencies, financial strength\n"
            "     Question: WHERE ARE WE?\n"
            "\n"
            "  2. STRATEGIC CHOICE      — Develop and evaluate options\n"
            "     Generate: obvious, creative, and radical strategies\n"
            "     Test each option:\n"
            "       • Suitability  — does it fit the environment?\n"
            "       • Feasibility  — do we have the resources?\n"
            "       • Acceptability — will stakeholders support it?\n"
            "     Question: WHERE COULD WE GO?\n"
            "\n"
            "  3. STRATEGIC IMPLEMENTATION — Translate into action\n"
            "     Align: structure, operations, leadership, culture, processes\n"
            "     Execution failures destroy more strategies than bad planning.\n"
            "     Question: HOW DO WE GET THERE?\n"
            "\n"
            "  4. STRATEGIC CONTROL     — Monitor and adapt\n"
            "     Performance measurement, intelligence gathering,\n"
            "     environmental scanning, feedback loops.\n"
            "     Strategy is never static.\n"
            "     Question: ARE WE ON TRACK?"
        ),
    },

    "intelligence_engine": {
        "title": "THE INTELLIGENCE ENGINE",
        "principle": (
            "Modern strategy depends on competitive intelligence.\n"
            "\n"
            "An intelligent organization continuously gathers information about:\n"
            "  • competitors  • markets  • technologies  • global trends\n"
            "\n"
            "But intelligence is not raw information.\n"
            "The real skill is SYNTHESIS.\n"
            "Turning scattered signals into insight.\n"
            "\n"
            "Organizations that master intelligence gain the ability to:\n"
            "  • predict industry change\n"
            "  • anticipate competitor strategy\n"
            "  • create opportunities before others see them\n"
            "\n"
            "Intelligence is the central nervous system of strategy."
        ),
    },

    "intelligence_age": {
        "title": "THE INTELLIGENCE AGE",
        "principle": (
            "Modern competition is no longer about industrial production.\n"
            "It is about decision speed and insight.\n"
            "\n"
            "Organizations succeed through:\n"
            "  • analytical capability\n"
            "  • technological leverage\n"
            "  • strategic foresight\n"
            "  • intelligent leadership\n"
            "\n"
            "The most valuable asset is not capital.\n"
            "It is strategic thinking capacity.\n"
            "\n"
            "Companies that cultivate intelligence become intelligent organizations.\n"
            "Those that do not eventually fail."
        ),
    },

    "strategic_leadership": {
        "title": "THE DOCTRINE OF STRATEGIC LEADERSHIP",
        "principle": (
            "Strategic leadership requires five disciplines:\n"
            "\n"
            "  1. ENVIRONMENTAL AWARENESS\n"
            "     Constant scanning of the external world.\n"
            "\n"
            "  2. ORGANIZATIONAL ALIGNMENT\n"
            "     Ensuring resources match strategy.\n"
            "\n"
            "  3. INTELLIGENCE DEVELOPMENT\n"
            "     Transforming information into actionable insight.\n"
            "\n"
            "  4. STRATEGIC ADAPTABILITY\n"
            "     Adjusting strategy as conditions evolve.\n"
            "\n"
            "  5. OPPORTUNITY CREATION\n"
            "     Not just reacting to change — but creating it."
        ),
    },

    "ultimate_principle": {
        "title": "THE ULTIMATE PRINCIPLE",
        "principle": (
            "Strategy is not merely planning.\n"
            "Strategy is the art of shaping the future.\n"
            "\n"
            "Organizations that practice strategic intelligence\n"
            "do not simply survive change.\n"
            "\n"
            "They engineer it."
        ),
    },

    "final_statement": {
        "title": "FINAL DOCTRINE STATEMENT",
        "principle": (
            "An organization achieves enduring success by:\n"
            "\n"
            "  1. Defining a clear mission and strategic intent\n"
            "  2. Continuously analyzing its environment and capabilities\n"
            "  3. Transforming information into competitive intelligence\n"
            "  4. Choosing strategies that create advantage\n"
            "  5. Aligning resources and culture for execution\n"
            "  6. Constantly adapting through feedback and learning\n"
            "\n"
            "Through this cycle, the organization becomes an intelligent\n"
            "strategic system capable of creating its own future."
        ),
    },
}


# ════════════════════════════════════════════════════════════════════════
#  DISPLAY
# ════════════════════════════════════════════════════════════════════════

def _header(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}")


def print_doctrine():
    """Print the full doctrine framework."""
    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "THE DOCTRINE OF STRATEGIC INTELLIGENCE".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" + "A Unified System for Strategy, Power, and Execution".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)

    for i, (key, section) in enumerate(DOCTRINE.items(), 1):
        numeral = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"][i - 1]
        _header(f"{numeral}. {section['title']}")
        for line in section["principle"].split("\n"):
            print(f"  {line}")

    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "END OF DOCTRINE".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)
    print()


# ════════════════════════════════════════════════════════════════════════
#  LIVE AUDIT — How your position maps to the doctrine
# ════════════════════════════════════════════════════════════════════════

def _q(query, params=None):
    con = get_connection()
    cur = con.execute(query, params or [])
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    con.close()
    return rows


def _grade(score, max_score):
    pct = score / max_score if max_score else 0
    if pct >= 0.8:
        return "A", "██████████"
    elif pct >= 0.6:
        return "B", "████████░░"
    elif pct >= 0.4:
        return "C", "██████░░░░"
    elif pct >= 0.2:
        return "D", "████░░░░░░"
    else:
        return "F", "██░░░░░░░░"


def doctrine_audit():
    """Audit your current position against the doctrine's principles."""

    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "DOCTRINE AUDIT".center(68) + "▓")
    print("▓" + "How your system maps to the doctrine".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)

    scores = {}

    # ── I. PRIME LAW: Present Survival vs Future Dominance ──────────
    _header("I. PRIME LAW AUDIT — Present vs Future Balance")

    # Present survival = do we have pricing, services, active tracking?
    from strategy import YOUR_SHOP
    has_prices = len(YOUR_SHOP["prices"]) > 0
    has_premium = any(p >= 60 for p in YOUR_SHOP["prices"].values())

    competitor_count = _q("SELECT COUNT(*) as n FROM competitors WHERE status = 'Active'")[0]["n"]
    move_count = _q("SELECT COUNT(*) as n FROM competitor_moves")[0]["n"]
    score_count = _q("SELECT COUNT(*) as n FROM competitor_scores")[0]["n"]

    present_score = sum([
        2 if has_prices else 0,
        2 if has_premium else 0,
        2 if competitor_count >= 10 else 1 if competitor_count >= 5 else 0,
        2 if score_count > 0 else 0,
        2 if move_count >= 5 else 1 if move_count > 0 else 0,
    ])

    # Future dominance = expansion intel, talent pipeline, positioning
    expansion_areas = _q("""
        SELECT COUNT(DISTINCT neighborhood) as n FROM competitors
        WHERE status = 'Active'
    """)[0]["n"]
    barber_intel = _q("SELECT COUNT(*) as n FROM barbers")[0]["n"]
    social_intel = _q("SELECT COUNT(*) as n FROM competitor_social")[0]["n"]

    future_score = sum([
        2 if expansion_areas >= 15 else 1 if expansion_areas >= 8 else 0,
        2 if barber_intel >= 20 else 1 if barber_intel >= 10 else 0,
        2 if social_intel >= 10 else 1 if social_intel >= 5 else 0,
        2 if YOUR_SHOP.get("booking_platform") else 0,
        2 if YOUR_SHOP.get("instagram_followers", 0) >= 1000 else 0,
    ])

    present_grade, present_bar = _grade(present_score, 10)
    future_grade, future_bar = _grade(future_score, 10)

    print(f"\n  Present Survival:   {present_bar}  {present_grade}  ({present_score}/10)")
    print(f"    Pricing defined: {'YES' if has_prices else 'NO'}")
    print(f"    Premium tier ($60+): {'YES' if has_premium else 'NO — ADD ONE'}")
    print(f"    Competitors tracked: {competitor_count}")
    print(f"    Threat scores computed: {score_count}")
    print(f"    Competitor moves logged: {move_count}")

    print(f"\n  Future Dominance:   {future_bar}  {future_grade}  ({future_score}/10)")
    print(f"    Market areas mapped: {expansion_areas}")
    print(f"    Barber talent intel: {barber_intel} barbers tracked")
    print(f"    Social intel points: {social_intel}")
    booking = YOUR_SHOP.get("booking_platform") or "NONE"
    has_proprietary_os = YOUR_SHOP.get("booking_os", {}).get("type") == "proprietary"
    if has_proprietary_os:
        print(f"    Booking platform: {booking} — PROPRIETARY OS (competitive weapon)")
    else:
        print(f"    Booking platform: {booking or 'NONE — GET ON BOOKSY'}")
    print(f"    Years experience: {YOUR_SHOP.get('years_experience', 'Not set')}")
    print(f"    Instagram followers: {YOUR_SHOP.get('instagram_followers', 0)}")

    scores["prime_law"] = (present_score + future_score, 20)

    # ── II. CORE MISSION AUDIT ──────────────────────────────────────
    _header("II. CORE MISSION AUDIT — Purpose Clarity")

    mission_items = {
        "Mission (why you exist)": None,
        "Vision (the future you intend to create)": None,
        "Strategic Intent (position to dominate)": None,
    }

    # Check if mission is defined
    mission_defined = YOUR_SHOP.get("name") != "Your Shop"

    has_retail = YOUR_SHOP.get("revenue_model", {}).get("wholesale_membership", False)
    has_deposits = YOUR_SHOP.get("deposits", False)
    objectives = [
        ("Price positioning defined", has_prices, True),
        ("Premium service tier", has_premium, True),
        ("Location identified", YOUR_SHOP.get("neighborhood") is not None, False),
        ("Booking platform active", YOUR_SHOP.get("booking_platform") is not None, False),
        ("Retail/product revenue stream", has_retail, False),
        ("Deposit system active", has_deposits, False),
    ]

    mission_score = 0
    print(f"\n  Mission Definition: {'DEFINED' if mission_defined else 'NOT YET — name your shop in strategy.py'}")
    if not mission_defined:
        print("    Update YOUR_SHOP['name'] in strategy.py")
    else:
        mission_score += 2

    print(f"\n  SMART Objectives Status:")
    for name, status, met in objectives:
        icon = "■" if status else "□"
        mission_score += 2 if status else 0
        print(f"    {icon} {name}: {'ACTIVE' if status else 'PENDING'}")

    mission_grade, mission_bar = _grade(mission_score, 14)
    print(f"\n  Mission Score:      {mission_bar}  {mission_grade}  ({mission_score}/14)")
    scores["core_mission"] = (mission_score, 14)

    # ── III. STRATEGIC TRINITY AUDIT ────────────────────────────────
    _header("III. STRATEGIC TRINITY AUDIT — Three Domains")

    # Environment coverage
    env_metrics = {
        "Competitors tracked": competitor_count,
        "Price data points": _q("SELECT COUNT(*) as n FROM price_history")[0]["n"],
        "Review snapshots": _q("SELECT COUNT(*) as n FROM review_snapshots")[0]["n"],
        "Competitor moves": move_count,
        "Neighborhoods mapped": expansion_areas,
    }

    env_score = sum([
        2 if competitor_count >= 20 else 1 if competitor_count >= 10 else 0,
        2 if env_metrics["Price data points"] >= 50 else 1 if env_metrics["Price data points"] >= 20 else 0,
        2 if env_metrics["Review snapshots"] >= 10 else 1 if env_metrics["Review snapshots"] >= 5 else 0,
        2 if move_count >= 10 else 1 if move_count >= 5 else 0,
        2 if expansion_areas >= 15 else 1 if expansion_areas >= 8 else 0,
    ])

    print(f"\n  ENVIRONMENT (external world):")
    for k, v in env_metrics.items():
        print(f"    {k:30s}  {v}")
    env_grade, env_bar = _grade(env_score, 10)
    print(f"    Coverage:         {env_bar}  {env_grade}  ({env_score}/10)")

    # Organization coverage
    print(f"\n  ORGANIZATION (internal system):")
    os_info = YOUR_SHOP.get("booking_os", {})
    org_items = {
        "Shop name": YOUR_SHOP.get("name", "Not set"),
        "Experience": f"{YOUR_SHOP.get('years_experience', 'N/A')} years",
        "Barbers": YOUR_SHOP.get("barbers", 0),
        "Price menu": f"{len(YOUR_SHOP.get('prices', {}))} services",
        "Booking platform": YOUR_SHOP.get("booking_platform") or "None",
        "Location": YOUR_SHOP.get("neighborhood") or "Not set",
    }
    for k, v in org_items.items():
        print(f"    {k:30s}  {v}")

    if os_info.get("type") == "proprietary":
        print(f"\n    PROPRIETARY BOOKING OS (planned):")
        for feat in os_info.get("features_live", []):
            print(f"      ◆ {feat} [live]")
        for feat in os_info.get("features_planned", []):
            print(f"      ◇ {feat} [planned]")
        migrating = os_info.get("migrating_from")
        if migrating:
            print(f"      Migrating from: {migrating}")
        print(f"      Advantage: {os_info.get('advantage', 'N/A')}")

    veteran = YOUR_SHOP.get("years_experience", 0) >= 5
    org_score = sum([
        2 if mission_defined else 0,
        2 if veteran else 1 if YOUR_SHOP.get("years_experience", 0) >= 1 else 0,
        2 if has_prices else 0,
        2 if YOUR_SHOP.get("booking_platform") else 0,
        2 if has_proprietary_os else 0,  # Proprietary OS is a separate advantage
        2 if YOUR_SHOP.get("neighborhood") else 0,
    ])
    org_grade, org_bar = _grade(org_score, 12)
    print(f"    Readiness:        {org_bar}  {org_grade}  ({org_score}/12)")

    # Intelligence coverage
    print(f"\n  INTELLIGENCE (the bridge):")
    intel_items = {
        "Threat scores": score_count,
        "Social intel points": social_intel,
        "Barber intel": barber_intel,
        "Price intelligence": env_metrics["Price data points"],
        "Agents operational": "YES (warehouse/agents/)",
    }
    for k, v in intel_items.items():
        print(f"    {k:30s}  {v}")

    intel_score = sum([
        2 if score_count >= 10 else 1 if score_count > 0 else 0,
        2 if social_intel >= 10 else 1 if social_intel >= 5 else 0,
        2 if barber_intel >= 20 else 1 if barber_intel >= 10 else 0,
        2 if env_metrics["Price data points"] >= 50 else 1,
        2,  # Agents are operational
    ])
    intel_grade, intel_bar = _grade(intel_score, 10)
    print(f"    Capability:       {intel_bar}  {intel_grade}  ({intel_score}/10)")

    trinity_score = env_score + org_score + intel_score
    scores["strategic_trinity"] = (trinity_score, 32)

    # ── IV. STRATEGIC PROCESS AUDIT ─────────────────────────────────
    _header("IV. STRATEGIC PROCESS AUDIT — The Four Stages")

    stages = [
        ("1. ANALYSIS", [
            ("Competitor landscape mapped", competitor_count >= 10),
            ("Pricing analysis complete", env_metrics["Price data points"] >= 20),
            ("Social landscape scanned", social_intel >= 5),
            ("Talent pool identified", barber_intel >= 5),
            ("Neighborhood density mapped", expansion_areas >= 10),
        ]),
        ("2. CHOICE", [
            ("Pricing position chosen (premium)", has_prices and any(p >= 40 for p in YOUR_SHOP["prices"].values())),
            ("Target neighborhoods identified", True),  # strategy.py does this
            ("Differentiation strategy", True),  # doctrine drives this
            ("Growth model selected", True),  # chair rental model
        ]),
        ("3. IMPLEMENTATION", [
            ("Booking platform active", YOUR_SHOP.get("booking_platform") is not None),
            ("Proprietary OS deployed", has_proprietary_os),
            ("10+ years industry experience", veteran),
            ("Instagram launched", YOUR_SHOP.get("instagram_followers", 0) > 0),
            ("Location secured", YOUR_SHOP.get("neighborhood") is not None),
            ("First chair rented", YOUR_SHOP.get("barbers", 1) > 1),
        ]),
        ("4. CONTROL", [
            ("Agents running (automated intel)", True),
            ("Scorecard system active", score_count > 0),
            ("Move tracking active", move_count > 0),
            ("Strategy playbook generated", True),  # strategy.py exists
        ]),
    ]

    process_score = 0
    process_max = 0

    for stage_name, checks in stages:
        passed = sum(1 for _, ok in checks if ok)
        total = len(checks)
        process_score += passed
        process_max += total
        pct = passed / total if total else 0

        if pct >= 0.8:
            status = "OPERATIONAL"
        elif pct >= 0.5:
            status = "PARTIAL"
        else:
            status = "NEEDS WORK"

        print(f"\n  {stage_name}  [{status}]  ({passed}/{total})")
        for name, ok in checks:
            icon = "■" if ok else "□"
            print(f"    {icon} {name}")

    scores["strategic_process"] = (process_score, process_max)

    # ── V. INTELLIGENCE ENGINE AUDIT ────────────────────────────────
    _header("V. INTELLIGENCE ENGINE AUDIT — Data → Intelligence Pipeline")

    pipeline = [
        ("DATA (raw collection)", [
            f"{competitor_count} competitors in warehouse",
            f"{env_metrics['Price data points']} price data points",
            f"{env_metrics['Review snapshots']} review snapshots",
            f"{social_intel} social data points",
            f"{barber_intel} barber profiles",
        ]),
        ("INFORMATION (structured)", [
            f"Price history table — tracks changes over time",
            f"Competitor moves table — {move_count} strategic moves logged",
            f"Review snapshots — sentiment scored",
            f"Social metrics — engagement rates tracked",
        ]),
        ("KNOWLEDGE (analyzed)", [
            f"Threat scores computed for {score_count} assessments",
            f"Hotness scores — momentum ranking",
            f"Neighborhood pricing maps",
            f"Market segment analysis (franchise vs independent)",
        ]),
        ("INTELLIGENCE (actionable)", [
            f"strategy.py — 6 sections of strategic moves",
            f"doctrine.py — operating framework for decisions",
            f"Revenue projections calibrated to YOUR prices",
            f"30-60-90 day action plan generated",
        ]),
    ]

    print()
    for level, items in pipeline:
        print(f"  {level}")
        for item in items:
            print(f"    → {item}")
        print(f"    {'│':>4s}")

    print(f"    {'▼':>4s}")
    print(f"  STRATEGIC DECISION")

    # ── VI-VIII. LEADERSHIP DISCIPLINES ─────────────────────────────
    _header("VII. STRATEGIC LEADERSHIP — Five Disciplines")

    disciplines = [
        ("Environmental Awareness",
         "Warehouse agents scan competitors, prices, reviews, social",
         competitor_count >= 10 and social_intel >= 5),
        ("Organizational Alignment",
         "Pricing, services, and booking aligned to premium position",
         has_prices and has_premium),
        ("Intelligence Development",
         "Data→Information→Knowledge→Intelligence pipeline operational",
         score_count > 0 and move_count > 0),
        ("Strategic Adaptability",
         "Agents run on schedule, strategy regenerates from live data",
         True),
        ("Opportunity Creation",
         "Underserved premium areas identified, community plays designed",
         expansion_areas >= 10),
    ]

    disc_score = 0
    for name, desc, active in disciplines:
        icon = "■" if active else "□"
        disc_score += 2 if active else 0
        print(f"\n  {icon} {name}")
        print(f"    {desc}")
        print(f"    Status: {'ACTIVE' if active else 'PENDING'}")

    scores["leadership"] = (disc_score, 10)

    # ── OVERALL DOCTRINE SCORE ──────────────────────────────────────
    _header("OVERALL DOCTRINE SCORE")

    total_score = sum(s for s, _ in scores.values())
    total_max = sum(m for _, m in scores.values())
    overall_grade, overall_bar = _grade(total_score, total_max)

    print(f"\n  {'Section':35s} {'Score':>8s}  {'Grade':>6s}")
    print(f"  {'─' * 55}")

    section_names = {
        "prime_law": "I. Prime Law",
        "core_mission": "II. Core Mission",
        "strategic_trinity": "III. Strategic Trinity",
        "strategic_process": "IV. Strategic Process",
        "leadership": "VII. Strategic Leadership",
    }

    for key, (score, max_s) in scores.items():
        grade, bar = _grade(score, max_s)
        name = section_names.get(key, key)
        print(f"  {name:35s} {score:>3d}/{max_s:<3d}    {bar}  {grade}")

    print(f"  {'─' * 55}")
    print(f"  {'OVERALL':35s} {total_score:>3d}/{total_max:<3d}    {overall_bar}  {overall_grade}")

    # Doctrine status
    print()
    if overall_grade == "A":
        print("  STATUS: DOCTRINE OPERATIONAL")
        print("  Your system is running as an intelligent strategic organization.")
    elif overall_grade == "B":
        print("  STATUS: DOCTRINE ADVANCING")
        print("  Strong foundation. Close the gaps in implementation.")
    elif overall_grade == "C":
        print("  STATUS: DOCTRINE DEVELOPING")
        print("  Analysis and choice are strong. Execution needs acceleration.")
    else:
        print("  STATUS: DOCTRINE INITIALIZING")
        print("  Intelligence is being gathered. Focus on the 30-day quick wins.")

    # Current position
    annual_gross = YOUR_SHOP.get("annual_gross", 0)
    has_deposits_active = YOUR_SHOP.get("deposits", False)
    has_wholesale = YOUR_SHOP.get("revenue_model", {}).get("wholesale_membership", False)
    setup = YOUR_SHOP.get("setup", "Unknown")
    goal = YOUR_SHOP.get("goal", "Not defined")

    print(f"\n  CURRENT POSITION:")
    print(f"    Setup:          {setup}")
    print(f"    Location:       {YOUR_SHOP.get('neighborhood', 'Not set')}")
    if annual_gross:
        print(f"    Annual gross:   ${annual_gross:,}")
        print(f"    Monthly gross:  ~${annual_gross // 12:,}")
    print(f"    Deposits:       {'ACTIVE' if has_deposits_active else 'NOT SET UP'}")
    print(f"    Retail/Product: {'WHOLESALE ACCESS' if has_wholesale else 'NO PRODUCT REVENUE'}")
    print(f"    Goal:           {goal}")

    # Critical gaps
    gaps = []
    if YOUR_SHOP.get("name") == "Your Shop":
        gaps.append("Shop not named — update YOUR_SHOP['name'] in strategy.py")
    if not has_premium:
        gaps.append("No premium tier ($60+) — add Royal Treatment service")

    # Proprietary OS specific
    os_info = YOUR_SHOP.get("booking_os", {})
    if os_info.get("migrating_from"):
        gaps.append(f"Still on {os_info['migrating_from']} — complete migration to your OS")

    # Revenue gaps
    if annual_gross and annual_gross < 50000:
        gaps.append(f"Gross at ${annual_gross:,}/yr — retail product margin can close the gap to $50K+")
    if setup == "Solo suite":
        gaps.append("Suite ceiling — no room for chair rentals, limited growth")

    if gaps:
        print(f"\n  CRITICAL GAPS:")
        for g in gaps:
            print(f"    ▸ {g}")
    else:
        print(f"\n  NO CRITICAL GAPS — doctrine is fully operational.")

    # Advantages
    print(f"\n  COMPETITIVE ADVANTAGES:")
    if has_proprietary_os:
        print("    ◆ PROPRIETARY BOOKING OS — only one in the market")
    if veteran:
        print(f"    ◆ {YOUR_SHOP.get('years_experience', 0)} YEARS EXPERIENCE — veteran operator")
    if has_premium:
        print("    ◆ PREMIUM PRICING POSITION — above market average")
    if has_wholesale:
        print("    ◆ WHOLESALE PRODUCT ACCESS — 50-70% margins on retail")
    if has_deposits_active:
        print("    ◆ DEPOSIT SYSTEM — forward revenue visibility + no-show protection")
    print("    ◆ COMPETITIVE INTELLIGENCE SYSTEM — warehouse + agents + doctrine")
    print("    ◆ CORE CLIENT BASE — retention phase, not chasing new clients")

    print()


# ════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--framework" in args:
        print_doctrine()
    elif "--audit" in args:
        doctrine_audit()
    else:
        print_doctrine()
        doctrine_audit()
