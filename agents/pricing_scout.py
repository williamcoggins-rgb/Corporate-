"""Tier 1 — Pricing & Services Scout Bot

Pulls haircut prices (regular cut, fade, skin fade, beard trim, hot shave,
line-up), package deals, add-ons, and membership info from public sources.

Flags undercut moves (e.g., competitor drops fade below your rate) and
new premium tiers ($60+ with extras).

Cadence: Daily (heavy on weekends/Mondays)
Sources: Google Business, Booksy, Vagaro, shop websites
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


# Standard barber services to track
TRACKED_SERVICES = [
    "Regular Haircut",
    "Fade",
    "Skin Fade",
    "Taper Fade",
    "Drop Fade",
    "Burst Fade",
    "Beard Trim",
    "Beard Sculpting",
    "Hot Towel Shave",
    "Straight Razor Shave",
    "Line-Up / Edge-Up",
    "Haircut + Beard Combo",
    "Kids Haircut",
    "Senior Haircut",
    "Scalp Treatment",
    "Hair Design / Part",
    "Shampoo & Condition",
]


class PricingScout(BaseAgent):
    name = "pricing_scout"
    description = "Pulls and tracks competitor service pricing"
    tier = 1

    def __init__(self, your_prices=None, **kwargs):
        super().__init__(**kwargs)
        # Your own prices for comparison (service_name -> price)
        self.your_prices = your_prices or {}

    def record_price(self, competitor_id, service_name, price, source=None):
        """Record a price observation for a competitor's service."""
        con = get_connection()
        pid = con.execute("SELECT nextval('seq_price_history')").fetchone()[0]
        con.execute(
            """INSERT INTO price_history (id, competitor_id, service_name, price, source)
               VALUES (?, ?, ?, ?, ?)""",
            [pid, competitor_id, service_name, price, source],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Recorded: {service_name} @ ${price:.2f} for competitor {competitor_id}")

        # Check for undercuts
        if service_name in self.your_prices:
            my_price = self.your_prices[service_name]
            if price < my_price:
                diff = my_price - price
                pct = (diff / my_price) * 100
                self.create_alert(
                    alert_type="price_undercut",
                    title=f"Undercut on {service_name}: ${price:.2f} vs your ${my_price:.2f}",
                    detail=f"Competitor {competitor_id} is ${diff:.2f} cheaper ({pct:.0f}% less)",
                    severity="warning" if pct > 10 else "info",
                    competitor_id=competitor_id,
                    data_json=json.dumps({
                        "service": service_name,
                        "their_price": float(price),
                        "your_price": float(my_price),
                        "difference": float(diff),
                        "pct_lower": round(pct, 1),
                    }),
                )

        # Flag premium tiers
        if price >= 60:
            self.create_alert(
                alert_type="premium_service",
                title=f"Premium tier: {service_name} @ ${price:.2f}",
                detail=f"Competitor {competitor_id} offering premium-priced service",
                severity="info",
                competitor_id=competitor_id,
            )

    def bulk_record_prices(self, competitor_id, prices_dict, source=None):
        """Record multiple prices at once. prices_dict = {service_name: price}"""
        for service, price in prices_dict.items():
            if price is not None:
                self.record_price(competitor_id, service, price, source)

    def get_price_history(self, competitor_id=None, service_name=None, days=90):
        """Query price history with optional filters."""
        con = get_connection()
        query = """
            SELECT ph.*, c.company_name
            FROM price_history ph
            JOIN competitors c ON c.competitor_id = ph.competitor_id
            WHERE ph.recorded_at >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY
        """.format(days=days)
        params = []
        if competitor_id:
            query += " AND ph.competitor_id = ?"
            params.append(competitor_id)
        if service_name:
            query += " AND ph.service_name ILIKE ?"
            params.append(f"%{service_name}%")
        query += " ORDER BY ph.recorded_at DESC"
        columns = None
        rows = con.execute(query, params).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def compare_fade_prices(self):
        """Quick comparison of fade pricing across all competitors."""
        con = get_connection()
        rows = con.execute("""
            SELECT c.company_name, ph.service_name, ph.price, ph.recorded_at
            FROM price_history ph
            JOIN competitors c ON c.competitor_id = ph.competitor_id
            WHERE ph.service_name ILIKE '%fade%'
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY ph.competitor_id, ph.service_name
                ORDER BY ph.recorded_at DESC
            ) = 1
            ORDER BY ph.price ASC
        """).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def execute(self):
        """Main scout run — override with actual data collection logic."""
        self.log("Pricing Scout ready. Use record_price() or bulk_record_prices() to feed data.")
        self.log(f"Tracking {len(TRACKED_SERVICES)} standard services")
        if self.your_prices:
            self.log(f"Monitoring undercuts against {len(self.your_prices)} of your prices")
