"""SKILLS DEPARTMENT — Skill Development & Deployment

Where Claude's raw capabilities become repeatable workflows:

  Skills turn tool access into institutional knowledge.
  Without skills, every interaction starts from scratch.
  With skills, domain expertise compounds.

This department manages the full skill lifecycle:

  Phase 1: IDENTIFY    — Define use cases and trigger conditions
  Phase 2: DESIGN      — Choose category, write YAML, plan structure
  Phase 3: BUILD       — Write instructions, create scripts, bundle assets
  Phase 4: TEST        — Trigger tests, functional tests, baseline comparison
  Phase 5: DEPLOY      — Upload, document, distribute
  Phase 6: MAINTAIN    — Monitor, update, retire

Three skill categories:

  Category 1: DOCUMENT / ASSET CREATION
    Generate reports, analysis docs, competitive briefs.
    Uses templates, style guides, and warehouse data.

  Category 2: WORKFLOW AUTOMATION
    Multi-step processes with validation gates.
    Coordinates agents, enforces quality, tracks progress.

  Category 3: MCP ENHANCEMENT
    Guides Claude's use of tools and APIs.
    Embeds domain expertise, reduces errors, optimizes calls.

Run:  python skills.py                         # Full skills status
      python skills.py --category document     # Document/Asset skills
      python skills.py --category workflow      # Workflow Automation skills
      python skills.py --category mcp           # MCP Enhancement skills
      python skills.py --pipeline              # Skills pipeline (all phases)
      python skills.py --patterns              # Design patterns reference
      python skills.py --audit                 # Doctrine compliance audit

Governed by: skills_doctrine.py — The Skills Department Doctrine
Connected to: doctrine.py, rnd.py, warehouse, agents, council
"""

import sys
import json
from datetime import date
from warehouse.db import get_connection
from strategy import YOUR_SHOP, _q
from skills_doctrine import SKILLS_DOCTRINE, show_full_doctrine, audit_skills


# ════════════════════════════════════════════════════════════════════════
#  SKILLS SCHEMA — extends the warehouse
# ════════════════════════════════════════════════════════════════════════

def init_skills_schema():
    """Create Skills tables in the warehouse."""
    con = get_connection()

    con.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            skill_id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            display_name VARCHAR NOT NULL,
            category VARCHAR NOT NULL,
            description TEXT,
            trigger_phrases TEXT,
            status VARCHAR DEFAULT 'draft',
            phase VARCHAR DEFAULT 'identify',
            pattern VARCHAR,
            priority VARCHAR DEFAULT 'medium',
            doctrine_alignment BOOLEAN DEFAULT TRUE,
            trigger_accuracy DECIMAL(5,2),
            execution_quality DECIMAL(5,2),
            token_efficiency DECIMAL(5,2),
            connected_to TEXT,
            version VARCHAR DEFAULT '0.1.0',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS skill_tests (
            test_id INTEGER PRIMARY KEY,
            skill_id INTEGER REFERENCES skills(skill_id),
            test_type VARCHAR NOT NULL,
            test_input TEXT,
            expected_output TEXT,
            actual_output TEXT,
            passed BOOLEAN,
            notes TEXT,
            run_date DATE DEFAULT CURRENT_DATE
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS skill_deployments (
            deployment_id INTEGER PRIMARY KEY,
            skill_id INTEGER REFERENCES skills(skill_id),
            platform VARCHAR NOT NULL,
            deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            version VARCHAR,
            status VARCHAR DEFAULT 'active',
            notes TEXT
        );
    """)

    con.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_skill START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_skill_test START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_skill_deployment START 1;
    """)

    con.close()


# ════════════════════════════════════════════════════════════════════════
#  SEED DATA — initial skills that serve the corporate structure
# ════════════════════════════════════════════════════════════════════════

def _seed_skills():
    """Seed initial skills aligned with corporate strategy."""
    con = get_connection()

    count = con.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    if count > 0:
        con.close()
        return

    skills = [
        # Category 1: Document / Asset Creation
        {
            "skill_id": 1,
            "name": "competitive-brief",
            "display_name": "Competitive Brief Generator",
            "category": "document",
            "description": (
                "Generates a formatted competitive intelligence brief from warehouse data. "
                "Trigger: 'competitive brief', 'competitor report', 'market analysis doc'."
            ),
            "trigger_phrases": "competitive brief, competitor report, market analysis doc, intel brief",
            "status": "active",
            "phase": "deploy",
            "pattern": "sequential_workflow",
            "priority": "high",
            "doctrine_alignment": True,
            "trigger_accuracy": 94.0,
            "execution_quality": 88.0,
            "token_efficiency": 85.0,
            "connected_to": "warehouse, agents/scorecard, strategy.py",
            "version": "1.0.0",
        },
        {
            "skill_id": 2,
            "name": "pricing-analysis",
            "display_name": "Pricing Analysis Report",
            "category": "document",
            "description": (
                "Generates pricing comparison reports across competitors and services. "
                "Trigger: 'pricing analysis', 'price comparison', 'how are we priced'."
            ),
            "trigger_phrases": "pricing analysis, price comparison, how are we priced, pricing report",
            "status": "active",
            "phase": "deploy",
            "pattern": "domain_intelligence",
            "priority": "high",
            "doctrine_alignment": True,
            "trigger_accuracy": 96.0,
            "execution_quality": 91.0,
            "token_efficiency": 88.0,
            "connected_to": "warehouse/pricing_intelligence, price_history, strategy.py",
            "version": "1.0.0",
        },
        {
            "skill_id": 3,
            "name": "council-brief",
            "display_name": "Council Briefing Package",
            "category": "document",
            "description": (
                "Prepares a formal briefing package for the advisory council. "
                "Trigger: 'council brief', 'prepare for council', 'advisory report'."
            ),
            "trigger_phrases": "council brief, prepare for council, advisory report, board meeting",
            "status": "testing",
            "phase": "test",
            "pattern": "sequential_workflow",
            "priority": "medium",
            "doctrine_alignment": True,
            "trigger_accuracy": 88.0,
            "execution_quality": 82.0,
            "token_efficiency": 79.0,
            "connected_to": "council.py, warehouse, strategy.py",
            "version": "0.9.0",
        },

        # Category 2: Workflow Automation
        {
            "skill_id": 4,
            "name": "competitor-onboarding",
            "display_name": "Competitor Onboarding Pipeline",
            "category": "workflow",
            "description": (
                "Automates the full competitor onboarding process: data collection, "
                "enrichment, scoring, and alert setup. Trigger: 'new competitor', "
                "'onboard competitor', 'add competitor'."
            ),
            "trigger_phrases": "new competitor, onboard competitor, add competitor, track competitor",
            "status": "active",
            "phase": "deploy",
            "pattern": "sequential_workflow",
            "priority": "critical",
            "doctrine_alignment": True,
            "trigger_accuracy": 92.0,
            "execution_quality": 87.0,
            "token_efficiency": 82.0,
            "connected_to": "agents/pricing_scout, agents/review_harvester, agents/scorecard, warehouse",
            "version": "1.1.0",
        },
        {
            "skill_id": 5,
            "name": "weekly-intel-cycle",
            "display_name": "Weekly Intelligence Cycle",
            "category": "workflow",
            "description": (
                "Runs the full CI cycle: collect, analyze, disseminate. "
                "Orchestrates all tier 1-4 agents in sequence. "
                "Trigger: 'run weekly cycle', 'intelligence sweep', 'weekly digest'."
            ),
            "trigger_phrases": "run weekly cycle, intelligence sweep, weekly digest, CI cycle",
            "status": "active",
            "phase": "deploy",
            "pattern": "multi_mcp_coordination",
            "priority": "critical",
            "doctrine_alignment": True,
            "trigger_accuracy": 91.0,
            "execution_quality": 85.0,
            "token_efficiency": 76.0,
            "connected_to": "agents/runner, all tier 1-4 agents, warehouse, alerts_log",
            "version": "1.0.0",
        },
        {
            "skill_id": 6,
            "name": "rnd-project-setup",
            "display_name": "R&D Project Kickoff",
            "category": "workflow",
            "description": (
                "Structured kickoff for new R&D projects. Ensures hypothesis, "
                "success metric, and concept paper exist before work begins. "
                "Trigger: 'new R&D project', 'start research', 'lab project'."
            ),
            "trigger_phrases": "new R&D project, start research, lab project, R&D kickoff",
            "status": "testing",
            "phase": "test",
            "pattern": "domain_intelligence",
            "priority": "medium",
            "doctrine_alignment": True,
            "trigger_accuracy": 89.0,
            "execution_quality": 84.0,
            "token_efficiency": 81.0,
            "connected_to": "rnd.py, rnd_doctrine.py, warehouse",
            "version": "0.8.0",
        },

        # Category 3: MCP Enhancement
        {
            "skill_id": 7,
            "name": "warehouse-query-guide",
            "display_name": "Warehouse Query Optimizer",
            "category": "mcp",
            "description": (
                "Guides Claude to write optimal DuckDB queries against the warehouse. "
                "Knows schema, relationships, and common analysis patterns. "
                "Trigger: 'query warehouse', 'analyze data', 'pull from warehouse'."
            ),
            "trigger_phrases": "query warehouse, analyze data, pull from warehouse, DuckDB query",
            "status": "active",
            "phase": "deploy",
            "pattern": "context_aware_selection",
            "priority": "high",
            "doctrine_alignment": True,
            "trigger_accuracy": 93.0,
            "execution_quality": 90.0,
            "token_efficiency": 92.0,
            "connected_to": "warehouse/db.py, all warehouse tables",
            "version": "1.2.0",
        },
        {
            "skill_id": 8,
            "name": "agent-orchestrator",
            "display_name": "Agent Fleet Orchestrator",
            "category": "mcp",
            "description": (
                "Coordinates multi-agent runs with proper sequencing and error handling. "
                "Knows agent dependencies, data flow, and tier structure. "
                "Trigger: 'run agents', 'agent sweep', 'fleet status'."
            ),
            "trigger_phrases": "run agents, agent sweep, fleet status, orchestrate agents",
            "status": "active",
            "phase": "deploy",
            "pattern": "multi_mcp_coordination",
            "priority": "high",
            "doctrine_alignment": True,
            "trigger_accuracy": 90.0,
            "execution_quality": 86.0,
            "token_efficiency": 84.0,
            "connected_to": "agents/runner, agents/base, all 13 agents",
            "version": "1.0.0",
        },
        {
            "skill_id": 9,
            "name": "expansion-readiness-check",
            "display_name": "Expansion Readiness Assessment",
            "category": "mcp",
            "description": (
                "Runs comprehensive expansion readiness checks against council criteria. "
                "Pulls live data, evaluates all five advisor conditions. "
                "Trigger: 'expansion check', 'am I ready', 'council readiness'."
            ),
            "trigger_phrases": "expansion check, am I ready, council readiness, exit strategy check",
            "status": "design",
            "phase": "design",
            "pattern": "domain_intelligence",
            "priority": "medium",
            "doctrine_alignment": True,
            "trigger_accuracy": None,
            "execution_quality": None,
            "token_efficiency": None,
            "connected_to": "council.py, strategy.py, warehouse",
            "version": "0.3.0",
        },
        {
            "skill_id": 10,
            "name": "site-selection-analysis",
            "display_name": "Site Selection Deep Dive",
            "category": "mcp",
            "description": (
                "Performs multi-factor site selection analysis using warehouse division data. "
                "Evaluates demographics, competition density, pricing, and demand. "
                "Trigger: 'site analysis', 'where to open', 'location evaluation'."
            ),
            "trigger_phrases": "site analysis, where to open, location evaluation, neighborhood analysis",
            "status": "design",
            "phase": "design",
            "pattern": "context_aware_selection",
            "priority": "low",
            "doctrine_alignment": True,
            "trigger_accuracy": None,
            "execution_quality": None,
            "token_efficiency": None,
            "connected_to": "warehouse/site_selection, warehouse/market_share, warehouse/demand_forecasting",
            "version": "0.1.0",
        },
    ]

    for s in skills:
        cols = ", ".join(s.keys())
        placeholders = ", ".join(["?" for _ in s])
        con.execute(f"INSERT INTO skills ({cols}) VALUES ({placeholders})", list(s.values()))

    con.close()
    print("  Skills seed data loaded.")


# ════════════════════════════════════════════════════════════════════════
#  DISPLAY FUNCTIONS
# ════════════════════════════════════════════════════════════════════════

def _header(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}")


def _status_icon(status):
    icons = {
        "active": "[LIVE]",
        "testing": "[TEST]",
        "design": "[PLAN]",
        "draft": "[IDEA]",
        "retired": "[DEAD]",
    }
    return icons.get(status, "[????]")


def _phase_bar(phase):
    phases = ["identify", "design", "build", "test", "deploy", "maintain"]
    idx = phases.index(phase) if phase in phases else 0
    filled = idx + 1
    bar = "".join(["█" if i < filled else "░" for i in range(6)])
    return f"[{bar}] {phase.upper()}"


def show_skills_status():
    """Print full skills department status."""
    _header("SKILLS DEPARTMENT — STATUS REPORT")

    try:
        skills = _q("""
            SELECT * FROM skills ORDER BY
                CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                WHEN 'medium' THEN 2 ELSE 3 END,
                skill_id
        """)
    except Exception:
        print("  Skills table not found. Initializing...")
        init_skills_schema()
        _seed_skills()
        skills = _q("SELECT * FROM skills ORDER BY skill_id")

    if not skills:
        print("  No skills registered.\n")
        return

    # Summary stats
    total = len(skills)
    active = sum(1 for s in skills if s["status"] == "active")
    testing = sum(1 for s in skills if s["status"] == "testing")
    design = sum(1 for s in skills if s["status"] in ("design", "draft"))

    cat_counts = {}
    for s in skills:
        cat = s["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    print(f"\n  FLEET: {total} skills | {active} ACTIVE | {testing} TESTING | {design} IN DESIGN")
    print(f"  CATEGORIES: {cat_counts.get('document', 0)} Document | {cat_counts.get('workflow', 0)} Workflow | {cat_counts.get('mcp', 0)} MCP Enhancement")

    # By category
    for cat, cat_label in [("document", "DOCUMENT / ASSET CREATION"),
                            ("workflow", "WORKFLOW AUTOMATION"),
                            ("mcp", "MCP ENHANCEMENT")]:
        cat_skills = [s for s in skills if s["category"] == cat]
        if not cat_skills:
            continue

        print(f"\n  {'─' * 66}")
        print(f"  CATEGORY: {cat_label}")
        print(f"  {'─' * 66}")

        for s in cat_skills:
            icon = _status_icon(s["status"])
            phase_bar = _phase_bar(s.get("phase", "identify"))
            print(f"\n    {icon} {s['display_name']} (v{s['version']})")
            print(f"           Folder: {s['name']}/")
            print(f"           Phase:  {phase_bar}")
            print(f"           Priority: {s['priority'].upper()}")

            ta = s.get("trigger_accuracy")
            eq = s.get("execution_quality")
            te = s.get("token_efficiency")
            if ta is not None:
                print(f"           Trigger: {ta}%  |  Quality: {eq}%  |  Tokens: {te}%")

            if s.get("connected_to"):
                print(f"           Links:  {s['connected_to']}")

            if s.get("description"):
                desc = s["description"][:120]
                print(f"           Desc:   {desc}...")

    print()


def show_category(category):
    """Show skills for a specific category."""
    cat_labels = {
        "document": "DOCUMENT / ASSET CREATION",
        "workflow": "WORKFLOW AUTOMATION",
        "mcp": "MCP ENHANCEMENT",
    }

    if category not in cat_labels:
        print(f"  Unknown category: {category}")
        print(f"  Valid: document, workflow, mcp")
        return

    _header(f"SKILLS — {cat_labels[category]}")

    try:
        skills = _q(
            "SELECT * FROM skills WHERE category = ? ORDER BY priority, skill_id",
            [category]
        )
    except Exception:
        print("  Skills table not found.\n")
        return

    if not skills:
        print(f"  No {category} skills registered.\n")
        return

    for s in skills:
        icon = _status_icon(s["status"])
        phase_bar = _phase_bar(s.get("phase", "identify"))
        print(f"\n  {icon} {s['display_name']} (v{s['version']})")
        print(f"         Folder: {s['name']}/")
        print(f"         Phase:  {phase_bar}")
        print(f"         Pattern: {s.get('pattern', 'N/A')}")

        if s.get("description"):
            print(f"         {s['description']}")

        if s.get("trigger_phrases"):
            print(f"         Triggers: {s['trigger_phrases']}")

        ta = s.get("trigger_accuracy")
        eq = s.get("execution_quality")
        if ta is not None:
            print(f"         Trigger: {ta}%  |  Quality: {eq}%")

    print()


def show_pipeline():
    """Show all skills organized by lifecycle phase."""
    _header("SKILLS PIPELINE — BY LIFECYCLE PHASE")

    phases = ["identify", "design", "build", "test", "deploy", "maintain"]

    try:
        skills = _q("SELECT * FROM skills WHERE status != 'retired' ORDER BY skill_id")
    except Exception:
        print("  Skills table not found.\n")
        return

    for phase in phases:
        phase_skills = [s for s in skills if s.get("phase") == phase]
        count = len(phase_skills)
        bar = _phase_bar(phase)

        print(f"\n  {bar}  ({count} skills)")
        if phase_skills:
            for s in phase_skills:
                cat_tag = s["category"][:3].upper()
                print(f"    [{cat_tag}] {s['display_name']} — {s['name']}/ v{s['version']}")
        else:
            print(f"    (empty)")

    print()


def show_patterns():
    """Print the design patterns reference."""
    _header("SKILL DESIGN PATTERNS REFERENCE")

    patterns = SKILLS_DOCTRINE["design_patterns"]
    print(f"\n  {patterns['title']}")
    print(f"  {'─' * 50}")
    for line in patterns["text"].split("\n"):
        print(f"  {line}")

    print(f"\n  {'─' * 50}")
    print("  PATTERN USAGE IN ACTIVE SKILLS:")
    print(f"  {'─' * 50}")

    try:
        skills = _q("SELECT name, display_name, pattern FROM skills WHERE pattern IS NOT NULL ORDER BY pattern")
        for s in skills:
            print(f"    {s['pattern']:30s} → {s['display_name']}")
    except Exception:
        print("    (No skills data available)")

    print()


# ════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]

    # Ensure schema exists
    init_skills_schema()
    _seed_skills()

    if "--category" in args:
        idx = args.index("--category")
        if idx + 1 < len(args):
            show_category(args[idx + 1])
        else:
            print("  Usage: python skills.py --category <document|workflow|mcp>")
    elif "--pipeline" in args:
        show_pipeline()
    elif "--patterns" in args:
        show_patterns()
    elif "--audit" in args:
        audit_skills()
    elif "--doctrine" in args:
        show_full_doctrine()
    else:
        show_skills_status()
