"""Tier 1 — Booking Platform Scout

Tracks competitor and solo barber presence across five booking platforms:
Booksy, Vagaro, StyleSeat, The Cut App, and Squire.

Monitors: profile existence, ratings, review counts, pricing visibility,
online booking status, and profile completeness.

Flags solo barbers in target zip codes who are direct competitors.

Cadence: Weekly
Sources: Booksy, Vagaro, StyleSeat, The Cut App, Squire
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


TRACKED_PLATFORMS = ["Booksy", "Vagaro", "StyleSeat", "TheCut", "Squire"]

# Target zip codes — same as warehouse competitor coverage
TARGET_ZIPS = [
    "28202", "28203", "28204", "28205", "28206", "28208",
    "28210", "28211", "28212", "28213", "28214", "28215",
    "28216", "28262", "28270", "28273", "28278", "28027", "28078",
]


class PlatformScout(BaseAgent):
    name = "platform_scout"
    description = "Tracks competitor presence across Booksy, Vagaro, StyleSeat, TheCut, Squire"
    tier = 1

    def record_platform_profile(self, competitor_id, platform, rating=None,
                                 review_count=0, profile_url=None,
                                 is_verified=False, accepts_online_booking=True,
                                 payment_methods=None, profile_completeness=None,
                                 last_active=None, notes=None):
        """Record a competitor's presence on a booking platform."""
        con = get_connection()
        pid = con.execute("SELECT nextval('seq_platform_profile')").fetchone()[0]
        con.execute(
            """INSERT INTO platform_profiles
               (id, competitor_id, platform, profile_url, rating, review_count,
                is_verified, accepts_online_booking, payment_methods,
                profile_completeness, last_active, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [pid, competitor_id, platform, profile_url, rating, review_count,
             is_verified, accepts_online_booking, payment_methods,
             profile_completeness, last_active, notes],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Platform profile: {platform} for competitor {competitor_id}")

    def record_solo_barber(self, barber_name, platform, zip_code, neighborhood=None,
                           rating=None, review_count=0, profile_url=None,
                           years_experience=None, specialties=None, price_range=None,
                           fade_price=None, haircut_price=None, beard_price=None,
                           combo_price=None, accepts_walkins=False, chair_rental=False,
                           instagram_handle=None, ownership_type=None,
                           primary_clientele=None, notes=None):
        """Record a solo barber found on a platform in target zip codes."""
        con = get_connection()
        sid = con.execute("SELECT nextval('seq_platform_solo')").fetchone()[0]
        con.execute(
            """INSERT INTO platform_solo_barbers
               (id, barber_name, platform, profile_url, zip_code, neighborhood,
                rating, review_count, years_experience, specialties, price_range,
                fade_price, haircut_price, beard_price, combo_price,
                accepts_walkins, chair_rental, instagram_handle,
                ownership_type, primary_clientele, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)""",
            [sid, barber_name, platform, profile_url, zip_code, neighborhood,
             rating, review_count, years_experience, specialties, price_range,
             fade_price, haircut_price, beard_price, combo_price,
             accepts_walkins, chair_rental, instagram_handle,
             ownership_type, primary_clientele, notes],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Solo barber: {barber_name} on {platform} in {zip_code}")

        # Alert if solo barber is in a weak coverage zip
        weak_zips = self._get_weak_zips()
        if zip_code in weak_zips:
            self.create_alert(
                alert_type="solo_barber_weak_zone",
                title=f"Solo barber {barber_name} found in underserved {zip_code}",
                detail=f"Platform: {platform}. Rating: {rating}. "
                       f"This zip has low competitor density.",
                severity="warning",
                data_json=json.dumps({
                    "barber": barber_name,
                    "platform": platform,
                    "zip_code": zip_code,
                    "rating": float(rating) if rating else None,
                }),
            )

    def _get_weak_zips(self):
        """Find zip codes with 1 or fewer competitors."""
        con = get_connection()
        rows = con.execute("""
            SELECT zip_code, COUNT(*) as cnt
            FROM competitors WHERE status = 'Active'
            GROUP BY zip_code HAVING cnt <= 1
        """).fetchall()
        con.close()
        return {r[0] for r in rows}

    def get_platform_coverage(self):
        """Show which competitors are on which platforms."""
        con = get_connection()
        rows = con.execute("""
            SELECT c.company_name, pp.platform, pp.rating, pp.review_count,
                   pp.accepts_online_booking, pp.profile_completeness
            FROM platform_profiles pp
            JOIN competitors c ON c.competitor_id = pp.competitor_id
            ORDER BY c.company_name, pp.platform
        """).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def get_solo_barbers_by_zip(self, zip_code=None):
        """List solo barbers, optionally filtered by zip."""
        con = get_connection()
        query = "SELECT * FROM platform_solo_barbers WHERE status = 'Active'"
        params = []
        if zip_code:
            query += " AND zip_code = ?"
            params.append(zip_code)
        query += " ORDER BY rating DESC NULLS LAST"
        rows = con.execute(query, params).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def get_platform_gaps(self):
        """Find competitors with NO platform presence."""
        con = get_connection()
        rows = con.execute("""
            SELECT c.company_name, c.zip_code, c.neighborhood
            FROM competitors c
            WHERE c.status = 'Active'
              AND c.competitor_id NOT IN (
                  SELECT DISTINCT competitor_id FROM platform_profiles
              )
            ORDER BY c.company_name
        """).fetchall()
        con.close()
        return rows

    def execute(self):
        """Main scout run — override with actual data collection logic."""
        self.log("Platform Scout ready.")
        self.log(f"Tracking {len(TRACKED_PLATFORMS)} platforms: {', '.join(TRACKED_PLATFORMS)}")
        self.log(f"Monitoring {len(TARGET_ZIPS)} target zip codes")
        weak = self._get_weak_zips()
        if weak:
            self.log(f"Weak coverage zips (<=1 shop): {', '.join(sorted(weak))}")

        # ── Booksy scrape ──────────────────────────────────────────
        try:
                        from agents.booksy_scraper import BookSyScraper
                        booksy = BookSyScraper()
                        results = booksy.run()
                        for biz in results.get("solo_barbers", []):
                                            self.record_solo_barber(
                                                                    barber_name=biz.get("name", "Unknown"),
                                                                    platform="Booksy",
                                                                    zip_code=biz.get("zip_code", ""),
                                                                    neighborhood=biz.get("neighborhood"),
                                                                    rating=biz.get("rating"),
                                                                    review_count=biz.get("review_count", 0),
                                                                    profile_url=biz.get("profile_url"),
                                                                    specialties=biz.get("specialties"),
                                                                    price_range=biz.get("price_range"),
                                                                    instagram_handle=biz.get("instagram_handle"),
                                                                    notes=biz.get("notes"),
                                            )
                                        for biz in results.get("competitors", []):
                                                            cid = self._get_or_create_competitor(biz.get("name", "Unknown"))
                                                            self.record_platform_profile(
                                                                                    competitor_id=cid,
                                                                                    platform="Booksy",
                                                                                    rating=biz.get("rating"),
                                                                                    review_count=biz.get("review_count", 0),
                                                                                    profile_url=biz.get("profile_url"),
                                                                                    accepts_online_booking=True,
                                                            )
                                                        self.log(f"Booksy scrape complete: {len(results.get('solo_barbers', []))} solo barbers, {len(results.get('competitors', []))} shops")
except Exception as e:
            self.log(f"Booksy scrape failed: {e}", level="error")
