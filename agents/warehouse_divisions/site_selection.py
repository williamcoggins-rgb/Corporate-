"""Division 7 — Site Selection Intelligence

Layers client geography + competitor density + competitor weakness scores
to rank potential shop locations by data, not gut feel.

Scout       — Collects property listings, lease rates, foot traffic, and demographic data
Researcher  — Cross-references locations against client heat map and competitor vulnerability
Analyst     — Produces location scores and ranked site recommendations
Auditor     — Validates location data completeness and flags missing coverage areas
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class SiteSelectionScout(BaseAgent):
    name = "site_selection_scout"
    description = "Collects commercial listings, lease rates, and location attributes"
    tier = 1

    def execute(self):
        self.log("Ready to ingest commercial property and location data.")

    def ingest_property(self, address, zip_code, sqft, monthly_rent,
                         lease_type=None, parking_spaces=None, foot_traffic_score=None,
                         visibility_score=None, notes=None):
        """Record a potential shop location."""
        con = get_connection()
        con.execute(
            """INSERT INTO site_candidates
               (address, zip_code, sqft, monthly_rent, lease_type,
                parking_spaces, foot_traffic_score, visibility_score, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [address, zip_code, sqft, monthly_rent, lease_type,
             parking_spaces, foot_traffic_score, visibility_score, notes],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Property: {address} ({sqft} sqft, ${monthly_rent}/mo)")

    def ingest_zip_demographics(self, zip_code, population, median_income,
                                  pct_male, pct_age_18_45, pct_black):
        """Record demographic data for a zip code."""
        con = get_connection()
        con.execute(
            """INSERT INTO zip_demographics
               (zip_code, population, median_income, pct_male, pct_age_18_45, pct_black)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [zip_code, population, median_income, pct_male, pct_age_18_45, pct_black],
        )
        con.close()
        self.records_processed += 1


class SiteSelectionResearcher(BaseAgent):
    name = "site_selection_researcher"
    description = "Analyzes location fit against client geography and competition"
    tier = 2

    def execute(self):
        self.log("Analyzing site candidates against client and competitor data...")

    def client_proximity_analysis(self):
        """How close each candidate site is to your existing client base."""
        con = get_connection()
        rows = con.execute("""
            WITH client_zips AS (
                SELECT zip_code, COUNT(*) as clients FROM client_origins GROUP BY zip_code
            )
            SELECT sc.address, sc.zip_code, sc.monthly_rent,
                   COALESCE(cz.clients, 0) as clients_in_zip,
                   (SELECT SUM(clients) FROM client_zips) as total_clients,
                   ROUND(COALESCE(cz.clients, 0) * 100.0 /
                         NULLIF((SELECT SUM(clients) FROM client_zips), 0), 1) as pct_clients_in_zip
            FROM site_candidates sc
            LEFT JOIN client_zips cz ON cz.zip_code = sc.zip_code
            ORDER BY clients_in_zip DESC
        """).fetchall()
        con.close()
        return rows

    def competitor_landscape_by_site(self):
        """Competitor density and threat level around each candidate site."""
        con = get_connection()
        rows = con.execute("""
            SELECT sc.address, sc.zip_code, sc.monthly_rent,
                   COUNT(DISTINCT c.competitor_id) as nearby_competitors,
                   ROUND(AVG(cs.score), 1) as avg_competitor_threat,
                   MIN(cs.score) as weakest_competitor,
                   MAX(cs.score) as strongest_competitor
            FROM site_candidates sc
            LEFT JOIN competitors c ON c.hq_zip = sc.zip_code AND c.status = 'Active'
            LEFT JOIN competitor_scores cs ON cs.competitor_id = c.competitor_id
                AND cs.score_type = 'threat_level'
            GROUP BY sc.address, sc.zip_code, sc.monthly_rent
            ORDER BY avg_competitor_threat ASC
        """).fetchall()
        con.close()
        return rows

    def demographic_fit(self):
        """Score each site's demographics against your target client profile."""
        con = get_connection()
        rows = con.execute("""
            SELECT sc.address, sc.zip_code,
                   zd.population, zd.median_income, zd.pct_male, zd.pct_age_18_45, zd.pct_black
            FROM site_candidates sc
            LEFT JOIN zip_demographics zd ON zd.zip_code = sc.zip_code
            ORDER BY zd.population DESC
        """).fetchall()
        con.close()
        return rows


class SiteSelectionAnalyst(BaseAgent):
    name = "site_selection_analyst"
    description = "Produces ranked site recommendations with composite scores"
    tier = 3

    def execute(self):
        self.log("Scoring and ranking site candidates...")
        rankings = self.rank_sites()
        for i, site in enumerate(rankings[:5], 1):
            self.log(f"  #{i}: {site['address']} (score: {site['composite_score']})")

    def rank_sites(self):
        """Score each site on a 0-100 composite: clients + demographics + competition + economics."""
        con = get_connection()
        sites = con.execute("""
            SELECT sc.address, sc.zip_code, sc.sqft, sc.monthly_rent,
                   sc.parking_spaces, sc.foot_traffic_score, sc.visibility_score
            FROM site_candidates sc
        """).fetchall()

        scored = []
        for site in sites:
            address, zip_code, sqft, rent, parking, foot_traffic, visibility = site

            # Client proximity score (0-25)
            client_count = con.execute(
                "SELECT COUNT(*) FROM client_origins WHERE zip_code = ?", [zip_code]
            ).fetchone()[0]
            client_score = min(25, client_count * 2.5)

            # Competitor weakness score (0-25): fewer + weaker = better
            comp_data = con.execute("""
                SELECT COUNT(*) as cnt, COALESCE(AVG(cs.score), 10) as avg_threat
                FROM competitors c
                LEFT JOIN competitor_scores cs ON cs.competitor_id = c.competitor_id
                    AND cs.score_type = 'threat_level'
                WHERE c.hq_zip = ? AND c.status = 'Active'
            """, [zip_code]).fetchone()
            comp_count, avg_threat = comp_data
            comp_score = max(0, 25 - (comp_count * 3) - (avg_threat * 1.5))

            # Demographics score (0-25)
            demo = con.execute(
                "SELECT population, median_income, pct_male, pct_age_18_45, pct_black FROM zip_demographics WHERE zip_code = ?",
                [zip_code]
            ).fetchone()
            if demo:
                pop, income, male, age, black = demo
                demo_score = min(25, (
                    min(8, (pop or 0) / 5000) +
                    min(7, (income or 0) / 10000) +
                    min(5, (male or 0) / 10) +
                    min(5, (age or 0) / 10)
                ))
            else:
                demo_score = 0

            # Economics score (0-25): reasonable rent relative to sqft
            rent_per_sqft = rent / sqft if sqft and rent else 0
            foot = foot_traffic or 0
            vis = visibility or 0
            econ_score = min(25, max(0, 15 - rent_per_sqft * 5) + foot / 2 + vis / 2 + min(5, (parking or 0)))

            composite = round(client_score + comp_score + demo_score + econ_score, 1)
            scored.append({
                "address": address,
                "zip_code": zip_code,
                "sqft": sqft,
                "monthly_rent": float(rent) if rent else None,
                "client_score": round(client_score, 1),
                "competition_score": round(comp_score, 1),
                "demographics_score": round(demo_score, 1),
                "economics_score": round(econ_score, 1),
                "composite_score": composite,
            })

        con.close()
        scored.sort(key=lambda x: x["composite_score"], reverse=True)
        return scored


class SiteSelectionAuditor(BaseAgent):
    name = "site_selection_auditor"
    description = "Validates location data and flags coverage gaps"
    tier = 4

    def execute(self):
        self.log("Auditing site selection data...")
        issues = self.audit()
        for issue in issues:
            self.create_alert(
                alert_type="data_quality",
                title=issue["title"],
                detail=issue["detail"],
                severity=issue["severity"],
            )

    def audit(self):
        """Check site selection data for gaps and reliability."""
        issues = []
        con = get_connection()

        # Check for sites without demographic data
        no_demo = con.execute("""
            SELECT sc.address, sc.zip_code FROM site_candidates sc
            LEFT JOIN zip_demographics zd ON zd.zip_code = sc.zip_code
            WHERE zd.zip_code IS NULL
        """).fetchall()
        if no_demo:
            issues.append({
                "title": f"{len(no_demo)} candidate sites missing demographic data",
                "detail": f"Sites without demographics: {', '.join(r[0] for r in no_demo[:3])}",
                "severity": "warning",
            })

        # Check for sites without competitor coverage in their zip
        no_intel = con.execute("""
            SELECT sc.address, sc.zip_code FROM site_candidates sc
            WHERE NOT EXISTS (
                SELECT 1 FROM competitors c WHERE c.hq_zip = sc.zip_code AND c.status = 'Active'
            )
        """).fetchall()
        if no_intel:
            issues.append({
                "title": f"{len(no_intel)} candidate sites have no competitor intel for their zip",
                "detail": "Cannot score competition without competitor data in the area",
                "severity": "warning",
            })

        # Check for missing location attributes
        incomplete = con.execute("""
            SELECT COUNT(*) FROM site_candidates
            WHERE foot_traffic_score IS NULL OR visibility_score IS NULL OR parking_spaces IS NULL
        """).fetchone()[0]
        if incomplete > 0:
            issues.append({
                "title": f"{incomplete} sites missing foot traffic, visibility, or parking data",
                "detail": "Visit sites in person to fill in observational scores",
                "severity": "info",
            })

        # Check minimum candidates
        total = con.execute("SELECT COUNT(*) FROM site_candidates").fetchone()[0]
        if total < 5:
            issues.append({
                "title": f"Only {total} site candidates evaluated",
                "detail": "Recommend evaluating 5+ locations for meaningful comparison",
                "severity": "info",
            })

        con.close()
        return issues
