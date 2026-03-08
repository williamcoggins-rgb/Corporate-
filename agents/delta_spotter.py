"""Tier 2 — Delta & Trend Spotter Bot

Compares data across runs to detect: price hikes/drops, review volume
spikes, rating changes, new services, barber movements.

Scores "threat level" — high if a competitor's average rating jumps
or they post consistent high-engagement content.

Trigger: After each data load
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class DeltaSpotter(BaseAgent):
    name = "delta_spotter"
    description = "Detects changes and trends across competitor data over time"
    tier = 2

    def detect_price_changes(self, days=7, threshold_pct=5):
        """Find services where price changed by more than threshold in recent window."""
        con = get_connection()
        rows = con.execute("""
            WITH ranked AS (
                SELECT competitor_id, service_name, price, recorded_at,
                       ROW_NUMBER() OVER (
                           PARTITION BY competitor_id, service_name
                           ORDER BY recorded_at DESC
                       ) as rn
                FROM price_history
                WHERE recorded_at >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY
            ),
            current_prices AS (
                SELECT * FROM ranked WHERE rn = 1
            ),
            previous_prices AS (
                SELECT * FROM ranked WHERE rn = 2
            )
            SELECT c.company_name, cp.service_name,
                   pp.price as old_price, cp.price as new_price,
                   ROUND(((cp.price - pp.price) / pp.price) * 100, 1) as pct_change
            FROM current_prices cp
            JOIN previous_prices pp
                ON cp.competitor_id = pp.competitor_id
                AND cp.service_name = pp.service_name
            JOIN competitors c ON c.competitor_id = cp.competitor_id
            WHERE ABS(((cp.price - pp.price) / pp.price) * 100) >= {threshold}
            ORDER BY ABS(pct_change) DESC
        """.format(days=days, threshold=threshold_pct)).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()

        changes = [dict(zip(columns, row)) for row in rows]
        for ch in changes:
            direction = "increased" if ch["pct_change"] > 0 else "decreased"
            self.create_alert(
                alert_type="price_change",
                title=f"{ch['company_name']} {direction} {ch['service_name']}: "
                      f"${ch['old_price']:.2f} → ${ch['new_price']:.2f} ({ch['pct_change']:+.1f}%)",
                severity="warning" if abs(ch["pct_change"]) > 15 else "info",
                data_json=json.dumps(ch, default=str),
            )
            self.records_processed += 1

        return changes

    def detect_rating_shifts(self, days=30, min_reviews=3):
        """Find competitors whose average rating changed significantly."""
        con = get_connection()
        rows = con.execute("""
            WITH recent AS (
                SELECT competitor_id,
                       AVG(rating) as recent_avg,
                       COUNT(*) as recent_count
                FROM review_snapshots
                WHERE collected_at >= CURRENT_TIMESTAMP - INTERVAL '{d}' DAY
                  AND rating IS NOT NULL
                GROUP BY competitor_id
                HAVING COUNT(*) >= {min}
            ),
            previous AS (
                SELECT competitor_id,
                       AVG(rating) as prev_avg,
                       COUNT(*) as prev_count
                FROM review_snapshots
                WHERE collected_at < CURRENT_TIMESTAMP - INTERVAL '{d}' DAY
                  AND collected_at >= CURRENT_TIMESTAMP - INTERVAL '{d2}' DAY
                  AND rating IS NOT NULL
                GROUP BY competitor_id
                HAVING COUNT(*) >= {min}
            )
            SELECT c.company_name, c.competitor_id,
                   ROUND(p.prev_avg, 2) as previous_rating,
                   ROUND(r.recent_avg, 2) as current_rating,
                   ROUND(r.recent_avg - p.prev_avg, 2) as rating_delta,
                   r.recent_count, p.prev_count
            FROM recent r
            JOIN previous p ON p.competitor_id = r.competitor_id
            JOIN competitors c ON c.competitor_id = r.competitor_id
            WHERE ABS(r.recent_avg - p.prev_avg) >= 0.3
            ORDER BY rating_delta DESC
        """.format(d=days, d2=days * 2, min=min_reviews)).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()

        shifts = [dict(zip(columns, row)) for row in rows]
        for s in shifts:
            direction = "improving" if s["rating_delta"] > 0 else "declining"
            severity = "warning" if abs(s["rating_delta"]) > 0.5 else "info"

            self.create_alert(
                alert_type="rating_shift",
                title=f"{s['company_name']} rating {direction}: "
                      f"{s['previous_rating']} → {s['current_rating']}",
                severity=severity,
                competitor_id=s["competitor_id"],
                data_json=json.dumps(s, default=str),
            )
            self.records_processed += 1

        return shifts

    def detect_review_volume_spikes(self, days=7, spike_multiplier=2.0):
        """Find competitors getting significantly more reviews than usual."""
        con = get_connection()
        rows = con.execute("""
            WITH recent AS (
                SELECT competitor_id, COUNT(*) as recent_reviews
                FROM review_snapshots
                WHERE collected_at >= CURRENT_TIMESTAMP - INTERVAL '{d}' DAY
                GROUP BY competitor_id
            ),
            baseline AS (
                SELECT competitor_id,
                       COUNT(*) * 1.0 / 4 as weekly_avg
                FROM review_snapshots
                WHERE collected_at >= CURRENT_TIMESTAMP - INTERVAL '{d4}' DAY
                  AND collected_at < CURRENT_TIMESTAMP - INTERVAL '{d}' DAY
                GROUP BY competitor_id
            )
            SELECT c.company_name, c.competitor_id,
                   r.recent_reviews,
                   ROUND(b.weekly_avg, 1) as baseline_weekly,
                   ROUND(r.recent_reviews / NULLIF(b.weekly_avg, 0), 1) as spike_ratio
            FROM recent r
            JOIN baseline b ON b.competitor_id = r.competitor_id
            JOIN competitors c ON c.competitor_id = r.competitor_id
            WHERE r.recent_reviews / NULLIF(b.weekly_avg, 0) >= {mult}
            ORDER BY spike_ratio DESC
        """.format(d=days, d4=days * 4, mult=spike_multiplier)).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()

        spikes = [dict(zip(columns, row)) for row in rows]
        for sp in spikes:
            self.create_alert(
                alert_type="review_spike",
                title=f"{sp['company_name']} review volume spike: "
                      f"{sp['recent_reviews']} reviews ({sp['spike_ratio']}x normal)",
                severity="warning",
                competitor_id=sp["competitor_id"],
            )
            self.records_processed += 1

        return spikes

    def calculate_threat_level(self, competitor_id):
        """Score a competitor's threat level 1-10 based on recent signals."""
        con = get_connection()
        score = 0

        # Recent positive rating trend
        rating_row = con.execute("""
            SELECT AVG(rating) FROM review_snapshots
            WHERE competitor_id = ?
              AND collected_at >= CURRENT_TIMESTAMP - INTERVAL '30' DAY
        """, [competitor_id]).fetchone()
        if rating_row and rating_row[0]:
            score += min(3, (rating_row[0] - 3) * 1.5)  # max 3 pts for high ratings

        # Social engagement
        social_row = con.execute("""
            SELECT engagement_rate FROM competitor_social
            WHERE competitor_id = ?
            ORDER BY snapshot_date DESC LIMIT 1
        """, [competitor_id]).fetchone()
        if social_row and social_row[0]:
            score += min(2, social_row[0] / 2)  # max 2 pts for engagement

        # Recent strategic moves
        move_count = con.execute("""
            SELECT COUNT(*) FROM competitor_moves
            WHERE competitor_id = ?
              AND move_date >= CURRENT_DATE - INTERVAL '60' DAY
        """, [competitor_id]).fetchone()[0]
        score += min(2, move_count * 0.5)  # max 2 pts for activity

        # Price competitiveness (lower = more threatening)
        price_row = con.execute("""
            SELECT AVG(price) FROM price_history
            WHERE competitor_id = ?
              AND service_name ILIKE '%fade%'
            QUALIFY ROW_NUMBER() OVER (PARTITION BY service_name ORDER BY recorded_at DESC) = 1
        """, [competitor_id]).fetchone()
        if price_row and price_row[0] and price_row[0] < 35:
            score += 2  # aggressive pricing
        elif price_row and price_row[0] and price_row[0] < 45:
            score += 1

        # Barber talent
        barber_count = con.execute(
            "SELECT COUNT(*) FROM barbers WHERE competitor_id = ? AND status = 'Active'",
            [competitor_id]
        ).fetchone()[0]
        score += min(1, barber_count * 0.2)  # max 1 pt for team depth

        final_score = max(1, min(10, round(score)))

        # Store the score
        sid = con.execute("SELECT nextval('seq_score')").fetchone()[0]
        con.execute(
            """INSERT INTO competitor_scores (id, competitor_id, score_type, score, components)
               VALUES (?, ?, 'threat_level', ?, ?)""",
            [sid, competitor_id, final_score, json.dumps({
                "rating_component": round(min(3, (rating_row[0] - 3) * 1.5), 1) if rating_row and rating_row[0] else 0,
                "social_component": round(min(2, social_row[0] / 2), 1) if social_row and social_row[0] else 0,
                "activity_component": round(min(2, move_count * 0.5), 1),
                "price_component": 2 if price_row and price_row[0] and price_row[0] < 35 else (1 if price_row and price_row[0] and price_row[0] < 45 else 0),
                "talent_component": round(min(1, barber_count * 0.2), 1),
            })],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Threat level for competitor {competitor_id}: {final_score}/10")
        return final_score

    def execute(self):
        self.log("Running delta detection...")
        price_changes = self.detect_price_changes()
        self.log(f"Found {len(price_changes)} significant price changes")
        rating_shifts = self.detect_rating_shifts()
        self.log(f"Found {len(rating_shifts)} rating shifts")
        volume_spikes = self.detect_review_volume_spikes()
        self.log(f"Found {len(volume_spikes)} review volume spikes")

        # Score all active competitors
        con = get_connection()
        competitors = con.execute(
            "SELECT competitor_id FROM competitors WHERE status = 'Active'"
        ).fetchall()
        con.close()
        for (cid,) in competitors:
            self.calculate_threat_level(cid)
