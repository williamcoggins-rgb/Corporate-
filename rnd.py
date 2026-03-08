"""R&D DEPARTMENT — Research & Development

Where your four assets compound:
  1. THE CRAFT      — 10 years of haircuts, hands-on expertise
  2. THE DEGREE     — Business strategy, financial modeling, market analysis
  3. THE AI         — Claude as a research partner, analyst, and builder
  4. THE OS         — Proprietary booking system backed by a data warehouse

R&D is not operations. R&D is what you're building NEXT.
Operations runs today. R&D builds tomorrow.

This department has four labs, each combining your assets differently:

  Lab 1: SERVICE LAB      — New services, pricing models, bundles
  Lab 2: OS LAB           — Booking OS features, data products, automation
  Lab 3: MARKET LAB       — Market research, expansion models, demand analysis
  Lab 4: BUSINESS LAB     — Revenue models, financial instruments, growth plays

Run:  python rnd.py                        # Full R&D status + all labs
      python rnd.py --lab service          # Service Lab
      python rnd.py --lab os               # OS Lab
      python rnd.py --lab market           # Market Lab
      python rnd.py --lab business         # Business Lab
      python rnd.py --pipeline             # R&D pipeline (what's in progress)
      python rnd.py --assets               # Asset inventory

Governed by: doctrine.py — Strategic Adaptability + Opportunity Creation
"""

import sys
import json
from datetime import date
from warehouse.db import get_connection
from strategy import YOUR_SHOP, _q


# ════════════════════════════════════════════════════════════════════════
#  R&D SCHEMA — extends the warehouse
# ════════════════════════════════════════════════════════════════════════

def init_rnd_schema():
    """Create R&D tables in the warehouse."""
    con = get_connection()

    con.execute("""
        CREATE TABLE IF NOT EXISTS rnd_projects (
            project_id INTEGER PRIMARY KEY,
            lab VARCHAR NOT NULL,
            title VARCHAR NOT NULL,
            description TEXT,
            status VARCHAR DEFAULT 'research',
            priority VARCHAR DEFAULT 'medium',
            assets_used TEXT,
            hypothesis TEXT,
            success_metric TEXT,
            findings TEXT,
            revenue_potential TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS rnd_experiments (
            experiment_id INTEGER PRIMARY KEY,
            project_id INTEGER REFERENCES rnd_projects(project_id),
            name VARCHAR NOT NULL,
            method TEXT,
            result TEXT,
            data_json TEXT,
            status VARCHAR DEFAULT 'planned',
            run_date DATE,
            notes TEXT
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS rnd_assets (
            asset_id INTEGER PRIMARY KEY,
            category VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            description TEXT,
            current_value TEXT,
            potential TEXT,
            leverage_notes TEXT
        );
    """)

    con.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_rnd_project START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_rnd_experiment START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_rnd_asset START 1;
    """)

    con.close()


def _seed_assets():
    """Seed the four core assets if not already present."""
    con = get_connection()
    existing = con.execute("SELECT COUNT(*) FROM rnd_assets").fetchone()[0]
    if existing > 0:
        con.close()
        return

    assets = [
        {
            "category": "THE CRAFT",
            "name": "Haircut Expertise",
            "description": (
                "10 years of hands-on barbering. Fades, skin fades, beard work, "
                "kids cuts. This is the core product. Every other asset serves this."
            ),
            "current_value": (
                f"${YOUR_SHOP.get('annual_gross', 42000):,}/year in service revenue. "
                f"Core client base in retention phase. Premium positioning at "
                f"${YOUR_SHOP['prices']['Fade']}/fade (above market avg)."
            ),
            "potential": (
                "Premium tier expansion ($75+ Royal Treatment). "
                "Teaching/mentoring revenue. Brand authority for retail. "
                "The hands validate everything else."
            ),
            "leverage_notes": (
                "Every new service, every product recommendation, every chair rental "
                "standard comes from credibility built by this asset. "
                "Without the craft, nothing else works."
            ),
        },
        {
            "category": "THE DEGREE",
            "name": "Business Education",
            "description": (
                "Formal business degree. Strategic management, financial analysis, "
                "market research, organizational behavior. Most barbers operate on "
                "instinct. You operate on frameworks."
            ),
            "current_value": (
                "Doctrine framework codified (doctrine.py). Strategic playbook "
                "generated from data (strategy.py). Five-advisor council "
                "built on strategic thinking models (council.py). "
                "SMART objectives, SWOT analysis, competitive intelligence — "
                "these aren't buzzwords to you, they're tools."
            ),
            "potential": (
                "Financial modeling for lease negotiations. Revenue projections "
                "that landlords trust. Franchise feasibility analysis. "
                "Consulting for other barbers who want to scale. "
                "The degree is the language landlords and banks speak."
            ),
            "leverage_notes": (
                "This asset is INVISIBLE to competitors. No Grease has a franchise "
                "system. Goodfellas has brand. But nobody in this market has a "
                "barber who can build a P&L, run a competitive analysis, and "
                "present a strategic plan. That's your moat."
            ),
        },
        {
            "category": "THE AI",
            "name": "Claude Partnership",
            "description": (
                "Claude as a research partner, analyst, and builder. "
                "Not a chatbot. A force multiplier. Used for: competitive "
                "intelligence, code development, strategic analysis, "
                "financial modeling, market research, and building the OS."
            ),
            "current_value": (
                "Built: warehouse schema, 13 agent classes, 4-tier bot pipeline, "
                "strategic doctrine, council framework, exit planning system, "
                "competitive landscape for 40+ Charlotte shops. "
                "All built with Claude. That's a dev team's output from one person."
            ),
            "potential": (
                "OS feature development at zero dev cost. Market research at "
                "enterprise speed. Financial models on demand. Content generation "
                "for marketing. Automated reporting. The AI means you move at "
                "10x the speed of a solo operator without the payroll."
            ),
            "leverage_notes": (
                "Every barber can get a haircut right. Very few can build a "
                "data warehouse, a booking OS, and a competitive intelligence "
                "system. Claude is the equalizer — it gives you the output of "
                "a tech team without the overhead."
            ),
        },
        {
            "category": "THE OS",
            "name": "Proprietary Booking OS",
            "description": (
                "Custom-built booking and operations system. Not Booksy. Not Vagaro. "
                "Not Square. YOUR system, backed by YOUR data warehouse. "
                "Migrating from Booksy."
            ),
            "current_value": (
                "Features: live transaction intelligence, adaptive scheduling, "
                "deposit collection, competitive intelligence integration. "
                "Connected to this warehouse. No competitor in Charlotte has "
                "anything like this."
            ),
            "potential": (
                "Client behavior analytics (rebooking patterns, spending trends). "
                "Automated deposit management. Dynamic pricing capabilities. "
                "Multi-location support for shop expansion. Chair rental management. "
                "Eventually: license the OS to other barbers. "
                "The OS is not just a tool — it's a potential product."
            ),
            "leverage_notes": (
                "Booksy charges barbers $30/mo and owns their client data. "
                "Your OS costs you nothing in subscription fees, you own all the data, "
                "and it does things Booksy can't (warehouse integration, CI reports, "
                "deposit intelligence). This is a competitive weapon AND a potential "
                "revenue stream."
            ),
        },
    ]

    for a in assets:
        aid = con.execute("SELECT nextval('seq_rnd_asset')").fetchone()[0]
        con.execute(
            """INSERT INTO rnd_assets
               (asset_id, category, name, description, current_value, potential, leverage_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [aid, a["category"], a["name"], a["description"],
             a["current_value"], a["potential"], a["leverage_notes"]],
        )

    con.close()


def _seed_projects():
    """Seed initial R&D projects if none exist."""
    con = get_connection()
    existing = con.execute("SELECT COUNT(*) FROM rnd_projects").fetchone()[0]
    if existing > 0:
        con.close()
        return

    projects = [
        # SERVICE LAB
        {
            "lab": "service",
            "title": "Royal Treatment Premium Tier",
            "description": "Design a $75+ premium service package: cut + beard + hot towel + product + experience.",
            "status": "research",
            "priority": "high",
            "assets_used": json.dumps(["THE CRAFT", "THE DEGREE"]),
            "hypothesis": "Clients will pay $75+ for a differentiated experience that combines craft with atmosphere.",
            "success_metric": "2-3 bookings/week within 60 days of launch. $650+/mo incremental revenue.",
            "revenue_potential": "$7,800-11,700/year",
        },
        {
            "lab": "service",
            "title": "Membership / Subscription Model",
            "description": "Monthly membership: 2 cuts/mo + product discount + priority booking. Research pricing and structure.",
            "status": "research",
            "priority": "medium",
            "assets_used": json.dumps(["THE CRAFT", "THE DEGREE", "THE OS"]),
            "hypothesis": "Memberships convert irregular clients to predictable monthly revenue and reduce no-shows to zero.",
            "success_metric": "10 members within 90 days. Churn < 15%/month.",
            "revenue_potential": "$6,000-12,000/year (10-20 members at $50-60/mo)",
        },
        {
            "lab": "service",
            "title": "Group / Event Booking Package",
            "description": "Wedding parties, prom groups, father-son packages. Research demand and pricing.",
            "status": "idea",
            "priority": "low",
            "assets_used": json.dumps(["THE CRAFT", "THE OS"]),
            "hypothesis": "Group bookings fill dead slots and generate premium pricing through convenience.",
            "success_metric": "1 group booking/month at $200+ average ticket.",
            "revenue_potential": "$2,400-4,800/year",
        },
        # OS LAB
        {
            "lab": "os",
            "title": "Booksy Migration Completion",
            "description": "Complete migration of all client data, booking history, and workflows from Booksy to proprietary OS.",
            "status": "in_progress",
            "priority": "critical",
            "assets_used": json.dumps(["THE OS", "THE AI"]),
            "hypothesis": "Full Booksy independence eliminates $30/mo fee, data dependency, and client marketing risk.",
            "success_metric": "Zero Booksy bookings. All clients on proprietary OS. No data loss.",
            "revenue_potential": "Saves $360/year + protects client relationships",
        },
        {
            "lab": "os",
            "title": "Client Analytics Dashboard",
            "description": "Build analytics from OS transaction data: rebooking rates, average ticket, product attach rate, deposit coverage, revenue trends.",
            "status": "research",
            "priority": "high",
            "assets_used": json.dumps(["THE OS", "THE AI", "THE DEGREE"]),
            "hypothesis": "Visibility into client behavior patterns enables data-driven service and pricing decisions.",
            "success_metric": "Dashboard operational with 6 KPIs. Updated automatically from OS data.",
            "revenue_potential": "Indirect — drives better decisions across all revenue streams",
        },
        {
            "lab": "os",
            "title": "Chair Rental Management Module",
            "description": "OS module for managing chair renters: scheduling, payment tracking, utilization metrics, chair-level P&L.",
            "status": "idea",
            "priority": "medium",
            "assets_used": json.dumps(["THE OS", "THE AI", "THE DEGREE"]),
            "hypothesis": "Automated chair rental tracking reduces admin burden and provides real-time chair utilization data.",
            "success_metric": "Track 1-3 chair renters with automated weekly billing and utilization reports.",
            "revenue_potential": "$12,000-36,000/year (chair rental revenue it manages)",
        },
        {
            "lab": "os",
            "title": "Dynamic Pricing Engine",
            "description": "Research time-of-day and day-of-week pricing. Peak hours premium, off-peak discount to fill dead slots.",
            "status": "idea",
            "priority": "low",
            "assets_used": json.dumps(["THE OS", "THE AI", "THE DEGREE"]),
            "hypothesis": "Variable pricing fills empty slots without devaluing peak demand.",
            "success_metric": "10% increase in off-peak utilization within 90 days.",
            "revenue_potential": "$2,000-5,000/year incremental",
        },
        {
            "lab": "os",
            "title": "OS Licensing Research",
            "description": "Feasibility study: can this OS be packaged and licensed to other barbers? What's the market? What's the pricing?",
            "status": "idea",
            "priority": "low",
            "assets_used": json.dumps(["THE OS", "THE AI", "THE DEGREE"]),
            "hypothesis": "Independent barbers are underserved by Booksy/Vagaro. A barber-built OS has credibility and feature fit.",
            "success_metric": "Market sizing complete. 5 potential pilot barbers identified. Pricing model drafted.",
            "revenue_potential": "SaaS: $20-50/barber/mo. 100 barbers = $24K-60K/year",
        },
        # MARKET LAB
        {
            "lab": "market",
            "title": "Client Geography Analysis",
            "description": "Export client zip codes from OS. Map where your clients actually live. Use this to pick shop location.",
            "status": "research",
            "priority": "high",
            "assets_used": json.dumps(["THE OS", "THE AI", "THE DEGREE"]),
            "hypothesis": "Client concentration in a specific area reveals the optimal shop location.",
            "success_metric": "Heat map of client locations. Top 3 zip codes identified. Cross-referenced with warehouse competitor density.",
            "revenue_potential": "Indirect — prevents a $50K+ mistake (wrong location)",
        },
        {
            "lab": "market",
            "title": "Grooming Product Market Research",
            "description": "Research which product lines move in Charlotte. What brands? What price points? What margins?",
            "status": "research",
            "priority": "medium",
            "assets_used": json.dumps(["THE CRAFT", "THE DEGREE", "THE AI"]),
            "hypothesis": "Product selection based on data (not gut) maximizes retail margin per square foot.",
            "success_metric": "Top 5 product lines identified with margin analysis. Wholesale vs retail pricing mapped.",
            "revenue_potential": "$3,600-7,200/year retail margin",
        },
        {
            "lab": "market",
            "title": "Charlotte Barber Market Sizing",
            "description": "Total addressable market: how many men get haircuts in Charlotte? How often? What do they spend? Where are the gaps?",
            "status": "idea",
            "priority": "medium",
            "assets_used": json.dumps(["THE DEGREE", "THE AI"]),
            "hypothesis": "Quantifying the market reveals whether Charlotte is growing, saturated, or shifting.",
            "success_metric": "Market size estimate. Growth rate. Segment breakdown (premium vs budget vs mid).",
            "revenue_potential": "Indirect — informs all expansion decisions",
        },
        # BUSINESS LAB
        {
            "lab": "business",
            "title": "Lease Negotiation Playbook",
            "description": "Build a negotiation framework: what to ask for, what to concede, red flags, tenant improvement strategies.",
            "status": "research",
            "priority": "high",
            "assets_used": json.dumps(["THE DEGREE", "THE AI"]),
            "hypothesis": "A structured negotiation approach saves $5K-15K over a 3-year lease term.",
            "success_metric": "Playbook complete with 10+ negotiation tactics. Term sheet template. Red flag checklist.",
            "revenue_potential": "Saves $5,000-15,000 over lease term",
        },
        {
            "lab": "business",
            "title": "Shop P&L Financial Model",
            "description": "Build a real financial model: revenue scenarios, cost structure, break-even analysis, sensitivity testing.",
            "status": "research",
            "priority": "high",
            "assets_used": json.dumps(["THE DEGREE", "THE AI", "THE OS"]),
            "hypothesis": "A validated financial model is the difference between a business plan and a guess.",
            "success_metric": "Model with 3 scenarios (lean/mid/premium). Break-even calculated. Sensitivity on chair rental fill rate.",
            "revenue_potential": "Indirect — this IS the decision tool for the exit",
        },
        {
            "lab": "business",
            "title": "Barber Consulting Service",
            "description": "Research: can you consult for other barbers who want to scale? Your degree + OS + warehouse = unique offering.",
            "status": "idea",
            "priority": "low",
            "assets_used": json.dumps(["THE DEGREE", "THE AI", "THE CRAFT"]),
            "hypothesis": "Barbers who want to go from chair to shop have no structured support. You've built the system they need.",
            "success_metric": "3 conversations with potential consulting clients. Pricing model drafted.",
            "revenue_potential": "$500-2,000/engagement. 10 clients/year = $5K-20K",
        },
        {
            "lab": "business",
            "title": "Small Business Grant / Funding Research",
            "description": "Research grants, microloans, and programs for Black-owned businesses in Charlotte. SBA, local programs, CDFIs.",
            "status": "idea",
            "priority": "medium",
            "assets_used": json.dumps(["THE DEGREE", "THE AI"]),
            "hypothesis": "Non-dilutive funding exists for businesses with your profile. The degree helps you write the applications.",
            "success_metric": "5+ programs identified with eligibility confirmed. 2 applications drafted.",
            "revenue_potential": "$5,000-50,000 in grants/microloans",
        },
    ]

    for p in projects:
        pid = con.execute("SELECT nextval('seq_rnd_project')").fetchone()[0]
        con.execute(
            """INSERT INTO rnd_projects
               (project_id, lab, title, description, status, priority,
                assets_used, hypothesis, success_metric, revenue_potential)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [pid, p["lab"], p["title"], p["description"], p["status"],
             p["priority"], p.get("assets_used"), p.get("hypothesis"),
             p.get("success_metric"), p.get("revenue_potential")],
        )

    con.close()


# ════════════════════════════════════════════════════════════════════════
#  DISPLAY HELPERS
# ════════════════════════════════════════════════════════════════════════

def _header(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}")


def _status_icon(status):
    return {
        "idea": "○",
        "research": "◐",
        "in_progress": "◑",
        "testing": "◕",
        "complete": "●",
        "deployed": "■",
        "paused": "▪",
    }.get(status, "?")


def _priority_tag(priority):
    return {
        "critical": "!!!",
        "high": "!! ",
        "medium": "!  ",
        "low": "   ",
    }.get(priority, "   ")


# ════════════════════════════════════════════════════════════════════════
#  ASSET INVENTORY
# ════════════════════════════════════════════════════════════════════════

def show_assets():
    """Display the four core assets and how they compound."""
    _header("ASSET INVENTORY — What You're Working With")

    assets = _q("SELECT * FROM rnd_assets ORDER BY asset_id")

    for a in assets:
        print(f"""
  ┌──────────────────────────────────────────────────────────────────────┐
  │  {a['category']:67s}│
  │  {a['name']:67s}│
  └──────────────────────────────────────────────────────────────────────┘

  DESCRIPTION:
    {_wrap(a['description'], 64)}

  CURRENT VALUE:
    {_wrap(a['current_value'], 64)}

  POTENTIAL:
    {_wrap(a['potential'], 64)}

  LEVERAGE:
    {_wrap(a['leverage_notes'], 64)}""")

    # Asset multiplication matrix
    _header("ASSET MULTIPLICATION MATRIX")
    print(f"""
  When assets combine, they multiply — not add.

  ┌──────────────────────────────────────────────────────────────────────┐
  │  CRAFT + DEGREE    = Strategic pricing, financial modeling of your  │
  │                      services, lease-ready business plans           │
  │                                                                      │
  │  CRAFT + AI        = Market research on service trends, automated  │
  │                      competitive pricing analysis, content ideas    │
  │                                                                      │
  │  CRAFT + OS        = Transaction intelligence, client behavior     │
  │                      data, rebooking optimization, deposit mgmt    │
  │                                                                      │
  │  DEGREE + AI       = Financial models, grant applications, market  │
  │                      sizing, business plans at enterprise quality   │
  │                                                                      │
  │  DEGREE + OS       = P&L dashboards, chair rental ROI tracking,   │
  │                      revenue forecasting from real transaction data │
  │                                                                      │
  │  AI + OS           = Feature development at zero dev cost,         │
  │                      automated reporting, warehouse integration     │
  │                                                                      │
  │  ALL FOUR          = A barber-operator with a proprietary tech     │
  │                      stack, strategic intelligence system, and the  │
  │                      business acumen to deploy it all. Nobody in    │
  │                      Charlotte has this combination. Nobody.        │
  └──────────────────────────────────────────────────────────────────────┘
""")


def _wrap(text, width):
    """Simple text wrapper for display, preserving line prefix."""
    if not text:
        return "(none)"
    words = text.split()
    lines = []
    current = ""
    for w in words:
        if len(current) + len(w) + 1 > width:
            lines.append(current)
            current = w
        else:
            current = f"{current} {w}" if current else w
    if current:
        lines.append(current)
    return ("\n    ").join(lines)


# ════════════════════════════════════════════════════════════════════════
#  LAB DISPLAYS
# ════════════════════════════════════════════════════════════════════════

def show_lab(lab_name, lab_title, lab_desc):
    """Display a single lab's projects."""
    _header(f"{lab_title}")
    print(f"\n  {lab_desc}\n")

    projects = _q(
        "SELECT * FROM rnd_projects WHERE lab = ? ORDER BY "
        "CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
        "WHEN 'medium' THEN 2 ELSE 3 END, project_id",
        [lab_name]
    )

    if not projects:
        print(f"  No projects in this lab yet.\n")
        return

    for p in projects:
        icon = _status_icon(p["status"])
        ptag = _priority_tag(p["priority"])
        assets = json.loads(p["assets_used"]) if p["assets_used"] else []
        asset_str = " + ".join(assets) if assets else "—"

        print(f"  {icon} [{p['priority'].upper():>8s}]  {p['title']}")
        print(f"    Status:     {p['status'].upper()}")
        print(f"    Assets:     {asset_str}")
        print(f"    {_wrap(p['description'], 62)}")
        if p["hypothesis"]:
            print(f"    Hypothesis: {_wrap(p['hypothesis'], 52)}")
        if p["success_metric"]:
            print(f"    Success:    {_wrap(p['success_metric'], 52)}")
        if p["revenue_potential"]:
            print(f"    Revenue:    {p['revenue_potential']}")
        if p["findings"]:
            print(f"    Findings:   {_wrap(p['findings'], 52)}")
        print()


def lab_service():
    show_lab("service", "SERVICE LAB — New Revenue From the Chair",
             "Research new services, pricing models, and packages.\n"
             "  Assets: THE CRAFT + THE DEGREE\n"
             "  Question: What else can your hands and your mind create?")


def lab_os():
    show_lab("os", "OS LAB — Building the Machine",
             "Develop the proprietary booking OS. Features, data products, automation.\n"
             "  Assets: THE OS + THE AI\n"
             "  Question: What should the OS do next?")


def lab_market():
    show_lab("market", "MARKET LAB — Understanding the Battlefield",
             "Market research, demand analysis, location intelligence.\n"
             "  Assets: THE DEGREE + THE AI + THE OS\n"
             "  Question: Where is the opportunity?")


def lab_business():
    show_lab("business", "BUSINESS LAB — Financial Engineering",
             "Revenue models, financial instruments, growth plays, funding.\n"
             "  Assets: THE DEGREE + THE AI\n"
             "  Question: How do you fund and structure the next move?")


# ════════════════════════════════════════════════════════════════════════
#  R&D PIPELINE
# ════════════════════════════════════════════════════════════════════════

def show_pipeline():
    """Show R&D pipeline across all labs."""
    _header("R&D PIPELINE — All Projects by Status")

    statuses = ["in_progress", "research", "idea", "testing", "complete", "deployed", "paused"]

    for status in statuses:
        projects = _q(
            "SELECT * FROM rnd_projects WHERE status = ? ORDER BY "
            "CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
            "WHEN 'medium' THEN 2 ELSE 3 END",
            [status]
        )
        if not projects:
            continue

        icon = _status_icon(status)
        print(f"\n  {icon} {status.upper().replace('_', ' ')} ({len(projects)})")
        print(f"  {'─'*60}")
        for p in projects:
            ptag = _priority_tag(p["priority"])
            print(f"    {ptag} [{p['lab']:>8s}]  {p['title']}")
            if p["revenue_potential"]:
                print(f"                        Revenue: {p['revenue_potential']}")

    # Summary
    all_projects = _q("SELECT * FROM rnd_projects")
    total = len(all_projects)
    by_status = {}
    for p in all_projects:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1

    # Revenue potential rollup
    print(f"\n  {'─'*60}")
    print(f"  PIPELINE SUMMARY:")
    print(f"    Total projects: {total}")
    for s, count in sorted(by_status.items()):
        print(f"      {_status_icon(s)} {s:15s}  {count}")

    # Count projects using each asset
    asset_usage = {"THE CRAFT": 0, "THE DEGREE": 0, "THE AI": 0, "THE OS": 0}
    for p in all_projects:
        if p["assets_used"]:
            for a in json.loads(p["assets_used"]):
                if a in asset_usage:
                    asset_usage[a] += 1

    print(f"\n  ASSET UTILIZATION:")
    for asset, count in asset_usage.items():
        bar = "█" * count + "░" * (total - count)
        print(f"    {asset:15s}  {bar}  {count}/{total} projects")

    print()


# ════════════════════════════════════════════════════════════════════════
#  FULL R&D STATUS
# ════════════════════════════════════════════════════════════════════════

def full_rnd():
    """Run full R&D department overview."""
    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "R&D DEPARTMENT".center(68) + "▓")
    print("▓" + "Research & Development".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" + "Four assets. Four labs. One pipeline.".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)

    show_assets()
    lab_service()
    lab_os()
    lab_market()
    lab_business()
    show_pipeline()

    _header("R&D DOCTRINE")
    print(f"""
  The doctrine says: "Organizations that focus only on the present
  become obsolete. Organizations that focus only on the future
  collapse before reaching it."

  R&D is how you build the future WITHOUT abandoning the present.

  RULES:
    1. Every project must name which assets it uses.
       If it doesn't leverage your assets, it's not YOUR R&D.

    2. Every project must have a hypothesis.
       "I think X because Y" — not "wouldn't it be cool if."

    3. Every project must have a success metric.
       If you can't measure it, you can't manage it. (The degree taught you that.)

    4. R&D feeds the council. The council feeds decisions.
       When a project moves from 'research' to 'complete,' the council
       evaluates whether to deploy it.

  YOUR COMPETITIVE ADVANTAGE IN R&D:
    Most barbers don't have R&D. They have "ideas."
    You have a structured pipeline with hypothesis testing,
    asset tracking, and revenue projection.

    That's the degree + the AI + the craft + the OS.
    That's why nobody else in this market can do what you're doing.

  COMMANDS:
    python rnd.py                        # This view
    python rnd.py --lab service          # Service Lab
    python rnd.py --lab os               # OS Lab
    python rnd.py --lab market           # Market Lab
    python rnd.py --lab business         # Business Lab
    python rnd.py --pipeline             # Pipeline status
    python rnd.py --assets               # Asset inventory
""")


# ════════════════════════════════════════════════════════════════════════
#  LABS REGISTRY
# ════════════════════════════════════════════════════════════════════════

LABS = {
    "service": lab_service,
    "os": lab_os,
    "market": lab_market,
    "business": lab_business,
}


# ════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Always ensure schema + seed data
    init_rnd_schema()
    _seed_assets()
    _seed_projects()

    args = sys.argv[1:]

    if "--lab" in args:
        idx = args.index("--lab")
        if idx + 1 < len(args):
            lab = args[idx + 1].lower()
            if lab in LABS:
                LABS[lab]()
            else:
                print(f"Unknown lab: {lab}")
                print(f"Available: {', '.join(LABS.keys())}")
        else:
            print(f"Available labs: {', '.join(LABS.keys())}")
    elif "--pipeline" in args:
        show_pipeline()
    elif "--assets" in args:
        show_assets()
    else:
        full_rnd()
