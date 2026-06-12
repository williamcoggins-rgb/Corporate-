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

    def _get_or_create_competitor(self, name):
        """Find an existing competitor by name or create a new record."""
        con = get_connection()
        row = con.execute(
            "SELECT competitor_id FROM competitors WHERE company_name ILIKE ?",
            [f"%{name}%"],
        ).fetchone()
        if row:
            con.close()
            return row[0]
        cid = con.execute("SELECT nextval('seq_competitor')").fetchone()[0]
        con.execute(
            """INSERT INTO competitors
               (competitor_id, company_name, industry, business_model)
               VALUES (?, ?, 'Barbershop', 'Service')""",
            [cid, name],
        )
        con.close()
        self.log(f"Created competitor record: {name} (ID: {cid})")
        return cid

    def execute(self):
        """Collect platform profiles via managed agent web search."""
        from managed_agent import run_agent_task

        con = get_connection()
        before_profiles = con.execute("SELECT COUNT(*) FROM platform_profiles").fetchone()[0]
        before_solo = con.execute("SELECT COUNT(*) FROM platform_solo_barbers").fetchone()[0]
        con.close()

        zips_str = ", ".join(TARGET_ZIPS[:10])
        result = run_agent_task(
            "You are running a focused booking platform scan for Charlotte NC "
            "barbershops. Search Booksy, StyleSeat, and Vagaro for barber "
            f"profiles in these zip codes: {zips_str}. "
            "Record what you find using record_platform_presence with a "
            "profiles array (each entry: competitor_name, platform, rating, "
            "review_count, profile_url, accepts_online_booking) and a "
            "solo_barbers array (each entry: barber_name, platform, zip_code, "
            "rating, review_count, profile_url). Target at least 5 profiles. "
            "Only record data you actually found — never fabricate."
        )

        if "error" in result:
            self.log(f"Collection session unavailable: {result['error']}")
            return

        con = get_connection()
        after_profiles = con.execute("SELECT COUNT(*) FROM platform_profiles").fetchone()[0]
        after_solo = con.execute("SELECT COUNT(*) FROM platform_solo_barbers").fetchone()[0]
        con.close()

        new_profiles = after_profiles - before_profiles
        new_solo = after_solo - before_solo
        self.records_processed = new_profiles + new_solo
        self.log(f"Collected {new_profiles} platform profiles + {new_solo} solo barbers via web search")
