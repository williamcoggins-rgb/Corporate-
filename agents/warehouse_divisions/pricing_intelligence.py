"""RETIRED — Division 1 — Pricing Intelligence

STATUS: RETIRED as of Phase One (June 2026).
SUPERSEDED BY: agents/pricing_strategist.py (Tier 3, registered in runner.py).
The new Pricing Strategist absorbs the Analyst function and writes Option C
plain-English narratives into the pricing_recommendations table.
NOT registered, NOT scheduled. See agents/warehouse_divisions/README.md to revive.

Original description:
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


class PricingIntelZipAnalyst(BaseAgent):
    """Zip-code pricing analyst — ranks zones by price level and identifies opportunities."""
    name = "pricing_intel_zip_analyst"
    description = "Analyzes pricing by zip code to rank areas from most to least expensive"
    tier = 3

    def execute(self):
        self.log("Analyzing pricing by zip code...")
        report = self.full_zip_report()
        self.records_processed = len(report.get("zip_rankings", []))

        # Alert on pricing gaps (zips where you could charge more)
        for gap in report.get("opportunity_gaps", []):
            self.create_alert(
                alert_type="zip_pricing_opportunity",
                title=f"Pricing opportunity in {gap['zip_code']} ({gap['neighborhood']})",
                detail=(f"Avg price ${gap['avg_price']:.2f} — "
                        f"{gap['pct_above_city_avg']:+.0f}% vs city avg ${gap['city_avg']:.2f}"),
                severity="info",
            )

    def full_zip_report(self):
        """Comprehensive zip-code pricing report.

        Returns:
          - zip_rankings: all zips ranked most→least expensive
          - service_breakdown: per-service zip rankings
          - opportunity_gaps: zips priced above city avg (premium zones)
          - underserved_zips: zips with few shops (potential openings)
        """
        from warehouse.db import get_connection
        import json
        con = get_connection()

        # 1) Overall zip rankings (most expensive first)
        zip_rankings = con.execute("""
            WITH latest_prices AS (
                SELECT ph.competitor_id, ph.service_name, ph.price,
                       ROW_NUMBER() OVER (
                           PARTITION BY ph.competitor_id, ph.service_name
                           ORDER BY ph.recorded_at DESC
                       ) as rn
                FROM price_history ph
            )
            SELECT c.zip_code,
                   COALESCE(c.neighborhood, c.hq_location) as area_name,
                   COUNT(DISTINCT c.competitor_id) as shop_count,
                   COUNT(DISTINCT lp.service_name) as services_tracked,
                   ROUND(AVG(lp.price), 2) as avg_price,
                   ROUND(MIN(lp.price), 2) as min_price,
                   ROUND(MAX(lp.price), 2) as max_price,
                   ROUND(MEDIAN(lp.price), 2) as median_price,
                   ROUND(STDDEV(lp.price), 2) as price_stddev
            FROM latest_prices lp
            JOIN competitors c ON c.competitor_id = lp.competitor_id
            WHERE lp.rn = 1 AND c.zip_code IS NOT NULL
            GROUP BY c.zip_code, COALESCE(c.neighborhood, c.hq_location)
            ORDER BY avg_price DESC
        """).fetchall()
        zip_cols = [d[0] for d in con.description]
        zip_data = [dict(zip(zip_cols, r)) for r in zip_rankings]

        # City-wide average
        city_avg_row = con.execute("""
            WITH latest_prices AS (
                SELECT price,
                       ROW_NUMBER() OVER (
                           PARTITION BY competitor_id, service_name
                           ORDER BY recorded_at DESC
                       ) as rn
                FROM price_history
            )
            SELECT ROUND(AVG(price), 2) FROM latest_prices WHERE rn = 1
        """).fetchone()
        city_avg = float(city_avg_row[0]) if city_avg_row[0] else 0

        # 2) Per-service zip rankings
        service_breakdown = con.execute("""
            WITH latest_prices AS (
                SELECT ph.competitor_id, ph.service_name, ph.price,
                       ROW_NUMBER() OVER (
                           PARTITION BY ph.competitor_id, ph.service_name
                           ORDER BY ph.recorded_at DESC
                       ) as rn
                FROM price_history ph
            )
            SELECT lp.service_name, c.zip_code,
                   COALESCE(c.neighborhood, c.hq_location) as area_name,
                   COUNT(DISTINCT c.competitor_id) as shop_count,
                   ROUND(AVG(lp.price), 2) as avg_price,
                   ROUND(MIN(lp.price), 2) as min_price,
                   ROUND(MAX(lp.price), 2) as max_price
            FROM latest_prices lp
            JOIN competitors c ON c.competitor_id = lp.competitor_id
            WHERE lp.rn = 1 AND c.zip_code IS NOT NULL
            GROUP BY lp.service_name, c.zip_code, COALESCE(c.neighborhood, c.hq_location)
            ORDER BY lp.service_name, avg_price DESC
        """).fetchall()
        svc_cols = [d[0] for d in con.description]
        svc_data = [dict(zip(svc_cols, r)) for r in service_breakdown]

        # 3) Opportunity gaps — zips priced above city average
        opportunity_gaps = []
        for z in zip_data:
            if city_avg > 0:
                pct = ((float(z["avg_price"]) - city_avg) / city_avg) * 100
            else:
                pct = 0
            if pct > 5:  # At least 5% above city avg
                opportunity_gaps.append({
                    "zip_code": z["zip_code"],
                    "neighborhood": z["area_name"],
                    "avg_price": float(z["avg_price"]),
                    "city_avg": city_avg,
                    "pct_above_city_avg": round(pct, 1),
                    "shop_count": z["shop_count"],
                })

        # 4) Underserved zips — few shops but existing demand
        underserved = [z for z in zip_data if z["shop_count"] <= 2]

        con.close()

        report = {
            "city_avg_price": city_avg,
            "zip_rankings": zip_data,
            "service_breakdown": svc_data,
            "opportunity_gaps": opportunity_gaps,
            "underserved_zips": underserved,
            "total_zips_analyzed": len(zip_data),
        }

        self.log(f"Analyzed {len(zip_data)} zips. City avg: ${city_avg:.2f}")
        self.log(f"Premium zones: {len(opportunity_gaps)}. Underserved: {len(underserved)}.")

        # Print the ranking
        self.log("\nZIP CODE PRICING (Most → Least Expensive):")
        self.log(f"{'─' * 70}")
        self.log(f"  {'Rank':<5} {'Zip':<7} {'Area':<22} {'Shops':<6} {'Avg':>8} {'Min':>8} {'Max':>8}")
        self.log(f"{'─' * 70}")
        for i, z in enumerate(zip_data, 1):
            marker = " *" if float(z["avg_price"]) > city_avg else ""
            self.log(f"  {i:<5} {z['zip_code']:<7} {(z['area_name'] or 'Unknown')[:20]:<22} "
                     f"{z['shop_count']:<6} ${z['avg_price']:>6} ${z['min_price']:>6} ${z['max_price']:>6}{marker}")
        self.log(f"{'─' * 70}")
        self.log(f"  City average: ${city_avg:.2f}   (* = above city avg)")

        return report


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
