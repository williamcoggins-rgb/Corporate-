"""Tier 3 — Skill Runner

Executes the data-backed skills (competitive-brief, pricing-analysis)
against the warehouse and writes last_run + output summary back to the
skills table, so the Skills Department dashboard reflects real execution.

Runs after Scorecard in the nightly Tier 3 cycle so briefs include
fresh threat scores.

Cadence: Nightly (Tier 3)
"""

from agents.base import BaseAgent


class SkillRunner(BaseAgent):
    name = "skill_runner"
    description = "Executes data-backed skills and records run history"
    tier = 3

    def execute(self):
        from skills import init_skills_schema, run_skill, RUNNABLE_SKILLS

        init_skills_schema()
        for skill_name in RUNNABLE_SKILLS:
            try:
                summary = run_skill(skill_name)
                self.records_processed += 1
                self.log(f"{skill_name}: {summary[:120]}")
            except Exception as e:
                self.log(f"{skill_name} FAILED: {e}")
