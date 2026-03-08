"""Division 1 — Pricing Intelligence

Connects competitor pricing data (already in warehouse) with your own
booking OS data to answer: Are we priced right?

Scout       — Pulls your OS transaction prices and maps them against warehouse competitor prices
Researcher  — Analyzes price elasticity: how your booking volume shifts when you or competitors change prices
Analyst     — Produces pricing recommendations with confidence scores
Auditor     — Validates price data freshness, flags stale competitor records, checks for anomalies
"""

from agents.base import BaseAgent


class PricingIntelScout(BaseAgent):
    name = "pricing_intel_scout"
    description = "Collects and maps your prices vs. competitor prices from OS and warehouse"
    tier = 1

    def execute(self):
        self.log("Pulling your OS transaction data for price mapping...")
        # Pull your actual transaction prices from booking OS
        # Cross-reference against warehouse competitor price_history
        # Output: price_comparison table with your_price, competitor_avg, competitor_min, competitor_max per service
        self.log("Ready. Feed OS transaction exports via ingest_os_prices().")

    def ingest_os_prices(self, service_name, your_price, date=None):
        """Record your own price from the booking OS for comparison."""
        from warehouse.db import get_connection
        con = get_connection()
        con.execute(
            """INSERT INTO your_price_history (service_name, price, recorded_date)
               VALUES (?, ?, COALESCE(?, CURRENT_DATE))""",
            [service_name, your_price, date],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Recorded your price: {service_name} @ ${your_price:.2f}")


class PricingIntelResearcher(BaseAgent):
    name = "pricing_intel_researcher"
    description = "Analyzes price elasticity and competitive positioning depth"
    tier = 2

    def execute(self):
        self.log("Analyzing price elasticity patterns...")
        # Correlate your price changes with booking volume changes
        # Study competitor price moves and their review/booking velocity after
        # Identify services where you have pricing power (high demand, few competitors)
        # Identify services where you're vulnerable (commoditized, many competitors undercutting)
        self.log("Ready. Requires OS booking volume data + warehouse price_history.")

    def find_pricing_power(self):
        """Identify services where you can charge more without losing volume."""
        from warehouse.db import get_connection
        con = get_connection()
        # Services where your price is below competitor avg AND your bookings are full
        rows = con.execute("""
            WITH competitor_avg AS (
                SELECT service_name, ROUND(AVG(price), 2) as avg_price, COUNT(DISTINCT competitor_id) as num_competitors
                FROM price_history
                QUALIFY ROW_NUMBER() OVER (PARTITION BY competitor_id, service_name ORDER BY recorded_at DESC) = 1
                GROUP BY service_name
            )
            SELECT service_name, avg_price, num_competitors
            FROM competitor_avg
            ORDER BY avg_price DESC
        """).fetchall()
        con.close()
        return rows

    def find_vulnerable_services(self):
        """Identify services where competitors are undercutting aggressively."""
        from warehouse.db import get_connection
        con = get_connection()
        rows = con.execute("""
            SELECT service_name, COUNT(DISTINCT competitor_id) as undercut_count,
                   ROUND(MIN(price), 2) as lowest_competitor_price
            FROM price_history
            QUALIFY ROW_NUMBER() OVER (PARTITION BY competitor_id, service_name ORDER BY recorded_at DESC) = 1
            GROUP BY service_name
            HAVING undercut_count >= 3
            ORDER BY undercut_count DESC
        """).fetchall()
        con.close()
        return rows


class PricingIntelAnalyst(BaseAgent):
    name = "pricing_intel_analyst"
    description = "Produces pricing recommendations with confidence scores"
    tier = 3

    def execute(self):
        self.log("Generating pricing recommendations...")
        # For each service, recommend: hold / raise / lower / bundle
        # Confidence score based on data freshness + sample size
        # Factor in: competitor density, your booking fill rate, margin targets
        self.log("Ready. Requires scout + researcher outputs.")

    def recommend(self):
        """Generate price recommendations per service."""
        from warehouse.db import get_connection
        import json
        con = get_connection()
        # Get competitor price landscape per service
        rows = con.execute("""
            WITH latest AS (
                SELECT service_name, price, competitor_id,
                       ROW_NUMBER() OVER (PARTITION BY competitor_id, service_name ORDER BY recorded_at DESC) as rn
                FROM price_history
            )
            SELECT service_name,
                   ROUND(AVG(price), 2) as market_avg,
                   ROUND(MIN(price), 2) as market_floor,
                   ROUND(MAX(price), 2) as market_ceiling,
                   ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price), 2) as p75,
                   COUNT(DISTINCT competitor_id) as sample_size
            FROM latest WHERE rn = 1
            GROUP BY service_name
            HAVING sample_size >= 3
            ORDER BY service_name
        """).fetchall()
        con.close()

        recommendations = []
        for row in rows:
            service, avg, floor, ceiling, p75, n = row
            confidence = min(1.0, n / 10)  # More data = higher confidence
            recommendations.append({
                "service": service,
                "market_avg": float(avg),
                "market_floor": float(floor),
                "market_ceiling": float(ceiling),
                "premium_target": float(p75),
                "sample_size": n,
                "confidence": round(confidence, 2),
            })
        return recommendations


class PricingIntelAuditor(BaseAgent):
    name = "pricing_intel_auditor"
    description = "Validates pricing data quality and flags gaps"
    tier = 4

    def execute(self):
        self.log("Auditing pricing data quality...")
        issues = self.audit()
        for issue in issues:
            self.create_alert(
                alert_type="data_quality",
                title=issue["title"],
                detail=issue["detail"],
                severity=issue["severity"],
            )
        self.log(f"Audit complete. {len(issues)} issues found.")

    def audit(self):
        """Check pricing data for staleness, anomalies, and gaps."""
        from warehouse.db import get_connection
        issues = []
        con = get_connection()

        # Check for stale prices (no update in 30+ days)
        stale = con.execute("""
            SELECT c.company_name, COUNT(DISTINCT ph.service_name) as stale_services
            FROM price_history ph
            JOIN competitors c ON c.competitor_id = ph.competitor_id
            WHERE ph.recorded_at < CURRENT_TIMESTAMP - INTERVAL '30' DAY
            QUALIFY ROW_NUMBER() OVER (PARTITION BY ph.competitor_id, ph.service_name ORDER BY ph.recorded_at DESC) = 1
            GROUP BY c.company_name
        """).fetchall()
        for name, count in stale:
            issues.append({
                "title": f"Stale pricing: {name} ({count} services)",
                "detail": f"No price update in 30+ days for {count} services",
                "severity": "warning",
            })

        # Check for price anomalies (>50% deviation from service avg)
        anomalies = con.execute("""
            WITH latest AS (
                SELECT competitor_id, service_name, price,
                       ROW_NUMBER() OVER (PARTITION BY competitor_id, service_name ORDER BY recorded_at DESC) as rn
                FROM price_history
            ),
            avgs AS (
                SELECT service_name, AVG(price) as avg_price FROM latest WHERE rn = 1 GROUP BY service_name
            )
            SELECT c.company_name, l.service_name, l.price, a.avg_price
            FROM latest l
            JOIN competitors c ON c.competitor_id = l.competitor_id
            JOIN avgs a ON a.service_name = l.service_name
            WHERE l.rn = 1 AND ABS(l.price - a.avg_price) / a.avg_price > 0.5
        """).fetchall()
        for name, svc, price, avg in anomalies:
            issues.append({
                "title": f"Price anomaly: {name} — {svc} @ ${price:.2f} (avg ${avg:.2f})",
                "detail": f"More than 50% deviation from market average",
                "severity": "info",
            })

        con.close()
        return issues
