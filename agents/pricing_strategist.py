"""Tier 3 — Pricing Strategist

Analyzes your price positioning versus competitors per service. Detects
undercuts, premiums, and market shifts. Writes recommendations into
pricing_recommendations with an Option C narrative per row.

Cadence: Monday 12:00 AM ET (after Weekly Snapshotter)
"""

import json
import datetime
from agents.base import BaseAgent
from warehouse.db import get_connection
from warehouse.snapshots import insert_pricing_recommendation

YOUR_PRICES = {
    "Regular Haircut": 40,
    "Fade": 45,
    "Skin Fade": 55,
    "Beard Trim": 20,
    "Kids Haircut": 25,
    "Student Haircut": 25,
    "Haircut + Beard Combo": 65,
}


class PricingStrategist(BaseAgent):
    name = "pricing_strategist"
    description = "Analyzes price positioning and writes plain-English recommendations"
    tier = 3

    def _market_stats_for_service(self, service_name):
        con = get_connection()
        row = con.execute("""
            WITH latest AS (
                SELECT competitor_id, price FROM price_history
                WHERE service_name ILIKE ?
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY competitor_id ORDER BY recorded_at DESC
                ) = 1
            )
            SELECT ROUND(AVG(price), 2) as avg_p,
                   ROUND(MEDIAN(price), 2) as med_p,
                   ROUND(MIN(price), 2) as min_p,
                   ROUND(MAX(price), 2) as max_p,
                   COUNT(*) as shop_count
            FROM latest
        """, [f"%{service_name}%"]).fetchone()

        competitors = con.execute("""
            WITH latest AS (
                SELECT competitor_id, price FROM price_history
                WHERE service_name ILIKE ?
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY competitor_id ORDER BY recorded_at DESC
                ) = 1
            )
            SELECT c.company_name, l.price
            FROM latest l
            JOIN competitors c ON c.competitor_id = l.competitor_id
            ORDER BY l.price ASC
        """, [f"%{service_name}%"]).fetchall()
        con.close()

        if not row or not row[0]:
            return None

        return {
            "avg": float(row[0]),
            "median": float(row[1]),
            "min": float(row[2]),
            "max": float(row[3]),
            "shop_count": row[4],
            "competitors": [{"name": c[0], "price": float(c[1])} for c in competitors],
        }

    def _decide_action(self, your_price, stats):
        avg = stats["avg"]
        median = stats["median"]
        gap_pct = ((your_price - avg) / avg) * 100 if avg else 0

        cheaper_count = sum(1 for c in stats["competitors"] if c["price"] < your_price)
        total = len(stats["competitors"])
        percentile = (cheaper_count / total * 100) if total else 50

        if gap_pct < -10:
            return "raise", "high"
        elif gap_pct < -5:
            return "raise", "medium"
        elif gap_pct > 15:
            return "monitor", "medium"
        elif gap_pct > 10:
            return "hold", "high"
        elif abs(gap_pct) <= 5:
            return "hold", "high"
        else:
            return "hold", "medium"

    def _build_narrative(self, service, your_price, stats, action):
        avg = stats["avg"]
        median = stats["median"]
        gap = your_price - avg
        gap_dir = "above" if gap > 0 else "below"

        cheapest = stats["competitors"][0] if stats["competitors"] else None
        priciest = stats["competitors"][-1] if stats["competitors"] else None

        parts = []

        parts.append(
            f"Your {service} at ${your_price} sits ${abs(gap):.0f} {gap_dir} "
            f"the market average of ${avg:.0f} ({stats['shop_count']} shops reporting)"
        )

        if cheapest and priciest:
            parts.append(
                f"Range runs from ${cheapest['price']:.0f} ({cheapest['name']}) "
                f"to ${priciest['price']:.0f} ({priciest['name']})"
            )

        undercut_count = sum(1 for c in stats["competitors"] if c["price"] < your_price)
        if undercut_count > 0:
            undercutters = [c for c in stats["competitors"] if c["price"] < your_price]
            closest = max(undercutters, key=lambda c: c["price"])
            parts.append(
                f"{undercut_count} shop(s) undercut you, "
                f"closest is {closest['name']} at ${closest['price']:.0f}"
            )

        if action == "raise":
            parts.append(
                f"Recommendation: RAISE — you're leaving money on the table at ${your_price}"
            )
        elif action == "lower":
            parts.append(
                f"Recommendation: LOWER — you're priced out of the competitive range"
            )
        elif action == "monitor":
            parts.append(
                f"Recommendation: MONITOR — your premium is large enough to watch for client sensitivity"
            )
        else:
            parts.append(
                f"Recommendation: HOLD — your pricing is well-positioned in this market"
            )

        return ". ".join(parts) + "."

    def execute(self):
        today = datetime.date.today()
        self.log(f"Analyzing pricing position as of {today}")

        for service, your_price in YOUR_PRICES.items():
            stats = self._market_stats_for_service(service)
            if not stats or stats["shop_count"] == 0:
                self.log(f"  {service}: No market data yet, skipping")
                continue

            action, confidence = self._decide_action(your_price, stats)
            narrative = self._build_narrative(service, your_price, stats, action)

            context = [
                {"name": c["name"], "price": c["price"]}
                for c in stats["competitors"][:10]
            ]

            try:
                insert_pricing_recommendation(
                    recommendation_date=today,
                    service_name=service,
                    your_current_price=your_price,
                    market_avg_price=stats["avg"],
                    market_median_price=stats["median"],
                    recommended_action=action,
                    confidence=confidence,
                    competitor_context=context,
                    narrative=narrative,
                )
                self.records_processed += 1
                self.log(f"  {service}: {action.upper()} (confidence: {confidence}) — "
                         f"you=${your_price}, mkt avg=${stats['avg']:.0f}")
            except Exception as e:
                if "Constraint Error" in str(e) or "UNIQUE" in str(e).upper():
                    self.log(f"  {service}: Already analyzed for {today}, skipping")
                else:
                    raise

        self.log(f"Generated {self.records_processed} pricing recommendations")
