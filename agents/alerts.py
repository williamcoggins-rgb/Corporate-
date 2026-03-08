"""Tier 4 — Alert Agents: Price War, Reputation Radar, Talent Movement

These agents run after data loads and generate actionable alerts.

Price War Alert — notify on significant price drops or flash deals
Reputation Radar — flag review clusters or sentiment shifts
Talent Movement — detect barber departures/arrivals
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class PriceWarAlert(BaseAgent):
    name = "price_war_alert"
    description = "Detects price wars, undercuts, and aggressive promo moves"
    tier = 4

    def __init__(self, your_prices=None, **kwargs):
        super().__init__(**kwargs)
        self.your_prices = your_prices or {}

    def scan_for_undercuts(self):
        """Compare latest competitor prices against yours."""
        if not self.your_prices:
            self.log("No base prices set — skipping undercut scan")
            return []

        con = get_connection()
        undercuts = []

        for service, your_price in self.your_prices.items():
            rows = con.execute("""
                SELECT company_name, competitor_id, price, service_name FROM (
                    SELECT c.company_name, c.competitor_id, ph.price, ph.service_name,
                           ROW_NUMBER() OVER (
                               PARTITION BY ph.competitor_id ORDER BY ph.recorded_at DESC
                           ) as rn
                    FROM price_history ph
                    JOIN competitors c ON c.competitor_id = ph.competitor_id
                    WHERE ph.service_name ILIKE ?
                ) WHERE rn = 1 AND price < ?
            """, [f"%{service}%", your_price]).fetchall()

            for row in rows:
                their_price = float(row[2])
                diff = your_price - their_price
                pct = (diff / your_price) * 100
                undercut = {
                    "competitor": row[0],
                    "competitor_id": row[1],
                    "service": row[3],
                    "their_price": their_price,
                    "your_price": float(your_price),
                    "difference": float(diff),
                    "pct_lower": round(pct, 1),
                }
                undercuts.append(undercut)

                severity = "critical" if pct > 20 else ("warning" if pct > 10 else "info")
                self.create_alert(
                    alert_type="price_war",
                    title=f"{row[0]} undercuts your {service}: ${their_price:.2f} vs ${your_price:.2f} ({pct:.0f}% less)",
                    detail=f"Consider: bundle deals, loyalty pricing, or value-add services to compete",
                    severity=severity,
                    competitor_id=row[1],
                    data_json=json.dumps(undercut),
                )
                self.records_processed += 1

        con.close()
        return undercuts

    def scan_for_price_drops(self, days=14, min_drop_pct=10):
        """Find competitors who recently dropped prices significantly."""
        con = get_connection()
        rows = con.execute("""
            WITH latest AS (
                SELECT competitor_id, service_name, price, recorded_at,
                       LAG(price) OVER (
                           PARTITION BY competitor_id, service_name
                           ORDER BY recorded_at
                       ) as prev_price
                FROM price_history
                WHERE recorded_at >= CURRENT_TIMESTAMP - INTERVAL '{d}' DAY
            )
            SELECT c.company_name, c.competitor_id, l.service_name,
                   l.prev_price, l.price as new_price,
                   ROUND(((l.price - l.prev_price) / l.prev_price) * 100, 1) as pct_change
            FROM latest l
            JOIN competitors c ON c.competitor_id = l.competitor_id
            WHERE l.prev_price IS NOT NULL
              AND ((l.price - l.prev_price) / l.prev_price) * 100 <= -{min_drop}
            ORDER BY pct_change ASC
        """.format(d=days, min_drop=min_drop_pct)).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()

        drops = [dict(zip(columns, row)) for row in rows]
        for d in drops:
            self.create_alert(
                alert_type="price_drop",
                title=f"{d['company_name']} dropped {d['service_name']}: "
                      f"${d['prev_price']:.2f} → ${d['new_price']:.2f} ({d['pct_change']:.1f}%)",
                severity="warning",
                competitor_id=d["competitor_id"],
            )
            self.records_processed += 1

        return drops

    def execute(self):
        self.log("Scanning for price wars...")
        undercuts = self.scan_for_undercuts()
        self.log(f"Found {len(undercuts)} undercuts")
        drops = self.scan_for_price_drops()
        self.log(f"Found {len(drops)} significant price drops")


class ReputationRadar(BaseAgent):
    name = "reputation_radar"
    description = "Monitors reputation shifts and review anomalies"
    tier = 4

    def scan_review_clusters(self, hours=48, neg_threshold=3, pos_threshold=5):
        """Find bursts of negative or positive reviews."""
        con = get_connection()

        # Negative clusters
        neg_rows = con.execute("""
            SELECT c.company_name, c.competitor_id,
                   COUNT(*) as neg_count,
                   GROUP_CONCAT(DISTINCT r.keywords) as common_issues
            FROM review_snapshots r
            JOIN competitors c ON c.competitor_id = r.competitor_id
            WHERE r.rating <= 2
              AND r.collected_at >= CURRENT_TIMESTAMP - INTERVAL '{h}' HOUR
            GROUP BY c.company_name, c.competitor_id
            HAVING neg_count >= {t}
            ORDER BY neg_count DESC
        """.format(h=hours, t=neg_threshold)).fetchall()

        for row in neg_rows:
            self.create_alert(
                alert_type="reputation_crisis",
                title=f"{row[0]}: {row[2]} negative reviews in {hours}hrs",
                detail=f"Common issues: {row[3]}. OPPORTUNITY: emphasize your strengths in these areas",
                severity="critical" if row[2] >= neg_threshold * 2 else "warning",
                competitor_id=row[1],
            )
            self.records_processed += 1

        # Positive clusters (competitor getting stronger)
        pos_rows = con.execute("""
            SELECT c.company_name, c.competitor_id,
                   COUNT(*) as pos_count,
                   ROUND(AVG(r.rating), 1) as avg_rating
            FROM review_snapshots r
            JOIN competitors c ON c.competitor_id = r.competitor_id
            WHERE r.rating >= 4
              AND r.collected_at >= CURRENT_TIMESTAMP - INTERVAL '{h}' HOUR
            GROUP BY c.company_name, c.competitor_id
            HAVING pos_count >= {t}
            ORDER BY pos_count DESC
        """.format(h=hours, t=pos_threshold)).fetchall()

        for row in pos_rows:
            self.create_alert(
                alert_type="competitor_surge",
                title=f"{row[0]}: {row[2]} positive reviews in {hours}hrs (avg {row[3]}/5)",
                detail=f"Competitor gaining momentum — monitor closely",
                severity="warning",
                competitor_id=row[1],
            )
            self.records_processed += 1

        con.close()

    def execute(self):
        self.log("Scanning reputation signals...")
        self.scan_review_clusters()


class TalentTracker(BaseAgent):
    name = "talent_tracker"
    description = "Monitors barber movement between shops"
    tier = 4

    def scan_for_departures(self, inactive_days=30):
        """Find barbers not seen in reviews/social recently."""
        con = get_connection()
        rows = con.execute("""
            SELECT b.barber_id, b.name, c.company_name, c.competitor_id,
                   b.last_seen, b.specialties
            FROM barbers b
            JOIN competitors c ON c.competitor_id = b.competitor_id
            WHERE b.status = 'Active'
              AND b.last_seen < CURRENT_DATE - INTERVAL '{d}' DAY
            ORDER BY b.last_seen ASC
        """.format(d=inactive_days)).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()

        stale = [dict(zip(columns, row)) for row in rows]
        for s in stale:
            self.create_alert(
                alert_type="barber_inactive",
                title=f"Barber '{s['name']}' at {s['company_name']} not seen since {s['last_seen']}",
                detail=f"Specialties: {s['specialties']}. May have departed — recruitment opportunity?",
                severity="info",
                competitor_id=s["competitor_id"],
            )
            self.records_processed += 1

        return stale

    def execute(self):
        self.log("Scanning for talent movement signals...")
        stale = self.scan_for_departures()
        self.log(f"Found {len(stale)} potentially inactive barbers")
