"""THE COUNCIL — Exit Strategy Planning Board

Five advisors. Each grounded in a doctrine pillar.
Each pulls live warehouse data. Each has a different lens.
Together they give you the full picture before you make a move.

This is your boardroom. Talk to them.

Run:  python council.py                     # Full council session
      python council.py --advisor <name>    # Consult one advisor
      python council.py --vote              # Council votes on readiness
      python council.py --brief             # Quick status from all five

Advisors:
  strategist   — The Strategist (Strategic Process)
  comptroller  — The Comptroller (Financial Feasibility)
  intel        — The Intel Officer (Market Intelligence)
  operator     — The Operator (Execution & Logistics)
  brand        — The Brand Architect (Positioning & Retention)

Governed by: doctrine.py — every advisor speaks from doctrine.
"""

import sys
from warehouse.db import get_connection
from strategy import YOUR_SHOP, _q


# ════════════════════════════════════════════════════════════════════════
#  COUNCIL CONFIGURATION
# ════════════════════════════════════════════════════════════════════════

def _header(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}")


def _advisor_header(name, title, doctrine_pillar):
    print(f"""
  ┌──────────────────────────────────────────────────────────────────────┐
  │  {name:67s}│
  │  {title:67s}│
  │  Doctrine: {doctrine_pillar:56s}│
  └──────────────────────────────────────────────────────────────────────┘""")


# ════════════════════════════════════════════════════════════════════════
#  SHARED DATA — pulled once, used by all advisors
# ════════════════════════════════════════════════════════════════════════

def _pull_council_data():
    """Pull all warehouse data the council needs in one pass."""
    data = {}

    # Your position
    data["annual_gross"] = YOUR_SHOP.get("annual_gross", 42000)
    data["monthly_gross"] = data["annual_gross"] / 12
    data["daily_gross"] = data["annual_gross"] / 50 / 5  # 50 weeks, 5 days
    data["fade_price"] = YOUR_SHOP["prices"]["Fade"]
    data["combo_price"] = YOUR_SHOP["prices"]["Haircut + Beard Combo"]
    data["has_wholesale"] = YOUR_SHOP.get("revenue_model", {}).get("wholesale_membership", False)
    data["has_deposits"] = YOUR_SHOP.get("deposits", False)
    data["has_proprietary_os"] = YOUR_SHOP.get("booking_os", {}).get("type") == "proprietary"
    data["migrating_from"] = YOUR_SHOP.get("booking_os", {}).get("migrating_from")
    data["setup"] = YOUR_SHOP.get("setup", "Unknown")
    data["years_exp"] = YOUR_SHOP.get("years_experience", 0)

    # Market data
    data["competitor_count"] = _q(
        "SELECT COUNT(*) as n FROM competitors WHERE status = 'Active'"
    )[0]["n"]

    data["avg_fade"] = _q(
        "SELECT ROUND(AVG(price), 2) as avg FROM price_history WHERE service_name = 'Fade'"
    )[0]["avg"] or 0

    data["max_fade"] = _q(
        "SELECT ROUND(MAX(price), 2) as mx FROM price_history WHERE service_name = 'Fade'"
    )[0]["mx"] or 0

    data["neighborhoods"] = _q("""
        SELECT c.neighborhood, COUNT(DISTINCT c.competitor_id) as shops,
               ROUND(AVG(ph.price), 2) as avg_fade
        FROM competitors c
        LEFT JOIN price_history ph ON ph.competitor_id = c.competitor_id
            AND ph.service_name = 'Fade'
        WHERE c.status = 'Active'
        GROUP BY c.neighborhood
        ORDER BY shops ASC
    """)

    data["franchise_count"] = _q("""
        SELECT COUNT(DISTINCT competitor_id) as n FROM competitors
        WHERE company_name LIKE 'No Grease%' OR company_name LIKE 'Da Lucky Spot%'
    """)[0]["n"]

    data["independent_count"] = data["competitor_count"] - data["franchise_count"]

    data["social_leaders"] = _q("""
        SELECT c.company_name, cs.followers, cs.engagement_rate
        FROM competitor_social cs
        JOIN competitors c ON c.competitor_id = cs.competitor_id
        ORDER BY cs.followers DESC LIMIT 5
    """)

    data["recent_moves"] = _q("""
        SELECT c.company_name, cm.move_type, cm.description
        FROM competitor_moves cm
        JOIN competitors c ON c.competitor_id = cm.competitor_id
        ORDER BY cm.move_date DESC LIMIT 5
    """)

    data["barber_count"] = _q("SELECT COUNT(*) as n FROM barbers")[0]["n"]

    data["review_avg"] = _q(
        "SELECT ROUND(AVG(rating), 1) as avg FROM review_snapshots"
    )[0]["avg"] or 0

    return data


# ════════════════════════════════════════════════════════════════════════
#  ADVISOR 1: THE STRATEGIST
# ════════════════════════════════════════════════════════════════════════

def advisor_strategist(d):
    """The Strategist — Strategic Process: Analysis, Choice, Implementation, Control."""
    _advisor_header(
        "THE STRATEGIST",
        "Direction, timing, and the shape of the move",
        "Strategic Process (Analysis → Choice → Implementation → Control)"
    )

    print(f"""
  ANALYSIS — Where are you?

    You are a solo operator in a suite generating ${d['annual_gross']:,}/year.
    That's ${d['monthly_gross']:,.0f}/month, ${d['daily_gross']:,.0f}/day.
    You have {d['years_exp']} years of experience and a core client base.
    You're not starting from zero. You're starting from a position of strength.

    But the suite has a ceiling. No walk-ins. No chair rentals. No retail
    display space. No signage. No brand presence on the street. The suite
    is a cost center that caps your upside.

  CHOICE — Where could you go?

    Option A: STAY IN THE SUITE
      Pros:  Low overhead, low risk, predictable
      Cons:  Capped at ~$55K even with retail + premium
      Verdict: Safe. But you didn't build an OS and a warehouse to be safe.

    Option B: JUMP TO A SHOP NOW
      Pros:  Immediate growth potential
      Cons:  No financial runway proven, no chair renter lined up,
             lease liability with no track record of shop-level revenue
      Verdict: Reckless. The doctrine says test feasibility first.

    Option C: THE RAMP (12-month bridge)
      Pros:  You build proof while earning, overlap so you never go dark,
             landlord gets a financial package not a prayer
      Cons:  Slower. Requires discipline.
      Verdict: This is the doctrine-aligned path.
               Analysis → Choice → Implementation → Control.
               You don't skip steps.

  IMPLEMENTATION — How do you get there?

    The ramp has 5 phases. Each one is a gate.
    You don't move to the next phase until the current one is cleared.

      Phase 1 (STACK):     Revenue layers in the suite
      Phase 2 (PROVE):     Financial case from your OS
      Phase 3 (SCOUT):     Find the space
      Phase 4 (BRIDGE):    Parallel operations
      Phase 5 (ESTABLISH): First 90 days in the shop

    Run: python strategy.py --section exit-plan
    for the full phase breakdown.

  CONTROL — Are you on track?

    Your OS is the control system. Every transaction, every deposit,
    every retail sale feeds back into the intelligence loop.
    The warehouse tracks the environment. The OS tracks you.
    Together they tell you: are you ready, or not yet?

  MY RECOMMENDATION:
    Start Phase 1 immediately. Stack retail + premium + deposit coverage.
    Set a 90-day checkpoint. If monthly gross hits $4,500+, you're on pace.
    If not, adjust before committing to a lease.
""")


# ════════════════════════════════════════════════════════════════════════
#  ADVISOR 2: THE COMPTROLLER
# ════════════════════════════════════════════════════════════════════════

def advisor_comptroller(d):
    """The Comptroller — Financial feasibility, risk, and the numbers."""
    _advisor_header(
        "THE COMPTROLLER",
        "The numbers don't lie. The numbers don't care about your feelings.",
        "Core Mission (Measurable Objectives / SMART Goals)"
    )

    # Suite cost estimate
    suite_weekly = 300  # estimated suite rent
    suite_monthly = suite_weekly * 4.33
    suite_annual = suite_monthly * 12

    # Shop cost modeling
    shop_rent_low = 2000
    shop_rent_high = 4000
    shop_utilities = 300
    shop_insurance = 200
    shop_supplies = 200
    shop_overhead_low = shop_rent_low + shop_utilities + shop_insurance + shop_supplies
    shop_overhead_high = shop_rent_high + shop_utilities + shop_insurance + shop_supplies

    # Chair rental income
    chair_rent_weekly = 250
    chair_rent_monthly = chair_rent_weekly * 4.33

    # Retail margin
    retail_margin_conservative = 300
    retail_margin_moderate = 600

    # Current net
    current_net = d["monthly_gross"] - suite_monthly

    print(f"""
  CURRENT P&L (estimated):
    ┌────────────────────────────────────────────────────────────────┐
    │                         MONTHLY        ANNUAL                 │
    │  Gross revenue:         ${d['monthly_gross']:>7,.0f}       ${d['annual_gross']:>7,}                │
    │  Suite rent:            ${suite_monthly:>7,.0f}       ${suite_annual:>7,.0f}                │
    │  Supplies:              $   100       $  1,200                │
    │  ────────────────────────────────────────────────────────────  │
    │  Estimated net:         ${current_net - 100:>7,.0f}       ${(current_net - 100) * 12:>7,.0f}                │
    └────────────────────────────────────────────────────────────────┘

  THE SHOP MATH — Three scenarios:

  Scenario 1: LEAN SHOP ($2,000/mo rent)
    Shop overhead:        ${shop_overhead_low:,}/mo
    Your services:        ${d['monthly_gross']:,.0f}/mo
    Retail margin:        ${retail_margin_conservative:,}/mo
    Premium tier:         $650/mo
    Chair rental x1:      ${chair_rent_monthly:,.0f}/mo
    ─────────────────────────────────
    Gross in:             ${d['monthly_gross'] + retail_margin_conservative + 650 + chair_rent_monthly:,.0f}/mo
    Overhead:             ${shop_overhead_low:,}/mo
    NET:                  ${d['monthly_gross'] + retail_margin_conservative + 650 + chair_rent_monthly - shop_overhead_low:,.0f}/mo
    vs Suite net:         ${current_net - 100:,.0f}/mo
    DELTA:                ${d['monthly_gross'] + retail_margin_conservative + 650 + chair_rent_monthly - shop_overhead_low - (current_net - 100):+,.0f}/mo

  Scenario 2: MID-RANGE SHOP ($3,000/mo rent)
    Shop overhead:        ${shop_overhead_low + 1000:,}/mo
    Your services:        ${d['monthly_gross']:,.0f}/mo
    Retail margin:        ${retail_margin_moderate:,}/mo
    Premium tier:         $800/mo
    Chair rental x2:      ${chair_rent_monthly * 2:,.0f}/mo
    ─────────────────────────────────
    Gross in:             ${d['monthly_gross'] + retail_margin_moderate + 800 + chair_rent_monthly * 2:,.0f}/mo
    Overhead:             ${shop_overhead_low + 1000:,}/mo
    NET:                  ${d['monthly_gross'] + retail_margin_moderate + 800 + chair_rent_monthly * 2 - (shop_overhead_low + 1000):,.0f}/mo
    vs Suite net:         ${current_net - 100:,.0f}/mo
    DELTA:                ${d['monthly_gross'] + retail_margin_moderate + 800 + chair_rent_monthly * 2 - (shop_overhead_low + 1000) - (current_net - 100):+,.0f}/mo

  Scenario 3: PREMIUM LOCATION ($4,000/mo rent)
    Shop overhead:        ${shop_overhead_high:,}/mo
    Your services:        ${d['monthly_gross']:,.0f}/mo
    Retail margin:        ${retail_margin_moderate:,}/mo
    Premium tier:         $975/mo
    Chair rental x3:      ${chair_rent_monthly * 3:,.0f}/mo
    ─────────────────────────────────
    Gross in:             ${d['monthly_gross'] + retail_margin_moderate + 975 + chair_rent_monthly * 3:,.0f}/mo
    Overhead:             ${shop_overhead_high:,}/mo
    NET:                  ${d['monthly_gross'] + retail_margin_moderate + 975 + chair_rent_monthly * 3 - shop_overhead_high:,.0f}/mo
    vs Suite net:         ${current_net - 100:,.0f}/mo
    DELTA:                ${d['monthly_gross'] + retail_margin_moderate + 975 + chair_rent_monthly * 3 - shop_overhead_high - (current_net - 100):+,.0f}/mo

  RISK ANALYSIS:
    What if chair rentals don't fill for 60 days?
    You're absorbing full shop overhead on services alone.

    Scenario 1 gap: ${shop_overhead_low - d['monthly_gross']:,.0f}/mo shortfall (need ${(shop_overhead_low - d['monthly_gross']) * 3:,.0f} reserve)
    Scenario 2 gap: ${shop_overhead_low + 1000 - d['monthly_gross']:,.0f}/mo shortfall (need ${(shop_overhead_low + 1000 - d['monthly_gross']) * 3:,.0f} reserve)

    MINIMUM CASH RESERVE BEFORE SIGNING A LEASE:
    3 months of shop overhead WITHOUT chair rental income.
    That's ${shop_overhead_low * 3:,} - ${shop_overhead_high * 3:,}.

  THE BRIDGE COST:
    Overlap period (2 months of double rent):
    Suite: ${suite_monthly * 2:,.0f}  +  Shop: ${shop_rent_low * 2:,} - ${shop_rent_high * 2:,}
    Total bridge cost: ${suite_monthly * 2 + shop_rent_low * 2:,.0f} - ${suite_monthly * 2 + shop_rent_high * 2:,.0f}

  DEPOSIT BOOK AS LEVERAGE:
    A deposit book showing 60+ days of forward-booked revenue is
    the single strongest document in your lease application.
    It proves demand exists independent of location.

  MY RECOMMENDATION:
    Lean shop (Scenario 1) is your entry point. $2,000-2,500/mo rent.
    Get 1 chair renter before you sign. That's $1,000/mo toward overhead
    from day one. With retail + premium, you're net positive immediately.
    Don't reach for Scenario 3 on the first move.
""")


# ════════════════════════════════════════════════════════════════════════
#  ADVISOR 3: THE INTEL OFFICER
# ════════════════════════════════════════════════════════════════════════

def advisor_intel(d):
    """The Intel Officer — Market intelligence, competitor landscape, threats."""
    _advisor_header(
        "THE INTEL OFFICER",
        "What the market is doing while you're planning",
        "Intelligence Engine (Data → Information → Knowledge → Intelligence)"
    )

    print(f"""
  MARKET LANDSCAPE:
    Competitors tracked:  {d['competitor_count']}
    Franchise operations: {d['franchise_count']}
    Independents:         {d['independent_count']}
    Market avg fade:      ${float(d['avg_fade']):,.2f}
    Market high fade:     ${float(d['max_fade']):,.2f}
    YOUR fade:            ${d['fade_price']}
    Position:             {'ABOVE MARKET' if d['fade_price'] > float(d['avg_fade']) else 'AT MARKET' if d['fade_price'] == float(d['avg_fade']) else 'BELOW MARKET'}

  WHAT THE COMPETITION IS DOING:""")

    if d["recent_moves"]:
        for move in d["recent_moves"]:
            print(f"    {move['company_name']:30s}  [{move['move_type']}]")
            print(f"      {move['description']}")
    else:
        print(f"    No recent moves logged. Run agents to refresh.")

    print(f"\n  SOCIAL LANDSCAPE:")
    if d["social_leaders"]:
        print(f"  {'Shop':35s} {'Followers':>10s} {'Engagement':>12s}")
        print(f"  {'─'*60}")
        for s in d["social_leaders"]:
            eng = f"{float(s['engagement_rate']):.1f}%" if s["engagement_rate"] else "N/A"
            print(f"  {s['company_name']:35s} {s['followers']:>10,}   {eng:>10s}")
    else:
        print(f"    No social data. Run the social agent.")

    print(f"""
  TERRITORY ANALYSIS — Where to plant the flag:""")

    low_density = [n for n in d["neighborhoods"] if n["shops"] <= 1]
    high_value = [n for n in low_density if n["avg_fade"] and float(n["avg_fade"]) >= 40]

    if high_value:
        print(f"\n  HIGH-VALUE, LOW-COMPETITION areas (1 shop, avg fade >= $40):")
        for area in high_value[:8]:
            print(f"    {area['neighborhood']:25s}  avg fade ${float(area['avg_fade']):,.0f}  ({area['shops']} shop)")
    else:
        print(f"    No high-value gaps found in current data.")

    # Franchise threat analysis
    print(f"""
  FRANCHISE THREAT:
    No Grease has {d['franchise_count']} location(s) in the warehouse.
    They are the gorilla in Charlotte's Black barbershop market.
    They have brand, they have locations, they have social following.

    BUT: They are a FRANCHISE. Their barbers are employees, not owners.
    Their incentive structure is different from yours.
    Their clients are buying a brand. Your clients are buying YOU.

    WHAT THIS MEANS FOR YOUR SHOP:
    Don't open next to a No Grease. Don't compete on their terms.
    Find the neighborhoods they haven't reached yet.
    Your advantage is: owner-operator + proprietary OS + premium positioning.
    That's a different value proposition entirely.

  TALENT POOL:
    Barbers tracked in warehouse: {d['barber_count']}
    These are potential chair renters. Study their specialties,
    their client bases, their current situations.
    The best chair renter is someone who brings their own clients.

  REVIEW LANDSCAPE:
    Market average rating: {d['review_avg']}/5.0
    Your target: 4.8+ on Google from day one of the shop.
    Migrate your best suite reviews to the new location.

  MY RECOMMENDATION:
    The data says there are gaps in the market. Low-density neighborhoods
    with premium pricing tolerance. Your OS gives you something nobody
    else has — real-time intel on your own business AND the competition.
    Use the client zip code data from your OS to pick the location.
    Let the data choose, not your gut.
""")


# ════════════════════════════════════════════════════════════════════════
#  ADVISOR 4: THE OPERATOR
# ════════════════════════════════════════════════════════════════════════

def advisor_operator(d):
    """The Operator — Execution, logistics, timing, and operational readiness."""
    _advisor_header(
        "THE OPERATOR",
        "Plans don't cut hair. Execution does.",
        "Strategic Implementation (Structure, Operations, Leadership)"
    )

    os_ready = d["has_proprietary_os"]
    booksy_migrated = d["migrating_from"] is None

    print(f"""
  OPERATIONAL READINESS CHECK:

    ┌────────────────────────────────────────────────────────────────┐
    │  System                    Status              Blocker?       │
    ├────────────────────────────────────────────────────────────────┤
    │  Proprietary OS            {'DEPLOYED' if os_ready else 'NOT READY':20s} {'NO' if os_ready else 'YES — CRITICAL':14s} │
    │  Booksy migration          {'COMPLETE' if booksy_migrated else 'IN PROGRESS':20s} {'NO' if booksy_migrated else 'YES — ACTIVE':14s} │
    │  Deposit system            {'ACTIVE' if d['has_deposits'] else 'NOT SET UP':20s} {'NO' if d['has_deposits'] else 'YES':14s} │
    │  Wholesale account         {'ACTIVE' if d['has_wholesale'] else 'NOT SET UP':20s} {'NO' if d['has_wholesale'] else 'YES':14s} │
    │  Chair renter recruited    {'UNKNOWN':20s} {'CHECK':14s} │
    │  Lease signed              {'NO':20s} {'PHASE 4':14s} │
    └────────────────────────────────────────────────────────────────┘

  CRITICAL PATH — What blocks everything else:""")

    blockers = []
    if not booksy_migrated:
        blockers.append(
            "BOOKSY MIGRATION: You cannot run a shop on someone else's platform.\n"
            "      Your OS is the backbone. Every client, every transaction, every\n"
            "      deposit must flow through YOUR system. Complete this first."
        )
    if not os_ready:
        blockers.append(
            "PROPRIETARY OS: Not deployed. This is the #1 competitive weapon.\n"
            "      No point opening a shop without your own operational system."
        )

    if blockers:
        for i, b in enumerate(blockers, 1):
            print(f"\n    BLOCKER {i}: {b}")
    else:
        print(f"\n    No critical blockers. OS is deployed, migration complete.")

    print(f"""
  SHOP BUILD-OUT TIMELINE (realistic):

    Week 1-2:   Lease negotiation + signing
                Landlord wants: P&L, deposit book, credit check, references
                You want: 2-3yr lease, tenant improvement allowance,
                         60-day build-out period included in lease

    Week 3-6:   Build-out (if needed)
                Chairs, mirrors, waiting area, retail display
                Plumbing (if adding sinks), electrical, signage
                Budget: $5,000-15,000 depending on condition
                Ask landlord for TI (tenant improvement) dollars

    Week 5-6:   Recruit chair renter #1
                Source from warehouse barber intel ({d['barber_count']} tracked)
                Interview for: client base, reliability, style fit
                Terms: $250/wk, month-to-month, supplies included or not

    Week 7-8:   Soft open
                Move YOUR premium clients first
                Keep the suite for remaining clients (overlap period)
                Chair renter starts

    Week 9-12:  Full migration
                All clients in the shop
                Suite lease ends
                Systems fully operational in new space

  DAY-ONE OPERATIONS CHECKLIST:
    □ OS configured for shop (new address, multi-chair scheduling)
    □ Payment processing set up at new location
    □ Google Business profile created / address updated
    □ Insurance policy active
    □ Retail inventory stocked and displayed
    □ Chair rental agreement signed with renter #1
    □ Signage installed
    □ Client communication sent (new location, same service, same you)

  THE BOOKSY QUESTION:
    {'You are still on Booksy. This is the most urgent operational item.' if not booksy_migrated else 'Booksy migration noted as pending. Push to complete before Phase 3.'}
    Every day on Booksy is a day your data lives on someone else's server.
    Every client who books through Booksy is a client Booksy can market to.
    Your OS eliminates this dependency entirely.

  MY RECOMMENDATION:
    {'Complete the Booksy migration. That is job #1. Nothing else matters until your OS is the single source of truth.' if not booksy_migrated else 'OS is your foundation. Start building the revenue layers (Phase 1) and get your 6-month P&L generating from the OS. The operational transition is straightforward once the numbers are proven.'}
""")


# ════════════════════════════════════════════════════════════════════════
#  ADVISOR 5: THE BRAND ARCHITECT
# ════════════════════════════════════════════════════════════════════════

def advisor_brand(d):
    """The Brand Architect — Positioning, client retention, and brand continuity."""
    _advisor_header(
        "THE BRAND ARCHITECT",
        "Your clients chose YOU. The shop is just the room.",
        "Strategic Leadership (Opportunity Creation)"
    )

    print(f"""
  THE BRAND REALITY:

    You are not a suite. You are not a location.
    You are a {d['years_exp']}-year veteran with core clients who chose you.
    They followed you to the suite. They will follow you to the shop.
    IF you handle the transition right.

  CLIENT RETENTION STRATEGY:

    THE CARDINAL RULE: No surprises.

    Phase 1 — SEED (60 days before move):
      Start mentioning "exciting changes coming" to your core clients.
      Don't announce. Tease. Let them ask.
      "I'm working on something for us."
      This creates anticipation, not anxiety.

    Phase 2 — INFORM (30 days before move):
      Personal messages to your top 20 clients.
      Not a mass text. Individual. By name.
      "I'm opening my own shop at [location]. Same me, more room,
       better experience. Your appointments carry over. Nothing changes
       except the address."

    Phase 3 — MIGRATE (transition period):
      Move your highest-value clients FIRST.
      They anchor the shop. They tell others.
      Their reviews establish the new location.
      Keep the suite open for stragglers — don't force anyone.

    Phase 4 — ANCHOR (first 30 days in shop):
      Grand opening event for existing clients first (not public).
      Make them feel like insiders, not afterthoughts.
      Then public grand opening the following week.

  BRAND POSITIONING IN THE SHOP:

    Suite positioning:     "Premium barber, by appointment"
    Shop positioning:      "Premium barbershop, owner-operated"

    What changes:
      + Retail display (product becomes part of the brand)
      + Waiting area (the experience starts before the chair)
      + Signage (street presence you never had)
      + Chair renters (curated talent, your standards)
      + Walk-ins (new client acquisition channel)

    What stays the same:
      Your hands. Your standards. Your price point.
      Your relationship with every core client.

  THE INSTAGRAM QUESTION:

    Current followers: {d.get('instagram_followers', 0) or 'Not tracking'}
    Market leaders:""")

    if d["social_leaders"]:
        for s in d["social_leaders"][:3]:
            print(f"      {s['company_name']:35s}  {s['followers']:,} followers")
    else:
        print(f"      No social data in warehouse.")

    print(f"""
    You said "not building influencer dependence." Good.
    But a shop needs PRESENCE, not influence.
    Before/after cuts. The space. The products.
    You don't need to be an influencer. You need to be findable.
    Target: 500 followers by shop opening. That's enough to be credible.
    Your OS + warehouse is your real competitive weapon, not Instagram.

  RETAIL AS BRAND EXTENSION:

    In the suite, product is an afterthought. You hand them a bottle.
    In the shop, product is part of the environment.
    A retail display says: "This isn't just a haircut. This is grooming."
    Every product on that shelf reinforces your premium positioning.
    Wholesale margin is the financial play. Brand elevation is the strategic play.

  NAME THE SHOP:

    Your strategy.py still says: name = "Your Shop"
    {'A shop without a name is not a brand. Name it.' if YOUR_SHOP.get('name') == 'Your Shop' else f'Current name: {YOUR_SHOP["name"]}'}
    The name should reflect:
      - Premium positioning (not "Cutz" or "Clipz")
      - Owner identity (it's YOUR shop)
      - Longevity (you've been doing this {d['years_exp']} years)

  MY RECOMMENDATION:
    Name the shop. That's the first brand decision.
    Start the client seed phase 60 days before any move.
    Your clients are your moat. Protect the relationship above everything.
""")


# ════════════════════════════════════════════════════════════════════════
#  COUNCIL VOTE — Readiness assessment
# ════════════════════════════════════════════════════════════════════════

def council_vote(d):
    """All five advisors vote on exit readiness."""
    _header("COUNCIL VOTE — Exit Readiness")

    votes = []

    # Strategist vote
    strat_ready = d["monthly_gross"] >= 4000
    votes.append(("THE STRATEGIST", strat_ready,
                  "Monthly gross must be $4,000+ with revenue layers proven"
                  if not strat_ready else
                  "Revenue layers stacked. Phase 1 target met."))

    # Comptroller vote
    # Can't verify cash reserve, so conservative
    comp_ready = d["monthly_gross"] >= 4000 and d["has_deposits"]
    votes.append(("THE COMPTROLLER", comp_ready,
                  "Need $4K+/mo gross AND deposits active to prove financial case"
                  if not comp_ready else
                  "Financial foundation is there. Build the 6-month P&L."))

    # Intel vote
    intel_ready = d["competitor_count"] >= 15 and len([
        n for n in d["neighborhoods"] if n["shops"] <= 1 and n["avg_fade"] and float(n["avg_fade"]) >= 35
    ]) >= 3
    votes.append(("THE INTEL OFFICER", intel_ready,
                  "Need 15+ competitors tracked and 3+ opportunity neighborhoods identified"
                  if not intel_ready else
                  "Market is mapped. Opportunity zones identified."))

    # Operator vote
    op_ready = d["has_proprietary_os"] and d["migrating_from"] is None
    votes.append(("THE OPERATOR", op_ready,
                  "OS must be deployed AND Booksy migration complete"
                  if not op_ready else
                  "Systems are go. Operational foundation is solid."))

    # Brand vote
    brand_ready = YOUR_SHOP.get("name") != "Your Shop"
    votes.append(("THE BRAND ARCHITECT", brand_ready,
                  "Name the shop. Can't build a brand around 'Your Shop'."
                  if not brand_ready else
                  f"Brand identity established: {YOUR_SHOP['name']}"))

    yes_count = sum(1 for _, v, _ in votes if v)
    total = len(votes)

    print(f"\n  QUESTION: Is this organization ready to begin the exit ramp?")
    print(f"")
    for name, vote, reason in votes:
        icon = "YES" if vote else "NO "
        marker = "■" if vote else "□"
        print(f"  {marker} {name:25s}  [{icon}]")
        print(f"    {reason}")
        print()

    print(f"  ────────────────────────────────────────────────")
    print(f"  VOTE: {yes_count}/{total} READY")
    print()

    if yes_count == total:
        print(f"  COUNCIL DECISION: PROCEED")
        print(f"  All advisors agree. Begin Phase 1 of the exit ramp.")
    elif yes_count >= 3:
        print(f"  COUNCIL DECISION: CONDITIONAL PROCEED")
        print(f"  Majority agrees but gaps remain. Address the NO votes")
        print(f"  while beginning Phase 1.")
    elif yes_count >= 1:
        print(f"  COUNCIL DECISION: NOT YET")
        print(f"  Foundation work needed. Focus on the blockers above.")
        print(f"  Revisit when at least 3 advisors vote YES.")
    else:
        print(f"  COUNCIL DECISION: BUILD FIRST")
        print(f"  Every advisor sees gaps. This is Phase 0.")
        print(f"  Stack the foundation before thinking about the exit.")

    print()


# ════════════════════════════════════════════════════════════════════════
#  COUNCIL BRIEF — Quick status from all five
# ════════════════════════════════════════════════════════════════════════

def council_brief(d):
    """Quick one-liner from each advisor."""
    _header("COUNCIL BRIEF — Quick Read")

    briefs = [
        ("STRATEGIST",
         f"Ramp is the right path. Phase 1 first. ${d['monthly_gross']:,.0f}/mo needs to be $4,500+."),
        ("COMPTROLLER",
         f"Lean shop ($2K rent) + 1 chair renter = net positive. Need ${2700*3:,} reserve minimum."),
        ("INTEL",
         f"{d['competitor_count']} competitors tracked. "
         f"{len([n for n in d['neighborhoods'] if n['shops'] <= 1])} low-density areas identified."),
        ("OPERATOR",
         f"OS: {'DEPLOYED' if d['has_proprietary_os'] else 'PENDING'}. "
         f"Booksy: {'MIGRATED' if d['migrating_from'] is None else 'IN PROGRESS'}. "
         f"{'Systems go.' if d['has_proprietary_os'] and d['migrating_from'] is None else 'Fix before moving.'}"),
        ("BRAND",
         f"Shop name: {'NOT SET — name it' if YOUR_SHOP.get('name') == 'Your Shop' else YOUR_SHOP['name']}. "
         f"Client base: core/loyal. They'll follow if you handle it right."),
    ]

    print()
    for title, brief in briefs:
        print(f"  {title:14s}  {brief}")
    print()


# ════════════════════════════════════════════════════════════════════════
#  FULL COUNCIL SESSION
# ════════════════════════════════════════════════════════════════════════

def full_session():
    """Run the full council session."""
    d = _pull_council_data()

    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "THE COUNCIL".center(68) + "▓")
    print("▓" + "Exit Strategy Planning Board".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" + "Five advisors. One doctrine. Your decision.".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)

    advisor_strategist(d)
    advisor_comptroller(d)
    advisor_intel(d)
    advisor_operator(d)
    advisor_brand(d)
    council_vote(d)

    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "END OF COUNCIL SESSION".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)
    print()
    print("  Run: python council.py --advisor <name>   for individual consult")
    print("  Run: python council.py --vote              for readiness vote")
    print("  Run: python council.py --brief             for quick status")
    print()


# ════════════════════════════════════════════════════════════════════════
#  ADVISOR REGISTRY
# ════════════════════════════════════════════════════════════════════════

ADVISORS = {
    "strategist": advisor_strategist,
    "comptroller": advisor_comptroller,
    "intel": advisor_intel,
    "operator": advisor_operator,
    "brand": advisor_brand,
}


# ════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]

    d = _pull_council_data()

    if "--advisor" in args:
        idx = args.index("--advisor")
        if idx + 1 < len(args):
            name = args[idx + 1].lower()
            if name in ADVISORS:
                ADVISORS[name](d)
            else:
                print(f"Unknown advisor: {name}")
                print(f"Available: {', '.join(ADVISORS.keys())}")
        else:
            print(f"Available advisors: {', '.join(ADVISORS.keys())}")
    elif "--vote" in args:
        council_vote(d)
    elif "--brief" in args:
        council_brief(d)
    else:
        full_session()
