"""Division 6 — Market Share Tracking

Estimates your share of the Charlotte barber market using competitor
review velocity as a proxy for their volume vs. your actual bookings.

Scout       — Collects your booking counts and competitor review velocity data
Researcher  — Builds volume estimation models using review-to-booking ratios
Analyst     — Produces market share estimates by zip code and service type
Auditor     — Validates estimation methodology and flags confidence issues
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class MarketShareScout(BaseAgent):
    name = "market_share_scout"
    description = "Collects booking volume and competitor activity proxies"
    tier = 1

    def execute(self):
        self.log("Ready to ingest your booking counts for market share estimation.")

    def ingest_your_monthly_volume(self, year_month, total_cuts, unique_clients, revenue):
        """Record your monthly booking volume."""
        con = get_connection()
        con.execute(
            """INSERT INTO your_monthly_volume
               (year_month, total_cuts, unique_clients, revenue)
               VALUES (?, ?, ?, ?)""",
            [year_month, total_cuts, unique_clients, revenue],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Recorded {year_month}: {total_cuts} cuts, {unique_clients} clients, ${revenue}")


class MarketShareResearcher(BaseAgent):
    name = "market_share_researcher"
    description = "Estimates competitor volume using review velocity and social signals"
    tier = 2

    REVIEW_TO_BOOKING_RATIO = 0.05  # ~5% of clients leave reviews (industry benchmark)

    def execute(self):
        self.log("Estimating competitor volumes...")

    def estimate_competitor_volume(self):
        """Estimate monthly cuts per competitor based on review velocity."""
        con = get_connection()
        rows = con.execute("""
            WITH monthly_reviews AS (
                SELECT competitor_id,
                       DATE_TRUNC('month', review_date) as month,
                       COUNT(*) as reviews_that_month
                FROM review_snapshots
                WHERE review_date >= CURRENT_DATE - INTERVAL '6' MONTH
                GROUP BY competitor_id, DATE_TRUNC('month', review_date)
            )
            SELECT c.company_name, c.competitor_id, c.hq_zip,
                   ROUND(AVG(mr.reviews_that_month), 1) as avg_monthly_reviews,
                   ROUND(AVG(mr.reviews_that_month) / ?, 0) as estimated_monthly_cuts,
                   (SELECT COUNT(*) FROM barbers b WHERE b.competitor_id = c.competitor_id AND b.status = 'Active') as barber_count
            FROM competitors c
            JOIN monthly_reviews mr ON mr.competitor_id = c.competitor_id
            WHERE c.status = 'Active'
            GROUP BY c.company_name, c.competitor_id, c.hq_zip
            ORDER BY estimated_monthly_cuts DESC
        """, [self.REVIEW_TO_BOOKING_RATIO]).fetchall()
        con.close()
        return rows

    def estimate_market_size_by_zip(self):
        """Estimate total market size per zip code."""
        con = get_connection()
        rows = con.execute("""
            WITH monthly_reviews AS (
                SELECT c.hq_zip, COUNT(*) as reviews_6mo
                FROM review_snapshots rs
                JOIN competitors c ON c.competitor_id = rs.competitor_id
                WHERE rs.review_date >= CURRENT_DATE - INTERVAL '6' MONTH
                AND c.status = 'Active'
                GROUP BY c.hq_zip
            )
            SELECT hq_zip,
                   reviews_6mo,
                   ROUND(reviews_6mo / ? / 6, 0) as est_monthly_market_cuts,
                   (SELECT COUNT(*) FROM competitors cc WHERE cc.hq_zip = mr.hq_zip AND cc.status = 'Active') as shops
            FROM monthly_reviews mr
            ORDER BY est_monthly_market_cuts DESC
        """, [self.REVIEW_TO_BOOKING_RATIO]).fetchall()
        con.close()
        return rows


class MarketShareAnalyst(BaseAgent):
    name = "market_share_analyst"
    description = "Calculates your market share by zip code and tracks trends"
    tier = 3

    def execute(self):
        self.log("Calculating market share estimates...")
        share = self.calculate_share()
        if share:
            self.log(f"  Your estimated market share: {share['overall_share_pct']}%")
            self.log(f"  Your monthly cuts: {share['your_monthly_cuts']}")
            self.log(f"  Estimated total market: {share['estimated_market_cuts']}/month")

    def calculate_share(self):
        """Calculate your share of the estimated total market."""
        con = get_connection()

        # Your latest monthly volume
        your_vol = con.execute("""
            SELECT total_cuts, unique_clients, revenue
            FROM your_monthly_volume
            ORDER BY year_month DESC LIMIT 1
        """).fetchone()

        if not your_vol:
            con.close()
            return None

        # Estimated total market from all competitors in your zip
        market = con.execute("""
            WITH monthly_reviews AS (
                SELECT COUNT(*) as reviews_6mo
                FROM review_snapshots rs
                JOIN competitors c ON c.competitor_id = rs.competitor_id
                WHERE rs.review_date >= CURRENT_DATE - INTERVAL '6' MONTH
                AND c.status = 'Active'
            )
            SELECT ROUND(reviews_6mo / 0.05 / 6, 0) as est_monthly_market FROM monthly_reviews
        """).fetchone()

        con.close()

        your_cuts = your_vol[0]
        market_cuts = int(market[0]) if market and market[0] else 0
        total_with_you = market_cuts + your_cuts

        return {
            "your_monthly_cuts": your_cuts,
            "your_unique_clients": your_vol[1],
            "your_monthly_revenue": float(your_vol[2]),
            "estimated_market_cuts": market_cuts,
            "overall_share_pct": round(your_cuts * 100.0 / total_with_you, 1) if total_with_you else 0,
        }

    def share_by_zip(self):
        """Your share broken down by the zip codes your clients come from."""
        con = get_connection()
        rows = con.execute("""
            WITH your_by_zip AS (
                SELECT zip_code, COUNT(*) as your_clients
                FROM client_origins
                GROUP BY zip_code
            ),
            market_by_zip AS (
                SELECT c.hq_zip as zip_code,
                       ROUND(COUNT(rs.review_id) / 0.05 / 6, 0) as est_monthly_cuts
                FROM review_snapshots rs
                JOIN competitors c ON c.competitor_id = rs.competitor_id
                WHERE rs.review_date >= CURRENT_DATE - INTERVAL '6' MONTH
                AND c.status = 'Active'
                GROUP BY c.hq_zip
            )
            SELECT COALESCE(yz.zip_code, mz.zip_code) as zip_code,
                   COALESCE(yz.your_clients, 0) as your_clients,
                   COALESCE(mz.est_monthly_cuts, 0) as market_est,
                   ROUND(COALESCE(yz.your_clients, 0) * 100.0 /
                         NULLIF(COALESCE(yz.your_clients, 0) + COALESCE(mz.est_monthly_cuts, 0), 0), 1) as share_pct
            FROM your_by_zip yz
            FULL OUTER JOIN market_by_zip mz ON yz.zip_code = mz.zip_code
            ORDER BY share_pct DESC
        """).fetchall()
        con.close()
        return rows


class MarketShareAuditor(BaseAgent):
    name = "market_share_auditor"
    description = "Validates market share methodology and flags confidence issues"
    tier = 4

    def execute(self):
        self.log("Auditing market share estimates...")
        issues = self.audit()
        for issue in issues:
            self.create_alert(
                alert_type="methodology",
                title=issue["title"],
                detail=issue["detail"],
                severity=issue["severity"],
            )

    def audit(self):
        """Validate the assumptions behind market share estimates."""
        issues = []
        con = get_connection()

        # Check review-to-booking ratio assumption
        # If you have both your reviews AND your bookings, you can calibrate
        your_data = con.execute("""
            SELECT ymv.total_cuts,
                   (SELECT COUNT(*) FROM review_snapshots
                    WHERE review_date >= CURRENT_DATE - INTERVAL '1' MONTH) as recent_competitor_reviews
            FROM your_monthly_volume ymv
            ORDER BY year_month DESC LIMIT 1
        """).fetchone()
        if not your_data or not your_data[0]:
            issues.append({
                "title": "No booking volume data to calibrate market share model",
                "detail": "Need your monthly cut counts to estimate share",
                "severity": "warning",
            })

        # Check competitor review coverage
        no_reviews = con.execute("""
            SELECT COUNT(*) FROM competitors c
            WHERE c.status = 'Active'
            AND NOT EXISTS (
                SELECT 1 FROM review_snapshots rs
                WHERE rs.competitor_id = c.competitor_id
                AND rs.review_date >= CURRENT_DATE - INTERVAL '6' MONTH
            )
        """).fetchone()[0]
        if no_reviews > 0:
            issues.append({
                "title": f"{no_reviews} active competitors have no recent reviews",
                "detail": "These shops are invisible to market share estimation — volume could be undercounted",
                "severity": "warning",
            })

        # Check for your volume data continuity
        months = con.execute("""
            SELECT COUNT(DISTINCT year_month) FROM your_monthly_volume
        """).fetchone()[0]
        if months < 3:
            issues.append({
                "title": f"Only {months} months of your volume data",
                "detail": "Need 3+ months to identify share trends",
                "severity": "info",
            })

        con.close()
        return issues
