"""Skill Executor — the bridge between Skills and Agents.

Skills are the brain. Agents are the hands. This module connects them.

A skill executor takes a skill definition and runs the actual agent pipeline
it describes — with proper sequencing, error handling, result collection,
and logging back to the skills tables.

The executor knows:
  - Which agents each skill needs
  - What order to run them in
  - What data to pass between stages
  - How to validate results against skill quality gates
  - How to log execution back to skill_tests and agent_runs

Usage:
    from agents.skill_executor import SkillExecutor

    executor = SkillExecutor()
    result = executor.run_skill("competitor-onboarding", competitor_id=5)
    result = executor.run_skill("weekly-intel-cycle")
    result = executor.run_skill("pricing-analysis")
"""

import json
import datetime
from warehouse.db import get_connection
from agents.base import BaseAgent
from agents.runner import AGENTS, TIERS, run_agents, run_tier, run_all


# ════════════════════════════════════════════════════════════════════════
#  SKILL → AGENT MAPPINGS
#
#  Each skill maps to a sequence of agent stages.
#  Stages run in order. Each stage can depend on the previous stage.
#  If a stage fails and is marked critical, the skill aborts.
# ════════════════════════════════════════════════════════════════════════

SKILL_PIPELINES = {
    # ── Workflow Skills ──────────────────────────────────────────────

    "competitor-onboarding": {
        "description": "Full competitor onboarding: collect → enrich → score → alert",
        "stages": [
            {
                "name": "extract",
                "agents": ["pricing_scout", "review_harvester", "shop_watcher"],
                "critical": True,
                "description": "Collect pricing, reviews, and shop details",
            },
            {
                "name": "enrich",
                "agents": ["normalizer", "barber_enricher"],
                "critical": True,
                "description": "Normalize data and enrich barber profiles",
            },
            {
                "name": "analyze",
                "agents": ["scorecard"],
                "critical": True,
                "description": "Generate competitor scorecard and threat level",
            },
            {
                "name": "alert",
                "agents": ["price_war_alert", "reputation_radar"],
                "critical": False,
                "description": "Check for price wars and reputation signals",
            },
        ],
    },

    "weekly-intel-cycle": {
        "description": "Full CI cycle: all tiers in sequence",
        "stages": [
            {
                "name": "tier1_extraction",
                "agents": TIERS["tier1"],
                "critical": True,
                "description": "Run all extraction agents (street-level scouts)",
            },
            {
                "name": "tier2_enrichment",
                "agents": TIERS["tier2"],
                "critical": True,
                "description": "Run all enrichment agents (detail crew)",
            },
            {
                "name": "tier3_analysis",
                "agents": TIERS["tier3"],
                "critical": True,
                "description": "Run all analytics agents (scorecard)",
            },
            {
                "name": "tier4_alerts",
                "agents": TIERS["tier4"],
                "critical": False,
                "description": "Run all alert agents + weekly digest",
            },
        ],
    },

    "rnd-project-setup": {
        "description": "Validate R&D project setup against doctrine",
        "stages": [
            {
                "name": "market_scan",
                "agents": ["pricing_scout", "social_listener"],
                "critical": False,
                "description": "Scan market context for the research area",
            },
            {
                "name": "competitive_context",
                "agents": ["scorecard"],
                "critical": False,
                "description": "Score competitors relevant to the R&D area",
            },
        ],
    },

    # ── Document Skills ──────────────────────────────────────────────

    "competitive-brief": {
        "description": "Gather data for competitive intelligence brief",
        "stages": [
            {
                "name": "score_refresh",
                "agents": ["scorecard"],
                "critical": True,
                "description": "Refresh competitor scorecards for latest data",
            },
            {
                "name": "alert_scan",
                "agents": ["price_war_alert", "reputation_radar"],
                "critical": False,
                "description": "Scan for active threats to include in brief",
            },
        ],
    },

    "pricing-analysis": {
        "description": "Gather data for pricing analysis report",
        "stages": [
            {
                "name": "price_refresh",
                "agents": ["pricing_scout"],
                "critical": True,
                "description": "Refresh pricing data from all sources",
            },
            {
                "name": "normalize",
                "agents": ["normalizer"],
                "critical": True,
                "description": "Normalize service names and prices",
            },
            {
                "name": "score",
                "agents": ["scorecard"],
                "critical": False,
                "description": "Update scorecards with fresh pricing",
            },
        ],
    },

    "council-brief": {
        "description": "Gather all data needed for council briefing",
        "stages": [
            {
                "name": "full_refresh",
                "agents": TIERS["tier1"],
                "critical": False,
                "description": "Refresh all extraction data",
            },
            {
                "name": "enrich_and_score",
                "agents": ["normalizer", "scorecard"],
                "critical": True,
                "description": "Normalize and score for council review",
            },
            {
                "name": "digest",
                "agents": ["weekly_digest"],
                "critical": True,
                "description": "Generate digest summary for council",
            },
        ],
    },

    # ── MCP Enhancement Skills ───────────────────────────────────────

    "agent-orchestrator": {
        "description": "Smart agent orchestration with dependency awareness",
        "stages": [
            # This skill is special — it dynamically determines stages
            # based on what's requested. Default: full pipeline.
            {
                "name": "full_pipeline",
                "agents": TIERS["tier1"] + TIERS["tier2"] + TIERS["tier3"] + TIERS["tier4"],
                "critical": False,
                "description": "Run full agent fleet in tier order",
            },
        ],
    },

    "warehouse-query-guide": {
        "description": "No agents needed — this skill guides query construction",
        "stages": [],
    },

    "expansion-readiness-check": {
        "description": "Gather data for expansion readiness assessment",
        "stages": [
            {
                "name": "market_data",
                "agents": ["pricing_scout", "social_listener", "platform_scout"],
                "critical": True,
                "description": "Refresh market data for readiness check",
            },
            {
                "name": "scoring",
                "agents": ["scorecard"],
                "critical": True,
                "description": "Update all competitor scores",
            },
        ],
    },

    "site-selection-analysis": {
        "description": "Gather data for site selection deep dive",
        "stages": [
            {
                "name": "area_intel",
                "agents": ["pricing_scout", "shop_watcher", "platform_scout"],
                "critical": True,
                "description": "Collect area intelligence for all neighborhoods",
            },
            {
                "name": "enrichment",
                "agents": ["normalizer", "barber_enricher", "platform_analyzer"],
                "critical": True,
                "description": "Enrich and analyze area data",
            },
            {
                "name": "scoring",
                "agents": ["scorecard"],
                "critical": False,
                "description": "Score areas for site suitability",
            },
        ],
    },
}


# ════════════════════════════════════════════════════════════════════════
#  THE EXECUTOR
# ════════════════════════════════════════════════════════════════════════

class SkillExecutor:
    """Runs a skill's agent pipeline and logs results."""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.results = {}

    def _log(self, msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"  [{timestamp}] {msg}")

    def _log_skill_run(self, skill_name, status, stages_completed, stages_total,
                       agents_run, agents_failed, duration_ms, notes=None):
        """Log the skill execution to skill_tests table."""
        try:
            con = get_connection()
            # Find skill_id
            row = con.execute(
                "SELECT skill_id FROM skills WHERE name = ?", [skill_name]
            ).fetchone()
            if not row:
                con.close()
                return

            skill_id = row[0]
            test_id = con.execute("SELECT nextval('seq_skill_test')").fetchone()[0]

            result_data = json.dumps({
                "stages_completed": stages_completed,
                "stages_total": stages_total,
                "agents_run": agents_run,
                "agents_failed": agents_failed,
                "duration_ms": duration_ms,
            })

            con.execute(
                """INSERT INTO skill_tests
                   (test_id, skill_id, test_type, test_input, actual_output,
                    passed, notes, run_date)
                   VALUES (?, ?, 'execution', ?, ?, ?, ?, CURRENT_DATE)""",
                [test_id, skill_id, "pipeline_run", result_data,
                 status == "completed", notes]
            )

            # Update skill's execution quality based on success rate
            if agents_run > 0:
                success_rate = round(((agents_run - agents_failed) / agents_run) * 100, 1)
                con.execute(
                    "UPDATE skills SET execution_quality = ?, updated_at = CURRENT_TIMESTAMP WHERE skill_id = ?",
                    [success_rate, skill_id]
                )

            con.close()
        except Exception as e:
            self._log(f"Warning: Could not log skill run — {e}")

    def get_pipeline(self, skill_name):
        """Get the agent pipeline for a skill."""
        return SKILL_PIPELINES.get(skill_name)

    def list_skill_agents(self, skill_name):
        """List all agents a skill will run."""
        pipeline = self.get_pipeline(skill_name)
        if not pipeline:
            return []
        agents = []
        for stage in pipeline.get("stages", []):
            agents.extend(stage["agents"])
        return agents

    def run_skill(self, skill_name, **kwargs):
        """Execute a skill's full agent pipeline.

        Returns a dict with:
          - status: "completed" | "partial" | "failed"
          - stages: list of stage results
          - agents_run: total agents executed
          - agents_failed: total agents that failed
          - duration_ms: total execution time
        """
        pipeline = self.get_pipeline(skill_name)
        if not pipeline:
            self._log(f"No pipeline defined for skill: {skill_name}")
            return {"status": "no_pipeline", "skill": skill_name}

        stages = pipeline.get("stages", [])
        if not stages:
            self._log(f"Skill '{skill_name}' has no agent stages (pure guidance skill)")
            return {"status": "no_agents", "skill": skill_name}

        self._log(f"{'=' * 56}")
        self._log(f"SKILL EXECUTOR: {skill_name}")
        self._log(f"{pipeline['description']}")
        self._log(f"{len(stages)} stages, {sum(len(s['agents']) for s in stages)} agents")
        self._log(f"{'=' * 56}")

        start = datetime.datetime.now()
        stage_results = []
        total_agents = 0
        total_failed = 0
        aborted = False

        for i, stage in enumerate(stages):
            stage_name = stage["name"]
            agent_names = stage["agents"]
            critical = stage.get("critical", False)

            self._log(f"")
            self._log(f"STAGE {i + 1}/{len(stages)}: {stage_name}")
            self._log(f"  {stage['description']}")
            self._log(f"  Agents: {', '.join(agent_names)}")

            if self.dry_run:
                self._log(f"  [DRY RUN] Skipping execution")
                stage_results.append({
                    "stage": stage_name,
                    "status": "dry_run",
                    "agents": agent_names,
                })
                continue

            # Run the agents for this stage
            stage_failed = 0
            stage_agents_run = 0

            for agent_name in agent_names:
                agent_cls = AGENTS.get(agent_name)
                if not agent_cls:
                    self._log(f"  Unknown agent: {agent_name} — skipping")
                    stage_failed += 1
                    continue

                self._log(f"  Running: {agent_name} (Tier {agent_cls.tier})...")
                agent = agent_cls(**kwargs)
                try:
                    agent.run()
                    stage_agents_run += 1
                    self._log(f"  Completed: {agent_name} — {agent.records_processed} records")
                except Exception as e:
                    stage_failed += 1
                    stage_agents_run += 1
                    self._log(f"  FAILED: {agent_name} — {e}")

            total_agents += stage_agents_run
            total_failed += stage_failed

            stage_status = "completed" if stage_failed == 0 else "partial"
            if stage_failed == len(agent_names):
                stage_status = "failed"

            stage_results.append({
                "stage": stage_name,
                "status": stage_status,
                "agents_run": stage_agents_run,
                "agents_failed": stage_failed,
                "critical": critical,
            })

            # If a critical stage failed completely, abort
            if critical and stage_status == "failed":
                self._log(f"  CRITICAL STAGE FAILED — aborting skill execution")
                aborted = True
                break

        end = datetime.datetime.now()
        duration_ms = int((end - start).total_seconds() * 1000)

        # Determine overall status
        if aborted:
            status = "failed"
        elif total_failed == 0:
            status = "completed"
        elif total_failed < total_agents:
            status = "partial"
        else:
            status = "failed"

        self._log(f"")
        self._log(f"{'─' * 56}")
        self._log(f"SKILL RESULT: {skill_name} — {status.upper()}")
        self._log(f"  Stages: {len(stage_results)}/{len(stages)} completed")
        self._log(f"  Agents: {total_agents} run, {total_failed} failed")
        self._log(f"  Duration: {duration_ms}ms")
        self._log(f"{'─' * 56}")

        # Log to database
        self._log_skill_run(
            skill_name, status,
            stages_completed=len([s for s in stage_results if s["status"] != "failed"]),
            stages_total=len(stages),
            agents_run=total_agents,
            agents_failed=total_failed,
            duration_ms=duration_ms,
        )

        result = {
            "skill": skill_name,
            "status": status,
            "stages": stage_results,
            "agents_run": total_agents,
            "agents_failed": total_failed,
            "duration_ms": duration_ms,
        }
        self.results[skill_name] = result
        return result

    def run_skill_by_trigger(self, user_input, **kwargs):
        """Match user input to a skill by trigger phrases, then run it.

        Returns the skill result or None if no skill matched.
        """
        user_lower = user_input.lower().strip()

        try:
            con = get_connection()
            skills = con.execute(
                "SELECT name, trigger_phrases FROM skills WHERE status = 'active'"
            ).fetchall()
            con.close()
        except Exception:
            return None

        best_match = None
        best_score = 0

        for skill_name, trigger_phrases in skills:
            if not trigger_phrases:
                continue
            phrases = [p.strip().lower() for p in trigger_phrases.split(",")]
            for phrase in phrases:
                # Exact match
                if phrase in user_lower:
                    score = len(phrase)
                    if score > best_score:
                        best_score = score
                        best_match = skill_name

        if best_match:
            self._log(f"Matched skill: {best_match} (score: {best_score})")
            return self.run_skill(best_match, **kwargs)

        self._log(f"No skill matched for: '{user_input}'")
        return None

    def preview_skill(self, skill_name):
        """Show what a skill will do without running it."""
        pipeline = self.get_pipeline(skill_name)
        if not pipeline:
            print(f"  No pipeline for: {skill_name}")
            return

        print(f"\n  {'━' * 56}")
        print(f"  SKILL PREVIEW: {skill_name}")
        print(f"  {pipeline['description']}")
        print(f"  {'━' * 56}")

        total_agents = 0
        for i, stage in enumerate(pipeline.get("stages", [])):
            agents = stage["agents"]
            total_agents += len(agents)
            critical = " [CRITICAL]" if stage.get("critical") else ""
            print(f"\n  Stage {i + 1}: {stage['name']}{critical}")
            print(f"    {stage['description']}")
            for a in agents:
                cls = AGENTS.get(a)
                tier = f"Tier {cls.tier}" if cls else "???"
                desc = cls.description if cls else "Unknown agent"
                print(f"      {a:25s} ({tier}) — {desc}")

        print(f"\n  Total: {len(pipeline.get('stages', []))} stages, {total_agents} agents")
        print(f"  {'━' * 56}\n")


# ════════════════════════════════════════════════════════════════════════
#  CONVENIENCE: Skill-aware agent runner
# ════════════════════════════════════════════════════════════════════════

def run_skill(skill_name, dry_run=False, **kwargs):
    """Convenience function — run a skill by name."""
    executor = SkillExecutor(dry_run=dry_run)
    return executor.run_skill(skill_name, **kwargs)


def match_and_run(user_input, dry_run=False, **kwargs):
    """Convenience function — match user input to a skill and run it."""
    executor = SkillExecutor(dry_run=dry_run)
    return executor.run_skill_by_trigger(user_input, **kwargs)


def preview_skill(skill_name):
    """Convenience function — preview a skill's pipeline."""
    executor = SkillExecutor()
    executor.preview_skill(skill_name)


# ════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if not args:
        print("\nUsage:")
        print("  python -m agents.skill_executor preview <skill-name>")
        print("  python -m agents.skill_executor run <skill-name>")
        print("  python -m agents.skill_executor dry-run <skill-name>")
        print("  python -m agents.skill_executor match '<user input>'")
        print("  python -m agents.skill_executor list")
        print()
        print("Available skills with pipelines:")
        for name, pipeline in sorted(SKILL_PIPELINES.items()):
            stages = len(pipeline.get("stages", []))
            agents = sum(len(s["agents"]) for s in pipeline.get("stages", []))
            print(f"  {name:30s} {stages} stages, {agents} agents — {pipeline['description']}")
        print()
        sys.exit(0)

    command = args[0]

    if command == "list":
        print("\nSkill Pipelines:")
        print("─" * 60)
        for name, pipeline in sorted(SKILL_PIPELINES.items()):
            stages = len(pipeline.get("stages", []))
            agents = sum(len(s["agents"]) for s in pipeline.get("stages", []))
            print(f"  {name:30s} {stages} stages, {agents} agents")
            print(f"    {pipeline['description']}")
        print()

    elif command == "preview" and len(args) > 1:
        preview_skill(args[1])

    elif command == "run" and len(args) > 1:
        result = run_skill(args[1])
        print(f"\nResult: {result['status'].upper()}")

    elif command == "dry-run" and len(args) > 1:
        result = run_skill(args[1], dry_run=True)
        print(f"\nResult: {result['status'].upper()} (dry run)")

    elif command == "match" and len(args) > 1:
        user_input = " ".join(args[1:])
        result = match_and_run(user_input, dry_run=True)
        if result:
            print(f"\nMatched and ran: {result['skill']}")
        else:
            print(f"\nNo skill matched for: '{user_input}'")

    else:
        print(f"Unknown command: {command}")
