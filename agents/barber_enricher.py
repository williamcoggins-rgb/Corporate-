"""Tier 2 — Barber-Level Enricher Bot

Tags individual barbers by name, specialties (fades, straight-razor
shaves, beard sculpting), client types. Builds a "talent map" — who's
the rising star drawing crowds?

Trigger: When data available from social/reviews
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class BarberEnricher(BaseAgent):
    name = "barber_enricher"
    description = "Tracks individual barbers, their specialties, and reputation"
    tier = 2

    def add_barber(self, competitor_id, name, instagram_handle=None,
                   specialties=None, seniority=None, notes=None):
        """Register a barber at a specific shop."""
        con = get_connection()

        # Check if barber already exists at this shop
        existing = con.execute(
            """SELECT barber_id FROM barbers
               WHERE competitor_id = ? AND LOWER(name) = LOWER(?)""",
            [competitor_id, name],
        ).fetchone()

        if existing:
            bid = existing[0]
            # Update last_seen
            con.execute("UPDATE barbers SET last_seen = CURRENT_DATE WHERE barber_id = ?", [bid])
            con.close()
            self.log(f"Barber '{name}' already tracked (ID: {bid}), updated last_seen")
            return bid

        bid = con.execute("SELECT nextval('seq_barber')").fetchone()[0]
        con.execute(
            """INSERT INTO barbers
               (barber_id, competitor_id, name, instagram_handle,
                specialties, seniority, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [bid, competitor_id, name, instagram_handle,
             specialties, seniority, notes],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Added barber: {name} at competitor {competitor_id} (ID: {bid})")
        return bid

    def add_specialty(self, barber_id, specialty, skill_level=None, source=None):
        """Tag a barber with a specialty."""
        con = get_connection()
        # Avoid duplicates
        existing = con.execute(
            "SELECT id FROM barber_specialties WHERE barber_id = ? AND LOWER(specialty) = LOWER(?)",
            [barber_id, specialty],
        ).fetchone()
        if existing:
            con.close()
            return existing[0]

        sid = con.execute("SELECT nextval('seq_barber_spec')").fetchone()[0]
        con.execute(
            """INSERT INTO barber_specialties (id, barber_id, specialty, skill_level, source)
               VALUES (?, ?, ?, ?, ?)""",
            [sid, barber_id, specialty, skill_level, source],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Tagged barber {barber_id} with specialty: {specialty}")
        return sid

    def record_barber_move(self, barber_name, from_competitor_id, to_competitor_id=None,
                           move_type="departure", notes=None):
        """Track a barber moving between shops."""
        con = get_connection()

        # Mark as inactive at old shop
        con.execute(
            """UPDATE barbers SET status = 'Departed'
               WHERE competitor_id = ? AND LOWER(name) = LOWER(?)""",
            [from_competitor_id, barber_name],
        )

        # If we know where they went, add them there
        if to_competitor_id:
            self.add_barber(to_competitor_id, barber_name, notes=f"Moved from competitor {from_competitor_id}")

        # Log the move
        mid = con.execute("SELECT nextval('seq_move')").fetchone()[0]
        desc = f"Barber '{barber_name}' {move_type}"
        if to_competitor_id:
            desc += f" to competitor {to_competitor_id}"
        if notes:
            desc += f". {notes}"
        con.execute(
            """INSERT INTO competitor_moves
               (move_id, competitor_id, move_date, move_type, description, impact_rating)
               VALUES (?, ?, CURRENT_DATE, 'Talent Movement', ?, ?)""",
            [mid, from_competitor_id, desc, 4],
        )
        con.close()
        self.records_processed += 1

        self.create_alert(
            alert_type="talent_movement",
            title=f"Barber movement: {barber_name} ({move_type})",
            detail=desc,
            severity="warning",
            competitor_id=from_competitor_id,
            data_json=json.dumps({
                "barber": barber_name,
                "from": from_competitor_id,
                "to": to_competitor_id,
                "move_type": move_type,
            }),
        )

    def get_talent_map(self):
        """Full talent map — all tracked barbers with specialties."""
        con = get_connection()
        rows = con.execute("""
            SELECT c.company_name, b.name as barber_name, b.instagram_handle,
                   b.specialties, b.seniority, b.status, b.first_seen, b.last_seen,
                   GROUP_CONCAT(bs.specialty, ', ') as tagged_specialties
            FROM barbers b
            JOIN competitors c ON c.competitor_id = b.competitor_id
            LEFT JOIN barber_specialties bs ON bs.barber_id = b.barber_id
            GROUP BY ALL
            ORDER BY c.company_name, b.name
        """).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def get_rising_stars(self, days=60):
        """Find barbers with high review mentions or social engagement recently."""
        con = get_connection()
        rows = con.execute("""
            SELECT b.name, c.company_name, b.specialties,
                   COUNT(DISTINCT r.id) as review_mentions
            FROM barbers b
            JOIN competitors c ON c.competitor_id = b.competitor_id
            LEFT JOIN review_snapshots r ON r.competitor_id = b.competitor_id
                AND LOWER(r.review_text) LIKE '%' || LOWER(b.name) || '%'
                AND r.collected_at >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY
            GROUP BY b.name, c.company_name, b.specialties
            HAVING review_mentions > 0
            ORDER BY review_mentions DESC
        """.format(days=days)).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def execute(self):
        self.log("Barber Enricher ready.")
        talent_map = self.get_talent_map()
        self.log(f"Currently tracking {len(talent_map)} barbers across all shops")
