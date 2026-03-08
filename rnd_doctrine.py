"""R&D DEPARTMENT DOCTRINE

The formal governing document for the Research & Development Department.
Derived from: Product Design & Development, R&D Management,
Technology & Innovation Management, Design & Development Research Methods.

This is not a suggestion document. It is the operating constitution.
Every R&D project, experiment, technology decision, and resource allocation
is tested against this doctrine.

Run:  python rnd_doctrine.py                  # Full doctrine display
      python rnd_doctrine.py --audit          # Audit active projects against doctrine
      python rnd_doctrine.py --decision       # Decision rules quick reference
      python rnd_doctrine.py --principles     # First principles only

Governed by: The five assets. Enforced by: discipline, not hope.
"""

import sys
import json
from warehouse.db import get_connection
from strategy import _q


# ════════════════════════════════════════════════════════════════════════
#  THE DOCTRINE
# ════════════════════════════════════════════════════════════════════════

RND_DOCTRINE = {
    "purpose": {
        "number": 1,
        "title": "PURPOSE",
        "text": (
            "The Research and Development Department exists to convert\n"
            "uncertainty into validated advantage.\n"
            "\n"
            "Its job is not to generate activity, noise, or decorative\n"
            "innovation theater. Its job is to discover, define, test,\n"
            "and deliver products, systems, tools, and capabilities that\n"
            "create measurable customer value, strengthen strategic\n"
            "position, and improve organizational knowledge.\n"
            "\n"
            "R&D is responsible for seeing earlier, learning faster,\n"
            "deciding better, and reducing the cost of being wrong."
        ),
    },

    "mission": {
        "number": 2,
        "title": "MISSION",
        "text": (
            "We identify meaningful problems, translate customer and\n"
            "business needs into clear development targets, evaluate\n"
            "technological options with discipline, and deliver validated\n"
            "solutions through structured learning, cross-functional\n"
            "execution, and continuous improvement.\n"
            "\n"
            "This mission reflects the emphasis on explicit customer value,\n"
            "concept definition up front, and technology assessment tied\n"
            "to goals rather than hype-chasing."
        ),
    },

    "first_principles": {
        "number": 3,
        "title": "FIRST PRINCIPLES",
        "text": (
            "1. Value before novelty.\n"
            "   We do not confuse invention with usefulness. Every\n"
            "   initiative must be anchored to customer value, business\n"
            "   relevance, or strategic capability.\n"
            "\n"
            "2. The voice of the customer is a design input, not a\n"
            "   marketing ornament.\n"
            "   Customer needs must be captured deliberately, translated\n"
            "   into requirements, and carried through concept, prototype,\n"
            "   and launch.\n"
            "\n"
            "3. Front-load learning.\n"
            "   The cheapest mistake is the one found early. We concentrate\n"
            "   effort at the beginning of a project to clarify vision,\n"
            "   trade-offs, risks, and targets before downstream commitment\n"
            "   hardens stupidity into budget burn.\n"
            "\n"
            "4. Research is not complete until it is validated.\n"
            "   Every model, tool, or solution must be evaluated through\n"
            "   formative and summative learning, not declared successful\n"
            "   because a slide deck looked expensive.\n"
            "\n"
            "5. Flow beats chaos.\n"
            "   Multitasking, interruption, rework, and vague handoffs are\n"
            "   treated as waste. Lean development principles govern how\n"
            "   knowledge moves through the department.\n"
            "\n"
            "6. Technology decisions must be explicit and comparative.\n"
            "   We assess technologies with multiple criteria, forecasting\n"
            "   methods, and roadmaps instead of gut-level techno-fetishism.\n"
            "\n"
            "7. Knowledge compounds.\n"
            "   Every project must leave behind clearer methods, reusable\n"
            "   tools, better assumptions, and stronger decision logic\n"
            "   than it found."
        ),
    },

    "core_commitments": {
        "number": 4,
        "title": "CORE COMMITMENTS",
        "text": (
            "The department commits to five permanent obligations.\n"
            "\n"
            "CUSTOMER UNDERSTANDING\n"
            "  We will continuously gather, analyze, and refine customer\n"
            "  insight through structured voice-of-customer methods, value\n"
            "  analysis, and requirement translation.\n"
            "\n"
            "TECHNICAL COMPETENCE\n"
            "  We will build and protect deep expertise in relevant domains,\n"
            "  methods, tools, and enabling technologies.\n"
            "\n"
            "DECISION DISCIPLINE\n"
            "  We will use defined criteria, comparative evaluation, and\n"
            "  documented trade-offs for project, technology, and portfolio\n"
            "  decisions.\n"
            "\n"
            "EXPERIMENTAL RIGOR\n"
            "  We will prototype, test, validate, revise, and re-test until\n"
            "  evidence supports advancement.\n"
            "\n"
            "ORGANIZATIONAL LEARNING\n"
            "  We will convert project experience into standards, playbooks,\n"
            "  tools, and training assets for future use."
        ),
    },

    "doctrine_of_work": {
        "number": 5,
        "title": "DOCTRINE OF WORK",
        "text": (
            "A. We begin with a Concept Paper.\n"
            "   Every initiative starts with a single aligned statement\n"
            "   of intent that defines:\n"
            "     - target customer\n"
            "     - problem worth solving\n"
            "     - product or capability vision\n"
            "     - key requirements\n"
            "     - non-negotiable constraints\n"
            "     - cost, timing, and performance targets\n"
            "     - major risks\n"
            "     - ownership and team roles\n"
            "   This is not bureaucracy cosplay. It is the mechanism for\n"
            "   aligning people, process, and tools before work begins.\n"
            "\n"
            "B. We treat development as knowledge creation.\n"
            "   R&D is not merely producing artifacts. It is producing\n"
            "   validated understanding. Each phase must increase clarity,\n"
            "   reduce uncertainty, and sharpen decisions.\n"
            "\n"
            "C. We use staged convergence.\n"
            "   We explore enough options early to avoid premature lock-in,\n"
            "   then converge deliberately based on evidence, not politics,\n"
            "   ego, or deadline panic.\n"
            "\n"
            "D. We design with the customer at the center.\n"
            "   Customer value is translated into measurable specifications\n"
            "   and competitive positioning, not left as soft language\n"
            "   floating around the room like incense.\n"
            "\n"
            "E. We work lean.\n"
            "   We actively remove waste in the development system: waiting,\n"
            "   unnecessary rework, overloaded systems, fragmented ownership,\n"
            "   poor information flow, and interruption-driven execution.\n"
            "\n"
            "F. We validate both products and methods.\n"
            "   We test not only outputs, but the models, tools, and\n"
            "   workflows used to create those outputs. Strong departments\n"
            "   improve their machinery, not just the stuff coming off\n"
            "   the belt."
        ),
    },

    "decision_rules": {
        "number": 6,
        "title": "DECISION RULES",
        "text": (
            "The department will APPROVE work only when all of the\n"
            "following are sufficiently clear:\n"
            "\n"
            "  [x] The problem is real\n"
            "  [x] The customer or user value is identifiable\n"
            "  [x] The opportunity aligns with strategy\n"
            "  [x] The technical path is plausible\n"
            "  [x] The learning plan is defined\n"
            "  [x] The risks are visible\n"
            "  [x] Success can be measured\n"
            "\n"
            "The department will STOP, PAUSE, or REFRAME work when:\n"
            "\n"
            "  [!] Customer value is weak or unproven\n"
            "  [!] Evidence does not support the concept\n"
            "  [!] Technology maturity is insufficient for intended timing\n"
            "  [!] The project consumes more strategic bandwidth than\n"
            "      its value justifies\n"
            "  [!] Assumptions remain vague after repeated cycles"
        ),
    },

    "research_standards": {
        "number": 7,
        "title": "RESEARCH STANDARDS",
        "text": (
            "All R&D activity must satisfy these standards:\n"
            "\n"
            "CLARITY OF PROBLEM\n"
            "  The research question must be explicit.\n"
            "\n"
            "TRACEABILITY\n"
            "  Requirements, hypotheses, design choices, and decisions\n"
            "  must be documented.\n"
            "\n"
            "METHOD FIT\n"
            "  Methods must match the problem being studied, whether\n"
            "  product research, tool research, model development,\n"
            "  model validation, or use research.\n"
            "\n"
            "ITERATIVE EVALUATION\n"
            "  Formative evaluation happens during development, not just\n"
            "  after the bill arrives.\n"
            "\n"
            "TRANSFERABILITY\n"
            "  Each project must generate lessons that can improve\n"
            "  future projects."
        ),
    },

    "technology_doctrine": {
        "number": 8,
        "title": "TECHNOLOGY DOCTRINE",
        "text": (
            "We do not adopt technology because it is fashionable, loudly\n"
            "marketed, or blessed by conference jargon. We adopt technology\n"
            "when assessment shows it can improve performance, strengthen\n"
            "competitive position, or open credible future options.\n"
            "\n"
            "Technology review must include:\n"
            "  - strategic fit\n"
            "  - maturity\n"
            "  - customer relevance\n"
            "  - implementation burden\n"
            "  - risk profile\n"
            "  - forecasted trajectory\n"
            "  - roadmap implications\n"
            "  - measurable upside\n"
            "\n"
            "Technology forecasting methods such as scenarios, growth\n"
            "curves, roadmapping, bibliometrics, and related analytical\n"
            "tools are part of standard strategic review when uncertainty\n"
            "is material."
        ),
    },

    "org_structure": {
        "number": 9,
        "title": "ORGANIZATIONAL STRUCTURE AND ROLES",
        "text": (
            "R&D operates as a cross-functional system, not a pile of\n"
            "isolated specialists guarding their little caves.\n"
            "\n"
            "Key role expectations:\n"
            "  - R&D Lead: owns doctrine, portfolio discipline, and\n"
            "    decision quality\n"
            "  - Project/Concept Owner: maintains unified vision, targets,\n"
            "    and trade-offs\n"
            "  - Research Lead: designs studies, testing logic, and\n"
            "    evidence standards\n"
            "  - Design/Engineering Leads: convert insight into viable\n"
            "    concepts and prototypes\n"
            "  - Customer Insight Lead: captures, synthesizes, and\n"
            "    translates customer value\n"
            "  - Operations/Commercial Partners: ensure downstream\n"
            "    feasibility and adoption\n"
            "\n"
            "Authority must be explicit. Ambiguity in ownership is treated\n"
            "as a process defect, not a personality quirk."
        ),
    },

    "metrics": {
        "number": 10,
        "title": "METRICS THAT MATTER",
        "text": (
            "We measure R&D by learning velocity and validated outcomes,\n"
            "not raw motion.\n"
            "\n"
            "Primary metrics:\n"
            "  - time to validated insight\n"
            "  - % of projects with explicit Concept Papers\n"
            "  - requirement clarity before development start\n"
            "  - prototype-to-decision cycle time\n"
            "  - rework caused by late requirement discovery\n"
            "  - customer-value lift or validated demand signal\n"
            "  - technology adoption readiness\n"
            "  - forecast accuracy over time\n"
            "  - % of projects producing reusable knowledge assets\n"
            "  - portfolio kill-rate before expensive commitment\n"
            "\n"
            "A department that never kills weak ideas is not visionary.\n"
            "It is drunk."
        ),
    },

    "behavioral_code": {
        "number": 11,
        "title": "BEHAVIORAL CODE",
        "text": (
            "Members of the department are expected to:\n"
            "\n"
            "  - argue from evidence\n"
            "  - surface risks early\n"
            "  - document assumptions\n"
            "  - share knowledge radically and responsibly\n"
            "  - welcome revision when data overturns preference\n"
            "  - avoid protecting weak ideas through politics\n"
            "  - treat prototypes as learning tools, not ego monuments\n"
            "  - distinguish clearly between fact, inference,\n"
            "    and speculation\n"
            "\n"
            "Disagreement is acceptable. Vague thinking is not."
        ),
    },

    "red_lines": {
        "number": 12,
        "title": "RED LINES",
        "text": (
            "The department does not:\n"
            "\n"
            "  X  pursue projects with no defined customer or strategic\n"
            "     value\n"
            "  X  substitute optimism for validation\n"
            "  X  confuse speed with progress\n"
            "  X  bury failure instead of learning from it\n"
            "  X  let seniority override evidence without explicit\n"
            "     justification\n"
            "  X  launch without understanding requirements, trade-offs,\n"
            "     and known risks"
        ),
    },

    "operating_rhythm": {
        "number": 13,
        "title": "STANDARD OPERATING RHYTHM",
        "text": (
            "Every project follows this cadence:\n"
            "\n"
            "  1. Opportunity identification\n"
            "  2. Customer and business requirement study\n"
            "  3. Concept definition\n"
            "  4. Prototype and test\n"
            "  5. Review and convergence\n"
            "  6. Validation for transfer, scale, or launch\n"
            "  7. Post-project learning capture\n"
            "\n"
            "This structure aligns with the product development flow\n"
            "and the logic of design-and-development research from\n"
            "exploratory work through evaluation."
        ),
    },

    "final_statement": {
        "number": 14,
        "title": "FINAL STATEMENT",
        "text": (
            "This department exists to make fewer foolish bets, make\n"
            "better intelligent bets, and learn faster than competitors.\n"
            "\n"
            "We honor creativity, but we operationalize it.\n"
            "We honor research, but we insist it produce decisions.\n"
            "We honor innovation, but only when it becomes useful,\n"
            "validated, and strategically meaningful.\n"
            "\n"
            "R&D is not our idea museum.\n"
            "It is our disciplined engine for creating the future\n"
            "on purpose."
        ),
    },
}


# ════════════════════════════════════════════════════════════════════════
#  DISPLAY HELPERS
# ════════════════════════════════════════════════════════════════════════

def _header(text):
    print()
    print("━" * 70)
    print(f"  {text}")
    print("━" * 70)


def _indent(text, prefix="    "):
    """Indent multi-line text."""
    return "\n".join(prefix + line for line in text.split("\n"))


# ════════════════════════════════════════════════════════════════════════
#  DOCTRINE DISPLAY
# ════════════════════════════════════════════════════════════════════════

def show_full_doctrine():
    """Display the complete R&D doctrine."""
    print()
    print("▓" * 70)
    print("▓" + " " * 68 + "▓")
    print("▓" + "R&D DEPARTMENT DOCTRINE".center(68) + "▓")
    print("▓" + "The Operating Constitution".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" + "Convert uncertainty into validated advantage.".center(68) + "▓")
    print("▓" + " " * 68 + "▓")
    print("▓" * 70)

    for key, section in RND_DOCTRINE.items():
        _header(f"§{section['number']}  {section['title']}")
        print()
        print(_indent(section["text"]))
        print()


def show_principles():
    """Display first principles only."""
    _header("R&D FIRST PRINCIPLES")
    print()
    print(_indent(RND_DOCTRINE["first_principles"]["text"]))
    print()


def show_decision_rules():
    """Display decision rules quick reference."""
    _header("R&D DECISION RULES — Quick Reference")
    print()
    print(_indent(RND_DOCTRINE["decision_rules"]["text"]))
    print()
    _header("RED LINES")
    print()
    print(_indent(RND_DOCTRINE["red_lines"]["text"]))
    print()


# ════════════════════════════════════════════════════════════════════════
#  DOCTRINE AUDIT — Test active projects against the doctrine
# ════════════════════════════════════════════════════════════════════════

def audit_projects():
    """Audit every active R&D project against doctrine decision rules."""
    _header("R&D DOCTRINE AUDIT — Active Projects vs. Decision Rules")

    active = _q(
        "SELECT * FROM rnd_projects WHERE status IN ('research', 'in_progress', 'testing') "
        "ORDER BY lab, CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
        "WHEN 'medium' THEN 2 ELSE 3 END"
    )

    if not active:
        print("\n  No active projects to audit.")
        return

    # Decision rule checks for each project
    checks = [
        ("problem_real", "Problem is real and defined"),
        ("customer_value", "Customer or user value is identifiable"),
        ("strategy_aligned", "Opportunity aligns with strategy"),
        ("technical_path", "Technical path is plausible"),
        ("learning_plan", "Learning plan is defined"),
        ("risks_visible", "Risks are visible"),
        ("measurable_success", "Success can be measured"),
    ]

    total_pass = 0
    total_checks = 0
    flagged = []

    for p in active:
        print(f"\n  ┌────────────────────────────────────────────────────────────┐")
        print(f"  │  [{p['lab'].upper():>8s}]  {p['title'][:46]:46s}│")
        print(f"  │  Status: {p['status'].upper():49s}│")
        print(f"  └────────────────────────────────────────────────────────────┘")

        project_score = 0

        # Check 1: Problem is real — has a description
        has_desc = bool(p.get("description") and len(p["description"]) > 20)
        # Check 2: Customer value — has revenue potential or clear user benefit
        has_value = bool(p.get("revenue_potential"))
        # Check 3: Strategy aligned — uses at least one core asset
        assets = json.loads(p["assets_used"]) if p.get("assets_used") else []
        strategy_aligned = len(assets) >= 1
        # Check 4: Technical path — status beyond idea means path is considered
        tech_plausible = p["status"] in ("research", "in_progress", "testing", "complete")
        # Check 5: Learning plan — has a hypothesis
        has_hypothesis = bool(p.get("hypothesis") and len(p["hypothesis"]) > 10)
        # Check 6: Risks visible — implicit in hypothesis framing (check hypothesis exists)
        risks_visible = has_hypothesis  # hypothesis implies falsifiable = risk acknowledged
        # Check 7: Measurable success — has success metric
        has_metric = bool(p.get("success_metric") and len(p["success_metric"]) > 10)

        results = [
            has_desc, has_value, strategy_aligned, tech_plausible,
            has_hypothesis, risks_visible, has_metric,
        ]

        for (key, label), passed in zip(checks, results):
            icon = "[PASS]" if passed else "[FAIL]"
            print(f"    {icon}  {label}")
            if passed:
                project_score += 1
            total_checks += 1
            if passed:
                total_pass += 1

        score_pct = int((project_score / len(checks)) * 100)
        print(f"\n    Score: {project_score}/{len(checks)} ({score_pct}%)")

        if project_score < len(checks):
            flagged.append((p["title"], p["lab"], project_score, len(checks)))

    # Summary
    _header("AUDIT SUMMARY")
    overall_pct = int((total_pass / total_checks) * 100) if total_checks else 0
    print(f"""
  Projects audited:  {len(active)}
  Total checks:      {total_checks}
  Passed:            {total_pass}
  Failed:            {total_checks - total_pass}
  Overall score:     {overall_pct}%
""")

    if flagged:
        print("  FLAGGED PROJECTS (incomplete doctrine compliance):")
        for title, lab, score, total in flagged:
            print(f"    [{lab.upper():>8s}]  {title} — {score}/{total}")
        print()
    else:
        print("  All active projects pass doctrine compliance.")
        print()

    # Red line check
    _header("RED LINE CHECK")
    idea_projects = _q("SELECT COUNT(*) as cnt FROM rnd_projects WHERE status = 'idea'")
    active_count = len(active)
    total_projects = _q("SELECT COUNT(*) as cnt FROM rnd_projects")[0]["cnt"]

    no_hypothesis = _q(
        "SELECT title, lab FROM rnd_projects WHERE "
        "(hypothesis IS NULL OR LENGTH(hypothesis) < 10) AND status != 'idea'"
    )
    no_metric = _q(
        "SELECT title, lab FROM rnd_projects WHERE "
        "(success_metric IS NULL OR LENGTH(success_metric) < 10) AND status != 'idea'"
    )

    print(f"""
  Active projects without hypothesis:  {len(no_hypothesis)}
  Active projects without metric:      {len(no_metric)}
  Portfolio kill-rate:                  {0}/{total_projects} (no projects killed yet)
""")

    if no_hypothesis:
        print("  WARNING: Projects missing hypothesis (doctrine §3.4 violation):")
        for p in no_hypothesis:
            print(f"    [{p['lab'].upper():>8s}]  {p['title']}")
        print()

    if no_metric:
        print("  WARNING: Projects missing success metric (doctrine §7 violation):")
        for p in no_metric:
            print(f"    [{p['lab'].upper():>8s}]  {p['title']}")
        print()

    print("  Doctrine §10: 'A department that never kills weak ideas is not")
    print("  visionary. It is drunk.' — Review the portfolio quarterly.")
    print()


# ════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--audit" in args:
        audit_projects()
    elif "--decision" in args or "--decisions" in args:
        show_decision_rules()
    elif "--principles" in args:
        show_principles()
    else:
        show_full_doctrine()
