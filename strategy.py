"""YOUR STRATEGIC MOVES — Competitive playbook generated from warehouse intel.

This is YOUR section. Not the warehouse. Not the agents.
This reads the intelligence and tells you what to DO.

Governed by: doctrine.py — The Doctrine of Strategic Intelligence
  The doctrine defines WHY and HOW we think.
  This file defines WHAT to do about it.

Run:  python strategy.py
      python strategy.py --section pricing
      python strategy.py --section talent
      python strategy.py --section positioning
      python strategy.py --section expansion
      python strategy.py --section threats
      python strategy.py --section quick-wins
      python strategy.py --section doctrine    # Run the doctrine audit
"""

import sys
from warehouse.db import get_connection


# ── YOUR BASELINE ──────────────────────────────────────────────────────
# Configure these to YOUR shop's reality. Everything else is calculated.

YOUR_SHOP = {
    "name": "Your Shop",
    "neighborhood": "South Park",
    "zip_code": "28210",
    "setup": "Solo suite",  # Suite rental, not a full shop yet
    "goal": "Transition from suite to full shop",
    "prices": {
        "Regular Haircut": 40,
        "Fade": 45,
        "Skin Fade": 55,
        "Beard Trim": 20,
        "Kids Haircut": 25,
        "Student Haircut": 25,
        "Haircut + Beard Combo": 65,
    },
    "barbers": 1,  # Solo operator
    "years_experience": 10,
    "annual_gross": 42_000,  # Current gross revenue
    "monthly_gross": 3_500,  # ~$42K / 12
    "client_base": "Core customers — retention phase, not acquisition",
    "deposits": True,  # Taking deposits on future bookings
    "revenue_model": {
        "streams": ["Services", "Grooming products (retail)", "Deposits"],
        "wholesale_membership": True,  # Major producer/wholesaler access
        "retail_strategy": "Grooming + retail — margin play on product",
    },
    "instagram_followers": 0,
    "instagram_strategy": "Limited — not building influencer dependence",
    "booking_platform": "Proprietary OS",
    "booking_os": {
        "type": "proprietary",
        "features": [
            "Live transaction intelligence",
            "Adaptive scheduling from day-to-day patterns",
            "Backed by its own data warehouse",
            "Competitive intelligence integration",
            "Deposit collection on future bookings",
        ],
        "migrating_from": "Booksy",
        "advantage": "No competitor in this market has anything close to this",
    },
    "monthly_rent_budget": None,
}


def _q(query, params=None):
    """Run a query, return list of dicts."""
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


def _move(num, title, detail, urgency="NOW"):
    tag = {"NOW": "🔴", "SOON": "🟡", "LATER": "🟢"}.get(urgency, "⚪")
    print(f"\n  {tag} MOVE #{num}: {title}  [{urgency}]")
    print(f"  {'─' * 60}")
    for line in detail.split("\n"):
        print(f"    {line}")


# ════════════════════════════════════════════════════════════════════════
#  SECTION 1: PRICING STRATEGY
# ════════════════════════════════════════════════════════════════════════

def pricing_strategy():
    _header("PRICING STRATEGY — Where Your Money Is")

    # Market averages
    avgs = _q("""
        SELECT service_name,
               ROUND(AVG(price), 2) as market_avg,
               ROUND(MIN(price), 2) as market_low,
               ROUND(MAX(price), 2) as market_high,
               COUNT(DISTINCT competitor_id) as shop_count
        FROM price_history
        WHERE service_name IN ('Regular Haircut','Fade','Skin Fade','Beard Trim','Kids Haircut','Haircut + Beard Combo')
        GROUP BY service_name
        ORDER BY market_avg DESC
    """)

    # Franchise vs independent
    segments = _q("""
        SELECT
            CASE WHEN c.company_name LIKE 'No Grease%' THEN 'No Grease Franchise'
                 WHEN c.company_name LIKE 'Da Lucky Spot%' THEN 'Da Lucky Spot Chain'
                 ELSE 'Independent'
            END as segment,
            ROUND(AVG(ph.price), 2) as avg_fade
        FROM price_history ph
        JOIN competitors c ON c.competitor_id = ph.competitor_id
        WHERE ph.service_name = 'Fade'
        GROUP BY segment
        ORDER BY avg_fade DESC
    """)

    print("\n  YOUR PRICES vs. THE MARKET:")
    print(f"  {'Service':30s} {'You':>8s} {'Market Avg':>12s} {'Range':>15s} {'Gap':>8s}")
    print(f"  {'─'*75}")

    total_gap = 0
    for row in avgs:
        svc = row["service_name"]
        your_price = YOUR_SHOP["prices"].get(svc)
        if your_price:
            gap = your_price - float(row["market_avg"])
            total_gap += gap
            arrow = "▲" if gap > 0 else "▼" if gap < 0 else "="
            print(f"  {svc:30s} ${your_price:>6.0f}   ${float(row['market_avg']):>9.2f}   "
                  f"${float(row['market_low'])}-${float(row['market_high']):>5.0f}   {arrow}${abs(gap):>.2f}")

    print(f"\n  SEGMENT PRICING (Fade):")
    for s in segments:
        print(f"    {s['segment']:30s}  ${float(s['avg_fade']):.2f}")

    # Strategic recommendations
    fade_avg = next((float(a["market_avg"]) for a in avgs if a["service_name"] == "Fade"), 0)
    your_fade = YOUR_SHOP["prices"].get("Fade", 0)
    skin_avg = next((float(a["market_avg"]) for a in avgs if a["service_name"] == "Skin Fade"), 0)
    combo_avg = next((float(a["market_avg"]) for a in avgs if a["service_name"] == "Haircut + Beard Combo"), 0)

    move_num = 1

    if your_fade < fade_avg:
        gap = fade_avg - your_fade
        _move(move_num, f"RAISE YOUR FADE TO ${fade_avg:.0f}",
              f"You're ${gap:.2f} BELOW market average on fades.\n"
              f"Every fade you cut at ${your_fade} is money left on the table.\n"
              f"No Grease charges $45. Independents average ${fade_avg:.2f}.\n"
              f"Raise to ${fade_avg:.0f} minimum — nobody in this market blinks at that.",
              "NOW")
        move_num += 1

    if YOUR_SHOP["prices"].get("Skin Fade", 0) < skin_avg:
        _move(move_num, f"SKIN FADE PREMIUM — CHARGE ${skin_avg:.0f}+",
              f"Skin fades are the highest-margin cut in the market (avg ${skin_avg:.2f}).\n"
              f"No Grease charges $50. Fade Factory charges $42. You should be at ${skin_avg:.0f}+.\n"
              f"This is a skill premium — clients pay it because not every barber can do it clean.",
              "NOW")
        move_num += 1

    _move(move_num, "ADD A 'FULL SERVICE' / 'ROYAL TREATMENT' TIER",
          f"No Grease's 'Royal Treatment' (facial + skin shave) pulls $75.\n"
          f"Major Barbershop charges $45 for cut + neck shave + scalp massage + steam towel + beer.\n"
          f"Charlotte Barber & Beard gets $65 for hot towel razor shave.\n"
          f"Create a premium package at $60-75 — cut, beard, hot towel, scalp massage.\n"
          f"This one service could be 30% of your revenue.",
          "NOW")
    move_num += 1

    _move(move_num, "KIDS HAIRCUTS — THE GATEWAY DRUG",
          f"Market avg is $24.73. You're at ${YOUR_SHOP['prices'].get('Kids Haircut', 0)}.\n"
          f"Kids cuts bring in the whole family. Dad sees the shop, books his own cut.\n"
          f"Price competitively at $20-25 — this is a customer acquisition cost, not profit center.\n"
          f"Da Lucky Spot does it at $15 (loss leader). Don't go that low.",
          "SOON")
    move_num += 1

    # Neighborhood pricing intelligence
    hoods = _q("""
        SELECT c.neighborhood,
               ROUND(AVG(ph.price), 2) as avg_fade,
               COUNT(DISTINCT c.competitor_id) as shops
        FROM price_history ph
        JOIN competitors c ON c.competitor_id = ph.competitor_id
        WHERE ph.service_name = 'Fade'
        GROUP BY c.neighborhood
        ORDER BY avg_fade DESC
    """)

    print(f"\n  {'─'*70}")
    print(f"  NEIGHBORHOOD PRICING MAP (Fades):")
    print(f"  {'─'*70}")
    print(f"  {'Neighborhood':25s} {'Avg Fade':>10s} {'Shops':>8s} {'Strategy':>25s}")
    for h in hoods:
        avg = float(h["avg_fade"])
        shops = h["shops"]
        if avg >= 40:
            strat = "PREMIUM — charge $40+"
        elif avg >= 32:
            strat = "STANDARD — charge $32-38"
        elif avg >= 25:
            strat = "VALUE — charge $28-32"
        else:
            strat = "BUDGET — underserved"
        print(f"  {h['neighborhood']:25s}   ${avg:>7.2f}   {shops:>5d}   {strat}")


# ════════════════════════════════════════════════════════════════════════
#  SECTION 2: TALENT STRATEGY
# ════════════════════════════════════════════════════════════════════════

def talent_strategy():
    _header("TALENT STRATEGY — Build Your Chair")

    # Barber density by shop
    density = _q("""
        SELECT c.company_name, COUNT(b.barber_id) as barbers,
               c.neighborhood, c.zip_code
        FROM competitors c
        LEFT JOIN barbers b ON b.competitor_id = c.competitor_id AND b.status = 'Active'
        GROUP BY c.company_name, c.neighborhood, c.zip_code
        ORDER BY barbers DESC
        LIMIT 15
    """)

    # Star barbers (with Instagram)
    stars = _q("""
        SELECT b.name, b.instagram_handle, b.seniority, b.specialties,
               c.company_name, b.notes
        FROM barbers b
        JOIN competitors c ON c.competitor_id = b.competitor_id
        WHERE b.instagram_handle IS NOT NULL
        ORDER BY c.company_name
    """)

    # Barber school pipeline
    schools = _q("""
        SELECT company_name, notes FROM competitors
        WHERE company_name LIKE '%School%' OR notes LIKE '%school%' OR notes LIKE '%Academy%'
    """)

    print("\n  COMPETITIVE STAFFING LEVELS:")
    print(f"  {'Shop':40s} {'Barbers':>8s} {'Area':>20s}")
    print(f"  {'─'*70}")
    for d in density[:15]:
        bar = "█" * d["barbers"]
        print(f"  {d['company_name']:40s} {d['barbers']:>5d}  {bar}  {d['neighborhood'] or ''}")

    move_num = 1

    _move(move_num, "YOUR OS IS YOUR RECRUITING PITCH",
          "You built what no other shop in Charlotte has — a proprietary booking OS.\n"
          "Chair rental barbers currently use Booksy/Squire and PAY for it.\n"
          "Your offer: rent a chair AND get access to the OS. No monthly software fee.\n"
          "Your OS tracks their clients, optimizes their schedule, shows them their numbers.\n"
          "Ed Washington (No Grease) gives 10% equity. You give technology.\n"
          "Start with 1-2 chair rentals at $200-300/week + OS access.",
          "SOON")
    move_num += 1

    _move(move_num, "RECRUIT FROM NO GREASE BARBER SCHOOL",
          "3,000+ graduates from No Grease School of Tonsorial Arts.\n"
          "12-18 month program, 1,528 hours. Fresh graduates need chairs.\n"
          "Shaun 'Lucky' Corbett graduated there in 2005 — now has 5 Walmart locations.\n"
          "Contact: (980) 819-9481, 3731 N Sharon Amity Rd.\n"
          "Your pitch: chair rental + your OS + mentorship from a 10-year barber.\n"
          "Nobody else in this market can offer that stack.",
          "SOON")
    move_num += 1

    _move(move_num, "WATCH THESE STAR BARBERS — THEY MOVE",
          "These barbers have personal brands bigger than their shops.\n"
          "When they move, clients follow. Track them for poaching opportunities:\n", "LATER")
    for s in stars:
        print(f"      {s['name']:25s} {s['instagram_handle']:25s} @ {s['company_name']}")
        if s.get("seniority"):
            print(f"      {'':25s} Seniority: {s['seniority']}")

    _move(move_num + 1, "YOUR SIGNATURE: GROOMING AUTHORITY + TECH",
          "The market leaders all have a THING:\n"
          "  • No Grease → 'The Royal Treatment' (facials + premium experience)\n"
          "  • Damu Gordon → Celebrity/NFL barber (aspirational brand)\n"
          "  • Steve the Barber → 40K IG, 4x awards (social proof machine)\n"
          "  • Shaun Corbett → Community impact (Walmart, Cops & Barbers)\n"
          "  • Tara (Fade Factory) → Women/kids specialist + bridal\n"
          "  • Marcus C. → 'The Beard Barber' (niche dominance)\n"
          "\n"
          "YOUR THING: The grooming authority.\n"
          "  10 years of craft + wholesale product access + proprietary OS.\n"
          "  You don't just cut hair — you send them home with the right product.\n"
          "  You don't just book appointments — your system knows what they need.\n"
          "  The barber who built his own tech AND curates his own product line.\n"
          "  Service + retail + intelligence. Nobody else in this market has all three.",
          "NOW")


# ════════════════════════════════════════════════════════════════════════
#  SECTION 3: POSITIONING & BRAND
# ════════════════════════════════════════════════════════════════════════

def positioning_strategy():
    _header("POSITIONING STRATEGY — How You Show Up")

    # Social leaders
    social = _q("""
        SELECT c.company_name, cs.platform, cs.followers, cs.engagement_rate
        FROM competitor_social cs
        JOIN competitors c ON c.competitor_id = cs.competitor_id
        WHERE cs.platform = 'Instagram'
        ORDER BY cs.followers DESC
        LIMIT 15
    """)

    # Booking platforms
    booking = _q("""
        SELECT
            CASE
                WHEN notes ILIKE '%booksy%' THEN 'Booksy'
                WHEN notes ILIKE '%squire%' THEN 'Squire'
                WHEN notes ILIKE '%fresha%' THEN 'Fresha'
                WHEN notes ILIKE '%square%' THEN 'Square'
                ELSE 'None/Walk-in'
            END as platform,
            COUNT(*) as shops
        FROM competitors
        GROUP BY platform
        ORDER BY shops DESC
    """)

    # Review volume leaders
    reviews = _q("""
        SELECT c.company_name,
               COUNT(*) as review_count,
               ROUND(AVG(r.rating), 2) as avg_rating,
               ROUND(AVG(r.sentiment_score), 2) as sentiment
        FROM review_snapshots r
        JOIN competitors c ON c.competitor_id = r.competitor_id
        GROUP BY c.company_name
        ORDER BY review_count DESC
    """)

    print("\n  INSTAGRAM LANDSCAPE (who your clients are following):")
    print(f"  {'Shop':45s} {'Followers':>10s} {'Engagement':>12s}")
    print(f"  {'─'*70}")
    for s in social:
        eng = f"{float(s['engagement_rate']):.1f}%" if s['engagement_rate'] else "N/A"
        print(f"  {s['company_name']:45s} {s['followers']:>8,d}   {eng:>10s}")

    print(f"\n  BOOKING PLATFORM MARKET SHARE:")
    for b in booking:
        bar = "█" * (b["shops"] * 2)
        print(f"    {b['platform']:15s}  {b['shops']:>3d} shops  {bar}")

    move_num = 1

    _move(move_num, "YOUR BOOKING OS IS A COMPETITIVE WEAPON — USE IT",
          "Every competitor in this market rents their brain from Booksy or Squire.\n"
          "You BUILT yours. It adapts. It learns from your transactions. It has its own warehouse.\n"
          "This is the single biggest technological advantage in Charlotte's barbershop market.\n"
          "\n"
          "Transition plan off Booksy:\n"
          "  1. Migrate your existing Booksy client list to your OS\n"
          "  2. Run both in parallel for 30 days (catch stragglers)\n"
          "  3. Send every Booksy client a direct link to your OS\n"
          "  4. Kill Booksy. You don't need a landlord for your own house.\n"
          "\n"
          "What none of them can do:\n"
          f"  Booksy shops: {next((b['shops'] for b in booking if b['platform']=='Booksy'), 0)}\n"
          f"  Squire shops: {next((b['shops'] for b in booking if b['platform']=='Squire'), 0)}\n"
          f"  Walk-in only: {next((b['shops'] for b in booking if b['platform']=='None/Walk-in'), 0)}\n"
          "  Proprietary OS: 1 — YOU. Nobody else has this.",
          "NOW")
    move_num += 1

    _move(move_num, "GROOMING + RETAIL — YOUR SECOND REVENUE STREAM",
          "You have wholesale access. Most barbers in this market DON'T.\n"
          "The shops that sell product are collecting revenue while the chair is empty.\n"
          "\n"
          "The math on retail in a suite:\n"
          "  Wholesale cost on a pomade/oil: ~$4-8\n"
          "  Retail price: $15-25\n"
          "  Margin: 50-70%\n"
          "  10 products/week = $600-1,000/month in PURE margin\n"
          "  That's $7K-12K/year added to your $42K gross\n"
          "\n"
          "Your OS should track:\n"
          "  • Which products each client buys (auto-reorder prompts)\n"
          "  • Product revenue vs service revenue (split reporting)\n"
          "  • Retail margin by product line\n"
          "  • Inventory alerts from your wholesale account\n"
          "\n"
          "Every client in that chair is a retail customer. They trust your hands\n"
          "on their head — they'll trust what you put in their hands.\n"
          "Curate 5-8 products max. YOUR picks. Not a shelf of options — a recommendation.",
          "NOW")
    move_num += 1

    _move(move_num, "DEPOSITS ARE CASH FLOW ENGINEERING — EXPAND IT",
          "You're already taking deposits. Most barbers in this market aren't.\n"
          "Deposits solve two problems at once:\n"
          "  1. No-shows cost you $0 instead of $45\n"
          "  2. Cash flow smooths out — you see revenue BEFORE the cut\n"
          "\n"
          "Your OS should track deposit conversion rates.\n"
          "At $42K/year gross, even 50% deposit coverage gives you $21K in\n"
          "predictable forward-looking revenue. Banks see that differently\n"
          "than they see walk-in cash when you're applying for a shop lease.\n"
          "\n"
          "Deposits + your OS transaction history = proof of stable income\n"
          "for a commercial lease application. Build that case NOW.",
          "NOW")
    move_num += 1

    _move(move_num, "INSTAGRAM — TOOL, NOT DEPENDENCY",
          "You're right: IG turned into an influencer game. You're a barber, not a creator.\n"
          "But you still need a digital storefront. Treat it like a business card, not a career.\n"
          "\n"
          "What works without becoming an influencer:\n"
          "  • Google Business Profile > Instagram for local discovery\n"
          "  • Your OS booking link is your funnel, not your IG bio\n"
          "  • Post 2-3x/week (not daily). Before/after. Let the work speak.\n"
          "  • Core clients share your work when you tag them — that's organic\n"
          "  • Use IG as proof-of-work, not a growth engine\n"
          "\n"
          "The competitors chasing 40K followers are building on rented land too.\n"
          "Your OS, your client list, your deposit book — that's OWNED distribution.",
          "SOON")
    move_num += 1

    _move(move_num, "REVIEWS — YOUR REAL GROWTH ENGINE (NOT SOCIAL)",
          "Since you're not going influencer, reviews are how new clients find you.\n"
          "The top shops run on review volume:\n",
          "NOW")
    for r in reviews:
        print(f"      {r['company_name']:40s}  {r['review_count']} reviews  avg {float(r['avg_rating']):.1f}/5")
    print(f"\n    Your core clients are loyal. Ask every one for a Google review.")
    print(f"    QR code in the suite. Text link after appointment from your OS.")
    print(f"    In South Park, Google reviews matter more than IG followers.")
    print(f"    Goal: 50 Google reviews. That's your SEO. That's your storefront.")
    move_num += 1

    _move(move_num, "COMMUNITY OVER MARKETING",
          "The most successful shops in this market are COMMUNITY HUBS:\n"
          "  • Shaun Corbett: Cops & Barbers 501(c)(3), turkey giveaways, tutoring\n"
          "  • No Grease: 'Who Wants to Be a Barber' scholarship competition\n"
          "  • Gordon's: 90 years of Cherry neighborhood history\n"
          "  • Fade Factory: Bridal/event styling (embedded in life moments)\n"
          "\n"
          "This isn't marketing. This is how you become irreplaceable.\n"
          "Pick ONE community initiative. Back-to-school free cuts. Partnership\n"
          "with a church. Free lineup for job interviews. Start small, be consistent.",
          "SOON")


# ════════════════════════════════════════════════════════════════════════
#  SECTION 4: EXPANSION & LOCATION
# ════════════════════════════════════════════════════════════════════════

def expansion_strategy():
    _header("EXPANSION STRATEGY — Where to Plant Your Flag")

    # Shop density by zip
    density = _q("""
        SELECT zip_code, neighborhood,
               COUNT(*) as shops,
               ROUND(AVG(ph.price), 2) as avg_fade
        FROM competitors c
        LEFT JOIN price_history ph ON ph.competitor_id = c.competitor_id AND ph.service_name = 'Fade'
        GROUP BY zip_code, neighborhood
        ORDER BY shops DESC
    """)

    # Underserved areas (few shops, high prices = opportunity)
    print("\n  MARKET DENSITY MAP:")
    print(f"  {'ZIP':>7s} {'Neighborhood':25s} {'Shops':>6s} {'Avg Fade':>10s} {'Assessment':>25s}")
    print(f"  {'─'*75}")

    saturated = []
    opportunity = []

    for d in density:
        shops = d["shops"]
        avg = float(d["avg_fade"]) if d["avg_fade"] else 0
        if shops >= 4:
            assessment = "SATURATED — avoid"
            saturated.append(d)
        elif shops >= 2 and avg < 30:
            assessment = "VALUE MARKET — tight margins"
        elif shops == 1 and avg >= 35:
            assessment = "★ OPPORTUNITY — premium gap"
            opportunity.append(d)
        elif shops == 1:
            assessment = "OPEN — room to enter"
            opportunity.append(d)
        else:
            assessment = "MODERATE"
        print(f"  {d['zip_code']:>7s} {d['neighborhood']:25s} {shops:>4d}   "
              f"{'$'+str(avg) if avg else 'N/A':>9s}   {assessment}")

    move_num = 1

    _move(move_num, "AVOID 28216 (BEATTIES FORD) AND 28206 (N TRYON)",
          f"28216 has {sum(d['shops'] for d in density if d['zip_code']=='28216')} shops. "
          f"28206 has {sum(d['shops'] for d in density if d['zip_code']=='28206')} shops.\n"
          "These corridors are oversaturated. Goodfellas, No Grease, Anderton,\n"
          "B&J, Edwards', M&M, Gillespie, Head Quarters, Clipper Kingz, Swag...\n"
          "You'd be fighting for scraps. Don't.",
          "NOW")
    move_num += 1

    # Find best opportunities
    print(f"\n  TOP LOCATION OPPORTUNITIES:")
    opps = _q("""
        WITH area_stats AS (
            SELECT c.neighborhood, c.zip_code,
                   COUNT(DISTINCT c.competitor_id) as shops,
                   ROUND(AVG(ph.price), 2) as avg_fade
            FROM competitors c
            LEFT JOIN price_history ph ON ph.competitor_id = c.competitor_id AND ph.service_name = 'Fade'
            GROUP BY c.neighborhood, c.zip_code
            HAVING COUNT(DISTINCT c.competitor_id) <= 2
        )
        SELECT * FROM area_stats
        WHERE avg_fade >= 30
        ORDER BY avg_fade DESC
    """)

    for o in opps[:8]:
        print(f"    ★ {o['neighborhood']} ({o['zip_code']}): {o['shops']} shop(s), avg fade ${float(o['avg_fade']):.0f}")

    # Check for South Park intel
    south_park_shops = _q("""
        SELECT company_name, neighborhood, zip_code
        FROM competitors
        WHERE neighborhood ILIKE '%south%park%'
           OR neighborhood ILIKE '%southpark%'
           OR zip_code = '28210'
        ORDER BY company_name
    """)

    _move(move_num, "YOU'RE ALREADY IN SOUTH PARK — MAP YOUR BACKYARD",
          f"You're in a suite in South Park (28210). That's premium territory.\n"
          f"South Park shops in our intel: {len(south_park_shops)}\n"
          "\n"
          "Before you leave, know what you're leaving and where you're going:\n"
          "  • How many clients are South Park locals vs driving in?\n"
          "  • If you move, do they follow? (Your OS should tell you this)\n"
          "  • South Park rent is HIGH — is the client density worth it?\n"
          "\n"
          "Your shop doesn't have to be in South Park. Your SUITE is in South Park.\n"
          "When you open a shop, optimize for: your clients' drive radius,\n"
          "lease affordability, and room for 2-3 chairs.",
          "NOW")
    move_num += 1

    _move(move_num, "TARGET LOCATIONS FOR YOUR SHOP",
          "South End (28203): Young professionals, 1 shop. Higher rent but foot traffic.\n"
          "Plaza Midwood (28205): 1 shop, gentrifying, $40+ fades. Community feel.\n"
          "Ballantyne (28270): Suburban money, 1 shop. Your South Park clients might follow.\n"
          "NoDa (28206): Art district, growing. Could be underserved for premium.\n"
          "\n"
          "KEY QUESTION: Where do your CORE CLIENTS live/work?\n"
          "Your OS has their booking patterns. Plot their zip codes.\n"
          "Open the shop where THEY already are, not where you think is trendy.\n"
          "\n"
          "Suite rent vs shop rent math:\n"
          "  Suite: ~$250-400/week (just you, no growth ceiling is the ceiling)\n"
          "  Shop: ~$2,000-4,000/month BUT chair rentals offset it\n"
          "  2 chairs at $250/wk = $2,000/month — that covers most leases",
          "SOON")
    move_num += 1

    _move(move_num, "STUDY NO GREASE'S MODEL — BUT DON'T COPY IT",
          "No Grease franchise: $132K-$278K investment. $200K net worth requirement.\n"
          "You're not buying a franchise. You're building your own.\n"
          "But study what works:\n"
          "  • Mall-adjacent locations = foot traffic (SouthPark, Northlake)\n"
          "  • Premium branding ('Knights of the Razor') justifies price\n"
          "  • Barber school pipeline = never short on talent\n"
          "\n"
          "What you have that they DON'T:\n"
          "  • Proprietary OS (they rent from Booksy)\n"
          "  • Wholesale product margin (most barbers buy retail)\n"
          "  • 10 years of client relationships + deposit book\n"
          "  • Lower overhead target (you don't need $278K to start)",
          "LATER")
    move_num += 1

    _move(move_num, "NON-TRADITIONAL LOCATIONS — THE SHAUN CORBETT LESSON",
          "Shaun Corbett put a barbershop inside Walmart. Now has 5 locations.\n"
          "Walmart gave him a $25,000 check at the grand opening.\n"
          "\n"
          "The lesson isn't 'go to Walmart.' The lesson is: go where your\n"
          "clients already ARE. Grocery stores. Gyms. Car washes.\n"
          "Non-traditional locations = zero competition + built-in foot traffic.\n"
          "\n"
          "For you: could your shop be INSIDE a men's clothing store?\n"
          "A gym? An office building? Your grooming+retail model fits perfectly\n"
          "in a space that already sells lifestyle.",
          "LATER")


# ════════════════════════════════════════════════════════════════════════
#  SECTION 5: THREAT ASSESSMENT
# ════════════════════════════════════════════════════════════════════════

def threat_assessment():
    _header("THREAT ASSESSMENT — Who to Watch, Who to Ignore")

    # Full threat + hotness
    threats = _q("""
        WITH latest_threat AS (
            SELECT competitor_id, score as threat,
                   ROW_NUMBER() OVER (PARTITION BY competitor_id ORDER BY scored_at DESC) as rn
            FROM competitor_scores WHERE score_type = 'threat_level'
        ),
        latest_hot AS (
            SELECT competitor_id, score as hotness,
                   ROW_NUMBER() OVER (PARTITION BY competitor_id ORDER BY scored_at DESC) as rn
            FROM competitor_scores WHERE score_type = 'hotness'
        )
        SELECT c.company_name, c.neighborhood,
               COALESCE(t.threat, 0) as threat_level,
               COALESCE(h.hotness, 0) as hotness,
               (SELECT COUNT(*) FROM barbers b WHERE b.competitor_id = c.competitor_id AND b.status='Active') as barbers,
               (SELECT COUNT(*) FROM competitor_moves m WHERE m.competitor_id = c.competitor_id) as moves
        FROM competitors c
        LEFT JOIN latest_threat t ON t.competitor_id = c.competitor_id AND t.rn = 1
        LEFT JOIN latest_hot h ON h.competitor_id = c.competitor_id AND h.rn = 1
        WHERE c.status = 'Active'
        ORDER BY t.threat DESC, h.hotness DESC
        LIMIT 20
    """)

    # Recent moves
    moves = _q("""
        SELECT c.company_name, m.move_date, m.move_type, m.description, m.impact_rating
        FROM competitor_moves m
        JOIN competitors c ON c.competitor_id = m.competitor_id
        ORDER BY m.move_date DESC
        LIMIT 15
    """)

    print(f"\n  {'Shop':40s} {'Threat':>8s} {'Hot':>6s} {'Barbers':>8s} {'Moves':>7s}")
    print(f"  {'─'*72}")
    for t in threats:
        threat = float(t["threat_level"])
        hot = float(t["hotness"])
        if threat >= 7:
            tag = "⚠️  HIGH"
        elif threat >= 5:
            tag = "🔶 MED"
        elif hot >= 80:
            tag = "👁️  WATCH"
        else:
            tag = "   low"
        print(f"  {t['company_name']:40s} {threat:>6.1f}/10 {hot:>5.0f} {t['barbers']:>6d}   {t['moves']:>5d}   {tag}")

    _header("RECENT COMPETITOR MOVES")
    for m in moves:
        impact = "!" * (m["impact_rating"] or 0)
        print(f"  {m['move_date']}  {m['move_type']:15s}  {m['company_name']:30s}  {impact}")
        print(f"  {'':12s}  {m['description'][:70]}")

    move_num = 1

    _move(move_num, "NO GREASE IS NOT YOUR COMPETITOR — THEY'RE YOUR WEATHER",
          "14 locations. $132K-$278K franchise. Licensed in 36 states.\n"
          "Multi-million dollar business. 3,000+ barber school graduates.\n"
          "You don't compete with No Grease. You exist in their ecosystem.\n"
          "\n"
          "DO: Position in areas they don't serve (they're mall-focused).\n"
          "DO: Recruit their school graduates.\n"
          "DO: Offer what they can't — personal touch, flexibility, no franchise feel.\n"
          "DON'T: Try to match their prices ($40-75). Undercut and differentiate.",
          "NOW")
    move_num += 1

    _move(move_num, "FADE FACTORY & DA LUCKY SPOT — YOUR REAL THREATS",
          "Both at 7/10 threat level. Both independent. Both growing.\n"
          "\n"
          "Fade Factory (Tara Smith): 4x award-winning, strong Yelp presence,\n"
          "  243 reviews, University City. She's doing what you want to do.\n"
          "  Study her: bridal/event styling, kids specialist, loyal base.\n"
          "\n"
          "Da Lucky Spot (Shaun Corbett): 5 Walmart locations, academy,\n"
          "  501(c)(3), media darling. He's the growth story in this market.\n"
          "  His $25-35 prices undercut everyone. Volume play.",
          "NOW")
    move_num += 1

    _move(move_num, "GORDON'S HISTORIC — RESPECT, DON'T COMPETE",
          "90 years old. Cherry neighborhood institution. Michael Gordon has\n"
          "33+ years at the helm. Trained the No Grease founders.\n"
          "Damu Gordon cuts NFL players.\n"
          "\n"
          "Gordon's is untouchable in its lane. But it's ONE location,\n"
          "appointment-heavy, and not expanding. Leave them alone.\n"
          "If anything, learn from them — that's where the history is.",
          "LATER")


# ════════════════════════════════════════════════════════════════════════
#  SECTION 6: QUICK WINS (30-60-90 DAY PLAN)
# ════════════════════════════════════════════════════════════════════════

def quick_wins():
    _header("QUICK WINS — Your 30-60-90 Day Playbook")
    _header("CURRENT POSITION: Solo suite in South Park | $42K/yr gross | Core clients | Deposits active")

    print("""
  ┌──────────────────────────────────────────────────────────────────────┐
  │  DAYS 1-30: STACK YOUR REVENUE (Suite → Shop Fund)                  │
  ├──────────────────────────────────────────────────────────────────────┤
  │                                                                      │
  │  □ Curate 5-8 retail products from your wholesale account            │
  │  □ Calculate margin on each (target 50-70% markup)                   │
  │  □ Add retail catalog to your booking OS (track per-client)          │
  │  □ Every chair appointment = product recommendation moment           │
  │  □ Migrate Booksy clients → your OS. Run parallel 30 days.          │
  │  □ Set deposit policy in OS: 50% of bookings require deposit         │
  │  □ Google Business Profile — get first 10 reviews from core clients  │
  │                                                                      │
  ├──────────────────────────────────────────────────────────────────────┤
  │  DAYS 31-60: BUILD THE LEASE CASE                                   │
  ├──────────────────────────────────────────────────────────────────────┤
  │                                                                      │
  │  □ Kill Booksy. 100% bookings through YOUR OS.                       │
  │  □ Retail generating $500-1,000/month (proof of second stream)       │
  │  □ OS reports: avg ticket, retention rate, deposit coverage          │
  │  □ 25+ Google reviews (South Park local SEO)                         │
  │  □ Run competitive intel on South Park / SouthPark Mall area         │
  │  □ Research lease costs: South End, Plaza Midwood, NoDa              │
  │  □ Build financial package: 12mo P&L, OS data, deposit book          │
  │                                                                      │
  ├──────────────────────────────────────────────────────────────────────┤
  │  DAYS 61-90: POSITION FOR THE MOVE                                  │
  ├──────────────────────────────────────────────────────────────────────┤
  │                                                                      │
  │  □ Services + retail combined = path to $60K+ annual gross           │
  │  □ 50+ Google reviews — your reputation is searchable proof          │
  │  □ OS generating: retention insights, product attach rates           │
  │  □ Identify 2-3 target shop locations with lease terms               │
  │  □ Financial model: suite costs vs shop costs vs shop revenue        │
  │  □ Can you bring 1 chair rental barber from day 1? (offset rent)     │
  │  □ Deposit book shows X months of forward-booked revenue             │
  │                                                                      │
  └──────────────────────────────────────────────────────────────────────┘
""")

    # Revenue projection — REAL MATH from current position
    _header("REVENUE MATH — From $42K Suite to Shop")

    your_fade = YOUR_SHOP["prices"]["Fade"]
    combo = YOUR_SHOP["prices"]["Haircut + Beard Combo"]
    premium = 75  # premium Royal Treatment tier

    print(f"\n  YOUR CURRENT REALITY:")
    print(f"    Annual gross:      $42,000")
    print(f"    Monthly gross:     ~$3,500")
    current_daily = 42000 / 52 / 5  # assuming 5 days
    print(f"    Daily avg:         ~${current_daily:,.0f}/day (5-day week)")
    implied_cuts = current_daily / your_fade
    print(f"    Implied cuts/day:  ~{implied_cuts:.1f} at ${your_fade}/cut")

    print(f"\n  {'Scenario':55s} {'Monthly':>10s} {'Annual':>10s}")
    print(f"  {'─'*78}")

    scenarios = [
        ("TODAY: Services only (suite)", 3500, 42000),
        ("+ Retail ($600/mo margin from wholesale)", 4100, 49200),
        ("+ Retail ($1,000/mo margin)", 4500, 54000),
        ("+ Premium tier (2 Royal Treatments/wk @ $75)", 5100, 61200),
        ("SHOP: Above + 1 chair rental ($250/wk)", 6183, 74200),
        ("SHOP: Above + 2 chair rentals ($250/wk)", 7267, 87200),
        ("SHOP: Above + 3 chair rentals", 8350, 100200),
    ]

    for name, monthly, annual in scenarios:
        marker = " ◄── YOU ARE HERE" if "TODAY" in name else ""
        marker = " ◄── SHOP THRESHOLD" if "1 chair rental" in name else marker
        print(f"  {name:55s} ${monthly:>8,d}  ${annual:>8,d}{marker}")

    print(f"\n  THE GAP TO CLOSE:")
    print(f"    Current:    $42,000/year (services only, suite)")
    print(f"    With retail: ~$50-54K/year (services + product margin)")
    print(f"    Shop break-even depends on lease, but retail + chair rentals")
    print(f"    can cover the difference between suite rent and shop rent.")
    print(f"")
    print(f"    Your deposit book is forward revenue proof for a landlord.")
    print(f"    Your OS transaction data is your financial credibility.")


# ════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════

def run_doctrine():
    """Run the doctrine framework and audit."""
    from doctrine import print_doctrine, doctrine_audit
    print_doctrine()
    doctrine_audit()


SECTIONS = {
    "doctrine": run_doctrine,
    "pricing": pricing_strategy,
    "talent": talent_strategy,
    "positioning": positioning_strategy,
    "expansion": expansion_strategy,
    "threats": threat_assessment,
    "quick-wins": quick_wins,
}


def run_all():
    print("=" * 70)
    print("  YOUR STRATEGIC MOVES")
    print("  Generated from competitive intelligence warehouse")
    print("  Charlotte, NC — Black-owned barbershop market")
    print("=" * 70)

    for name, fn in SECTIONS.items():
        fn()

    _header("END OF STRATEGIC PLAYBOOK")
    print("  Run 'python strategy.py --section <name>' for individual sections.")
    print(f"  Available: {', '.join(SECTIONS.keys())}")
    print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--section" in args:
        idx = args.index("--section")
        if idx + 1 < len(args):
            section = args[idx + 1]
            if section in SECTIONS:
                SECTIONS[section]()
            else:
                print(f"Unknown section: {section}")
                print(f"Available: {', '.join(SECTIONS.keys())}")
        else:
            print(f"Available sections: {', '.join(SECTIONS.keys())}")
    else:
        run_all()
