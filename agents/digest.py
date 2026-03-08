"""Tier 4 — Weekly Charlotte Barber Digest Bot

Generates a full weekly summary:
- Top price movers
- New shops / closures
- Barber movement
- Review trends
- Social winners
- "What to watch" section

Cadence: Sundays
"""

import datetime
from agents.base import BaseAgent
from warehouse.db import get_connection


class WeeklyDigest(BaseAgent):
    name = "weekly_digest"
    description = "Generates the weekly competitive intelligence digest"
    tier = 4

    def __init__(self, days=7, **kwargs):
        super().__init__(**kwargs)
        self.days = days
        self.sections = []

    def _add_section(self, title, items):
        self.sections.append({"title": title, "items": items})

    def _gather_price_movers(self):
        """Top price changes this period."""
        con = get_connection()
        rows = con.execute("""
            WITH ranked AS (
                SELECT competitor_id, service_name, price, recorded_at,
                       LAG(price) OVER (
                           PARTITION BY competitor_id, service_name
                           ORDER BY recorded_at
                       ) as prev_price
                FROM price_history
                WHERE recorded_at >= CURRENT_TIMESTAMP - INTERVAL '{d}' DAY
            )
            SELECT c.company_name, r.service_name,
                   r.prev_price, r.price as new_price,
                   ROUND(((r.price - r.prev_price) / NULLIF(r.prev_price, 0)) * 100, 1) as pct_change
            FROM ranked r
            JOIN competitors c ON c.competitor_id = r.competitor_id
            WHERE r.prev_price IS NOT NULL AND r.prev_price != r.price
            ORDER BY ABS(pct_change) DESC
            LIMIT 5
        """.format(d=self.days)).fetchall()
        con.close()

        items = []
        for r in rows:
            direction = "UP" if r[4] > 0 else "DOWN"
            items.append(f"{r[0]} — {r[1]}: ${r[2]:.2f} → ${r[3]:.2f} ({direction} {abs(r[4]):.1f}%)")
        self._add_section("TOP PRICE MOVERS", items if items else ["No price changes detected this period."])

    def _gather_new_shops(self):
        """New competitors or closures this period."""
        con = get_connection()
        rows = con.execute("""
            SELECT move_type, c.company_name, m.description
            FROM competitor_moves m
            JOIN competitors c ON c.competitor_id = m.competitor_id
            WHERE m.move_type IN ('New Location', 'Closure', 'Expansion', 'Rebrand')
              AND m.move_date >= CURRENT_DATE - INTERVAL '{d}' DAY
            ORDER BY m.move_date DESC
        """.format(d=self.days)).fetchall()
        con.close()

        items = [f"[{r[0]}] {r[1]}: {r[2]}" for r in rows]
        self._add_section("SHOP MOVEMENTS", items if items else ["No shop openings, closures, or expansions."])

    def _gather_barber_moves(self):
        """Talent movement this period."""
        con = get_connection()
        rows = con.execute("""
            SELECT c.company_name, m.description
            FROM competitor_moves m
            JOIN competitors c ON c.competitor_id = m.competitor_id
            WHERE m.move_type = 'Talent Movement'
              AND m.move_date >= CURRENT_DATE - INTERVAL '{d}' DAY
            ORDER BY m.move_date DESC
        """.format(d=self.days)).fetchall()
        con.close()

        items = [f"{r[0]}: {r[1]}" for r in rows]
        self._add_section("BARBER MOVEMENT", items if items else ["No talent movement detected."])

    def _gather_review_trends(self):
        """Review highlights this period."""
        con = get_connection()
        rows = con.execute("""
            SELECT c.company_name,
                   COUNT(*) as review_count,
                   ROUND(AVG(r.rating), 1) as avg_rating,
                   ROUND(AVG(r.sentiment_score), 2) as avg_sentiment
            FROM review_snapshots r
            JOIN competitors c ON c.competitor_id = r.competitor_id
            WHERE r.collected_at >= CURRENT_TIMESTAMP - INTERVAL '{d}' DAY
            GROUP BY c.company_name
            ORDER BY review_count DESC
            LIMIT 5
        """.format(d=self.days)).fetchall()
        con.close()

        items = [f"{r[0]}: {r[1]} reviews (avg {r[2]}/5, sentiment {r[3]:+.2f})" for r in rows]
        self._add_section("REVIEW TRENDS", items if items else ["No new reviews collected."])

    def _gather_social_winners(self):
        """Top social performers this period."""
        con = get_connection()
        rows = con.execute("""
            SELECT c.company_name, s.platform, s.followers, s.engagement_rate
            FROM competitor_social s
            JOIN competitors c ON c.competitor_id = s.competitor_id
            WHERE s.snapshot_date >= CURRENT_DATE - INTERVAL '{d}' DAY
            ORDER BY s.engagement_rate DESC NULLS LAST
            LIMIT 5
        """.format(d=self.days)).fetchall()
        con.close()

        items = [f"{r[0]} on {r[1]}: {r[2]:,} followers ({r[3]:.1f}% engagement)" for r in rows if r[3]]
        self._add_section("SOCIAL WINNERS", items if items else ["No social data collected this period."])

    def _gather_alerts_summary(self):
        """Unacknowledged alerts from this period."""
        con = get_connection()
        rows = con.execute("""
            SELECT alert_type, severity, COUNT(*) as count
            FROM alerts_log
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '{d}' DAY
              AND acknowledged = FALSE
            GROUP BY alert_type, severity
            ORDER BY
                CASE severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END,
                count DESC
        """.format(d=self.days)).fetchall()
        con.close()

        items = [f"[{r[1].upper()}] {r[0]}: {r[2]} alert(s)" for r in rows]
        self._add_section("UNRESOLVED ALERTS", items if items else ["All clear — no pending alerts."])

    def _gather_what_to_watch(self):
        """Emerging signals worth monitoring."""
        con = get_connection()

        items = []

        # Rising threat levels
        threats = con.execute("""
            SELECT c.company_name, cs.score
            FROM competitor_scores cs
            JOIN competitors c ON c.competitor_id = cs.competitor_id
            WHERE cs.score_type = 'threat_level' AND cs.score >= 7
            QUALIFY ROW_NUMBER() OVER (PARTITION BY cs.competitor_id ORDER BY cs.scored_at DESC) = 1
            ORDER BY cs.score DESC
            LIMIT 3
        """).fetchall()
        for t in threats:
            items.append(f"HIGH THREAT: {t[0]} (threat level {t[1]}/10)")

        # Competitors with many recent moves
        active = con.execute("""
            SELECT c.company_name, COUNT(*) as move_count
            FROM competitor_moves m
            JOIN competitors c ON c.competitor_id = m.competitor_id
            WHERE m.move_date >= CURRENT_DATE - INTERVAL '{d}' DAY
            GROUP BY c.company_name
            HAVING move_count >= 3
            ORDER BY move_count DESC
        """.format(d=self.days)).fetchall()
        for a in active:
            items.append(f"VERY ACTIVE: {a[0]} ({a[1]} moves this period)")

        con.close()
        self._add_section("WHAT TO WATCH", items if items else ["Competitive landscape is stable this period."])

    def generate(self):
        """Generate the full digest."""
        self.sections = []
        self._gather_price_movers()
        self._gather_new_shops()
        self._gather_barber_moves()
        self._gather_review_trends()
        self._gather_social_winners()
        self._gather_alerts_summary()
        self._gather_what_to_watch()
        return self.sections

    def format_digest(self):
        """Format the digest as a readable string."""
        today = datetime.date.today()
        start = today - datetime.timedelta(days=self.days)

        lines = []
        lines.append("=" * 60)
        lines.append(f"  CHARLOTTE BARBER INTEL — WEEKLY DIGEST")
        lines.append(f"  {start.strftime('%b %d')} – {today.strftime('%b %d, %Y')}")
        lines.append("=" * 60)

        for section in self.sections:
            lines.append(f"\n{'─' * 60}")
            lines.append(f"  {section['title']}")
            lines.append(f"{'─' * 60}")
            for item in section["items"]:
                lines.append(f"  • {item}")

        lines.append(f"\n{'=' * 60}")
        lines.append(f"  End of digest. {self.records_processed} data points analyzed.")
        lines.append("=" * 60)
        return "\n".join(lines)

    def execute(self):
        self.log("Generating weekly digest...")
        self.generate()
        digest_text = self.format_digest()
        print(digest_text)

        # Store digest as an alert for record-keeping
        self.create_alert(
            alert_type="weekly_digest",
            title=f"Weekly Digest — {datetime.date.today().strftime('%b %d, %Y')}",
            detail=digest_text,
            severity="info",
        )
        self.records_processed = len(self.sections)
