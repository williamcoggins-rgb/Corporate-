"""RETIRED — Division 4 — Revenue per Service Analysis

STATUS: RETIRED as of Phase One (June 2026).
BLOCKED ON: booking-OS integration (requires service_economics table).
Planned for Phase Two once booking-OS feeds exist.
NOT registered, NOT scheduled. See agents/warehouse_divisions/README.md to revive.

Original description:
Crosses finance OS (cost of supplies per service) with booking OS
(frequency, tips, duration) to find the most profitable service — not
just the highest priced.

Scout       — Collects per-service cost data, tip rates, and duration from both OS systems
Researcher  — Calculates true margin per service (price - supplies - time cost)
Analyst     — Ranks services by profit per hour, recommends menu optimization
Auditor     — Validates cost inputs and flags services with missing data
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class RevenueServiceScout(BaseAgent):
    name = "revenue_svc_scout"
    description = "Collects per-service revenue, cost, and time data from OS systems"
    tier = 1

    def execute(self):
        self.log("Ready to ingest service-level financial data.")

    def ingest_service_economics(self, service_name, avg_price, avg_tip,
                                  supply_cost, duration_minutes, bookings_per_week):
        """Record the full economics of a service."""
        con = get_connection()
        con.execute(
            """INSERT INTO service_economics
               (service_name, avg_price, avg_tip, supply_cost, duration_minutes, bookings_per_week)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [service_name, avg_price, avg_tip, supply_cost, duration_minutes, bookings_per_week],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Recorded: {service_name} — ${avg_price} + ${avg_tip} tip, "
                 f"${supply_cost} cost, {duration_minutes}min")


class RevenueServiceResearcher(BaseAgent):
    name = "revenue_svc_researcher"
    description = "Calculates true profit margin and hourly rate per service"
    tier = 2

    def execute(self):
        self.log("Calculating true service profitability...")

    def profit_per_hour(self, hourly_overhead=0):
        """Calculate profit per hour for each service."""
        con = get_connection()
        rows = con.execute("""
            SELECT service_name, avg_price, avg_tip, supply_cost, duration_minutes, bookings_per_week,
                   ROUND(avg_price + avg_tip - supply_cost, 2) as gross_profit_per_cut,
                   ROUND((avg_price + avg_tip - supply_cost) * (60.0 / duration_minutes), 2) as gross_profit_per_hour,
                   ROUND((avg_price + avg_tip - supply_cost) * bookings_per_week, 2) as weekly_gross
            FROM service_economics
            QUALIFY ROW_NUMBER() OVER (PARTITION BY service_name ORDER BY recorded_at DESC) = 1
            ORDER BY gross_profit_per_hour DESC
        """).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def time_analysis(self):
        """How your chair time is distributed across services."""
        con = get_connection()
        rows = con.execute("""
            SELECT service_name, duration_minutes, bookings_per_week,
                   ROUND(duration_minutes * bookings_per_week, 0) as weekly_minutes,
                   ROUND(duration_minutes * bookings_per_week / 60.0, 1) as weekly_hours
            FROM service_economics
            QUALIFY ROW_NUMBER() OVER (PARTITION BY service_name ORDER BY recorded_at DESC) = 1
            ORDER BY weekly_minutes DESC
        """).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]


class RevenueServiceAnalyst(BaseAgent):
    name = "revenue_svc_analyst"
    description = "Ranks services and recommends menu optimization"
    tier = 3

    def execute(self):
        self.log("Generating service menu optimization...")
        recs = self.optimize_menu()
        for r in recs:
            self.log(f"  {r['service']}: {r['action']} — {r['reason']}")

    def optimize_menu(self):
        """Recommend: promote, maintain, reprice, or drop each service."""
        con = get_connection()
        rows = con.execute("""
            SELECT service_name,
                   avg_price, avg_tip, supply_cost, duration_minutes, bookings_per_week,
                   ROUND(avg_price + avg_tip - supply_cost, 2) as profit_per_cut,
                   ROUND((avg_price + avg_tip - supply_cost) * (60.0 / duration_minutes), 2) as profit_per_hour,
                   ROUND((avg_price + avg_tip - supply_cost) * bookings_per_week, 2) as weekly_profit
            FROM service_economics
            QUALIFY ROW_NUMBER() OVER (PARTITION BY service_name ORDER BY recorded_at DESC) = 1
        """).fetchall()
        con.close()

        if not rows:
            return []

        # Calculate averages for comparison
        avg_profit_hr = sum(r[7] for r in rows) / len(rows)

        recommendations = []
        for row in rows:
            name, price, tip, cost, mins, bpw, ppc, pph, weekly = row
            if pph > avg_profit_hr * 1.3:
                action, reason = "PROMOTE", f"${pph}/hr is 30%+ above avg — push more bookings here"
            elif pph < avg_profit_hr * 0.5:
                action, reason = "REPRICE or DROP", f"${pph}/hr is below half the avg — raise price or remove"
            elif mins > 45 and pph < avg_profit_hr:
                action, reason = "REPRICE", f"{mins}min service below avg $/hr — price doesn't justify chair time"
            elif bpw >= 5 and pph >= avg_profit_hr:
                action, reason = "MAINTAIN", f"High volume + solid margin — bread and butter"
            else:
                action, reason = "MAINTAIN", f"Performing at average"

            recommendations.append({
                "service": name,
                "profit_per_hour": float(pph),
                "weekly_profit": float(weekly),
                "action": action,
                "reason": reason,
            })
        recommendations.sort(key=lambda x: x["profit_per_hour"], reverse=True)
        return recommendations


class RevenueServiceAuditor(BaseAgent):
    name = "revenue_svc_auditor"
    description = "Validates service economics data and flags incomplete entries"
    tier = 4

    def execute(self):
        self.log("Auditing service economics data...")
        issues = self.audit()
        for issue in issues:
            self.create_alert(
                alert_type="data_quality",
                title=issue["title"],
                detail=issue["detail"],
                severity=issue["severity"],
            )

    def audit(self):
        """Check for missing or suspicious service economics data."""
        issues = []
        con = get_connection()

        # Services offered in booking OS but no economics recorded
        # Compare against tracked services from pricing scout
        from agents.pricing_scout import TRACKED_SERVICES
        recorded = con.execute(
            "SELECT DISTINCT service_name FROM service_economics"
        ).fetchall()
        recorded_names = {r[0] for r in recorded}
        missing = [s for s in TRACKED_SERVICES if s not in recorded_names]
        if missing:
            issues.append({
                "title": f"{len(missing)} tracked services have no cost data",
                "detail": f"Missing economics for: {', '.join(missing[:5])}",
                "severity": "warning",
            })

        # Check for zero supply costs (suspicious)
        zeros = con.execute("""
            SELECT service_name FROM service_economics WHERE supply_cost = 0
            QUALIFY ROW_NUMBER() OVER (PARTITION BY service_name ORDER BY recorded_at DESC) = 1
        """).fetchall()
        if zeros:
            issues.append({
                "title": f"{len(zeros)} services with $0 supply cost",
                "detail": f"Every service uses some supplies. Verify: {', '.join(r[0] for r in zeros[:5])}",
                "severity": "info",
            })

        # Check for services with negative margins
        negative = con.execute("""
            SELECT service_name, avg_price, supply_cost
            FROM service_economics
            WHERE supply_cost >= avg_price
            QUALIFY ROW_NUMBER() OVER (PARTITION BY service_name ORDER BY recorded_at DESC) = 1
        """).fetchall()
        if negative:
            issues.append({
                "title": f"{len(negative)} services with negative margin",
                "detail": f"Supply cost >= price: {', '.join(r[0] for r in negative)}",
                "severity": "critical",
            })

        con.close()
        return issues
