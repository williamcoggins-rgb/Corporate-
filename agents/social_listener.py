"""Tier 1 — Social & Content Listener Bot

Monitors Instagram, TikTok, Facebook, X for competitor posts — new barber
hires, before/after fades, shop events, client shoutouts, style trends.
Tracks engagement (likes, comments, shares).

Alerts on viral content or promo drops.

Cadence: Hourly / real-time
Sources: Instagram, TikTok (public), Facebook, X
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


VIRAL_THRESHOLDS = {
    "Instagram": {"likes": 500, "comments": 50},
    "TikTok": {"likes": 5000, "comments": 100},
    "Facebook": {"likes": 200, "comments": 30},
    "X/Twitter": {"likes": 200, "retweets": 50},
}

PROMO_KEYWORDS = [
    "discount", "% off", "$ off", "free", "special", "deal", "promo",
    "first cut", "new client", "grand opening", "flash sale", "limited time",
    "book now", "walk-in special",
]


class SocialListener(BaseAgent):
    name = "social_listener"
    description = "Monitors competitor social media for intel signals"
    tier = 1

    def record_social_snapshot(self, competitor_id, platform, followers,
                               engagement_rate=None):
        """Record a social media metrics snapshot."""
        con = get_connection()
        sid = con.execute("SELECT nextval('seq_social')").fetchone()[0]
        con.execute(
            """INSERT INTO competitor_social
               (id, competitor_id, platform, followers, engagement_rate)
               VALUES (?, ?, ?, ?, ?)""",
            [sid, competitor_id, platform, followers, engagement_rate],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Social snapshot: {platform} — {followers:,} followers for competitor {competitor_id}")

    def analyze_post(self, competitor_id, platform, post_text, likes=0,
                     comments=0, shares=0, post_url=None, post_date=None):
        """Analyze a social post for intel signals."""
        text_lower = post_text.lower() if post_text else ""

        # Check for promo/deal signals
        promo_hits = [kw for kw in PROMO_KEYWORDS if kw in text_lower]
        if promo_hits:
            self.create_alert(
                alert_type="promo_detected",
                title=f"Promo detected on {platform}",
                detail=f"Keywords: {promo_hits}. Post: {post_text[:300]}",
                severity="warning",
                competitor_id=competitor_id,
                data_json=json.dumps({
                    "platform": platform,
                    "keywords": promo_hits,
                    "likes": likes,
                    "url": post_url,
                }),
            )

        # Check for viral content
        thresholds = VIRAL_THRESHOLDS.get(platform, {})
        is_viral = False
        if thresholds.get("likes") and likes >= thresholds["likes"]:
            is_viral = True
        if thresholds.get("comments") and comments >= thresholds["comments"]:
            is_viral = True

        if is_viral:
            self.create_alert(
                alert_type="viral_content",
                title=f"Viral post on {platform}: {likes:,} likes, {comments:,} comments",
                detail=f"Post: {post_text[:300]}",
                severity="warning",
                competitor_id=competitor_id,
                data_json=json.dumps({
                    "platform": platform,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "url": post_url,
                }),
            )

        # Check for hiring signals
        hire_keywords = ["hiring", "new barber", "join our team", "chair available",
                         "looking for", "welcome", "just joined"]
        hire_hits = [kw for kw in hire_keywords if kw in text_lower]
        if hire_hits:
            self.create_alert(
                alert_type="hiring_signal",
                title=f"Hiring/staffing signal on {platform}",
                detail=f"Keywords: {hire_hits}. Post: {post_text[:300]}",
                severity="info",
                competitor_id=competitor_id,
            )
            # Log as a competitor move
            con = get_connection()
            mid = con.execute("SELECT nextval('seq_move')").fetchone()[0]
            con.execute(
                """INSERT INTO competitor_moves
                   (move_id, competitor_id, move_date, move_type, description, source_url)
                   VALUES (?, ?, CURRENT_DATE, 'Hire', ?, ?)""",
                [mid, competitor_id, f"Hiring signal: {post_text[:200]}", post_url],
            )
            con.close()

        self.records_processed += 1
        return {
            "promo_detected": bool(promo_hits),
            "is_viral": is_viral,
            "hiring_signal": bool(hire_hits),
        }

    def get_follower_trends(self, competitor_id=None, days=90):
        """Get follower count trends over time."""
        con = get_connection()
        query = """
            SELECT c.company_name, s.platform, s.followers,
                   s.engagement_rate, s.snapshot_date
            FROM competitor_social s
            JOIN competitors c ON c.competitor_id = s.competitor_id
            WHERE s.snapshot_date >= CURRENT_DATE - INTERVAL '{days}' DAY
        """.format(days=days)
        params = []
        if competitor_id:
            query += " AND s.competitor_id = ?"
            params.append(competitor_id)
        query += " ORDER BY s.snapshot_date DESC"
        rows = con.execute(query, params).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def execute(self):
        self.log("Social Listener ready. Use record_social_snapshot() and analyze_post() to feed data.")
        self.log(f"Monitoring for promos ({len(PROMO_KEYWORDS)} keywords) and viral thresholds")
