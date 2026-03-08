"""Tier 2 — Platform Intelligence Analyzer

Transforms raw platform data into competitive insights:
- Platform adoption rates across competitors
- Solo barber density per zip code per platform
- Price comparison: solo barbers vs established shops
- Platform gap scoring (who's missing where)
- Solo barber threat assessment

Cadence: Weekly (after Platform Scout)
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class PlatformAnalyzer(BaseAgent):
    name = "platform_analyzer"
    description = "Analyzes booking platform presence and solo barber competition"
    tier = 2

    def _platform_adoption_rates(self):
        """Calculate what % of competitors are on each platform."""
        con = get_connection()
        total = con.execute(
            "SELECT COUNT(*) FROM competitors WHERE status = 'Active'"
        ).fetchone()[0]

        rates = con.execute("""
            SELECT pp.platform, COUNT(DISTINCT pp.competitor_id) as on_platform
            FROM platform_profiles pp
            JOIN competitors c ON c.competitor_id = pp.competitor_id
            WHERE c.status = 'Active'
            GROUP BY pp.platform
            ORDER BY on_platform DESC
        """).fetchall()
        con.close()

        results = []
        for platform, count in rates:
            pct = round((count / total) * 100, 1) if total > 0 else 0
            results.append({
                "platform": platform,
                "shops_on_platform": count,
                "total_shops": total,
                "adoption_pct": pct,
            })
            self.log(f"{platform}: {count}/{total} shops ({pct}%)")
        return results

    def _solo_density_by_zip(self):
        """Count solo barbers per zip code per platform."""
        con = get_connection()
        rows = con.execute("""
            SELECT zip_code, platform, COUNT(*) as solo_count,
                   ROUND(AVG(rating), 1) as avg_rating,
                   ROUND(AVG(fade_price), 2) as avg_fade_price
            FROM platform_solo_barbers
            WHERE status = 'Active'
            GROUP BY zip_code, platform
            ORDER BY solo_count DESC
        """).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        results = [dict(zip(columns, row)) for row in rows]
        for r in results:
            self.log(f"ZIP {r['zip_code']} / {r['platform']}: "
                     f"{r['solo_count']} solos, avg rating {r['avg_rating']}, "
                     f"avg fade ${r['avg_fade_price']}")
        return results

    def _price_comparison(self):
        """Compare solo barber prices vs established shop prices."""
        con = get_connection()

        # Established shop average fade price (latest per competitor)
        shop_avg = con.execute("""
            SELECT ROUND(AVG(price), 2) as avg_fade
            FROM (
                SELECT competitor_id, price
                FROM price_history
                WHERE service_name ILIKE '%fade%'
                  AND service_name NOT ILIKE '%skin%'
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY competitor_id, service_name
                    ORDER BY recorded_at DESC
                ) = 1
            )
        """).fetchone()[0]

        # Solo barber average fade price
        solo_avg = con.execute("""
            SELECT ROUND(AVG(fade_price), 2) as avg_fade
            FROM platform_solo_barbers
            WHERE fade_price IS NOT NULL AND status = 'Active'
        """).fetchone()[0]

        con.close()

        diff = float(shop_avg - solo_avg) if shop_avg and solo_avg else 0
        result = {
            "shop_avg_fade": float(shop_avg) if shop_avg else None,
            "solo_avg_fade": float(solo_avg) if solo_avg else None,
            "difference": diff,
            "solo_undercuts_by": diff if diff > 0 else 0,
        }
        self.log(f"Shops avg fade: ${result['shop_avg_fade']} | "
                 f"Solos avg fade: ${result['solo_avg_fade']} | "
                 f"Diff: ${diff:.2f}")
        return result

    def _platform_gap_score(self):
        """Score each competitor on platform coverage (0-100)."""
        con = get_connection()
        # Get all active competitors
        competitors = con.execute(
            "SELECT competitor_id, company_name FROM competitors WHERE status = 'Active'"
        ).fetchall()

        # Get platform counts per competitor
        coverage = con.execute("""
            SELECT competitor_id, COUNT(DISTINCT platform) as platform_count
            FROM platform_profiles
            GROUP BY competitor_id
        """).fetchall()
        coverage_map = {r[0]: r[1] for r in coverage}

        total_platforms = 5  # Booksy, Vagaro, StyleSeat, TheCut, Squire
        results = []
        for cid, name in competitors:
            count = coverage_map.get(cid, 0)
            score = round((count / total_platforms) * 100, 1)
            results.append({
                "competitor_id": cid,
                "company_name": name,
                "platforms_on": count,
                "total_platforms": total_platforms,
                "coverage_score": score,
            })

        # Store scores
        for r in results:
            sid = con.execute("SELECT nextval('seq_score')").fetchone()[0]
            con.execute(
                """INSERT INTO competitor_scores (id, competitor_id, score_type, score, components)
                   VALUES (?, ?, 'platform_coverage', ?, ?)""",
                [sid, r["competitor_id"], r["coverage_score"],
                 json.dumps({"platforms_on": r["platforms_on"]})],
            )
            self.records_processed += 1

        con.close()

        # Log the worst gaps
        no_platform = [r for r in results if r["platforms_on"] == 0]
        if no_platform:
            self.log(f"{len(no_platform)} competitors have ZERO platform presence")
            for r in no_platform[:5]:
                self.log(f"  - {r['company_name']}")

        return results

    def _solo_threat_assessment(self):
        """Identify the most threatening solo barbers."""
        con = get_connection()
        threats = con.execute("""
            SELECT barber_name, platform, zip_code, neighborhood,
                   rating, review_count, fade_price, specialties
            FROM platform_solo_barbers
            WHERE status = 'Active'
              AND rating >= 4.5
              AND review_count >= 20
            ORDER BY review_count DESC
        """).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()

        results = [dict(zip(columns, row)) for row in threats]
        for r in results:
            self.create_alert(
                alert_type="solo_barber_threat",
                title=f"High-rated solo: {r['barber_name']} ({r['platform']})",
                detail=f"ZIP {r['zip_code']}, {r['rating']} stars, "
                       f"{r['review_count']} reviews, fade ${r['fade_price']}",
                severity="warning" if r["review_count"] >= 50 else "info",
                data_json=json.dumps({
                    k: (float(v) if v is not None and not isinstance(v, str) else v)
                    for k, v in r.items()
                }),
            )
        return results

    def generate_platform_report(self):
        """Generate a full platform intelligence report."""
        report = {
            "adoption_rates": self._platform_adoption_rates(),
            "solo_density": self._solo_density_by_zip(),
            "price_comparison": self._price_comparison(),
            "gap_scores": self._platform_gap_score(),
            "solo_threats": self._solo_threat_assessment(),
        }
        return report

    def execute(self):
        """Run full platform analysis."""
        self.log("Starting platform intelligence analysis...")
        report = self.generate_platform_report()
        self.log(f"Analysis complete. "
                 f"{len(report['adoption_rates'])} platforms tracked, "
                 f"{len(report['solo_threats'])} solo threats identified.")
