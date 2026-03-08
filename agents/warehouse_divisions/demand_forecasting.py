"""Division 3 — Demand Forecasting

Combines booking OS history with external signals (events, seasons,
competitor moves) to predict busy and slow periods before they happen.

Scout       — Collects booking volume, no-show rates, and external event data
Researcher  — Identifies seasonal patterns, day-of-week trends, and event correlations
Analyst     — Produces weekly demand forecasts with confidence intervals
Auditor     — Validates forecast accuracy against actuals, flags drift
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class DemandForecastScout(BaseAgent):
    name = "demand_forecast_scout"
    description = "Collects booking volume and external demand signals"
    tier = 1

    def execute(self):
        self.log("Ready to ingest booking volume and event data.")

    def ingest_daily_volume(self, date, bookings, cancellations=0, no_shows=0, walk_ins=0):
        """Record daily booking metrics from OS."""
        con = get_connection()
        con.execute(
            """INSERT INTO daily_booking_volume
               (booking_date, total_bookings, cancellations, no_shows, walk_ins)
               VALUES (?, ?, ?, ?, ?)""",
            [date, bookings, cancellations, no_shows, walk_ins],
        )
        con.close()
        self.records_processed += 1

    def ingest_local_event(self, event_date, event_name, event_type, expected_attendance=None):
        """Record local events that could affect demand (Panthers game, concerts, etc.)."""
        con = get_connection()
        con.execute(
            """INSERT INTO local_events (event_date, event_name, event_type, expected_attendance)
               VALUES (?, ?, ?, ?)""",
            [event_date, event_name, event_type, expected_attendance],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Event: {event_name} on {event_date}")


class DemandForecastResearcher(BaseAgent):
    name = "demand_forecast_researcher"
    description = "Identifies demand patterns, seasonality, and event correlations"
    tier = 2

    def execute(self):
        self.log("Analyzing demand patterns...")

    def day_of_week_pattern(self):
        """Average bookings by day of week."""
        con = get_connection()
        rows = con.execute("""
            SELECT DAYNAME(booking_date) as day_name,
                   DAYOFWEEK(booking_date) as day_num,
                   ROUND(AVG(total_bookings), 1) as avg_bookings,
                   ROUND(AVG(no_shows), 1) as avg_no_shows,
                   COUNT(*) as weeks_of_data
            FROM daily_booking_volume
            GROUP BY DAYNAME(booking_date), DAYOFWEEK(booking_date)
            ORDER BY day_num
        """).fetchall()
        con.close()
        return rows

    def monthly_seasonality(self):
        """Average bookings by month to find seasonal peaks/valleys."""
        con = get_connection()
        rows = con.execute("""
            SELECT MONTHNAME(booking_date) as month_name,
                   MONTH(booking_date) as month_num,
                   ROUND(AVG(total_bookings), 1) as avg_daily_bookings,
                   SUM(total_bookings) as total_bookings,
                   COUNT(*) as days_of_data
            FROM daily_booking_volume
            GROUP BY MONTHNAME(booking_date), MONTH(booking_date)
            ORDER BY month_num
        """).fetchall()
        con.close()
        return rows

    def event_impact_analysis(self):
        """Compare booking volume on event days vs. normal days."""
        con = get_connection()
        rows = con.execute("""
            WITH event_days AS (
                SELECT DISTINCT event_date FROM local_events
            )
            SELECT
                CASE WHEN ed.event_date IS NOT NULL THEN 'Event Day' ELSE 'Normal Day' END as day_type,
                ROUND(AVG(dbv.total_bookings), 1) as avg_bookings,
                COUNT(*) as sample_days
            FROM daily_booking_volume dbv
            LEFT JOIN event_days ed ON ed.event_date = dbv.booking_date
            GROUP BY day_type
        """).fetchall()
        con.close()
        return rows

    def competitor_move_impact(self):
        """Check if competitor moves (closures, price hikes) correlate with your volume spikes."""
        con = get_connection()
        rows = con.execute("""
            SELECT cm.move_type, cm.move_date, c.company_name,
                   dbv.total_bookings as your_bookings_that_day,
                   (SELECT ROUND(AVG(total_bookings), 1) FROM daily_booking_volume
                    WHERE booking_date BETWEEN cm.move_date - INTERVAL '7' DAY AND cm.move_date - INTERVAL '1' DAY
                   ) as your_avg_prior_week
            FROM competitor_moves cm
            JOIN competitors c ON c.competitor_id = cm.competitor_id
            LEFT JOIN daily_booking_volume dbv ON dbv.booking_date = cm.move_date
            WHERE cm.move_type IN ('closure', 'price_increase', 'barber_departure')
            ORDER BY cm.move_date DESC
        """).fetchall()
        con.close()
        return rows


class DemandForecastAnalyst(BaseAgent):
    name = "demand_forecast_analyst"
    description = "Produces weekly demand forecasts with confidence intervals"
    tier = 3

    def execute(self):
        self.log("Generating demand forecast...")
        forecast = self.forecast_next_week()
        for day in forecast:
            self.log(f"  {day['day']}: predicted={day['predicted_bookings']} "
                     f"(range {day['low']}–{day['high']})")

    def forecast_next_week(self):
        """Simple forecast based on day-of-week averages + event adjustments."""
        con = get_connection()
        # Get day-of-week baselines
        baselines = con.execute("""
            SELECT DAYOFWEEK(booking_date) as dow,
                   ROUND(AVG(total_bookings), 1) as avg_bookings,
                   ROUND(STDDEV(total_bookings), 1) as std_bookings
            FROM daily_booking_volume
            GROUP BY DAYOFWEEK(booking_date)
        """).fetchall()

        # Check for events next week
        events_next_week = con.execute("""
            SELECT event_date, event_name, event_type
            FROM local_events
            WHERE event_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7' DAY
        """).fetchall()

        con.close()

        # Build forecast
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        baseline_map = {row[0]: (float(row[1]), float(row[2]) if row[2] else 1.0) for row in baselines}
        event_dates = {str(e[0]) for e in events_next_week}

        forecast = []
        for dow in range(1, 8):
            avg, std = baseline_map.get(dow, (0, 1))
            # Bump prediction 15% on event days
            event_boost = 1.15 if any(True for e in events_next_week) else 1.0
            predicted = round(avg * event_boost, 1)
            forecast.append({
                "day": day_names[dow - 1],
                "predicted_bookings": predicted,
                "low": round(max(0, predicted - std), 1),
                "high": round(predicted + std, 1),
                "has_event": dow in [int(e[0].strftime('%u')) if hasattr(e[0], 'strftime') else 0 for e in events_next_week],
            })
        return forecast


class DemandForecastAuditor(BaseAgent):
    name = "demand_forecast_auditor"
    description = "Validates forecast accuracy against actuals and flags drift"
    tier = 4

    def execute(self):
        self.log("Auditing forecast accuracy...")
        issues = self.audit()
        for issue in issues:
            self.create_alert(
                alert_type="forecast_quality",
                title=issue["title"],
                detail=issue["detail"],
                severity=issue["severity"],
            )

    def audit(self):
        """Check data quality and forecast reliability."""
        issues = []
        con = get_connection()

        # Check for gaps in daily volume data
        gaps = con.execute("""
            WITH date_range AS (
                SELECT MIN(booking_date) as start_date, MAX(booking_date) as end_date,
                       COUNT(*) as recorded_days
                FROM daily_booking_volume
            ),
            expected AS (
                SELECT DATEDIFF('day', start_date, end_date) + 1 as expected_days,
                       recorded_days
                FROM date_range
            )
            SELECT expected_days - recorded_days as missing_days, expected_days, recorded_days
            FROM expected
        """).fetchone()

        if gaps and gaps[0] and gaps[0] > 0:
            issues.append({
                "title": f"{gaps[0]} missing days in booking volume data",
                "detail": f"Expected {gaps[1]} days, have {gaps[2]}. Gaps reduce forecast accuracy.",
                "severity": "warning",
            })

        # Check for no-show rate anomalies
        noshow = con.execute("""
            SELECT booking_date, no_shows, total_bookings,
                   ROUND(no_shows * 100.0 / NULLIF(total_bookings, 0), 1) as noshow_pct
            FROM daily_booking_volume
            WHERE no_shows * 100.0 / NULLIF(total_bookings, 0) > 20
            ORDER BY booking_date DESC
            LIMIT 5
        """).fetchall()
        if noshow:
            issues.append({
                "title": f"{len(noshow)} days with >20% no-show rate",
                "detail": "High no-show days distort demand baselines. Consider excluding or flagging.",
                "severity": "info",
            })

        # Check minimum data for reliable forecasting (need 8+ weeks)
        weeks = con.execute("""
            SELECT COUNT(DISTINCT DATE_TRUNC('week', booking_date)) as weeks_of_data
            FROM daily_booking_volume
        """).fetchone()[0]
        if weeks and weeks < 8:
            issues.append({
                "title": f"Only {weeks} weeks of booking data (need 8+ for reliable forecasts)",
                "detail": "Forecast confidence is low with limited history.",
                "severity": "warning",
            })

        con.close()
        return issues
