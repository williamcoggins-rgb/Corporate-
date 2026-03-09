"""SKILLS DEPARTMENT DOCTRINE

The formal governing document for the Skills Development Department.
Derived from: Claude Skills Architecture, Progressive Disclosure Design,
Workflow Automation, Composable AI Systems.

This is not a suggestion document. It is the operating constitution.
Every skill created, tested, deployed, and maintained is governed by
this doctrine.

Run:  python skills_doctrine.py                  # Full doctrine display
      python skills_doctrine.py --audit          # Audit active skills against doctrine
      python skills_doctrine.py --principles     # Core principles only
      python skills_doctrine.py --checklist      # Pre-deployment checklist

Governed by: The six phases. Enforced by: structure, not hope.
"""

import sys
import json
from warehouse.db import get_connection
from strategy import _q


# ════════════════════════════════════════════════════════════════════════
#  THE DOCTRINE
# ════════════════════════════════════════════════════════════════════════

SKILLS_DOCTRINE = {
    "purpose": {
        "number": 1,
        "title": "PURPOSE",
        "text": (
            "The Skills Department exists to convert raw tool access\n"
            "into reliable, repeatable workflows.\n"
            "\n"
            "Its job is not to generate clever prompts or decorative\n"
            "automation theater. Its job is to discover, define, test,\n"
            "and deliver instructional packages that make Claude perform\n"
            "domain-specific tasks consistently, efficiently, and with\n"
            "measurable quality improvement over baseline.\n"
            "\n"
            "Without skills, every interaction starts from scratch.\n"
            "With skills, institutional knowledge compounds."
        ),
    },

    "mission": {
        "number": 2,
        "title": "MISSION",
        "text": (
            "We identify repeatable tasks, translate operational and\n"
            "strategic needs into structured skill packages, validate\n"
            "trigger accuracy and execution quality through testing,\n"
            "and deploy skills that reduce friction, eliminate errors,\n"
            "and encode domain expertise into the AI layer.\n"
            "\n"
            "Skills are the bridge between what the warehouse knows\n"
            "and what Claude can do with that knowledge."
        ),
    },

    "core_principles": {
        "number": 3,
        "title": "CORE PRINCIPLES",
        "text": (
            "Three design principles govern every skill:\n"
            "\n"
            "  1. PROGRESSIVE DISCLOSURE\n"
            "     Three layers of information loading:\n"
            "       - YAML frontmatter: Always loaded, brief metadata\n"
            "       - SKILL.md body: Loaded when relevant, core instructions\n"
            "       - Linked files: Loaded only if needed, deep references\n"
            "     Minimize token usage. Never front-load everything.\n"
            "\n"
            "  2. COMPOSABILITY\n"
            "     Every skill must work alongside other skills.\n"
            "     No skill assumes it is the only one active.\n"
            "     Skills coordinate, they do not compete.\n"
            "\n"
            "  3. PORTABILITY\n"
            "     Skills work across Claude.ai, Claude Code, and API.\n"
            "     No platform-specific dependencies unless documented.\n"
            "     The skill is the recipe. The MCP is the kitchen."
        ),
    },

    "skill_anatomy": {
        "number": 4,
        "title": "SKILL ANATOMY",
        "text": (
            "Every skill is a folder containing:\n"
            "\n"
            "  REQUIRED:\n"
            "    SKILL.md         — Markdown with YAML frontmatter\n"
            "                       Contains: name, description, instructions\n"
            "\n"
            "  OPTIONAL:\n"
            "    scripts/         — Executable code (Python, Bash)\n"
            "    references/      — Documentation loaded on demand\n"
            "    assets/          — Templates, fonts, icons\n"
            "\n"
            "  YAML FRONTMATTER RULES:\n"
            "    - name: kebab-case, matches folder name\n"
            "    - description: What it does + when to trigger (<1024 chars)\n"
            "    - No XML tags in frontmatter\n"
            "    - No 'claude' or 'anthropic' in skill names\n"
            "\n"
            "  FOLDER NAMING:\n"
            "    - Kebab-case only (e.g., pricing-analysis)\n"
            "    - No spaces, underscores, or capitals\n"
            "    - No README.md inside skill folders"
        ),
    },

    "skill_categories": {
        "number": 5,
        "title": "SKILL CATEGORIES",
        "text": (
            "Three categories of skills, each with different design patterns:\n"
            "\n"
            "  CATEGORY 1: DOCUMENT / ASSET CREATION\n"
            "    Purpose: Generate documents, reports, designs\n"
            "    Pattern: Embed style guides, use templates\n"
            "    Example: Generate competitive analysis PDF\n"
            "\n"
            "  CATEGORY 2: WORKFLOW AUTOMATION\n"
            "    Purpose: Multi-step processes with validation\n"
            "    Pattern: Sequential steps, checkpoints, templates\n"
            "    Example: Competitor onboarding pipeline\n"
            "\n"
            "  CATEGORY 3: MCP ENHANCEMENT\n"
            "    Purpose: Guide tool usage, coordinate API calls\n"
            "    Pattern: Embed domain expertise, reduce errors\n"
            "    Example: Warehouse query optimization skill"
        ),
    },

    "design_patterns": {
        "number": 6,
        "title": "DESIGN PATTERNS",
        "text": (
            "Five proven patterns for skill construction:\n"
            "\n"
            "  PATTERN 1: SEQUENTIAL WORKFLOW\n"
            "    Steps with dependencies and validation gates.\n"
            "    Each step must complete before the next begins.\n"
            "\n"
            "  PATTERN 2: MULTI-MCP COORDINATION\n"
            "    Orchestrate calls across multiple services.\n"
            "    Example: Pull Figma > analyze > create Linear tasks.\n"
            "\n"
            "  PATTERN 3: ITERATIVE REFINEMENT\n"
            "    Draft > check > refine loop with scripts.\n"
            "    Quality improves with each iteration.\n"
            "\n"
            "  PATTERN 4: CONTEXT-AWARE TOOL SELECTION\n"
            "    Decision tree selects the right tool for context.\n"
            "    Example: Choose storage method based on file type.\n"
            "\n"
            "  PATTERN 5: DOMAIN-SPECIFIC INTELLIGENCE\n"
            "    Compliance and validation before any action.\n"
            "    Example: Check doctrine alignment before execution."
        ),
    },

    "quality_gates": {
        "number": 7,
        "title": "QUALITY GATES",
        "text": (
            "Every skill must pass these gates before deployment:\n"
            "\n"
            "  GATE 1: TRIGGER ACCURACY\n"
            "    - 90%+ trigger rate on relevant queries\n"
            "    - <5% false trigger rate on unrelated queries\n"
            "    - Tested with paraphrased and edge-case inputs\n"
            "\n"
            "  GATE 2: EXECUTION QUALITY\n"
            "    - Minimal tool calls and token usage\n"
            "    - Zero failed API calls in happy path\n"
            "    - Consistent output format across runs\n"
            "\n"
            "  GATE 3: USER EXPERIENCE\n"
            "    - No manual redirects needed\n"
            "    - Works for new users without training\n"
            "    - Output matches or exceeds no-skill baseline\n"
            "\n"
            "  GATE 4: DOCTRINE ALIGNMENT\n"
            "    - Serves a defined strategic objective\n"
            "    - Does not duplicate existing capabilities\n"
            "    - Composable with other active skills"
        ),
    },

    "lifecycle": {
        "number": 8,
        "title": "SKILL LIFECYCLE",
        "text": (
            "Six phases govern a skill from idea to retirement:\n"
            "\n"
            "  PHASE 1: IDENTIFY\n"
            "    Define 2-3 concrete use cases.\n"
            "    Ask: What does the user want? What steps are needed?\n"
            "\n"
            "  PHASE 2: DESIGN\n"
            "    Choose category. Write YAML. Structure SKILL.md.\n"
            "    Plan scripts and references.\n"
            "\n"
            "  PHASE 3: BUILD\n"
            "    Write instructions. Create scripts. Bundle assets.\n"
            "    Keep SKILL.md under 5,000 words.\n"
            "\n"
            "  PHASE 4: TEST\n"
            "    Manual, scripted, and programmatic testing.\n"
            "    Trigger tests + functional tests + baseline comparison.\n"
            "\n"
            "  PHASE 5: DEPLOY\n"
            "    Upload to Claude.ai or deploy via API.\n"
            "    Document installation and usage.\n"
            "\n"
            "  PHASE 6: MAINTAIN\n"
            "    Monitor feedback. Update version. Retire if obsolete.\n"
            "    Skills that don't get used get killed."
        ),
    },

    "troubleshooting": {
        "number": 9,
        "title": "TROUBLESHOOTING DOCTRINE",
        "text": (
            "Common failure modes and their prescribed fixes:\n"
            "\n"
            "  PROBLEM: Upload fails\n"
            "  FIX: Check SKILL.md name format, validate YAML syntax\n"
            "\n"
            "  PROBLEM: Skill doesn't trigger\n"
            "  FIX: Add keywords to description, test with Claude directly\n"
            "\n"
            "  PROBLEM: Skill triggers too often\n"
            "  FIX: Add negatives ('Do NOT use for...'), increase specificity\n"
            "\n"
            "  PROBLEM: MCP tools fail\n"
            "  FIX: Verify MCP connection and API keys independently\n"
            "\n"
            "  PROBLEM: Instructions ignored\n"
            "  FIX: Make instructions concise and top-loaded,\n"
            "       add 'Performance Notes' section for thoroughness\n"
            "\n"
            "  PROBLEM: Context window bloat\n"
            "  FIX: Keep SKILL.md <5,000 words, limit active skills,\n"
            "       use progressive disclosure aggressively"
        ),
    },

    "integration_with_corporate": {
        "number": 10,
        "title": "INTEGRATION WITH CORPORATE HQ",
        "text": (
            "Skills are not standalone — they serve the corporate structure:\n"
            "\n"
            "  DOCTRINE CONNECTION:\n"
            "    Every skill must trace to a doctrine principle.\n"
            "    Skills that serve no strategic purpose are killed.\n"
            "\n"
            "  WAREHOUSE CONNECTION:\n"
            "    Skills can read from and write to the warehouse.\n"
            "    MCP Enhancement skills are the primary bridge.\n"
            "\n"
            "  AGENT CONNECTION:\n"
            "    Skills can orchestrate existing agents.\n"
            "    Workflow Automation skills coordinate agent runs.\n"
            "\n"
            "  R&D CONNECTION:\n"
            "    New skills are prototyped in R&D labs.\n"
            "    Validated skills graduate to production.\n"
            "\n"
            "  COUNCIL CONNECTION:\n"
            "    Skills affecting strategic direction require council review.\n"
            "    The council evaluates skill impact on expansion readiness."
        ),
    },
}


# ════════════════════════════════════════════════════════════════════════
#  DISPLAY FUNCTIONS
# ════════════════════════════════════════════════════════════════════════

def _header(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}")


def show_full_doctrine():
    """Print the complete Skills Doctrine."""
    _header("THE SKILLS DEPARTMENT DOCTRINE")
    print("  The operating constitution for skill development and deployment.")
    print("  Every skill created, tested, and maintained obeys this doctrine.\n")

    for key, section in SKILLS_DOCTRINE.items():
        num = section.get("number", "")
        title = section["title"]
        text = section.get("text", "")

        print(f"\n  {'─' * 66}")
        print(f"  ARTICLE {num}: {title}")
        print(f"  {'─' * 66}")
        for line in text.split("\n"):
            print(f"  {line}")

    print(f"\n{'━' * 70}")
    print("  END OF DOCTRINE")
    print(f"{'━' * 70}\n")


def show_principles():
    """Print core principles only."""
    _header("SKILLS DOCTRINE — CORE PRINCIPLES")
    for key in ["purpose", "mission", "core_principles"]:
        section = SKILLS_DOCTRINE[key]
        print(f"\n  ARTICLE {section['number']}: {section['title']}")
        print(f"  {'─' * 50}")
        for line in section["text"].split("\n"):
            print(f"  {line}")
    print()


def show_checklist():
    """Print the pre-deployment checklist."""
    _header("SKILLS PRE-DEPLOYMENT CHECKLIST")
    print("""
  BEFORE BUILD:
    [ ] Use cases defined (2-3 concrete scenarios)
    [ ] Category chosen (Document / Workflow / MCP Enhancement)
    [ ] Folder name is kebab-case
    [ ] YAML frontmatter planned

  DURING BUILD:
    [ ] SKILL.md has valid YAML frontmatter
    [ ] Instructions are actionable with code blocks
    [ ] Scripts in scripts/ are executable
    [ ] References in references/ are organized
    [ ] SKILL.md is under 5,000 words
    [ ] Progressive disclosure applied (3 layers)

  TESTING:
    [ ] Trigger test: fires on relevant queries
    [ ] Trigger test: does NOT fire on unrelated queries
    [ ] Functional test: output is correct
    [ ] Functional test: no API failures
    [ ] Baseline comparison: outperforms no-skill approach
    [ ] Edge cases tested

  DEPLOYMENT:
    [ ] Installation documented
    [ ] Usage examples provided
    [ ] Version tagged
    [ ] Doctrine alignment confirmed

  POST-DEPLOYMENT:
    [ ] Monitoring active
    [ ] Feedback loop established
    [ ] Retirement criteria defined
""")


# ════════════════════════════════════════════════════════════════════════
#  AUDIT — test active skills against doctrine
# ════════════════════════════════════════════════════════════════════════

def audit_skills():
    """Audit active skills against the doctrine."""
    _header("SKILLS DOCTRINE AUDIT")

    try:
        skills = _q("""
            SELECT skill_id, name, category, status, phase,
                   trigger_accuracy, execution_quality, doctrine_alignment
            FROM skills
            WHERE status != 'retired'
            ORDER BY skill_id
        """)
    except Exception:
        print("  No skills table found. Run: python skills.py to initialize.\n")
        return

    if not skills:
        print("  No active skills to audit.\n")
        return

    violations = 0
    warnings = 0

    for s in skills:
        name = s["name"]
        issues = []

        # Check trigger accuracy
        ta = s.get("trigger_accuracy")
        if ta is not None and ta < 90:
            issues.append(f"FAIL: Trigger accuracy {ta}% < 90% minimum")
            violations += 1
        elif ta is not None and ta < 95:
            issues.append(f"WARN: Trigger accuracy {ta}% — room for improvement")
            warnings += 1

        # Check execution quality
        eq = s.get("execution_quality")
        if eq is not None and eq < 80:
            issues.append(f"FAIL: Execution quality {eq}% < 80% minimum")
            violations += 1

        # Check doctrine alignment
        da = s.get("doctrine_alignment")
        if da is not None and not da:
            issues.append("FAIL: Not aligned with doctrine")
            violations += 1

        # Check phase progression
        phase = s.get("phase", "identify")
        status = s.get("status", "draft")
        if status == "active" and phase not in ("deploy", "maintain"):
            issues.append(f"WARN: Active skill still in '{phase}' phase")
            warnings += 1

        # Print results
        status_icon = "PASS" if not issues else "ISSUES"
        print(f"\n  [{status_icon}] {name} ({s['category']})")
        print(f"         Status: {status}  |  Phase: {phase}")
        if issues:
            for issue in issues:
                print(f"         {issue}")
        else:
            print("         All gates passed.")

    print(f"\n  {'─' * 50}")
    print(f"  AUDIT SUMMARY: {len(skills)} skills | {violations} violations | {warnings} warnings")
    if violations > 0:
        print("  ACTION REQUIRED: Fix violations before next deployment.")
    elif warnings > 0:
        print("  STATUS: Passing with warnings. Address when possible.")
    else:
        print("  STATUS: All skills doctrine-compliant.")
    print()


# ════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--audit" in args:
        audit_skills()
    elif "--principles" in args:
        show_principles()
    elif "--checklist" in args:
        show_checklist()
    else:
        show_full_doctrine()
