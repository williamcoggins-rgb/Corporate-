"""Tier 3 — Market Pulse

Aggregates competitor data into neighborhood-level and market-wide summaries
for monthly and quarterly periods. Writes an Option C narrative per row.

Cadence: 1st of month 1:00 AM ET (also writes quarterly on quarter boundaries)
"""

import datetime
from agents.base import BaseAgent
from warehouse.db import get_connection
from warehouse.snapshots import insert_market_summary


QUARTER_ENDS = {3, 6, 9, 12}


class MarketPulse(BaseAgent):
    name = "market_pulse"
    description = "Generates monthly/quarterly market summaries with narrative"
    tier = 3

    def _gather_stats(self, period_start, period_end, neighborhood=None):
        con = get_connection()
        hood_filter = ""
        params = []
        if neighborhood:
            hood_filter = "AND c.neighborhood = ?"
            params.append(neighborhood)

        comp_row = con.execute(f"""
            SELECT COUNT(DISTINCT c.competitor_id)
            FROM competitors c
            WHERE c.status = 'Active' {hood_filter}
        """, params).fetchone()
        competitor_count = comp_row[0] if comp_row else 0

        price_params = list(params)
        price_row = con.execute(f"""
            WITH latest AS (
                SELECT ph.competitor_id, ph.price FROM price_history ph
                JOIN competitors c ON c.competitor_id = ph.competitor_id
                WHERE 1=1 {hood_filter}
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY ph.competitor_id, ph.service_name
                    ORDER BY ph.recorded_at DESC
                ) = 1
            )
            SELECT ROUND(AVG(price), 2),
                   ROUND(MEDIAN(price), 2),
                   ROUND(MIN(price), 2),
                   ROUND(MAX(price), 2)
            FROM latest
        """, price_params).fetchone()

        avg_price = float(price_row[0]) if price_row and price_row[0] else None
        median_price = float(price_row[1]) if price_row and price_row[1] else None
        price_low = float(price_row[2]) if price_row and price_row[2] else None
        price_high = float(price_row[3]) if price_row and price_row[3] else None

        review_params = [period_start, period_end] + list(params)
        review_row = con.execute(f"""
            SELECT ROUND(AVG(r.rating), 2), COUNT(*)
            FROM review_snapshots r
            JOIN competitors c ON c.competitor_id = r.competitor_id
            WHERE r.collected_at >= ? AND r.collected_at < ? {hood_filter}
        """, review_params).fetchone()
        avg_rating = float(review_row[0]) if review_row and review_row[0] else None
        total_reviews = review_row[1] if review_row else 0

        move_params = [period_start, period_end]
        new_params = move_params + list(params)
        new_row = con.execute(f"""
            SELECT COUNT(*) FROM competitor_moves m
            JOIN competitors c ON c.competitor_id = m.competitor_id
            WHERE m.move_type = 'New Location'
              AND m.move_date >= ? AND m.move_date < ? {hood_filter}
        """, new_params).fetchone()
        new_shops = new_row[0] if new_row else 0

        closed_params = move_params + list(params)
        closed_row = con.execute(f"""
            SELECT COUNT(*) FROM competitor_moves m
            JOIN competitors c ON c.competitor_id = m.competitor_id
            WHERE m.move_type = 'Closure'
              AND m.move_date >= ? AND m.move_date < ? {hood_filter}
        """, closed_params).fetchone()
        closed_shops = closed_row[0] if closed_row else 0

        con.close()
        return {
            "competitor_count": competitor_count,
            "avg_market_price": avg_price,
            "median_market_price": median_price,
            "avg_rating": avg_rating,
            "total_reviews": total_reviews,
            "new_shops": new_shops,
            "closed_shops": closed_shops,
            "price_range_low": price_low,
            "price_range_high": price_high,
        }

    def _build_narrative(self, period_type, period_start, period_end,
                          neighborhood, stats):
        scope = neighborhood if neighborhood else "Charlotte market"
        period_label = f"{period_start.strftime('%b %d')} to {period_end.strftime('%b %d, %Y')}"

        parts = []
        parts.append(
            f"{scope} {period_type} summary for {period_label}: "
            f"{stats['competitor_count']} active shops"
        )

        if stats["avg_market_price"] is not None:
            parts.append(
                f"Average service price ${stats['avg_market_price']:.0f}, "
                f"range ${stats['price_range_low']:.0f}-${stats['price_range_high']:.0f}"
            )

        if stats["avg_rating"] is not None:
            parts.append(
                f"Average rating {stats['avg_rating']:.1f}/5 "
                f"with {stats['total_reviews']} reviews collected this period"
            )

        movements = []
        if stats["new_shops"]:
            movements.append(f"{stats['new_shops']} new shop(s) opened")
        if stats["closed_shops"]:
            movements.append(f"{stats['closed_shops']} closure(s)")
        if movements:
            parts.append(". ".join(movements))
        else:
            parts.append("No shop openings or closures recorded")

        return ". ".join(parts) + "."

    def _get_neighborhoods(self):
        con = get_connection()
        rows = con.execute("""
            SELECT DISTINCT neighborhood FROM competitors
            WHERE status = 'Active' AND neighborhood IS NOT NULL
              AND TRIM(neighborhood) != ''
            ORDER BY neighborhood
        """).fetchall()
        con.close()
        return [r[0] for r in rows]

    def _write_summary(self, period_type, period_start, period_end, neighborhood=None):
        stats = self._gather_stats(period_start, period_end, neighborhood)
        narrative = self._build_narrative(
            period_type, period_start, period_end, neighborhood, stats
        )

        try:
            insert_market_summary(
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                neighborhood=neighborhood,
                narrative=narrative,
                **stats,
            )
            self.records_processed += 1
            label = neighborhood or "MARKET-WIDE"
            self.log(f"  [{period_type}] {label}: {stats['competitor_count']} shops, "
                     f"avg ${stats['avg_market_price'] or 0:.0f}")
        except Exception as e:
            if "Constraint Error" in str(e) or "UNIQUE" in str(e).upper():
                label = neighborhood or "MARKET-WIDE"
                self.log(f"  [{period_type}] {label}: Already summarized, skipping")
            else:
                raise

    def execute(self):
        today = datetime.date.today()

        month_start = today.replace(day=1)
        prev_month_end = month_start - datetime.timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        self.log(f"Generating monthly summary for {prev_month_start.strftime('%B %Y')}")

        self._write_summary("monthly", prev_month_start, prev_month_end)

        neighborhoods = self._get_neighborhoods()
        for hood in neighborhoods:
            self._write_summary("monthly", prev_month_start, prev_month_end, hood)

        if today.month in QUARTER_ENDS or (today.month - 1) in QUARTER_ENDS:
            q_month = today.month if today.month in QUARTER_ENDS else today.month - 1
            q_end_month = q_month
            q_start_month = q_end_month - 2

            q_start = today.replace(month=q_start_month, day=1)
            if q_end_month == 12:
                q_end = today.replace(year=today.year + 1, month=1, day=1) - datetime.timedelta(days=1)
            else:
                q_end = today.replace(month=q_end_month + 1, day=1) - datetime.timedelta(days=1)

            self.log(f"Quarter boundary detected — generating Q summary "
                     f"{q_start.strftime('%b')}–{q_end.strftime('%b %Y')}")

            self._write_summary("quarterly", q_start, q_end)
            for hood in neighborhoods:
                self._write_summary("quarterly", q_start, q_end, hood)

        self.log(f"Generated {self.records_processed} market summaries")
