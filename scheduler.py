"""CORPORATE HQ — 24/7 Scheduler

Fires Managed Agent sessions on the correct cadence.
Runs inside the Flask app via APScheduler (or standalone).

SCHEDULE:
  Tier 1 (Scout)      → 6am, 12pm, 6pm daily
  Tier 2 (Process)    → 30 min after each Tier 1 run
  Tier 3 (Analytics)  → 11pm nightly
  Tier 4 (Alerts)     → Every 4 hours
  Weekly Digest       → Sunday 8am

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
from managed_agent import launch_session, _load_agent_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEDULER] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("corporate_hq_scheduler")


# ── SCHEDULED JOB FUNCTIONS ────────────────────────────────────────────

def run_tier1():
    log.info("▶ TIER 1 — Scout cycle starting")
    from agents.runner import run_tier
    results = run_tier("tier1")
    completed = sum(1 for v in results.values() if v == "completed")
    total = len(results)
    log.info(f"  ✓ Tier 1 complete: {completed}/{total} scouts finished")
    _schedule_tier2_followup()
    return results


def run_tier2():
    log.info("▶ TIER 2 — Processing cycle starting")
    session_id = launch_session("tier2")
    if session_id:
        log.info(f"  ✓ Tier 2 session launched: {session_id}")
    else:
        log.warning("  ✗ Tier 2 session failed to launch")
    return session_id


def run_tier3():
    log.info("▶ TIER 3 — Analytics cycle starting")
    session_id = launch_session("tier3")
    if session_id:
        log.info(f"  ✓ Tier 3 session launched: {session_id}")
    else:
        log.warning("  ✗ Tier 3 session failed to launch")
    return session_id


def run_tier4():
    log.info("▶ TIER 4 — Alert cycle starting")
    session_id = launch_session("tier4")
    if session_id:
        log.info(f"  ✓ Tier 4 session launched: {session_id}")
    else:
        log.warning("  ✗ Tier 4 session failed to launch")
    return session_id


def run_weekly_digest():
    log.info("▶ WEEKLY DIGEST — Generating Sunday briefing")
    session_id = launch_session("digest")
    if session_id:
        log.info(f"  ✓ Digest session launched: {session_id}")
    else:
        log.warning("  ✗ Digest session failed to launch")
    return session_id


def _schedule_tier2_followup():
    import threading
    def _delayed_tier2():
        import time
        log.info("  ⏱ Waiting 30 min for Tier 2 followup...")
        time.sleep(30 * 60)
        run_tier2()
    t = threading.Thread(target=_delayed_tier2, daemon=True)
    t.start()


# ── SCHEDULER INIT ─────────────────────────────────────────────────────

def init_scheduler(app=None):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        log.error("APScheduler not installed. Run: pip install apscheduler")
        return None

    agent_id = _load_agent_id()
    if not agent_id:
        log.warning("No Managed Agent ID found. Create agent first:")
        log.warning("  python managed_agent.py create")
        log.warning("Scheduler starting anyway — sessions will fail until agent is created.")

    scheduler = BackgroundScheduler(timezone="America/New_York")

    # Tier 1: 6am, 12pm, 6pm daily
    scheduler.add_job(
        run_tier1, CronTrigger(hour=6, minute=0),
        id="tier1_morning", name="Tier 1 — Morning Scout",
        replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        run_tier1, CronTrigger(hour=12, minute=0),
        id="tier1_midday", name="Tier 1 — Midday Scout",
        replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        run_tier1, CronTrigger(hour=18, minute=0),
        id="tier1_evening", name="Tier 1 — Evening Scout",
        replace_existing=True, misfire_grace_time=300,
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

    # Weekly digest: Sunday 8am
    scheduler.add_job(
        run_weekly_digest, CronTrigger(day_of_week="sun", hour=8, minute=0),
        id="weekly_digest", name="Weekly Digest — Sunday Briefing",
        replace_existing=True, misfire_grace_time=600,
    )

    scheduler.start()

    log.info("━" * 60)
    log.info("  CORPORATE HQ SCHEDULER — ACTIVE")
    log.info(f"  Agent ID: {agent_id or 'NOT SET — run managed_agent.py create'}")
    log.info("━" * 60)
    log.info("  Schedule:")
    log.info("    Tier 1 (Scout)     → 6am, 12pm, 6pm daily ET")
    log.info("    Tier 2 (Process)   → 30 min after each Tier 1")
    log.info("    Tier 3 (Analytics) → 11pm nightly ET")
    log.info("    Tier 4 (Alerts)    → Every 4 hours ET")
    log.info("    Weekly Digest      → Sunday 8am ET")
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
