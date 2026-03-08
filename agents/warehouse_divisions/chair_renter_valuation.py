"""Division 5 — Chair Renter Valuation

Uses your demand data to model exactly what each chair is worth per hour,
per day, per week.  Sets renter rates based on actual numbers, not gut feel.

Scout       — Collects chair utilization rates, peak/off-peak splits, and renter inquiry data
Researcher  — Models chair revenue potential by time slot and day
Analyst     — Produces chair rental rate recommendations and renter ROI projections
Auditor     — Validates utilization data and stress-tests assumptions
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class ChairRenterScout(BaseAgent):
    name = "chair_renter_scout"
    description = "Collects chair utilization and market rental rate data"
    tier = 1

    def execute(self):
        self.log("Ready to ingest chair utilization and rental market data.")

    def ingest_chair_utilization(self, date, chair_number, hours_booked, hours_available,
                                  revenue_generated=None):
        """Record daily chair utilization metrics."""
        con = get_connection()
        con.execute(
            """INSERT INTO chair_utilization
               (util_date, chair_number, hours_booked, hours_available, revenue_generated)
               VALUES (?, ?, ?, ?, ?)""",
            [date, chair_number, hours_booked, hours_available, revenue_generated],
        )
        con.close()
        self.records_processed += 1

    def ingest_market_rental_rate(self, shop_name, zip_code, weekly_rate,
                                   includes_products=False, chair_count=None):
        """Record what other shops charge for chair rental (competitor intel)."""
        con = get_connection()
        con.execute(
            """INSERT INTO market_chair_rates
               (shop_name, zip_code, weekly_rate, includes_products, chair_count)
               VALUES (?, ?, ?, ?, ?)""",
            [shop_name, zip_code, weekly_rate, includes_products, chair_count],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Market rate: {shop_name} charges ${weekly_rate}/week")


class ChairRenterResearcher(BaseAgent):
    name = "chair_renter_researcher"
    description = "Models chair revenue potential by time slot and day"
    tier = 2

    def execute(self):
        self.log("Analyzing chair revenue potential...")

    def peak_vs_offpeak(self):
        """Compare chair utilization and revenue: peak vs off-peak hours."""
        con = get_connection()
        rows = con.execute("""
            SELECT
                CASE WHEN DAYOFWEEK(util_date) IN (6, 7) THEN 'Weekend'
                     WHEN DAYOFWEEK(util_date) = 5 THEN 'Friday'
                     ELSE 'Weekday' END as period,
                ROUND(AVG(hours_booked), 1) as avg_hours_booked,
                ROUND(AVG(hours_available), 1) as avg_hours_available,
                ROUND(AVG(hours_booked * 100.0 / NULLIF(hours_available, 0)), 1) as util_pct,
                ROUND(AVG(revenue_generated), 2) as avg_revenue
            FROM chair_utilization
            GROUP BY period
            ORDER BY avg_revenue DESC
        """).fetchall()
        con.close()
        return rows

    def revenue_per_chair_hour(self):
        """What each chair hour is actually worth based on real data."""
        con = get_connection()
        rows = con.execute("""
            SELECT chair_number,
                   ROUND(SUM(revenue_generated) / NULLIF(SUM(hours_booked), 0), 2) as revenue_per_hour,
                   ROUND(AVG(hours_booked * 100.0 / NULLIF(hours_available, 0)), 1) as avg_util_pct,
                   COUNT(*) as days_tracked
            FROM chair_utilization
            WHERE revenue_generated IS NOT NULL
            GROUP BY chair_number
        """).fetchall()
        con.close()
        return rows

    def market_rate_comparison(self):
        """Compare your potential rates against what the market charges."""
        con = get_connection()
        rows = con.execute("""
            SELECT zip_code,
                   COUNT(*) as shops_surveyed,
                   ROUND(AVG(weekly_rate), 2) as avg_weekly_rate,
                   ROUND(MIN(weekly_rate), 2) as min_rate,
                   ROUND(MAX(weekly_rate), 2) as max_rate,
                   ROUND(SUM(CASE WHEN includes_products THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 0) as pct_include_products
            FROM market_chair_rates
            GROUP BY zip_code
            ORDER BY avg_weekly_rate DESC
        """).fetchall()
        con.close()
        return rows


class ChairRenterAnalyst(BaseAgent):
    name = "chair_renter_analyst"
    description = "Produces chair rental rate recommendations and renter ROI projections"
    tier = 3

    def execute(self):
        self.log("Generating chair rental recommendations...")
        rec = self.recommend_rates()
        if rec:
            self.log(f"  Recommended weekly rate: ${rec['recommended_weekly_rate']}")
            self.log(f"  Annual chair revenue: ${rec['annual_chair_revenue']}")
            self.log(f"  Breakeven utilization: {rec['breakeven_util_pct']}%")

    def recommend_rates(self):
        """Calculate optimal chair rental rate based on your actual chair economics."""
        con = get_connection()

        # Your chair revenue data
        your_data = con.execute("""
            SELECT ROUND(SUM(revenue_generated) / NULLIF(SUM(hours_booked), 0), 2) as rev_per_hour,
                   ROUND(AVG(hours_booked), 1) as avg_daily_hours,
                   ROUND(AVG(hours_available), 1) as avg_daily_available
            FROM chair_utilization
            WHERE revenue_generated IS NOT NULL
        """).fetchone()

        # Market rates
        market = con.execute("""
            SELECT ROUND(AVG(weekly_rate), 2) as market_avg,
                   ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY weekly_rate), 2) as market_p75
            FROM market_chair_rates
        """).fetchone()

        con.close()

        if not your_data or not your_data[0]:
            return None

        rev_per_hour, avg_hours, avg_available = [float(x) if x else 0 for x in your_data]
        market_avg = float(market[0]) if market and market[0] else 0
        market_p75 = float(market[1]) if market and market[1] else 0

        # A chair renter should pay you what the chair would earn you if empty
        # minus a discount to make it attractive
        opportunity_cost_weekly = rev_per_hour * avg_hours * 5  # 5 working days
        # Renter pays 60-70% of opportunity cost (they bring their own clients)
        recommended = round(opportunity_cost_weekly * 0.65, 2)

        # Don't go below market average
        if market_avg and recommended < market_avg:
            recommended = market_avg

        return {
            "your_rev_per_chair_hour": rev_per_hour,
            "opportunity_cost_weekly": round(opportunity_cost_weekly, 2),
            "market_avg_weekly": market_avg,
            "market_p75_weekly": market_p75,
            "recommended_weekly_rate": recommended,
            "annual_chair_revenue": round(recommended * 52, 2),
            "breakeven_util_pct": round((recommended / (rev_per_hour * avg_available * 5)) * 100, 1) if rev_per_hour and avg_available else 0,
        }


class ChairRenterAuditor(BaseAgent):
    name = "chair_renter_auditor"
    description = "Validates chair utilization data and stress-tests rental assumptions"
    tier = 4

    def execute(self):
        self.log("Auditing chair renter valuation data...")
        issues = self.audit()
        for issue in issues:
            self.create_alert(
                alert_type="data_quality",
                title=issue["title"],
                detail=issue["detail"],
                severity=issue["severity"],
            )

    def audit(self):
        """Validate chair data and stress-test assumptions."""
        issues = []
        con = get_connection()

        # Check for sufficient utilization data
        days = con.execute("SELECT COUNT(*) FROM chair_utilization").fetchone()[0]
        if days < 30:
            issues.append({
                "title": f"Only {days} days of chair utilization data",
                "detail": "Need 30+ days for reliable rate recommendations",
                "severity": "warning",
            })

        # Check for market rate sample size
        market_count = con.execute("SELECT COUNT(*) FROM market_chair_rates").fetchone()[0]
        if market_count < 5:
            issues.append({
                "title": f"Only {market_count} market rental rates collected",
                "detail": "Need 5+ comparable shops for reliable market positioning",
                "severity": "warning",
            })

        # Check for utilization over 100% (data error)
        over = con.execute("""
            SELECT COUNT(*) FROM chair_utilization
            WHERE hours_booked > hours_available
        """).fetchone()[0]
        if over > 0:
            issues.append({
                "title": f"{over} records show hours_booked > hours_available",
                "detail": "Data entry error — booked hours cannot exceed available hours",
                "severity": "critical",
            })

        # Check revenue without utilization
        missing_rev = con.execute("""
            SELECT COUNT(*) FROM chair_utilization
            WHERE hours_booked > 0 AND revenue_generated IS NULL
        """).fetchone()[0]
        if missing_rev > 0:
            issues.append({
                "title": f"{missing_rev} utilized days missing revenue data",
                "detail": "Revenue data needed for accurate rate calculations",
                "severity": "warning",
            })

        con.close()
        return issues
