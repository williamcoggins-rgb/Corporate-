"""CORPORATE HQ — The Dashboard

Futuristic command center for the barbershop empire.
Flask backend serving live DuckDB warehouse data.

Run:  python app.py
      Then open http://localhost:5000
"""

import json
import os
from flask import Flask, jsonify, render_template_string
from warehouse.db import get_connection, init_schema
from strategy import YOUR_SHOP

app = Flask(__name__)

# Auto-initialize DB + seed data if empty (needed for Railway/fresh deploys)
def _ensure_db():
    init_schema()
    con = get_connection()
    try:
        count = con.execute("SELECT COUNT(*) FROM competitors").fetchone()[0]
        if count == 0:
            con.close()
            from seed_charlotte import seed
            seed()
            try:
                from seed_platforms import seed_platforms
                seed_platforms()
            except Exception:
                pass  # Optional seed
    except Exception:
        con.close()
        raise
    else:
        con.close()

_ensure_db()


# ════════════════════════════════════════════════════════════════════════
#  DATA LAYER — pulls from the warehouse
# ════════════════════════════════════════════════════════════════════════

def _q(query, params=None):
    con = get_connection()
    try:
        cur = con.execute(query, params or [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        con.close()


def get_dashboard_data():
    """Pull all data the dashboard needs in one pass."""
    d = {}

    # Shop basics
    d["shop"] = {
        "name": YOUR_SHOP.get("name", "HQ"),
        "neighborhood": YOUR_SHOP.get("neighborhood", ""),
        "setup": YOUR_SHOP.get("setup", ""),
        "goal": YOUR_SHOP.get("goal", ""),
        "years_experience": YOUR_SHOP.get("years_experience", 0),
        "annual_gross": YOUR_SHOP.get("annual_gross", 0),
        "monthly_gross": YOUR_SHOP.get("monthly_gross", 0),
        "barbers": YOUR_SHOP.get("barbers", 1),
        "deposits": YOUR_SHOP.get("deposits", False),
        "booking_platform": YOUR_SHOP.get("booking_platform", ""),
        "has_proprietary_os": YOUR_SHOP.get("booking_os", {}).get("type") == "proprietary",
        "migrating_from": YOUR_SHOP.get("booking_os", {}).get("migrating_from"),
        "os_features": YOUR_SHOP.get("booking_os", {}).get("features", []),
        "wholesale": YOUR_SHOP.get("revenue_model", {}).get("wholesale_membership", False),
    }
    d["prices"] = YOUR_SHOP.get("prices", {})

    # Competitor counts
    d["competitor_count"] = _q(
        "SELECT COUNT(*) as n FROM competitors WHERE status = 'Active'"
    )[0]["n"]

    d["franchise_count"] = _q("""
        SELECT COUNT(DISTINCT competitor_id) as n FROM competitors
        WHERE company_name LIKE 'No Grease%' OR company_name LIKE 'Da Lucky Spot%'
    """)[0]["n"]

    d["independent_count"] = d["competitor_count"] - d["franchise_count"]

    # Pricing
    d["avg_fade"] = float(_q(
        "SELECT COALESCE(ROUND(AVG(price), 2), 0) as avg FROM price_history WHERE service_name = 'Fade'"
    )[0]["avg"])

    d["max_fade"] = float(_q(
        "SELECT COALESCE(ROUND(MAX(price), 2), 0) as mx FROM price_history WHERE service_name = 'Fade'"
    )[0]["mx"])

    # Neighborhoods
    d["neighborhoods"] = _q("""
        SELECT c.neighborhood, COUNT(DISTINCT c.competitor_id) as shops,
               ROUND(AVG(ph.price), 2) as avg_fade
        FROM competitors c
        LEFT JOIN price_history ph ON ph.competitor_id = c.competitor_id
            AND ph.service_name = 'Fade'
        WHERE c.status = 'Active'
        GROUP BY c.neighborhood
        ORDER BY shops ASC
    """)

    # Recent moves
    d["recent_moves"] = _q("""
        SELECT c.company_name, cm.move_type, cm.description,
               cm.move_date
        FROM competitor_moves cm
        JOIN competitors c ON c.competitor_id = cm.competitor_id
        ORDER BY cm.move_date DESC LIMIT 6
    """)

    # Social leaders
    d["social_leaders"] = _q("""
        SELECT c.company_name, cs.followers, cs.engagement_rate, cs.platform
        FROM competitor_social cs
        JOIN competitors c ON c.competitor_id = cs.competitor_id
        ORDER BY cs.followers DESC LIMIT 5
    """)

    # Barber talent pool
    d["barber_count"] = _q("SELECT COUNT(*) as n FROM barbers")[0]["n"]

    # Scores
    d["score_count"] = _q("SELECT COUNT(*) as n FROM competitor_scores")[0]["n"]

    # Review avg
    d["review_avg"] = float(_q(
        "SELECT COALESCE(ROUND(AVG(rating), 1), 0) as avg FROM review_snapshots"
    )[0]["avg"])

    # Top competitors by threat
    d["top_threats"] = _q("""
        SELECT c.company_name, c.neighborhood, c.ownership_type,
               cs.score as threat_score
        FROM competitor_scores cs
        JOIN competitors c ON c.competitor_id = cs.competitor_id
        WHERE cs.score_type = 'threat'
        ORDER BY cs.score DESC LIMIT 8
    """)

    # Agent runs
    d["agent_runs"] = _q("""
        SELECT agent_name, status, started_at, records_processed
        FROM agent_runs
        ORDER BY started_at DESC LIMIT 8
    """)

    # Alerts
    d["alerts"] = _q("""
        SELECT alert_type, severity, title, detail, created_at
        FROM alerts_log
        ORDER BY created_at DESC LIMIT 6
    """)

    # R&D projects
    try:
        d["rnd_projects"] = _q("""
            SELECT project_id, lab, title, status, priority, revenue_potential
            FROM rnd_projects
            ORDER BY priority DESC, project_id ASC
        """)
    except Exception:
        d["rnd_projects"] = []

    # Council vote conditions
    monthly = d["shop"]["monthly_gross"]
    d["council"] = {
        "strategist": {"ready": monthly >= 4000, "condition": "$4K+/mo gross with revenue layers"},
        "comptroller": {"ready": monthly >= 4000 and d["shop"]["deposits"], "condition": "$4K+/mo AND deposits active"},
        "intel": {"ready": d["competitor_count"] >= 15, "condition": "15+ competitors with live data"},
        "operator": {"ready": d["shop"]["has_proprietary_os"] and d["shop"]["migrating_from"] is None, "condition": "OS deployed AND Booksy migrated"},
        "brand": {"ready": d["shop"]["name"] != "Your Shop", "condition": "Shop named — brand identity set"},
    }

    return d


# ════════════════════════════════════════════════════════════════════════
#  API ROUTES
# ════════════════════════════════════════════════════════════════════════

@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(get_dashboard_data())


@app.route("/api/competitors")
def api_competitors():
    rows = _q("""
        SELECT c.*, cs.score as threat_score
        FROM competitors c
        LEFT JOIN competitor_scores cs ON c.competitor_id = cs.competitor_id
            AND cs.score_type = 'threat'
        WHERE c.status = 'Active'
        ORDER BY cs.score DESC NULLS LAST
    """)
    return jsonify(rows)


@app.route("/api/pricing")
def api_pricing():
    rows = _q("""
        SELECT ph.service_name, c.company_name, ph.price, ph.recorded_at
        FROM price_history ph
        JOIN competitors c ON c.competitor_id = ph.competitor_id
        ORDER BY ph.service_name, ph.price DESC
    """)
    return jsonify(rows)


# ════════════════════════════════════════════════════════════════════════
#  MAIN ROUTE — serves the dashboard
# ════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    data = get_dashboard_data()
    return render_template_string(DASHBOARD_HTML, data=data, data_json=json.dumps(data, default=str))


# ════════════════════════════════════════════════════════════════════════
#  THE DASHBOARD — HTML + CSS + JS (all inline, zero dependencies)
# ════════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CORPORATE HQ</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
/* ═══════════════════════════════════════════════════════════════
   CSS CUSTOM PROPERTIES — THE BARBER POLE PALETTE
   ═══════════════════════════════════════════════════════════════ */
@property --angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}
@property --holo-angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}

:root {
  --white: #FAFAFA;
  --red: #E63946;
  --red-soft: #FF6B6B;
  --teal: #2EC4B6;
  --teal-soft: #5EEADB;

  --bg-base: #08080C;
  --bg-surface: #0F0F14;
  --bg-elevated: #16161D;
  --bg-hover: #1E1E28;
  --bg-card: rgba(15, 15, 20, 0.7);

  --text-primary: #FAFAFA;
  --text-secondary: #9CA3AF;
  --text-muted: #5C6370;

  --border-subtle: rgba(250, 250, 250, 0.06);
  --border-glow: rgba(46, 196, 182, 0.15);

  --shadow-glow-red: 0 0 30px rgba(230, 57, 70, 0.12);
  --shadow-glow-teal: 0 0 30px rgba(46, 196, 182, 0.12);

  --radius: 24px;
  --radius-sm: 14px;
  --radius-xs: 8px;

  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', monospace;

  /* Fluid type scale */
  --text-xs: clamp(0.6875rem, 0.5vw + 0.5rem, 0.75rem);
  --text-sm: clamp(0.8125rem, 0.6vw + 0.6rem, 0.875rem);
  --text-base: clamp(0.875rem, 0.8vw + 0.6rem, 1rem);
  --text-lg: clamp(1.125rem, 1vw + 0.75rem, 1.25rem);
  --text-xl: clamp(1.5rem, 2vw + 0.75rem, 2rem);
  --text-2xl: clamp(2rem, 3vw + 1rem, 3rem);
  --text-hero: clamp(2.5rem, 4vw + 1rem, 3.5rem);
}

/* ═══════════════════════════════════════════════════════════════
   RESET + BASE
   ═══════════════════════════════════════════════════════════════ */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  overflow-x: hidden;
  min-height: 100vh;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

/* ═══════════════════════════════════════════════════════════════
   ANIMATED MESH BACKGROUND
   ═══════════════════════════════════════════════════════════════ */
.mesh-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
.mesh-bg .orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.15;
}
.mesh-bg .orb-red {
  width: 50vmax; height: 50vmax;
  background: radial-gradient(circle, var(--red), transparent 70%);
  top: -15%; left: -10%;
  animation: drift1 20s ease-in-out infinite alternate;
}
.mesh-bg .orb-teal {
  width: 45vmax; height: 45vmax;
  background: radial-gradient(circle, var(--teal), transparent 70%);
  bottom: -20%; right: -10%;
  animation: drift2 24s ease-in-out infinite alternate;
}
.mesh-bg .orb-white {
  width: 30vmax; height: 30vmax;
  background: radial-gradient(circle, rgba(250,250,250,0.4), transparent 70%);
  top: 40%; left: 50%;
  opacity: 0.04;
  animation: drift3 18s ease-in-out infinite alternate;
}
@keyframes drift1 { to { transform: translate(25vw, 18vh) scale(1.15); } }
@keyframes drift2 { to { transform: translate(-20vw, -12vh) scale(0.9); } }
@keyframes drift3 { to { transform: translate(-15vw, 10vh) scale(1.3); } }

/* ═══════════════════════════════════════════════════════════════
   GRID NOISE OVERLAY
   ═══════════════════════════════════════════════════════════════ */
.noise-overlay {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* ═══════════════════════════════════════════════════════════════
   LAYOUT — SHELL
   ═══════════════════════════════════════════════════════════════ */
.shell {
  position: relative;
  z-index: 2;
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px 28px 60px;
}

/* ═══════════════════════════════════════════════════════════════
   TOP BAR — ANIMATED BARBER POLE BORDER
   ═══════════════════════════════════════════════════════════════ */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 28px;
  border-radius: var(--radius);
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  margin-bottom: 28px;
  overflow: hidden;
}
.topbar::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: var(--radius);
  padding: 1px;
  background: conic-gradient(from var(--angle), var(--red), var(--teal), var(--white), var(--red));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: spin-border 4s linear infinite;
  opacity: 0.6;
}
@keyframes spin-border { to { --angle: 360deg; } }

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
.topbar-logo {
  width: 42px; height: 42px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--red), var(--teal));
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 18px;
  color: var(--white);
  box-shadow: 0 0 20px rgba(230,57,70,0.2), 0 0 20px rgba(46,196,182,0.2);
}
.topbar-title {
  font-size: var(--text-lg);
  font-weight: 800;
  letter-spacing: 3px;
  text-transform: uppercase;
  background: linear-gradient(135deg, var(--white) 0%, rgba(250,250,250,0.6) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.topbar-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  letter-spacing: 1px;
}
.topbar-status {
  display: flex;
  align-items: center;
  gap: 18px;
}
.status-dot {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
}
.status-dot .dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
}
.dot-green { background: #34D399; box-shadow: 0 0 8px rgba(52,211,153,0.4); }
.dot-red { background: var(--red); box-shadow: 0 0 8px rgba(230,57,70,0.4); }
.dot-teal { background: var(--teal); box-shadow: 0 0 8px rgba(46,196,182,0.4); }
.dot-yellow { background: #FBBF24; box-shadow: 0 0 8px rgba(251,191,36,0.4); }
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

/* ═══════════════════════════════════════════════════════════════
   MIGRATION BANNER — persistent until Booksy is done
   ═══════════════════════════════════════════════════════════════ */
.migration-banner {
  background: linear-gradient(90deg, rgba(230,57,70,0.1), rgba(46,196,182,0.08));
  border: 1px solid rgba(230,57,70,0.2);
  border-radius: var(--radius-sm);
  padding: 12px 20px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.migration-banner .label {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--red-soft);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-weight: 600;
}
.migration-banner .bar-track {
  flex: 1;
  height: 4px;
  background: rgba(250,250,250,0.06);
  border-radius: 4px;
  overflow: hidden;
  max-width: 400px;
}
.migration-banner .bar-fill {
  height: 100%;
  width: 35%;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--red), var(--teal));
  animation: shimmer 2s ease-in-out infinite;
}
@keyframes shimmer {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.migration-banner .pct {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--red-soft);
}

/* ═══════════════════════════════════════════════════════════════
   BENTO GRID
   ═══════════════════════════════════════════════════════════════ */
.bento {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: minmax(80px, auto);
}

/* Card sizes */
.b-hero    { grid-column: span 8; grid-row: span 4; }
.b-side    { grid-column: span 4; grid-row: span 4; }
.b-wide    { grid-column: span 6; grid-row: span 4; }
.b-third   { grid-column: span 4; grid-row: span 4; }
.b-full    { grid-column: span 12; grid-row: span 3; }
.b-half    { grid-column: span 6; grid-row: span 3; }

@media (max-width: 1024px) {
  .bento { grid-template-columns: repeat(6, 1fr); }
  .b-hero, .b-full { grid-column: span 6; }
  .b-side, .b-third { grid-column: span 6; }
  .b-wide, .b-half { grid-column: span 6; }
}
@media (max-width: 640px) {
  .bento { grid-template-columns: 1fr; }
  .b-hero, .b-side, .b-wide, .b-third, .b-full, .b-half { grid-column: span 1; }
  .shell { padding: 12px 14px 40px; }
}

/* ═══════════════════════════════════════════════════════════════
   GLASS CARD — base component
   ═══════════════════════════════════════════════════════════════ */
.card {
  background: rgba(15, 15, 20, 0.65);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(250,250,250,0.07);
  border-radius: var(--radius);
  padding: 24px 26px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              box-shadow 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              background 0.4s;
  box-shadow: 0 4px 24px rgba(0,0,0,0.2),
              inset 0 1px 0 rgba(250,250,250,0.04);
  container-type: inline-size;
}
.card:hover {
  border-color: rgba(250,250,250,0.12);
  background: rgba(15, 15, 20, 0.75);
  box-shadow: 0 12px 48px rgba(0,0,0,0.35),
              inset 0 1px 0 rgba(250,250,250,0.06);
}
/* Stripe flashlight hover — radial gradient follows cursor */
.card .spotlight {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: radial-gradient(
    500px circle at var(--mx) var(--my),
    rgba(46, 196, 182, 0.08),
    transparent 40%
  );
  opacity: 0;
  transition: opacity 0.4s;
  pointer-events: none;
  z-index: 0;
}
.card:hover .spotlight { opacity: 1; }
.card > *:not(.spotlight) { position: relative; z-index: 1; }
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.card-label {
  font-size: 10px;
  font-family: var(--font-mono);
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
}
.card-badge {
  font-size: 10px;
  font-family: var(--font-mono);
  padding: 3px 8px;
  border-radius: 4px;
  letter-spacing: 1px;
  font-weight: 600;
}
.badge-red { background: rgba(230,57,70,0.15); color: var(--red-soft); border: 1px solid rgba(230,57,70,0.2); }
.badge-teal { background: rgba(46,196,182,0.15); color: var(--teal-soft); border: 1px solid rgba(46,196,182,0.2); }
.badge-yellow { background: rgba(251,191,36,0.15); color: #FBBF24; border: 1px solid rgba(251,191,36,0.2); }
.badge-green { background: rgba(52,211,153,0.12); color: #34D399; border: 1px solid rgba(52,211,153,0.2); }

/* ═══════════════════════════════════════════════════════════════
   GLOW CARD VARIANT — animated border
   ═══════════════════════════════════════════════════════════════ */
.card-glow::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: var(--radius);
  padding: 1px;
  background: conic-gradient(from var(--angle), var(--red), transparent 25%, var(--teal), transparent 65%, var(--red));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: spin-border 5s linear infinite;
  opacity: 0;
  transition: opacity 0.5s;
  z-index: 2;
}
/* Blur halo behind the rotating border */
.card-glow::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: var(--radius);
  background: conic-gradient(from var(--angle), var(--red), transparent 25%, var(--teal), transparent 65%, var(--red));
  filter: blur(18px);
  opacity: 0;
  transition: opacity 0.5s;
  z-index: -1;
  animation: spin-border 5s linear infinite;
}
.card-glow:hover::before { opacity: 0.6; }
.card-glow:hover::after { opacity: 0.2; }

/* ═══════════════════════════════════════════════════════════════
   STAT NUMBERS — big metric display
   ═══════════════════════════════════════════════════════════════ */
.stat-big {
  font-size: var(--text-hero);
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.04em;
  margin: 6px 0;
  font-variant-numeric: tabular-nums;
}
.stat-big.red {
  background: linear-gradient(135deg, var(--red), var(--red-soft));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 20px rgba(230,57,70,0.25));
}
.stat-big.teal {
  background: linear-gradient(135deg, var(--teal), var(--teal-soft));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 20px rgba(46,196,182,0.25));
}
.stat-big.white {
  background: linear-gradient(135deg, #fff 0%, rgba(255,255,255,0.7) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

.stat-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.stat-unit {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-secondary);
}
.stat-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  font-family: var(--font-mono);
}
.stat-delta {
  font-size: 11px;
  font-family: var(--font-mono);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}
.delta-up { background: rgba(52,211,153,0.12); color: #34D399; }
.delta-down { background: rgba(230,57,70,0.12); color: var(--red-soft); }

/* ═══════════════════════════════════════════════════════════════
   METRIC GRID — small stat cards inside hero
   ═══════════════════════════════════════════════════════════════ */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 12px;
}
.metric-cell {
  background: rgba(250,250,250,0.03);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 16px 18px;
  text-align: center;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  box-shadow: inset 0 1px 0 rgba(250,250,250,0.03);
}
.metric-cell:hover {
  background: rgba(250,250,250,0.06);
  border-color: rgba(46,196,182,0.2);
  box-shadow: inset 0 1px 0 rgba(250,250,250,0.05), 0 0 16px rgba(46,196,182,0.06);
  transform: translateY(-1px);
}
.metric-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--white);
  font-variant-numeric: tabular-nums;
}
.metric-label {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-top: 4px;
}

@media (max-width: 640px) {
  .metric-grid { grid-template-columns: repeat(2, 1fr); }
}

/* ═══════════════════════════════════════════════════════════════
   COUNCIL VOTE PANEL
   ═══════════════════════════════════════════════════════════════ */
.council-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.council-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-xs);
  background: rgba(250,250,250,0.02);
  border: 1px solid var(--border-subtle);
  transition: all 0.2s;
}
.council-row:hover { background: rgba(250,250,250,0.04); }
.council-vote {
  width: 28px; height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  flex-shrink: 0;
}
.vote-yes { background: rgba(52,211,153,0.15); color: #34D399; border: 1px solid rgba(52,211,153,0.25); }
.vote-no { background: rgba(230,57,70,0.12); color: var(--red-soft); border: 1px solid rgba(230,57,70,0.2); }
.council-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 100px;
}
.council-cond {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  flex: 1;
}

/* ═══════════════════════════════════════════════════════════════
   COMPETITOR TABLE
   ═══════════════════════════════════════════════════════════════ */
.intel-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 4px;
}
.intel-table th {
  font-size: 9px;
  font-family: var(--font-mono);
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-muted);
  text-align: left;
  padding: 6px 12px;
  font-weight: 600;
}
.intel-table td {
  padding: 10px 12px;
  font-size: 12px;
  background: rgba(250,250,250,0.02);
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}
.intel-table td:first-child { border-left: 1px solid var(--border-subtle); border-radius: 8px 0 0 8px; }
.intel-table td:last-child { border-right: 1px solid var(--border-subtle); border-radius: 0 8px 8px 0; }
.intel-table tr:hover td { background: rgba(250,250,250,0.04); }

.threat-bar {
  height: 4px;
  border-radius: 2px;
  background: rgba(250,250,250,0.06);
  min-width: 60px;
}
.threat-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--teal), var(--red));
}

/* ═══════════════════════════════════════════════════════════════
   PRICE SERVICE BARS
   ═══════════════════════════════════════════════════════════════ */
.price-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.price-row:last-child { border-bottom: none; }
.price-name {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 120px;
  font-weight: 500;
}
.price-bar-wrap {
  flex: 1;
  height: 6px;
  background: rgba(250,250,250,0.04);
  border-radius: 3px;
  overflow: hidden;
}
.price-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1);
}
.price-val {
  font-size: 13px;
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--white);
  min-width: 40px;
  text-align: right;
}

/* ═══════════════════════════════════════════════════════════════
   R&D PIPELINE PILLS
   ═══════════════════════════════════════════════════════════════ */
.pipeline-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-xs);
  background: rgba(250,250,250,0.02);
  border: 1px solid var(--border-subtle);
  margin-bottom: 6px;
  transition: all 0.2s;
}
.pipeline-row:hover { background: rgba(250,250,250,0.04); }
.pipeline-id {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  min-width: 24px;
}
.pipeline-title {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
}
.pipeline-lab {
  font-size: 9px;
  font-family: var(--font-mono);
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(250,250,250,0.05);
  color: var(--text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}
.pipeline-status {
  font-size: 9px;
  font-family: var(--font-mono);
  padding: 2px 8px;
  border-radius: 3px;
  letter-spacing: 1px;
  text-transform: uppercase;
  font-weight: 600;
}

/* ═══════════════════════════════════════════════════════════════
   ALERT FEED
   ═══════════════════════════════════════════════════════════════ */
.alert-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.alert-row:last-child { border-bottom: none; }
.alert-icon {
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-top: 4px;
  flex-shrink: 0;
}
.alert-title { font-size: 12px; font-weight: 500; color: var(--text-primary); }
.alert-detail { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* ═══════════════════════════════════════════════════════════════
   MOVE FEED — competitive moves
   ═══════════════════════════════════════════════════════════════ */
.move-row {
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.move-row:last-child { border-bottom: none; }
.move-who {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}
.move-type {
  font-size: 9px;
  font-family: var(--font-mono);
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(46,196,182,0.1);
  color: var(--teal-soft);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-left: 6px;
}
.move-desc {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 3px;
  line-height: 1.4;
}

/* ═══════════════════════════════════════════════════════════════
   AGENT STATUS GRID
   ═══════════════════════════════════════════════════════════════ */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}
.agent-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--radius-xs);
  background: rgba(250,250,250,0.02);
  border: 1px solid var(--border-subtle);
  font-size: 11px;
  transition: all 0.2s;
}
.agent-cell:hover { background: rgba(250,250,250,0.04); }
.agent-name {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-secondary);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.agent-status {
  font-size: 9px;
  font-family: var(--font-mono);
  padding: 1px 5px;
  border-radius: 3px;
  letter-spacing: 0.5px;
  font-weight: 600;
}

/* ═══════════════════════════════════════════════════════════════
   HOLOGRAPHIC TITLE
   ═══════════════════════════════════════════════════════════════ */
.holo-text {
  background: linear-gradient(
    var(--holo-angle),
    var(--red) 0%, var(--white) 25%, var(--teal) 50%, var(--white) 75%, var(--red) 100%
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: holo 5s linear infinite;
  font-weight: 900;
}
@keyframes holo { from { --holo-angle: 0deg; } to { --holo-angle: 360deg; } }

/* ═══════════════════════════════════════════════════════════════
   SECTION DIVIDERS
   ═══════════════════════════════════════════════════════════════ */
.section-label {
  font-size: 10px;
  font-family: var(--font-mono);
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 28px 0 12px;
  grid-column: span 12;
}

/* ═══════════════════════════════════════════════════════════════
   OS FEATURES LIST
   ═══════════════════════════════════════════════════════════════ */
.os-feat {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 12px;
  color: var(--text-secondary);
}
.os-feat .check {
  width: 16px; height: 16px;
  border-radius: 4px;
  background: rgba(46,196,182,0.12);
  border: 1px solid rgba(46,196,182,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--teal);
  font-size: 10px;
  flex-shrink: 0;
}

/* ═══════════════════════════════════════════════════════════════
   SCROLLBAR
   ═══════════════════════════════════════════════════════════════ */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(250,250,250,0.08); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(250,250,250,0.14); }

/* ═══════════════════════════════════════════════════════════════
   EMPTY STATES
   ═══════════════════════════════════════════════════════════════ */
.empty {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--font-mono);
}
</style>
</head>
<body>

<!-- ANIMATED MESH BACKGROUND -->
<div class="mesh-bg">
  <div class="orb orb-red"></div>
  <div class="orb orb-teal"></div>
  <div class="orb orb-white"></div>
</div>
<div class="noise-overlay"></div>

<!-- DASHBOARD SHELL -->
<div class="shell">

  <!-- ═══ TOP BAR ═══ -->
  <div class="topbar">
    <div class="topbar-brand">
      <div class="topbar-logo">HQ</div>
      <div>
        <div class="topbar-title">Corporate HQ</div>
        <div class="topbar-subtitle">Strategic Intelligence Command</div>
      </div>
    </div>
    <div class="topbar-status">
      <div class="status-dot">
        <span class="dot dot-green"></span>
        OS LIVE
      </div>
      <div class="status-dot">
        <span class="dot {% if data.shop.migrating_from %}dot-yellow{% else %}dot-green{% endif %}"></span>
        {% if data.shop.migrating_from %}MIGRATING{% else %}BOOKSY CLEAR{% endif %}
      </div>
      <div class="status-dot">
        <span class="dot dot-teal"></span>
        {{ data.competitor_count }} TARGETS
      </div>
      <div class="status-dot">
        <span class="dot {% if data.council.strategist.ready %}dot-green{% else %}dot-red{% endif %}"></span>
        COUNCIL {{ [data.council.strategist.ready, data.council.comptroller.ready, data.council.intel.ready, data.council.operator.ready, data.council.brand.ready]|select|list|length }}/5
      </div>
    </div>
  </div>

  <!-- ═══ BOOKSY MIGRATION BANNER ═══ -->
  {% if data.shop.migrating_from %}
  <div class="migration-banner">
    <div class="label">Booksy Migration</div>
    <div class="bar-track"><div class="bar-fill"></div></div>
    <div class="pct">In Progress</div>
  </div>
  {% endif %}

  <!-- ═══ BENTO GRID ═══ -->
  <div class="bento">

    <!-- ══════════ ROW 1: HERO + COUNCIL ══════════ -->

    <!-- HERO CARD — Revenue Command -->
    <div class="card card-glow b-hero">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Revenue Command</span>
        <span class="card-badge badge-teal">LIVE</span>
      </div>
      <div class="stat-row">
        <div class="stat-big white">${{ "{:,.0f}".format(data.shop.monthly_gross) }}</div>
        <div class="stat-unit">/month</div>
        <span class="stat-delta delta-down">TARGET $4,500</span>
      </div>
      <div class="stat-sub">${{ "{:,}".format(data.shop.annual_gross) }}/yr gross &middot; {{ data.shop.setup }} &middot; {{ data.shop.neighborhood }}</div>

      <div class="metric-grid">
        <div class="metric-cell">
          <div class="metric-value" style="color: var(--teal);">{{ data.competitor_count }}</div>
          <div class="metric-label">Competitors</div>
        </div>
        <div class="metric-cell">
          <div class="metric-value" style="color: var(--red);">{{ data.franchise_count }}</div>
          <div class="metric-label">Franchises</div>
        </div>
        <div class="metric-cell">
          <div class="metric-value">{{ data.barber_count }}</div>
          <div class="metric-label">Barber Intel</div>
        </div>
        <div class="metric-cell">
          <div class="metric-value">{{ data.score_count }}</div>
          <div class="metric-label">Threat Scores</div>
        </div>
      </div>
    </div>

    <!-- COUNCIL CARD -->
    <div class="card card-glow b-side">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">The Council</span>
        {% set yes_votes = data.council.values()|selectattr('ready')|list|length %}
        <span class="card-badge {% if yes_votes >= 3 %}badge-green{% elif yes_votes >= 1 %}badge-yellow{% else %}badge-red{% endif %}">{{ yes_votes }}/5 READY</span>
      </div>
      <div class="council-grid">
        {% for name, info in data.council.items() %}
        <div class="council-row">
          <div class="council-vote {% if info.ready %}vote-yes{% else %}vote-no{% endif %}">
            {% if info.ready %}Y{% else %}N{% endif %}
          </div>
          <div class="council-name">{{ name|title }}</div>
          <div class="council-cond">{{ info.condition }}</div>
        </div>
        {% endfor %}
      </div>
    </div>

    <!-- ══════════ SECTION: INTELLIGENCE ══════════ -->
    <div class="section-label">Intelligence Center</div>

    <!-- PRICING CARD -->
    <div class="card card-glow b-wide">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Service Menu vs Market</span>
        <span class="card-badge badge-teal">{{ data.prices|length }} SERVICES</span>
      </div>
      {% for name, price in data.prices.items() %}
      <div class="price-row">
        <div class="price-name">{{ name }}</div>
        <div class="price-bar-wrap">
          <div class="price-bar-fill" style="width: {{ (price / 80 * 100)|int }}%; background: linear-gradient(90deg, var(--teal), {% if price >= 55 %}var(--red){% elif price >= 35 %}var(--teal-soft){% else %}var(--teal){% endif %});"></div>
        </div>
        <div class="price-val">${{ price }}</div>
      </div>
      {% endfor %}
      {% if data.avg_fade > 0 %}
      <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border-subtle);">
        <div class="stat-sub">MARKET AVG FADE: ${{ "%.0f"|format(data.avg_fade) }} &middot; MARKET HIGH: ${{ "%.0f"|format(data.max_fade) }} &middot; YOUR FADE: ${{ data.prices.get('Fade', 0) }}</div>
      </div>
      {% endif %}
    </div>

    <!-- COMPETITIVE MOVES -->
    <div class="card card-glow b-wide">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Competitor Moves</span>
        <span class="card-badge badge-red">LIVE FEED</span>
      </div>
      {% if data.recent_moves %}
        {% for move in data.recent_moves %}
        <div class="move-row">
          <div>
            <span class="move-who">{{ move.company_name }}</span>
            <span class="move-type">{{ move.move_type }}</span>
          </div>
          <div class="move-desc">{{ move.description }}</div>
        </div>
        {% endfor %}
      {% else %}
        <div class="empty">No moves logged. Deploy agents to start tracking.</div>
      {% endif %}
    </div>

    <!-- ══════════ SECTION: OPERATIONS ══════════ -->
    <div class="section-label">Operations &amp; Systems</div>

    <!-- OS STATUS -->
    <div class="card card-glow b-third">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Proprietary OS</span>
        <span class="card-badge {% if data.shop.has_proprietary_os %}badge-green{% else %}badge-red{% endif %}">
          {% if data.shop.has_proprietary_os %}DEPLOYED{% else %}PENDING{% endif %}
        </span>
      </div>
      {% for feat in data.shop.os_features %}
      <div class="os-feat">
        <div class="check">&#10003;</div>
        <span>{{ feat }}</span>
      </div>
      {% endfor %}
      {% if data.shop.migrating_from %}
      <div style="margin-top: 10px; padding: 8px 10px; border-radius: 6px; background: rgba(230,57,70,0.08); border: 1px solid rgba(230,57,70,0.15);">
        <div style="font-size: 10px; font-family: var(--font-mono); color: var(--red-soft); letter-spacing: 1px;">MIGRATING FROM {{ data.shop.migrating_from|upper }}</div>
      </div>
      {% endif %}
    </div>

    <!-- AGENT STATUS -->
    <div class="card card-glow b-third">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Agent Fleet</span>
        <span class="card-badge badge-teal">13 AGENTS</span>
      </div>
      <div class="agent-grid">
        {% set agents = ['PricingScout', 'ReviewHarvester', 'SocialListener', 'ShopWatcher', 'PlatformScout', 'Normalizer', 'BarberEnricher', 'DeltaSpotter', 'PlatformAnalyzer', 'Scorecard', 'PriceWarAlert', 'ReputationRadar', 'WeeklyDigest'] %}
        {% for agent in agents[:10] %}
        <div class="agent-cell">
          <span class="dot {% if loop.index <= 1 %}dot-green{% else %}dot-yellow{% endif %}" style="width:6px;height:6px;border-radius:50%;flex-shrink:0;"></span>
          <span class="agent-name">{{ agent }}</span>
          <span class="agent-status" style="{% if loop.index <= 1 %}color: #34D399; background: rgba(52,211,153,0.1);{% else %}color: var(--text-muted); background: rgba(250,250,250,0.04);{% endif %}">
            {% if loop.index <= 1 %}LIVE{% else %}BUILT{% endif %}
          </span>
        </div>
        {% endfor %}
      </div>
    </div>

    <!-- ALERTS -->
    <div class="card card-glow b-third">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Alert Feed</span>
        <span class="card-badge badge-yellow">{{ data.alerts|length }} ALERTS</span>
      </div>
      {% if data.alerts %}
        {% for alert in data.alerts %}
        <div class="alert-row">
          <div class="alert-icon" style="background: {% if alert.severity == 'critical' %}var(--red){% elif alert.severity == 'warning' %}#FBBF24{% else %}var(--teal){% endif %};
               box-shadow: 0 0 6px {% if alert.severity == 'critical' %}rgba(230,57,70,0.4){% elif alert.severity == 'warning' %}rgba(251,191,36,0.4){% else %}rgba(46,196,182,0.4){% endif %};"></div>
          <div>
            <div class="alert-title">{{ alert.title }}</div>
            {% if alert.detail %}
            <div class="alert-detail">{{ alert.detail[:80] }}</div>
            {% endif %}
          </div>
        </div>
        {% endfor %}
      {% else %}
        <div class="empty">No alerts. All clear.</div>
      {% endif %}
    </div>

    <!-- ══════════ SECTION: R&D ══════════ -->
    <div class="section-label">R&amp;D Pipeline</div>

    <!-- R&D PROJECTS -->
    <div class="card card-glow b-hero">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Project Pipeline</span>
        <span class="card-badge badge-teal">{{ data.rnd_projects|length }} PROJECTS</span>
      </div>
      {% if data.rnd_projects %}
        {% for p in data.rnd_projects[:12] %}
        <div class="pipeline-row">
          <div class="pipeline-id">#{{ p.project_id }}</div>
          <div class="pipeline-title">{{ p.title }}</div>
          <div class="pipeline-lab">{{ p.lab }}</div>
          <div class="pipeline-status" style="
            {% if p.status == 'in_progress' %}background: rgba(46,196,182,0.12); color: var(--teal-soft);
            {% elif p.status == 'research' %}background: rgba(251,191,36,0.1); color: #FBBF24;
            {% elif p.status == 'killed' %}background: rgba(230,57,70,0.1); color: var(--red-soft);
            {% elif p.status == 'complete' %}background: rgba(52,211,153,0.1); color: #34D399;
            {% else %}background: rgba(250,250,250,0.04); color: var(--text-muted);
            {% endif %}
          ">{{ p.status|upper }}</div>
          <div class="pipeline-status" style="
            {% if p.priority == 'critical' %}background: rgba(230,57,70,0.12); color: var(--red-soft);
            {% elif p.priority == 'high' %}background: rgba(251,191,36,0.1); color: #FBBF24;
            {% else %}background: rgba(250,250,250,0.04); color: var(--text-muted);
            {% endif %}
          ">{{ p.priority|upper }}</div>
        </div>
        {% endfor %}
      {% else %}
        <div class="empty">No R&D projects loaded. Run: python rnd.py --seed</div>
      {% endif %}
    </div>

    <!-- TERRITORY MAP -->
    <div class="card card-glow b-side">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Territory Intel</span>
        <span class="card-badge badge-teal">{{ data.neighborhoods|length }} ZONES</span>
      </div>
      <table class="intel-table">
        <thead>
          <tr>
            <th>Neighborhood</th>
            <th>Shops</th>
            <th>Avg Fade</th>
          </tr>
        </thead>
        <tbody>
          {% for n in data.neighborhoods[:10] %}
          <tr>
            <td style="font-weight: 500;">{{ n.neighborhood or 'Unknown' }}</td>
            <td>
              <span style="font-family: var(--font-mono); {% if n.shops <= 1 %}color: var(--teal);{% elif n.shops >= 4 %}color: var(--red-soft);{% endif %}">
                {{ n.shops }}
              </span>
            </td>
            <td>
              {% if n.avg_fade %}
              <span style="font-family: var(--font-mono);">${{ "%.0f"|format(n.avg_fade) }}</span>
              {% else %}
              <span style="color: var(--text-muted);">--</span>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <!-- ══════════ SECTION: SOCIAL ══════════ -->
    <div class="section-label">Social &amp; Brand Intelligence</div>

    <!-- SOCIAL LEADERS -->
    <div class="card card-glow b-half">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Social Landscape</span>
        <span class="card-badge badge-red">TOP 5</span>
      </div>
      {% if data.social_leaders %}
      <table class="intel-table">
        <thead>
          <tr>
            <th>Shop</th>
            <th>Platform</th>
            <th>Followers</th>
            <th>Engagement</th>
          </tr>
        </thead>
        <tbody>
          {% for s in data.social_leaders %}
          <tr>
            <td style="font-weight: 500;">{{ s.company_name }}</td>
            <td><span style="font-family: var(--font-mono); font-size: 10px; color: var(--text-muted);">{{ s.platform or 'N/A' }}</span></td>
            <td style="font-family: var(--font-mono);">{{ "{:,}".format(s.followers) }}</td>
            <td style="font-family: var(--font-mono);">{% if s.engagement_rate %}{{ "%.1f"|format(s.engagement_rate) }}%{% else %}--{% endif %}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
        <div class="empty">No social data. Deploy SocialListener agent.</div>
      {% endif %}
    </div>

    <!-- THREAT BOARD -->
    <div class="card card-glow b-half">
      <div class="spotlight"></div>
      <div class="card-header">
        <span class="card-label">Threat Board</span>
        <span class="card-badge badge-red">{{ data.top_threats|length }} TRACKED</span>
      </div>
      {% if data.top_threats %}
      <table class="intel-table">
        <thead>
          <tr>
            <th>Competitor</th>
            <th>Area</th>
            <th>Type</th>
            <th>Threat</th>
          </tr>
        </thead>
        <tbody>
          {% for t in data.top_threats %}
          <tr>
            <td style="font-weight: 500;">{{ t.company_name }}</td>
            <td style="font-size: 11px; color: var(--text-secondary);">{{ t.neighborhood or '--' }}</td>
            <td><span style="font-family: var(--font-mono); font-size: 10px;">{{ t.ownership_type or '--' }}</span></td>
            <td>
              <div class="threat-bar">
                <div class="threat-fill" style="width: {{ ((t.threat_score or 0) / 10 * 100)|int }}%;"></div>
              </div>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
        <div class="empty">No threat scores computed. Run Scorecard agent.</div>
      {% endif %}
    </div>

  </div><!-- /bento -->

  <!-- FOOTER -->
  <div style="text-align: center; padding: 40px 0 0; color: var(--text-muted); font-family: var(--font-mono); font-size: 10px; letter-spacing: 2px;">
    CORPORATE HQ &middot; STRATEGIC INTELLIGENCE COMMAND &middot; POWERED BY THE DOCTRINE
  </div>

</div><!-- /shell -->

<script>
const DATA = {{ data_json|safe }};

document.addEventListener('DOMContentLoaded', () => {

  // ═══ STRIPE FLASHLIGHT — cursor-tracking radial glow ═══
  const cards = document.querySelectorAll('.card');
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty('--mx', `${e.clientX - rect.left}px`);
      card.style.setProperty('--my', `${e.clientY - rect.top}px`);
    });
  });

  // ═══ STAGGERED CARD ENTRANCE ═══
  cards.forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(16px) scale(0.98)';
    card.style.transition = `opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1) ${50 + i * 50}ms, transform 0.6s cubic-bezier(0.16, 1, 0.3, 1) ${50 + i * 50}ms`;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        card.style.opacity = '1';
        card.style.transform = 'translateY(0) scale(1)';
      });
    });
  });

  // ═══ ANIMATE PRICE BARS ═══
  const bars = document.querySelectorAll('.price-bar-fill');
  bars.forEach((bar, i) => {
    const w = bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = w; }, 200 + i * 100);
  });

  // ═══ COUNT-UP ANIMATION ═══
  const metrics = document.querySelectorAll('.metric-value');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const text = el.textContent.trim();
      const val = parseInt(text);
      if (isNaN(val) || el.dataset.counted) return;
      el.dataset.counted = 'true';
      let current = 0;
      const duration = 800;
      const start = performance.now();
      const step = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        current = Math.round(val * eased);
        el.textContent = current;
        if (progress < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
      observer.unobserve(el);
    });
  }, { threshold: 0.5 });
  metrics.forEach(el => observer.observe(el));

  // ═══ LIVE PULSE — topbar status dots ═══
  const dots = document.querySelectorAll('.status-dot .dot');
  dots.forEach((dot, i) => {
    dot.style.animationDelay = `${i * 0.3}s`;
  });

});
</script>
</body>
</html>'''


# ════════════════════════════════════════════════════════════════════════
#  RUN
# ════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  CORPORATE HQ — Dashboard launching on port {port}...")
    print(f"  Open: http://localhost:{port}\n")
    app.run(debug=False, host="0.0.0.0", port=port)
