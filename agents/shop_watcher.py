"""Tier 1 — Shop Status & Expansion Watcher Bot

Scans for hours changes, new locations, remodel photos, hiring posts,
or closures. Maps proximity — warns if a hot shop opens near your
neighborhood or expands aggressively.

Cadence: Weekly + on triggers
Sources: Google Business, websites, social, job boards
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class ShopWatcher(BaseAgent):
    name = "shop_watcher"
    description = "Monitors shop openings, closures, expansions, and status changes"
    tier = 1

    def __init__(self, your_zip=None, alert_radius_miles=3, **kwargs):
        super().__init__(**kwargs)
        self.your_zip = your_zip
        self.alert_radius_miles = alert_radius_miles

    def record_status_change(self, competitor_id, change_type, description,
                              source_url=None, impact_rating=None):
        """Record a shop status change as a competitor move.

        change_type: 'New Location', 'Closure', 'Remodel', 'Hours Change',
                     'Ownership Change', 'Rebrand', 'Expansion'
        """
        con = get_connection()
        mid = con.execute("SELECT nextval('seq_move')").fetchone()[0]
        con.execute(
            """INSERT INTO competitor_moves
               (move_id, competitor_id, move_date, move_type, description,
                source_url, impact_rating)
               VALUES (?, ?, CURRENT_DATE, ?, ?, ?, ?)""",
            [mid, competitor_id, change_type, description, source_url, impact_rating],
        )
        con.close()
        self.records_processed += 1

        # Determine severity
        high_impact_types = {"New Location", "Closure", "Expansion", "Ownership Change"}
        severity = "warning" if change_type in high_impact_types else "info"

        self.create_alert(
            alert_type="shop_status_change",
            title=f"{change_type}: {description[:80]}",
            detail=description,
            severity=severity,
            competitor_id=competitor_id,
            data_json=json.dumps({"change_type": change_type, "source": source_url}),
        )
        return mid

    def record_new_competitor(self, company_name, zip_code=None, neighborhood=None,
                               shop_type=None, source_url=None, **kwargs):
        """Discovered a new competitor — add them and alert."""
        from warehouse.competitors import add_competitor

        notes = f"Discovered by shop_watcher."
        if neighborhood:
            notes += f" Neighborhood: {neighborhood}."
        if shop_type:
            notes += f" Type: {shop_type}."

        cid = add_competitor(
            company_name,
            industry="Barber",
            hq_location=f"{neighborhood or ''}, Charlotte, NC {zip_code or ''}".strip(", "),
            business_model=shop_type,
            notes=notes,
            **kwargs,
        )
        self.records_processed += 1

        severity = "warning"
        if self.your_zip and zip_code == self.your_zip:
            severity = "critical"

        self.create_alert(
            alert_type="new_competitor",
            title=f"New competitor discovered: {company_name}",
            detail=f"Location: {neighborhood or 'Unknown'}, ZIP {zip_code or 'Unknown'}",
            severity=severity,
            competitor_id=cid,
            data_json=json.dumps({
                "zip_code": zip_code,
                "neighborhood": neighborhood,
                "source": source_url,
            }),
        )
        return cid

    def check_proximity(self, competitor_id, competitor_zip):
        """Check if a competitor is in or near your zip code."""
        if not self.your_zip:
            return False
        # Simple zip-code match for now — can be enhanced with geocoding
        if competitor_zip == self.your_zip:
            con = get_connection()
            row = con.execute(
                "SELECT company_name FROM competitors WHERE competitor_id = ?",
                [competitor_id]
            ).fetchone()
            con.close()
            name = row[0] if row else f"Competitor {competitor_id}"
            self.create_alert(
                alert_type="proximity_warning",
                title=f"{name} is in your zip code ({self.your_zip})",
                severity="critical",
                competitor_id=competitor_id,
            )
            return True
        return False

    def execute(self):
        self.log("Shop Watcher ready. Use record_status_change() and record_new_competitor().")
        if self.your_zip:
            self.log(f"Monitoring proximity to ZIP {self.your_zip}")
