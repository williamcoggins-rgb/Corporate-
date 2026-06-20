"""Tier 3 — Weekly Snapshotter

Snapshots every active competitor's current state (price, rating, reviews,
followers, barber count) into weekly_competitor_snapshots. Computes
week-over-week deltas from the prior snapshot. Writes an Option C
narrative per competitor.

Cadence: Sunday 11:30 PM ET
"""

import datetime
from agents.base import BaseAgent
from warehouse.db import get_connection
from warehouse.snapshots import insert_weekly_snapshot, get_prior_snapshot, insert_trend


class WeeklySnapshotter(BaseAgent):
    name = "weekly_snapshotter"
    description = "Snapshots each competitor weekly with plain-English narrative"
    tier = 3

    def _current_metrics(self, competitor_id):
        con = get_connection()

        price_row = con.execute("""
            WITH latest AS (
                SELECT price FROM price_history
                WHERE competitor_id = ?
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY service_name ORDER BY recorded_at DESC
                ) = 1
            )
            SELECT ROUND(AVG(price), 2) FROM latest
        """, [competitor_id]).fetchone()
        avg_price = float(price_row[0]) if price_row and price_row[0] else None

        review_row = con.execute("""
            SELECT ROUND(AVG(rating), 2), COUNT(*)
            FROM review_snapshots WHERE competitor_id = ?
        """, [competitor_id]).fetchone()
        rating = float(review_row[0]) if review_row and review_row[0] else None
        review_count = review_row[1] if review_row else 0

        social_row = con.execute("""
            SELECT SUM(followers) FROM (
                SELECT followers FROM competitor_social
                WHERE competitor_id = ?
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY platform ORDER BY snapshot_date DESC
                ) = 1
            )
        """, [competitor_id]).fetchone()
        follower_count = social_row[0] if social_row and social_row[0] else 0

        barber_row = con.execute(
            "SELECT COUNT(*) FROM barbers WHERE competitor_id = ? AND status = 'Active'",
            [competitor_id]
        ).fetchone()
        barber_count = barber_row[0] if barber_row else 0

        con.close()
        return {
            "avg_price": avg_price,
            "rating": rating,
            "review_count": review_count,
            "follower_count": follower_count,
            "barber_count": barber_count,
        }

    def _build_narrative(self, name, metrics, deltas):
        parts = []

        if metrics["avg_price"] is not None:
            if deltas.get("price_delta") and deltas["price_delta"] != 0:
                direction = "up" if deltas["price_delta"] > 0 else "down"
                parts.append(
                    f"Average service price is ${metrics['avg_price']:.0f}, "
                    f"{direction} ${abs(deltas['price_delta']):.0f} from last week"
                )
            else:
                parts.append(f"Average service price held steady at ${metrics['avg_price']:.0f}")

        if metrics["rating"] is not None:
            if deltas.get("review_delta") and deltas["review_delta"] > 0:
                parts.append(
                    f"Rating {metrics['rating']:.1f}/5 across {metrics['review_count']} reviews "
                    f"({deltas['review_delta']} new)"
                )
            else:
                parts.append(f"Rating {metrics['rating']:.1f}/5 across {metrics['review_count']} reviews")

        if metrics["follower_count"]:
            if deltas.get("follower_delta") and deltas["follower_delta"] != 0:
                direction = "gained" if deltas["follower_delta"] > 0 else "lost"
                parts.append(
                    f"{metrics['follower_count']:,} followers "
                    f"({direction} {abs(deltas['follower_delta']):,})"
                )
            else:
                parts.append(f"{metrics['follower_count']:,} followers, no change")

        if metrics["barber_count"]:
            if deltas.get("barber_delta") and deltas["barber_delta"] != 0:
                direction = "added" if deltas["barber_delta"] > 0 else "lost"
                parts.append(
                    f"{metrics['barber_count']} active barber(s) "
                    f"({direction} {abs(deltas['barber_delta'])})"
                )
            else:
                parts.append(f"{metrics['barber_count']} active barber(s)")

        if not parts:
            return f"{name}: No data available yet. Agents are still gathering details."

        return f"{name}: " + ". ".join(parts) + "."

    def _detect_trends(self, competitor_id, name, metrics, deltas, snapshot_week):
        if deltas.get("price_delta") and abs(deltas["price_delta"]) >= 3:
            direction = "increase" if deltas["price_delta"] > 0 else "decrease"
            severity = "watch" if abs(deltas["price_delta"]) >= 5 else "info"
            insert_trend(
                competitor_id, "price_movement", snapshot_week,
                metric_name="avg_price",
                metric_value=metrics["avg_price"],
                metric_prior=metrics["avg_price"] - deltas["price_delta"],
                severity=severity,
                narrative=(
                    f"{name} moved average price {direction} by "
                    f"${abs(deltas['price_delta']):.0f} to ${metrics['avg_price']:.0f}."
                ),
            )

        if deltas.get("barber_delta") and deltas["barber_delta"] >= 2:
            insert_trend(
                competitor_id, "growth", snapshot_week,
                metric_name="barber_count",
                metric_value=metrics["barber_count"],
                metric_prior=metrics["barber_count"] - deltas["barber_delta"],
                severity="watch",
                narrative=(
                    f"{name} added {deltas['barber_delta']} barbers this week, "
                    f"now at {metrics['barber_count']} total. Expansion signal."
                ),
            )

        if deltas.get("follower_delta") and deltas["follower_delta"] >= 500:
            insert_trend(
                competitor_id, "growth", snapshot_week,
                metric_name="follower_count",
                metric_value=metrics["follower_count"],
                metric_prior=metrics["follower_count"] - deltas["follower_delta"],
                severity="info",
                narrative=(
                    f"{name} gained {deltas['follower_delta']:,} followers this week "
                    f"(now {metrics['follower_count']:,}). Social momentum building."
                ),
            )

    def execute(self):
        snapshot_week = datetime.date.today()
        # Snap to most recent Sunday
        snapshot_week -= datetime.timedelta(days=snapshot_week.weekday() + 1)
        if snapshot_week > datetime.date.today():
            snapshot_week -= datetime.timedelta(days=7)

        self.log(f"Snapshotting competitors for week of {snapshot_week}")

        con = get_connection()
        competitors = con.execute(
            "SELECT competitor_id, company_name FROM competitors WHERE status = 'Active'"
        ).fetchall()
        con.close()

        for cid, name in competitors:
            metrics = self._current_metrics(cid)
            prior = get_prior_snapshot(cid, snapshot_week)

            deltas = {}
            if prior:
                if metrics["avg_price"] is not None and prior["avg_price"] is not None:
                    deltas["price_delta"] = round(metrics["avg_price"] - prior["avg_price"], 2)
                if metrics["rating"] is not None and prior["rating"] is not None:
                    deltas["rating_delta"] = round(metrics["rating"] - prior["rating"], 2)
                if prior["review_count"] is not None:
                    deltas["review_delta"] = metrics["review_count"] - prior["review_count"]
                if prior["follower_count"] is not None:
                    deltas["follower_delta"] = metrics["follower_count"] - prior["follower_count"]
                if prior["barber_count"] is not None:
                    deltas["barber_delta"] = metrics["barber_count"] - prior["barber_count"]

            narrative = self._build_narrative(name, metrics, deltas)

            try:
                insert_weekly_snapshot(
                    competitor_id=cid,
                    snapshot_week=snapshot_week,
                    avg_price=metrics["avg_price"],
                    rating=metrics["rating"],
                    review_count=metrics["review_count"],
                    follower_count=metrics["follower_count"],
                    barber_count=metrics["barber_count"],
                    price_delta=deltas.get("price_delta"),
                    rating_delta=deltas.get("rating_delta"),
                    review_delta=deltas.get("review_delta"),
                    follower_delta=deltas.get("follower_delta"),
                    barber_delta=deltas.get("barber_delta"),
                    narrative=narrative,
                )
                self.records_processed += 1
                self.log(f"  {name}: {narrative[:80]}...")
            except Exception as e:
                if "Constraint Error" in str(e) or "UNIQUE" in str(e).upper():
                    self.log(f"  {name}: Already snapshotted for {snapshot_week}, skipping")
                else:
                    raise

            self._detect_trends(cid, name, metrics, deltas, snapshot_week)

        self.log(f"Snapshotted {self.records_processed} competitors for week of {snapshot_week}")
