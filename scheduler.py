"""CORPORATE HQ — 24/7 Scheduler

Runs the warehouse agent tiers on the correct cadence via APScheduler
(inside the Flask app, or standalone).

Tier-1 data now arrives from Cowork through the /ingest endpoints — the
managed-agent web-search path the scouts used is retired (out of budget), so
there is no local Tier-1 cron. Tiers 2-4 and the digest run the registered
agents directly via agents.runner (no managed-agent sessions).

SCHEDULE:
  Tier 1 (Scout)       → Cowork via /ingest endpoints (no local cron)
  Tier 2 (Process)     → 10:30pm nightly
  Tier 3 (Analytics)   → 11pm nightly
  Tier 4 (Alerts)      → Every 4 hours (alerts only, digest removed)
  Weekly Snapshotter   → Sunday 11:30pm
  Pricing Strategist   → Monday 12:00am
  Market Pulse         → 1st of month 1:00am
  Weekly Digest        → Sunday 8am (dedicated job, not in Tier 4)

All times Eastern (America/New_York)

Usage (standalone):
    python scheduler.py              # Run scheduler as standalone process
    python scheduler.py --once tier1 # Run a single tier immediately and exit

Usage (from Flask app):
    from scheduler import init_scheduler
    init_scheduler(app)
"""

import os
import sys
import logging
import datetime
# NOTE: managed_agent (launch_session/_load_agent_id) is intentionally NOT
# imported here anymore — its web-search sessions are retired. Tiers run
# directly through agents.runner instead.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEDULER] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("corporate_hq_scheduler")


# ── SCHEDULED JOB FUNCTIONS ────────────────────────────────────────────

def run_tier1():
    # Tier 1 (the scouts) delegated to managed-agent web-search sessions, which
    # are retired. Cowork now feeds Tier-1 data directly through the /ingest
    # endpoints, so there is no local Tier-1 job to run here.
    log.info("▶ TIER 1 — fed by Cowork via /ingest endpoints "
             "(local scout trigger retired)")
    return {}


def run_tier2():
    log.info("▶ TIER 2 — Processing cycle starting")
    from agents.runner import run_tier
    results = run_tier("tier2")
    completed = sum(1 for v in results.values() if v == "completed")
    log.info(f"  ✓ Tier 2 complete: {completed}/{len(results)} agents finished")
    return results


def run_tier3():
    log.info("▶ TIER 3 — Analytics cycle starting")
    from agents.runner import run_tier
    results = run_tier("tier3")
    completed = sum(1 for v in results.values() if v == "completed")
    log.info(f"  ✓ Tier 3 complete: {completed}/{len(results)} agents finished")
    return results


def run_tier4():
    log.info("▶ TIER 4 — Alert cycle starting")
    from agents.runner import run_tier
    results = run_tier("tier4")
    completed = sum(1 for v in results.values() if v == "completed")
    log.info(f"  ✓ Tier 4 complete: {completed}/{len(results)} agents finished")
    return results


def run_weekly_snapshotter():
    log.info("▶ WEEKLY SNAPSHOTTER — Capturing competitor state")
    from agents.runner import run_agents
    results = run_agents(["weekly_snapshotter"])
    completed = sum(1 for v in results.values() if v == "completed")
    log.info(f"  ✓ Snapshotter complete: {completed}/{len(results)}")
    return results


def run_pricing_strategist():
    log.info("▶ PRICING STRATEGIST — Analyzing price positioning")
    from agents.runner import run_agents
    results = run_agents(["pricing_strategist"])
    completed = sum(1 for v in results.values() if v == "completed")
    log.info(f"  ✓ Pricing Strategist complete: {completed}/{len(results)}")
    return results


def run_market_pulse():
    log.info("▶ MARKET PULSE — Generating period summaries")
    from agents.runner import run_agents
    results = run_agents(["market_pulse"])
    completed = sum(1 for v in results.values() if v == "completed")
    log.info(f"  ✓ Market Pulse complete: {completed}/{len(results)}")
    return results


def run_weekly_digest():
    log.info("▶ WEEKLY DIGEST — Generating Sunday briefing")
    from agents.runner import run_agents
    results = run_agents(["weekly_digest"])
    completed = sum(1 for v in results.values() if v == "completed")
    log.info(f"  ✓ Digest complete: {completed}/{len(results)}")
    return results


# ── SCHEDULER INIT ─────────────────────────────────────────────────────

def init_scheduler(app=None):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        log.error("APScheduler not installed. Run: pip install apscheduler")
        return None

    scheduler = BackgroundScheduler(timezone="America/New_York")

    # Tier 1 is fed by Cowork via the /ingest endpoints — no local scout cron.
    # (The managed-agent web-search path the scouts used is retired.)

    # Tier 2: 10:30pm nightly — process the day's Cowork-fed data before analytics
    scheduler.add_job(
        run_tier2, CronTrigger(hour=22, minute=30),
        id="tier2_nightly", name="Tier 2 — Nightly Processing",
        replace_existing=True, misfire_grace_time=600,
    )

    # Tier 3: 11pm nightly
    scheduler.add_job(
        run_tier3, CronTrigger(hour=23, minute=0),
        id="tier3_nightly", name="Tier 3 — Nightly Analytics",
        replace_existing=True, misfire_grace_time=600,
    )

    # Tier 4: every 4 hours
    scheduler.add_job(
        run_tier4, CronTrigger(hour="0,4,8,12,16,20", minute=30),
        id="tier4_alerts", name="Tier 4 — Alert Cycle",
        replace_existing=True, misfire_grace_time=300,
    )

    # Weekly Snapshotter: Sunday 11:30pm
    scheduler.add_job(
        run_weekly_snapshotter, CronTrigger(day_of_week="sun", hour=23, minute=30),
        id="weekly_snapshotter", name="Weekly Snapshotter — Sunday Snapshot",
        replace_existing=True, misfire_grace_time=600,
    )

    # Pricing Strategist: Monday 12am (after Snapshotter)
    scheduler.add_job(
        run_pricing_strategist, CronTrigger(day_of_week="mon", hour=0, minute=0),
        id="pricing_strategist", name="Pricing Strategist — Monday Analysis",
        replace_existing=True, misfire_grace_time=600,
    )

    # Market Pulse: 1st of month 1am
    scheduler.add_job(
        run_market_pulse, CronTrigger(day=1, hour=1, minute=0),
        id="market_pulse", name="Market Pulse — Monthly Summary",
        replace_existing=True, misfire_grace_time=600,
    )

    # Weekly digest: Sunday 8am
    scheduler.add_job(
        run_weekly_digest, CronTrigger(day_of_week="sun", hour=8, minute=0),
        id="weekly_digest", name="Weekly Digest — Sunday Briefing",
        replace_existing=True, misfire_grace_time=600,
    )

    scheduler.start()

    log.info("━" * 60)
    log.info("  CORPORATE HQ SCHEDULER — ACTIVE")
    log.info("  Tier-1 data source: Cowork via /ingest endpoints")
    log.info("━" * 60)
    log.info("  Schedule:")
    log.info("    Tier 1 (Scout)       → Cowork via /ingest (no local cron)")
    log.info("    Tier 2 (Process)     → 10:30pm nightly ET")
    log.info("    Tier 3 (Analytics)   → 11pm nightly ET")
    log.info("    Tier 4 (Alerts)      → Every 4 hours ET (alerts only)")
    log.info("    Weekly Snapshotter   → Sunday 11:30pm ET")
    log.info("    Pricing Strategist   → Monday 12:00am ET")
    log.info("    Market Pulse         → 1st of month 1:00am ET")
    log.info("    Weekly Digest        → Sunday 8am ET")
    log.info("━" * 60)

    return scheduler


def get_schedule_status(scheduler):
    if not scheduler:
        return {"status": "not_running", "jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
            "next_run_human": _human_time(next_run) if next_run else "N/A",
        })

    return {
        "status": "running",
        "timezone": "America/New_York",
        "jobs": sorted(jobs, key=lambda j: j["next_run"] or ""),
    }


def _human_time(dt):
    if not dt:
        return "Unknown"
    now = datetime.datetime.now(dt.tzinfo)
    delta = dt - now
    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return f"in {total_seconds}s"
    elif total_seconds < 3600:
        return f"in {total_seconds // 60}m"
    elif total_seconds < 86400:
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        return f"in {h}h {m}m"
    else:
        d = total_seconds // 86400
        return f"in {d}d"


# ── STANDALONE MODE ────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        if len(sys.argv) < 3:
            print("Usage: python scheduler.py --once <tier>")
            sys.exit(1)
        tier = sys.argv[2]
        tier_map = {
            "tier1": run_tier1,
            "tier2": run_tier2,
            "tier3": run_tier3,
            "tier4": run_tier4,
            "digest": run_weekly_digest,
            "snapshotter": run_weekly_snapshotter,
            "pricing": run_pricing_strategist,
            "pulse": run_market_pulse,
        }
        fn = tier_map.get(tier)
        if not fn:
            print(f"Unknown tier: {tier}. Valid: {list(tier_map.keys())}")
            sys.exit(1)
        print(f"Running {tier} once...")
        fn()
        sys.exit(0)

    print("Starting Corporate HQ Scheduler (standalone mode)...")
    print("Press Ctrl+C to stop.\n")

    scheduler = init_scheduler()
    if not scheduler:
        print("Failed to start scheduler.")
        sys.exit(1)

    try:
        import time
        while True:
            time.sleep(60)
            status = get_schedule_status(scheduler)
            next_jobs = status["jobs"][:3]
            if next_jobs:
                upcoming = ", ".join(
                    f"{j['name'].split('—')[0].strip()} ({j['next_run_human']})"
                    for j in next_jobs
                )
                log.info(f"Upcoming: {upcoming}")
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")
        scheduler.shutdown()
