"""ingest.py — Cowork -> Corporate HQ ingestion endpoints.

Two write-only endpoints that let external Cowork scheduled tasks land
competitor intelligence into the DuckDB warehouse, reusing the existing
warehouse wrappers (no parallel/duplicate write path). Registered in app.py:

    from ingest import ingest_bp
    app.register_blueprint(ingest_bp)

AUTH: every request must send  Authorization: Bearer <INGEST_TOKEN>
where INGEST_TOKEN is set as a Railway env var. Rejected otherwise.

ROUTES:
  POST /ingest/moat-map   -> upsert competitor shop profiles via load_full_profile
                             + log one agent_runs row
  POST /ingest/tripwire   -> record competitor change events (competitor_moves via
                             add_move) + optional alerts (alerts_log) + log one
                             agent_runs row

HEARTBEAT DESIGN: a quiet run (no findings that day) POSTs empty arrays. That is a
valid request, not an error — it logs an agent_runs row with status "ok" and
records_processed=0 and returns HTTP 200. Only actual per-item errors/exceptions
produce a failure status (500 only when nothing at all was written).
"""

import os
import hmac
import threading
import functools
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

# Reuse the existing warehouse write paths — do NOT re-implement inserts for
# competitors/moves. These are the canonical writers.
from warehouse.intel import add_move, add_product, add_financial, add_social
from warehouse.competitors import get_competitor, add_competitor, update_competitor
from warehouse.db import get_connection                 # accessor confirmed against db.py

INGEST_TOKEN = os.environ.get("INGEST_TOKEN")  # set on Railway
# When true (default), a successful ingest wakes the Tier 2-4 processing chain
# so new data is normalized/scored immediately instead of waiting for the cron.
_AUTO_PROCESS = os.environ.get("INGEST_AUTO_PROCESS", "1") != "0"
ingest_bp = Blueprint("ingest", __name__)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def _require_token(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        expected = f"Bearer {INGEST_TOKEN}" if INGEST_TOKEN else None
        if not expected or not hmac.compare_digest(auth, expected):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


def _log_agent_run(agent_name, status, records_processed, notes=""):
    """Log one agent_runs row. Columns verified against db.py init_schema():
    run_id (seq_agent_run), agent_name, started_at (default), finished_at,
    status, records_processed, notes.
    """
    con = get_connection()
    try:
        run_id = con.execute("SELECT nextval('seq_agent_run')").fetchone()[0]
        con.execute(
            """INSERT INTO agent_runs
                   (run_id, agent_name, finished_at, status, records_processed, notes)
               VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)""",
            [run_id, agent_name, status, records_processed, notes],
        )
    finally:
        con.close()


def _add_alert(alert):
    """Write one alerts_log row. Columns verified against db.py init_schema():
    alert_id (seq_alert), alert_type (NOT NULL), severity, competitor_id,
    title (NOT NULL), detail, data_json, acknowledged (default),
    created_at (default). The draft's 'body'/'source' fields don't exist —
    body maps to detail, source is folded into alert_type.
    """
    con = get_connection()
    try:
        alert_id = con.execute("SELECT nextval('seq_alert')").fetchone()[0]
        con.execute(
            """INSERT INTO alerts_log
                   (alert_id, alert_type, severity, competitor_id, title, detail, data_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [alert_id,
             alert.get("alert_type", "cowork-tripwire"),
             alert.get("severity", "info"),
             alert.get("competitor_id"),
             alert.get("title") or "(untitled alert)",
             alert.get("body") or alert.get("detail"),
             alert.get("data_json")],
        )
    finally:
        con.close()


def _resolve_competitor_id(move):
    """Resolve a move to a real competitor_id (competitor_moves has an FK).

    Prefer an explicit competitor_id; else look the company_name up in the
    existing warehouse; else create a minimal record (discovery), matching how
    ShopWatcher onboards newly-spotted shops.
    """
    cid = move.get("competitor_id")
    if cid is not None:
        return cid
    name = move.get("company_name")
    if not name:
        return None
    existing = get_competitor(name)
    if existing:
        return existing["competitor_id"]
    return add_competitor(name, notes="Discovered via Cowork tripwire")


def _record_move(move):
    """Record one competitor move via the canonical add_move() writer."""
    cid = _resolve_competitor_id(move)
    if cid is None:
        raise ValueError("move requires 'competitor_id' or 'company_name'")
    return add_move(
        competitor_id=cid,
        move_date=move.get("move_date") or _today(),
        move_type=move.get("move_type"),
        description=move.get("description"),
        source_url=move.get("source_url"),
        impact_rating=move.get("impact_rating"),
    )


# Master-record columns we let a re-ingest fill (never overwrite existing values).
_MASTER_FIELDS = {
    "industry", "website", "hq_location", "zip_code", "neighborhood",
    "ownership_type", "primary_clientele", "founded_year", "employee_count",
    "annual_revenue", "business_model", "notes",
}


def _ingest_profile(profile):
    """Upsert one competitor and APPEND its observations. Returns competitor_id.

    Existing shop (matched by exact name): reuse its competitor_id, fill only
    empty master fields, and append the time-series rows. New shop: create it,
    then attach the nested rows. Baseline (e.g. Jun 12) history is preserved —
    products/financials/moves/social are append-only tables, so new dated rows
    stack on top rather than overwriting.
    """
    profile = dict(profile)  # copy — we pop nested keys off it
    products = profile.pop("products", []) or []
    financials = profile.pop("financials", []) or []
    moves = profile.pop("moves", []) or []
    social = profile.pop("social", []) or []
    name = profile.get("company_name")
    if not name:
        raise ValueError("profile requires 'company_name'")

    existing = get_competitor(name)
    # get_competitor is a fuzzy ILIKE match — only treat it as the SAME shop
    # when the names actually match, else we'd merge two different competitors.
    if existing and str(existing.get("company_name", "")).strip().lower() != name.strip().lower():
        existing = None

    master = {k: v for k, v in profile.items()
              if k in _MASTER_FIELDS and v is not None}
    if existing:
        cid = existing["competitor_id"]
        # Enrich-only: fill master fields that are currently empty; never
        # overwrite an existing baseline value.
        gaps = {k: v for k, v in master.items() if not existing.get(k)}
        if gaps:
            update_competitor(cid, **gaps)
    else:
        cid = add_competitor(name, **master)

    for p in products:
        add_product(cid, **p)
    for f in financials:
        add_financial(cid, **f)
    for m in moves:
        add_move(cid, **m)
    for s in social:
        add_social(cid, **s)
    return cid


# ── Downstream processing chain ────────────────────────────────────────
# New data landing via ingest must wake Tiers 2-4 (Normalizer → … → Scorecard
# → alerts) rather than waiting for the nightly cron. Runs are coalesced and
# async so the ingest response returns fast and concurrent POSTs don't stack.
_chain_lock = threading.Lock()
_chain_rerun = threading.Event()


def _run_processing_chain():
    from agents.runner import run_tier
    while True:
        _chain_rerun.clear()
        for tier in ("tier2", "tier3", "tier4"):
            try:
                run_tier(tier)
            except Exception:
                pass  # individual agents log their own failures to agent_runs
        if not _chain_rerun.is_set():
            break


def trigger_processing_chain():
    """Wake Tiers 2-4 to process freshly-ingested data. Returns True if it
    started a run, False if disabled or folded into an in-flight run."""
    if not _AUTO_PROCESS:
        return False
    if not _chain_lock.acquire(blocking=False):
        _chain_rerun.set()  # a chain is already running — ask it to loop again
        return False

    def _worker():
        try:
            _run_processing_chain()
        finally:
            _chain_lock.release()

    threading.Thread(target=_worker, daemon=True, name="ingest-chain").start()
    return True


@ingest_bp.route("/ingest/moat-map", methods=["POST"])
@_require_token
def ingest_moat_map():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "profiles" not in payload:
        return jsonify({"ok": False, "error": "missing 'profiles'"}), 400
    profiles = payload["profiles"]
    if not isinstance(profiles, list):
        return jsonify({"ok": False, "error": "'profiles' must be a list"}), 400

    written, ids, errors = 0, [], []
    for profile in profiles:
        try:
            ids.append(_ingest_profile(profile))
            written += 1
        except Exception as e:
            errors.append({"company_name": (profile or {}).get("company_name"),
                           "error": str(e)})

    # ok when there were no errors (INCLUDING the empty-array heartbeat);
    # partial when some wrote and some failed; failed only when nothing wrote.
    status = "ok" if not errors else ("partial" if written else "failed")
    note = "heartbeat" if not profiles else (f"{len(errors)} error(s)" if errors else "")
    try:
        _log_agent_run("moat-map", status, written, notes=note)
    except Exception as e:
        errors.append({"agent_runs_log": str(e)})

    # New data landed → wake the Tier 2-4 chain to process it now.
    triggered = trigger_processing_chain() if written else False

    http = 200 if status in ("ok", "partial") else 500
    return jsonify({"ok": status != "failed", "status": status,
                    "written": written, "competitor_ids": ids,
                    "processing_triggered": triggered,
                    "errors": errors}), http


@ingest_bp.route("/ingest/tripwire", methods=["POST"])
@_require_token
def ingest_tripwire():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "moves" not in payload:
        return jsonify({"ok": False, "error": "missing 'moves'"}), 400
    moves = payload["moves"]
    if not isinstance(moves, list):
        return jsonify({"ok": False, "error": "'moves' must be a list"}), 400

    written, errors = 0, []
    for move in moves:
        try:
            _record_move(move)
            written += 1
        except Exception as e:
            errors.append({"move": (move or {}).get("company_name"), "error": str(e)})

    alerts_written = 0
    for alert in (payload.get("alerts") or []):
        try:
            _add_alert(alert)
            alerts_written += 1
        except Exception as e:
            errors.append({"alert": (alert or {}).get("title"), "error": str(e)})

    # ok when there were no errors (INCLUDING the empty-array heartbeat);
    # partial when something wrote despite errors; failed only when nothing wrote.
    status = "ok" if not errors else ("partial" if (written or alerts_written) else "failed")
    note = "heartbeat" if (not moves and not payload.get("alerts")) \
        else f"{alerts_written} alert(s), {len(errors)} error(s)"
    try:
        _log_agent_run("tripwire", status, written, notes=note)
    except Exception as e:
        errors.append({"agent_runs_log": str(e)})

    # New data landed → wake the Tier 2-4 chain to process it now.
    triggered = trigger_processing_chain() if (written or alerts_written) else False

    http = 200 if status in ("ok", "partial") else 500
    return jsonify({"ok": status != "failed", "status": status,
                    "moves_written": written, "alerts_written": alerts_written,
                    "processing_triggered": triggered,
                    "errors": errors}), http
