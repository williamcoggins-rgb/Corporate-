"""Tier 3 — Competitor Scorecard Bot + Neighborhood Ranker

Calculates aggregates: average cut price by neighborhood, review
sentiment index, social engagement rank, "hotness" score (blend of
recent reviews + social buzz). Ranks shops by momentum.

Cadence: Post-load (nightly)
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class Scorecard(BaseAgent):
    name = "scorecard"
    description = "Generates competitor scorecards and neighborhood rankings"
    tier = 3

    def generate_scorecard(self, competitor_id):
        """Build a full scorecard for one competitor."""
        con = get_connection()

        card = {"competitor_id": competitor_id}

        # Basic info
        row = con.execute(
            "SELECT company_name, industry, hq_location, status FROM competitors WHERE competitor_id = ?",
            [competitor_id]
        ).fetchone()
        if not row:
            con.close()
            return None
        card["company_name"] = row[0]
        card["location"] = row[2]
        card["status"] = row[3]

        # Average pricing (latest per service)
        prices = con.execute("""
            SELECT service_name, price FROM price_history
            WHERE competitor_id = ?
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY service_name ORDER BY recorded_at DESC
            ) = 1
        """, [competitor_id]).fetchall()
        card["services"] = {p[0]: float(p[1]) for p in prices}
        card["avg_service_price"] = round(sum(card["services"].values()) / len(card["services"]), 2) if card["services"] else None

        # Review stats
        review_row = con.execute("""
            SELECT COUNT(*) as total_reviews,
                   ROUND(AVG(rating), 2) as avg_rating,
                   ROUND(AVG(sentiment_score), 2) as avg_sentiment
            FROM review_snapshots
            WHERE competitor_id = ?
        """, [competitor_id]).fetchone()
        card["total_reviews"] = review_row[0]
        card["avg_rating"] = float(review_row[1]) if review_row[1] else None
        card["avg_sentiment"] = float(review_row[2]) if review_row[2] else None

        # Social stats (latest)
        socials = con.execute("""
            SELECT platform, followers, engagement_rate
            FROM competitor_social
            WHERE competitor_id = ?
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY platform ORDER BY snapshot_date DESC
            ) = 1
        """, [competitor_id]).fetchall()
        card["social"] = {s[0]: {"followers": s[1], "engagement": float(s[2]) if s[2] else None} for s in socials}
        card["total_followers"] = sum(s[1] for s in socials if s[1])

        # Barber count
        barber_row = con.execute(
            "SELECT COUNT(*) FROM barbers WHERE competitor_id = ? AND status = 'Active'",
            [competitor_id]
        ).fetchone()
        card["active_barbers"] = barber_row[0]

        # Recent moves
        moves_row = con.execute("""
            SELECT COUNT(*) FROM competitor_moves
            WHERE competitor_id = ?
              AND move_date >= CURRENT_DATE - INTERVAL '90' DAY
        """, [competitor_id]).fetchone()
        card["recent_moves_90d"] = moves_row[0]

        # Latest threat score
        threat_row = con.execute("""
            SELECT score FROM competitor_scores
            WHERE competitor_id = ? AND score_type = 'threat_level'
            ORDER BY scored_at DESC LIMIT 1
        """, [competitor_id]).fetchone()
        card["threat_level"] = float(threat_row[0]) if threat_row else None

        # Calculate hotness score (0-100)
        hotness = 0
        if card["avg_rating"]:
            hotness += card["avg_rating"] * 10  # max 50
        if card["total_followers"]:
            hotness += min(20, card["total_followers"] / 5000 * 20)  # max 20
        if card["avg_sentiment"]:
            hotness += (card["avg_sentiment"] + 1) * 15  # max 30
        card["hotness_score"] = round(min(100, hotness), 1)

        # Store hotness score
        sid = con.execute("SELECT nextval('seq_score')").fetchone()[0]
        con.execute(
            """INSERT INTO competitor_scores (id, competitor_id, score_type, score, components)
               VALUES (?, ?, 'hotness', ?, ?)""",
            [sid, competitor_id, card["hotness_score"], json.dumps(card, default=str)],
        )
        con.close()
        self.records_processed += 1
        return card

    def rank_by_neighborhood(self):
        """Rank competitors grouped by neighborhood/area."""
        con = get_connection()
        rows = con.execute("""
            WITH latest_social AS (
                SELECT competitor_id, SUM(followers) as total_followers
                FROM (
                    SELECT competitor_id, platform, followers,
                           ROW_NUMBER() OVER (PARTITION BY competitor_id, platform ORDER BY snapshot_date DESC) as rn
                    FROM competitor_social
                )
                WHERE rn = 1
                GROUP BY competitor_id
            ),
            latest_scores AS (
                SELECT competitor_id, score
                FROM (
                    SELECT competitor_id, score,
                           ROW_NUMBER() OVER (PARTITION BY competitor_id ORDER BY scored_at DESC) as rn
                    FROM competitor_scores
                    WHERE score_type = 'hotness'
                )
                WHERE rn = 1
            )
            SELECT c.company_name, c.hq_location,
                   COALESCE(ROUND(AVG(r.rating), 2), 0) as avg_rating,
                   COALESCE(ls.total_followers, 0) as total_followers,
                   COUNT(DISTINCT b.barber_id) as barber_count,
                   COALESCE(sc.score, 0) as hotness
            FROM competitors c
            LEFT JOIN review_snapshots r ON r.competitor_id = c.competitor_id
            LEFT JOIN latest_social ls ON ls.competitor_id = c.competitor_id
            LEFT JOIN barbers b ON b.competitor_id = c.competitor_id AND b.status = 'Active'
            LEFT JOIN latest_scores sc ON sc.competitor_id = c.competitor_id
            WHERE c.status = 'Active'
            GROUP BY c.company_name, c.hq_location, ls.total_followers, sc.score
            ORDER BY c.hq_location, hotness DESC
        """).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def get_leaderboard(self, score_type="hotness", limit=10):
        """Top competitors by any score type."""
        con = get_connection()
        rows = con.execute("""
            SELECT c.company_name, cs.score, cs.scored_at
            FROM competitor_scores cs
            JOIN competitors c ON c.competitor_id = cs.competitor_id
            WHERE cs.score_type = ?
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY cs.competitor_id ORDER BY cs.scored_at DESC
            ) = 1
            ORDER BY cs.score DESC
            LIMIT ?
        """, [score_type, limit]).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def price_comparison_by_area(self, service_name="Fade"):
        """Average price for a service across neighborhoods."""
        con = get_connection()
        rows = con.execute("""
            WITH latest_prices AS (
                SELECT ph.competitor_id, ph.service_name, ph.price,
                       ROW_NUMBER() OVER (
                           PARTITION BY ph.competitor_id, ph.service_name
                           ORDER BY ph.recorded_at DESC
                       ) as rn
                FROM price_history ph
                WHERE ph.service_name ILIKE ?
            )
            SELECT c.hq_location as area,
                   COUNT(DISTINCT c.competitor_id) as shops,
                   ROUND(AVG(lp.price), 2) as avg_price,
                   ROUND(MIN(lp.price), 2) as min_price,
                   ROUND(MAX(lp.price), 2) as max_price
            FROM latest_prices lp
            JOIN competitors c ON c.competitor_id = lp.competitor_id
            WHERE lp.rn = 1
            GROUP BY c.hq_location
            ORDER BY avg_price ASC
        """, [f"%{service_name}%"]).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def execute(self):
        self.log("Generating scorecards for all active competitors...")
        con = get_connection()
        competitors = con.execute(
            "SELECT competitor_id, company_name FROM competitors WHERE status = 'Active'"
        ).fetchall()
        con.close()

        for cid, name in competitors:
            card = self.generate_scorecard(cid)
            if card:
                self.log(f"  {name}: hotness={card['hotness_score']}, "
                         f"rating={card['avg_rating']}, followers={card['total_followers']}")

        self.log("\nNeighborhood rankings:")
        rankings = self.rank_by_neighborhood()
        for r in rankings:
            self.log(f"  {r['hq_location'] or 'Unknown'}: {r['company_name']} "
                     f"(hotness: {r['hotness']}, rating: {r['avg_rating']})")
