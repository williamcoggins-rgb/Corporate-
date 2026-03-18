"""MICHAEL PORTER COMPETITIVE ANALYSIS — No Grease Barbershop (2026)

A structured analysis applying Porter's three core frameworks:
  1. Five Forces Analysis     — industry attractiveness & competitive intensity
  2. Generic Strategies       — how No Grease competes (and how YOU should)
  3. Value Chain Analysis     — where No Grease creates (and leaks) value

Governed by: doctrine.py — The Doctrine of Strategic Intelligence
Intel source: Deep research conducted March 2026 (50+ searches, 7 platforms)
Subject: No Grease Inc. — 14 locations, first Black-owned franchise barbershop in US

Run:  python porter_analysis.py                    # Full analysis
      python porter_analysis.py --five-forces      # Five Forces only
      python porter_analysis.py --generic          # Generic Strategies only
      python porter_analysis.py --value-chain      # Value Chain only
      python porter_analysis.py --implications      # Strategic implications for YOUR shop
"""

import sys
from warehouse.db import get_connection


def _q(query, params=None):
    con = get_connection()
    cur = con.execute(query, params or [])
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    con.close()
    return rows


def _header(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}")


def _sub(title):
    print(f"\n  ┌─ {title}")
    print(f"  │")


def _point(text, indent=2):
    for line in text.split("\n"):
        print(f"  {'│':>{indent}}   {line}")


def _end():
    print(f"  └{'─' * 60}")


# ════════════════════════════════════════════════════════════════════════
#  PORTER'S FIVE FORCES — Industry Structure Analysis
# ════════════════════════════════════════════════════════════════════════

FIVE_FORCES = {
    "threat_of_new_entrants": {
        "force": "THREAT OF NEW ENTRANTS",
        "rating": "HIGH",
        "score": 4,  # out of 5
        "analysis": (
            "The barbershop industry has LOW barriers to entry at the\n"
            "independent level. A barber with a license, $5K-15K, and\n"
            "a suite rental can open tomorrow. Charlotte sees new solo\n"
            "operators weekly.\n"
            "\n"
            "HOWEVER — at the FRANCHISE level, barriers are MODERATE:\n"
            "  - No Grease franchise investment: $132K-$278K\n"
            "  - Net worth requirement: $200K+\n"
            "  - Cash requirement: $50K+\n"
            "  - Brand equity built over 25+ years\n"
            "  - Barber school pipeline (3,000+ graduates)\n"
            "\n"
            "No Grease has raised the bar for what 'entering the market'\n"
            "means. Solo operators enter easily but cannot compete at\n"
            "scale. New franchise entrants face significant capital and\n"
            "brand-building requirements."
        ),
        "key_factors": [
            "Low capital requirements for solo operators",
            "Barber licensing is accessible (12-18 month programs)",
            "Suite rental model eliminates need for full buildout",
            "BUT: franchise-scale entry requires $132K-$278K",
            "BUT: brand equity takes decades to build",
            "BUT: No Grease's barber school creates talent lock-in",
        ],
    },

    "bargaining_power_of_suppliers": {
        "force": "BARGAINING POWER OF SUPPLIERS",
        "rating": "LOW-MODERATE",
        "score": 2,
        "analysis": (
            "Supplier power in barbering is generally LOW.\n"
            "\n"
            "Product suppliers (clippers, products, chairs) are abundant.\n"
            "No single supplier dominates. Wahl, Andis, BabylissPRO all\n"
            "compete for barber dollars.\n"
            "\n"
            "HOWEVER — two supplier dynamics matter:\n"
            "\n"
            "  1. REAL ESTATE (the hidden supplier)\n"
            "     Mall operators like SouthPark Mall are powerful suppliers.\n"
            "     In 2021, SouthPark terminated No Grease's lease early —\n"
            "     public outcry reversed it, but this exposed dependency.\n"
            "     No Grease now diversifies: malls, standalone, outlets.\n"
            "\n"
            "  2. TALENT (barbers as suppliers of labor)\n"
            "     Skilled barbers are scarce. Good faders command premium.\n"
            "     No Grease mitigates this by OWNING the supply:\n"
            "     - School of Tonsorial Arts (3,000+ graduates)\n"
            "     - Ed Washington gives lead barbers 10% equity\n"
            "     This is backward integration — Porter's classic defense."
        ),
        "key_factors": [
            "Product/equipment suppliers are abundant and interchangeable",
            "Real estate landlords hold moderate power (lease dependency)",
            "Skilled barber talent is scarce — HIGH supplier power",
            "No Grease mitigates via barber school (backward integration)",
            "Ed Washington's 10% equity model reduces talent flight risk",
            "TD Bank relationship secures capital supply",
        ],
    },

    "bargaining_power_of_buyers": {
        "force": "BARGAINING POWER OF BUYERS (Customers)",
        "rating": "MODERATE",
        "score": 3,
        "analysis": (
            "Individual customer power is LOW — no single client moves\n"
            "the needle. But COLLECTIVE buyer power is moderate because:\n"
            "\n"
            "  1. SWITCHING COSTS ARE LOW\n"
            "     A client can walk into any barbershop. No contracts.\n"
            "     No lock-in. Booksy, Square, and walk-ins make switching\n"
            "     frictionless.\n"
            "\n"
            "  2. PRICE SENSITIVITY VARIES BY SEGMENT\n"
            "     Budget segment: highly price-sensitive ($15-25 cuts)\n"
            "     Mid-market: moderate sensitivity ($30-45 cuts)\n"
            "     Premium/luxury: LOW sensitivity ($55-100+ cuts)\n"
            "     No Grease positions in mid-to-premium, reducing buyer power.\n"
            "\n"
            "  3. INFORMATION IS ABUNDANT\n"
            "     Google, Yelp, Instagram, Booksy all expose pricing,\n"
            "     reviews, and portfolio quality. Buyers are well-informed.\n"
            "\n"
            "No Grease counters buyer power through:\n"
            "  - Brand loyalty (25+ years of cultural equity)\n"
            "  - Community identity (barbershop as cultural institution)\n"
            "  - Premium experience (Knights of the Razor luxury tier)\n"
            "  - Deposits on future bookings (creates forward commitment)"
        ),
        "key_factors": [
            "Individual buyer power is low (fragmented customer base)",
            "Switching costs are near-zero for consumers",
            "Price transparency via Yelp/Google/Booksy empowers buyers",
            "Premium positioning reduces price sensitivity",
            "Brand loyalty and cultural identity create emotional lock-in",
            "Deposit system creates financial switching cost",
        ],
    },

    "threat_of_substitutes": {
        "force": "THREAT OF SUBSTITUTES",
        "rating": "LOW-MODERATE",
        "score": 2,
        "analysis": (
            "Substitutes for professional barbering include:\n"
            "\n"
            "  1. HOME HAIRCUTS (DIY clippers) — growing since COVID\n"
            "     Wahl, Manscaped, Bevel sell direct-to-consumer.\n"
            "     Threat is real for basic cuts but NOT for fades,\n"
            "     lineups, or precision work.\n"
            "\n"
            "  2. HAIR SALONS (unisex) — some overlap but different\n"
            "     experience. Barbershop culture is not replicable\n"
            "     in a salon setting.\n"
            "\n"
            "  3. MOBILE BARBERS — convenience play but lacks the\n"
            "     shop experience, community, and consistency.\n"
            "\n"
            "  4. SUBSCRIPTION GROOMING BOXES — Dollar Shave Club,\n"
            "     Bevel, etc. Substitute for product revenue only.\n"
            "\n"
            "The barbershop's CULTURAL FUNCTION is the real moat.\n"
            "No Grease leans into this heavily — the blog post\n"
            "'Black History Is American History: The Barbershop's\n"
            "Role in Building Unity' is strategic positioning, not\n"
            "just content. It reinforces that a haircut is not just\n"
            "a service — it's a cultural experience.\n"
            "\n"
            "Substitutes cannot replicate this."
        ),
        "key_factors": [
            "DIY home clippers growing but limited to basic cuts",
            "Unisex salons overlap but lack barbershop culture",
            "Mobile barbers are convenience plays with no community",
            "Grooming subscriptions substitute product revenue only",
            "Cultural institution status is the ultimate substitute barrier",
            "No Grease's content strategy reinforces cultural moat",
        ],
    },

    "competitive_rivalry": {
        "force": "COMPETITIVE RIVALRY (Intensity of Competition)",
        "rating": "HIGH",
        "score": 4,
        "analysis": (
            "Charlotte barbershop competition is INTENSE.\n"
            "\n"
            "From warehouse data:\n"
            "  - 20+ tracked competitors in the Charlotte metro\n"
            "  - Mix of franchise chains, multi-shop operators,\n"
            "    and solo suite renters\n"
            "  - Price range: $15 (budget) to $100+ (luxury)\n"
            "\n"
            "COMPETITIVE STRUCTURE:\n"
            "\n"
            "  FRANCHISE TIER (No Grease competes here)\n"
            "  - No Grease: 14 locations, 25+ years, cultural brand\n"
            "  - Sport Clips, Great Clips: volume/discount model\n"
            "  - Floyd's 99: lifestyle positioning\n"
            "\n"
            "  PREMIUM INDEPENDENT TIER\n"
            "  - Boutique shops with strong Instagram presence\n"
            "  - $50-80 cuts, appointment-only, limited chairs\n"
            "\n"
            "  SOLO OPERATOR TIER\n"
            "  - Suite renters on Booksy/Square\n"
            "  - Low overhead, personal relationships\n"
            "  - YOUR competitive space\n"
            "\n"
            "RIVALRY IS HIGH because:\n"
            "  - Low differentiation at the service level\n"
            "  - Low switching costs\n"
            "  - Many competitors in every neighborhood\n"
            "  - Exit barriers are low (walk away from lease)\n"
            "\n"
            "No Grease differentiates through SCALE + CULTURE + SCHOOL,\n"
            "a combination no other Charlotte barbershop has."
        ),
        "key_factors": [
            "20+ tracked competitors in Charlotte metro alone",
            "Three-tier market: franchise, premium independent, solo",
            "Low differentiation at the pure service level",
            "Low switching costs drive constant client movement",
            "No Grease differentiates via scale + culture + talent pipeline",
            "Knights of the Razor creates premium sub-brand within rivalry",
        ],
    },
}


def print_five_forces():
    """Print the full Five Forces analysis."""
    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "PORTER'S FIVE FORCES ANALYSIS".center(68) + "▓")
    print("▓" + "No Grease Inc. — March 2026".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)

    # Pull live data to enrich
    ng_moves = _q("""
        SELECT m.move_date, m.move_type, m.description, m.impact_rating
        FROM competitor_moves m
        JOIN competitors c ON c.competitor_id = m.competitor_id
        WHERE c.company_name ILIKE '%grease%'
        AND m.move_date >= '2026-01-01'
        ORDER BY m.move_date DESC
    """)

    total_competitors = _q("SELECT COUNT(*) as n FROM competitors WHERE status = 'Active'")[0]["n"]

    print(f"\n  Live Intel: {len(ng_moves)} No Grease moves tracked in 2026")
    print(f"  Total competitors in warehouse: {total_competitors}")

    # Force diagram
    print(f"""
                    ┌───────────────────────────┐
                    │   THREAT OF NEW ENTRANTS  │
                    │        RATING: HIGH       │
                    │        Score: 4/5         │
                    └─────────────┬─────────────┘
                                  │
    ┌──────────────────┐          │          ┌──────────────────┐
    │  SUPPLIER POWER  │          │          │   BUYER POWER    │
    │  LOW-MODERATE    ├──────────┼──────────┤   MODERATE       │
    │  Score: 2/5      │          │          │   Score: 3/5     │
    └──────────────────┘          │          └──────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │   COMPETITIVE RIVALRY     │
                    │        RATING: HIGH       │
                    │        Score: 4/5         │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │  THREAT OF SUBSTITUTES    │
                    │     LOW-MODERATE          │
                    │     Score: 2/5            │
                    └───────────────────────────┘
    """)

    # Overall industry attractiveness
    total_score = sum(f["score"] for f in FIVE_FORCES.values())
    avg = total_score / 5

    print(f"  OVERALL INDUSTRY FORCE PRESSURE: {total_score}/25")
    if avg >= 4:
        verdict = "UNATTRACTIVE — intense competitive pressure on all sides"
    elif avg >= 3:
        verdict = "MODERATELY ATTRACTIVE — manageable with strong positioning"
    elif avg >= 2:
        verdict = "ATTRACTIVE — favorable conditions for well-positioned players"
    else:
        verdict = "HIGHLY ATTRACTIVE — wide open for value capture"
    print(f"  INDUSTRY ATTRACTIVENESS: {verdict}")

    # Detail each force
    for key, force in FIVE_FORCES.items():
        _header(f"{force['force']}  [{force['rating']}]  ({force['score']}/5)")
        for line in force["analysis"].split("\n"):
            print(f"  {line}")
        print(f"\n  Key Factors:")
        for factor in force["key_factors"]:
            print(f"    - {factor}")

    # 2026 moves that validate the analysis
    if ng_moves:
        _header("2026 MOVES VALIDATING THIS ANALYSIS")
        for m in ng_moves:
            impact = f" [Impact: {m['impact_rating']}/5]" if m.get("impact_rating") else ""
            print(f"  {m['move_date']} | {m['move_type']:12s} | {m['description'][:80]}...{impact}")


# ════════════════════════════════════════════════════════════════════════
#  PORTER'S GENERIC STRATEGIES — How No Grease Competes
# ════════════════════════════════════════════════════════════════════════

GENERIC_STRATEGIES = {
    "no_grease_strategy": {
        "title": "NO GREASE'S GENERIC STRATEGY: BROAD DIFFERENTIATION",
        "analysis": (
            "Porter defines three generic strategies:\n"
            "\n"
            "  1. COST LEADERSHIP  — lowest cost producer in the industry\n"
            "  2. DIFFERENTIATION  — unique value perceived industry-wide\n"
            "  3. FOCUS            — serving a narrow segment exceptionally\n"
            "\n"
            "No Grease pursues BROAD DIFFERENTIATION with elements of FOCUS.\n"
            "\n"
            "Their differentiation sources:\n"
            "\n"
            "  ┌─────────────────────────────────────────────────────────┐\n"
            "  │  CULTURAL IDENTITY                                     │\n"
            "  │  First Black-owned franchise barbershop in the US      │\n"
            "  │  25+ years of brand equity                             │\n"
            "  │  'UNSTOPPABLE 2026' — identity-driven campaigns        │\n"
            "  ├─────────────────────────────────────────────────────────┤\n"
            "  │  VERTICAL INTEGRATION                                  │\n"
            "  │  Barber school (talent pipeline owned)                 │\n"
            "  │  Knights of the Razor (luxury sub-brand)               │\n"
            "  │  Product line (grooming products)                      │\n"
            "  │  Franchise system (distribution model)                 │\n"
            "  ├─────────────────────────────────────────────────────────┤\n"
            "  │  GEOGRAPHIC SCALE                                      │\n"
            "  │  14 locations across multiple states                   │\n"
            "  │  Houston Galleria expansion (Texas entry)              │\n"
            "  │  Multi-format: malls, standalone, outlets              │\n"
            "  ├─────────────────────────────────────────────────────────┤\n"
            "  │  FINANCIAL INFRASTRUCTURE                              │\n"
            "  │  TD Bank partnership (capital access)                  │\n"
            "  │  National Urban League network                         │\n"
            "  │  Franchise fee revenue ($132K-$278K per unit)          │\n"
            "  └─────────────────────────────────────────────────────────┘\n"
            "\n"
            "They are NOT competing on cost. They are NOT a niche player.\n"
            "They are building a national brand with cultural moat."
        ),
    },

    "stuck_in_the_middle_risk": {
        "title": "PORTER'S 'STUCK IN THE MIDDLE' TEST",
        "analysis": (
            "Porter warns that firms pursuing BOTH cost leadership AND\n"
            "differentiation risk being 'stuck in the middle' — neither\n"
            "cheap enough nor differentiated enough.\n"
            "\n"
            "No Grease PASSES this test:\n"
            "\n"
            "  - They do NOT compete on price (not the cheapest)\n"
            "  - They DO differentiate clearly (culture, scale, school)\n"
            "  - Knights of the Razor is a PREMIUM sub-brand ($65+ cuts)\n"
            "  - Their franchise model targets operators with $200K+ net worth\n"
            "\n"
            "RISK AREA: Mid-market pricing at standard locations.\n"
            "  Regular No Grease locations price at $30-45 range.\n"
            "  This is mid-market — competitive territory.\n"
            "  Knights of the Razor resolves this by creating a\n"
            "  premium ceiling within the same brand architecture.\n"
            "\n"
            "VERDICT: Not stuck in the middle. Clear differentiation\n"
            "strategy with a premium escalation path."
        ),
    },

    "your_strategy": {
        "title": "YOUR GENERIC STRATEGY: FOCUSED DIFFERENTIATION",
        "analysis": (
            "As a solo suite operator, you CANNOT compete on:\n"
            "  - Cost leadership (you don't have volume economics)\n"
            "  - Broad differentiation (you don't have 14 locations)\n"
            "\n"
            "Your strategy MUST be FOCUSED DIFFERENTIATION:\n"
            "\n"
            "  Target segment: Premium clients in South Park\n"
            "  Differentiation: Proprietary booking OS + veteran skill\n"
            "  Price position: $40-65 (above mid-market)\n"
            "  Moat: Technology + experience + client relationships\n"
            "\n"
            "Porter says focus strategies win when:\n"
            "  1. The segment is underserved by broad competitors  ✓\n"
            "     (No Grease serves mass market; premium solos are few)\n"
            "  2. The firm has unique capabilities for the segment   ✓\n"
            "     (Proprietary OS, 10 years experience, deposit system)\n"
            "  3. Broad competitors cannot easily replicate the focus  ✓\n"
            "     (No Grease can't give each client a solo-operator experience)\n"
            "\n"
            "No Grease's WEAKNESS is your opportunity:\n"
            "  They scale through franchise standardization.\n"
            "  You differentiate through personalized mastery.\n"
            "  These are fundamentally different value propositions."
        ),
    },
}


def print_generic_strategies():
    """Print the Generic Strategies analysis."""
    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "PORTER'S GENERIC STRATEGIES".center(68) + "▓")
    print("▓" + "How No Grease Competes vs How YOU Should".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)

    # Strategy positioning map
    print("""
      COMPETITIVE ADVANTAGE
      ─────────────────────────────────────────────
                    LOWER COST    │  DIFFERENTIATION
      ─────────────────────────────────────────────
      BROAD     │  Cost          │  BROAD
      TARGET    │  Leadership    │  DIFFERENTIATION
                │  (Great Clips, │  ◄── NO GREASE
                │   Sport Clips) │      IS HERE
      ─────────┼────────────────┼──────────────────
      NARROW   │  Cost          │  FOCUSED
      TARGET   │  Focus         │  DIFFERENTIATION
                │  (Budget       │  ◄── YOU ARE
                │   walk-ins)    │      HERE
      ─────────────────────────────────────────────
    """)

    for key, strategy in GENERIC_STRATEGIES.items():
        _header(strategy["title"])
        for line in strategy["analysis"].split("\n"):
            print(f"  {line}")


# ════════════════════════════════════════════════════════════════════════
#  PORTER'S VALUE CHAIN — Where No Grease Creates (& Leaks) Value
# ════════════════════════════════════════════════════════════════════════

VALUE_CHAIN = {
    "primary_activities": [
        {
            "activity": "INBOUND LOGISTICS",
            "description": "How No Grease acquires inputs",
            "details": (
                "  - Barber talent: School of Tonsorial Arts (3,000+ grads)\n"
                "  - Product supply: Grooming product line (own brand)\n"
                "  - Real estate: Multi-format (malls, standalone, outlets)\n"
                "  - Capital: TD Bank partnership + franchise fees\n"
                "\n"
                "  VALUE CREATION: Backward integration into talent supply\n"
                "  gives them cost and quality control that competitors\n"
                "  who recruit from the open market cannot match.\n"
                "\n"
                "  VULNERABILITY: Real estate dependency (SouthPark incident).\n"
                "  Mitigating by diversifying location formats."
            ),
        },
        {
            "activity": "OPERATIONS",
            "description": "How No Grease delivers the service",
            "details": (
                "  - 14 locations, standardized franchise operations\n"
                "  - Knights of the Razor premium tier within standard locations\n"
                "  - Franchise manual + training from barber school\n"
                "  - Ed Washington model: lead barbers get 10% equity\n"
                "\n"
                "  VALUE CREATION: Franchise standardization = consistent\n"
                "  experience across locations. 10% equity model = motivated\n"
                "  operators (Porter's human resource management support).\n"
                "\n"
                "  VULNERABILITY: Franchise standardization can feel\n"
                "  impersonal. Solo operators win on personal connection."
            ),
        },
        {
            "activity": "OUTBOUND LOGISTICS",
            "description": "How the experience reaches the customer",
            "details": (
                "  - Physical locations in high-traffic areas (malls, outlets)\n"
                "  - Online booking (standard platforms)\n"
                "  - Product retail at point of service\n"
                "  - Huntersville + Houston = geographic expansion pipeline\n"
                "\n"
                "  VALUE CREATION: Mall locations capture walk-in traffic\n"
                "  that independent shops cannot access.\n"
                "\n"
                "  VULNERABILITY: Mall foot traffic is declining. Houston\n"
                "  expansion carries execution risk in unknown market."
            ),
        },
        {
            "activity": "MARKETING & SALES",
            "description": "How No Grease acquires and retains clients",
            "details": (
                "  - 'UNSTOPPABLE 2026' brand campaign\n"
                "  - Cultural content: 'Black History Is American History' blog\n"
                "  - 'The Line Up' music cypher series (70K+ views per episode)\n"
                "  - National media coverage (Axios, WCNC, CLTure)\n"
                "  - Yelp/Google listing management (updated March 2026)\n"
                "  - Word of mouth from 25+ years of community presence\n"
                "\n"
                "  VALUE CREATION: Cultural positioning transcends traditional\n"
                "  marketing. The barbershop IS the marketing — community\n"
                "  events, content, and cultural identity drive acquisition\n"
                "  without heavy ad spend.\n"
                "\n"
                "  VULNERABILITY: Content cadence appears irregular.\n"
                "  No 2026 podcast appearances or major media hits found."
            ),
        },
        {
            "activity": "SERVICE (After-Sales)",
            "description": "How No Grease retains and grows client value",
            "details": (
                "  - Grooming product line for at-home maintenance\n"
                "  - Knights of the Razor as upsell/premium escalation\n"
                "  - Community events (Sneaker Ball — last held 2025)\n"
                "  - Franchise loyalty across locations (brand portability)\n"
                "\n"
                "  VALUE CREATION: Product retail extends the revenue\n"
                "  relationship beyond the chair. Brand portability means\n"
                "  clients who relocate can find another No Grease.\n"
                "\n"
                "  VULNERABILITY: No 2026 Sneaker Ball announced.\n"
                "  Community event cadence may be slowing."
            ),
        },
    ],

    "support_activities": [
        {
            "activity": "FIRM INFRASTRUCTURE",
            "details": (
                "  - Franchise system (licensed in 36 states)\n"
                "  - TD Bank financial partnership\n"
                "  - National Urban League network\n"
                "  - Multi-entity structure (franchise + school + products)\n"
                "  - Edmund Washington's Razored Ventures LLC (franchise ops)\n"
                "  - Razored Technologies (tech startup — future play)"
            ),
        },
        {
            "activity": "HUMAN RESOURCE MANAGEMENT",
            "details": (
                "  - School of Tonsorial Arts (1,528 clock hours, 12-18 months)\n"
                "  - 3,000+ graduates = captive talent pipeline\n"
                "  - 10% equity for lead barbers (Ed Washington model)\n"
                "  - No barber experience required for franchisees\n"
                "  - Franchise model develops multi-unit operators over 3 years"
            ),
        },
        {
            "activity": "TECHNOLOGY DEVELOPMENT",
            "details": (
                "  - Razored Technologies (Edmund Washington's tech startup)\n"
                "  - Standard booking platforms (no proprietary OS detected)\n"
                "  - Yelp/Google listing management\n"
                "\n"
                "  CRITICAL GAP: No evidence of proprietary technology.\n"
                "  This is where YOUR proprietary OS is a genuine advantage."
            ),
        },
        {
            "activity": "PROCUREMENT",
            "details": (
                "  - Own product line (grooming products)\n"
                "  - Franchise-scale purchasing power for equipment/supplies\n"
                "  - Multi-location lease negotiation leverage\n"
                "  - TD Bank relationship for capital procurement"
            ),
        },
    ],
}


def print_value_chain():
    """Print the Value Chain analysis."""
    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "PORTER'S VALUE CHAIN ANALYSIS".center(68) + "▓")
    print("▓" + "Where No Grease Creates & Leaks Value".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)

    # Value chain diagram
    print("""
    ┌─────────────────────────────────────────────────────────────────┐
    │                    SUPPORT ACTIVITIES                           │
    │  ┌───────────────────────────────────────────────────────────┐  │
    │  │ Firm Infrastructure: Franchise system, TD Bank, NUL       │  │
    │  ├───────────────────────────────────────────────────────────┤  │
    │  │ HR Management: Barber school (3,000+ grads), 10% equity   │  │
    │  ├───────────────────────────────────────────────────────────┤  │
    │  │ Technology: Razored Technologies (⚠ NO proprietary OS)    │  │
    │  ├───────────────────────────────────────────────────────────┤  │
    │  │ Procurement: Own product line, franchise-scale purchasing  │  │
    │  └───────────────────────────────────────────────────────────┘  │
    │                                                                 │
    │                    PRIMARY ACTIVITIES                           │
    │  ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │
    │  │ Inbound  │          │ Outbound │Marketing │          │      │
    │  │ Logistics│Operations│ Logistics│ & Sales  │ Service  │ ═══► │
    │  │          │          │          │          │          │  M   │
    │  │ Barber   │ 14 sites │ Malls +  │UNSTOPPA- │ Products │  A   │
    │  │ School   │ Franchise│ Outlets  │BLE 2026  │ KotR     │  R   │
    │  │ TD Bank  │ KotR     │ Houston  │ Content  │ Events   │  G   │
    │  │ Products │ 10% eq.  │ H'ville  │ Media    │ Loyalty  │  I   │
    │  │          │          │          │          │          │  N   │
    │  └──────────┴──────────┴──────────┴──────────┴──────────┘      │
    └─────────────────────────────────────────────────────────────────┘
    """)

    _header("PRIMARY ACTIVITIES")
    for activity in VALUE_CHAIN["primary_activities"]:
        _sub(f"{activity['activity']} — {activity['description']}")
        for line in activity["details"].split("\n"):
            print(f"  │ {line}")
        _end()

    _header("SUPPORT ACTIVITIES")
    for activity in VALUE_CHAIN["support_activities"]:
        _sub(activity["activity"])
        for line in activity["details"].split("\n"):
            print(f"  │ {line}")
        _end()


# ════════════════════════════════════════════════════════════════════════
#  STRATEGIC IMPLICATIONS — What This Means for YOUR Shop
# ════════════════════════════════════════════════════════════════════════

def print_implications():
    """Print strategic implications derived from all three Porter frameworks."""
    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "STRATEGIC IMPLICATIONS".center(68) + "▓")
    print("▓" + "What Porter's Frameworks Mean for YOUR Position".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)

    _header("I. FIVE FORCES IMPLICATIONS — Where to Compete")
    print("""
  The barbershop industry is MODERATELY ATTRACTIVE (15/25 force pressure).
  Two forces are high (new entrants, rivalry), two are low (suppliers,
  substitutes), one is moderate (buyers).

  STRATEGIC RESPONSE:
    1. You cannot fight new entrants — they will keep coming.
       Instead, RAISE SWITCHING COSTS for your clients:
       - Proprietary OS with client history = they lose data if they leave
       - Deposit system = financial commitment to future visits
       - Relationship depth = a solo operator advantage No Grease can't match

    2. Rivalry is intense but SEGMENTED.
       You don't compete with No Grease directly — different tier.
       Your real competitors are other solo suite operators in South Park.
       Focus intel collection on THAT segment.

    3. Substitute threat is LOW — lean into the cultural experience.
       No app replaces the barbershop. Make your suite a destination.
    """)

    _header("II. GENERIC STRATEGY IMPLICATIONS — How to Compete")
    print("""
  No Grease = Broad Differentiation (scale + culture + school)
  You = Focused Differentiation (premium + technology + mastery)

  THESE DO NOT DIRECTLY COLLIDE.

  Porter's key insight: firms with DIFFERENT generic strategies can
  coexist profitably in the same industry because they serve different
  value propositions.

  WHERE YOU WIN AGAINST NO GREASE:
    - Personal relationship (1 barber, not a franchise rotation)
    - Technology (proprietary OS vs. their standard booking)
    - Flexibility (you adapt instantly; they have franchise protocols)
    - Premium positioning ($65 combo vs. their $30-45 standard)

  WHERE NO GREASE WINS AGAINST YOU:
    - Scale (14 locations vs. 1 suite)
    - Brand recognition (25 years vs. building)
    - Talent pipeline (barber school vs. solo)
    - Capital access (TD Bank + franchise fees vs. self-funded)

  THE PLAY: Don't try to beat them at their game.
  Win at yours. Focused differentiation. Premium solo mastery.
    """)

    _header("III. VALUE CHAIN IMPLICATIONS — Where to Create Value")
    print("""
  No Grease's value chain reveals THREE exploitable gaps:

  GAP 1: NO PROPRIETARY TECHNOLOGY
    No Grease has Razored Technologies (Ed Washington's startup)
    but NO evidence of a deployed proprietary booking/ops system.
    They use standard platforms.

    YOUR MOVE: Your proprietary OS is a genuine competitive weapon.
    No one in the Charlotte market has this. This is Porter's
    'technology development' support activity — and you own it.

  GAP 2: FRANCHISE STANDARDIZATION = IMPERSONAL
    14 locations means standardized experience. The same cut,
    the same script, the same flow. Efficient but not intimate.

    YOUR MOVE: The solo suite experience is inherently personal.
    Client knows YOU. You know THEIR head. No rotation, no
    franchise manual overriding your judgment. This is the
    'operations' primary activity — differentiated by design.

  GAP 3: CONTENT CADENCE IS SLOWING
    No 2026 Sneaker Ball. No podcast appearances. Blog post is
    good but singular. 'The Line Up' series hasn't had new episodes.

    YOUR MOVE: If you build content, you're not competing against
    an active content machine. The field is quieter than expected.
    """)

    _header("IV. PORTER'S COMPETITIVE ADVANTAGE TEST")
    print("""
  Porter defines competitive advantage as performing activities
  DIFFERENTLY or performing DIFFERENT activities than rivals.

  No Grease performs STANDARD barbershop activities at SCALE.
  That's their advantage: scale economics + brand.

  You perform DIFFERENT activities:
    - Proprietary technology (no one else has this)
    - Data-driven competitive intelligence (this system)
    - Deposit-forward revenue model
    - Wholesale product margins (50-70%)
    - Solo mastery positioning

  VERDICT: You have legitimate competitive advantage in a
  focused segment that No Grease's broad strategy cannot serve
  efficiently. Porter would approve.
    """)

    _header("V. 30-60-90 DAY PORTER-DRIVEN ACTION PLAN")
    print("""
  30 DAYS — FORTIFY YOUR FOCUS POSITION
    [ ] Complete migration from Booksy to proprietary OS
    [ ] Document your value chain (where YOU create value)
    [ ] Set premium pricing floor at $45 minimum for all cuts
    [ ] Activate deposit system as switching cost mechanism

  60 DAYS — EXPLOIT THEIR GAPS
    [ ] Launch content while No Grease's content is quiet
    [ ] Build client profiles in your OS (data = lock-in)
    [ ] Track 5 solo operators in South Park (your real rivals)
    [ ] Test premium add-on services ($20+ beard oil treatment)

  90 DAYS — SCALE YOUR FOCUS
    [ ] Evaluate transition from suite to shop (if margins support)
    [ ] Develop signature service (your 'Knights of the Razor')
    [ ] Build referral system in proprietary OS
    [ ] Re-run Porter analysis with updated warehouse data
    """)


# ════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════

def print_full_analysis():
    """Print the complete Porter analysis."""
    print_five_forces()
    print_generic_strategies()
    print_value_chain()
    print_implications()

    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "END OF PORTER ANALYSIS".center(68) + "▓")
    print("▓" + "Intelligence drives strategy. Strategy drives action.".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)
    print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--five-forces" in args:
        print_five_forces()
    elif "--generic" in args:
        print_generic_strategies()
    elif "--value-chain" in args:
        print_value_chain()
    elif "--implications" in args:
        print_implications()
    else:
        print_full_analysis()
