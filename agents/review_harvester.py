"""Tier 1 — Review & Vibe Harvester Bot

Grabs reviews from Google, Yelp, Facebook, Booksy. Pulls rating, text,
keywords ("clean fade", "long wait", "great conversation").

Tracks sentiment shifts — sudden complaints about no-shows or praise
for a new barber could signal talent poaching or internal changes.

Cadence: Every 4-8 hours
Sources: Google Reviews, Yelp, Facebook, Booksy
"""

import json
import re
from agents.base import BaseAgent
from warehouse.db import get_connection


# Keywords that signal important intel in reviews
POSITIVE_KEYWORDS = [
    "clean fade", "sharp", "best barber", "fire cut", "on point",
    "fresh", "crispy", "talented", "worth the wait", "always come back",
    "great conversation", "vibe", "atmosphere", "professional",
]

NEGATIVE_KEYWORDS = [
    "long wait", "no show", "rude", "rushed", "uneven", "overpriced",
    "dirty", "unprofessional", "never again", "walked out", "appointment",
    "late", "cancelled", "double booked",
]

TALENT_KEYWORDS = [
    "new barber", "left", "moved", "different shop", "followed",
    "used to go to", "switched from", "hired", "quit",
]


class ReviewHarvester(BaseAgent):
    name = "review_harvester"
    description = "Collects and analyzes competitor reviews for sentiment and signals"
    tier = 1

    def ingest_review(self, competitor_id, platform, rating, review_text,
                      reviewer_name=None, review_date=None):
        """Ingest a single review, score sentiment, extract keywords."""
        con = get_connection()
        rid = con.execute("SELECT nextval('seq_review')").fetchone()[0]

        # Simple keyword-based sentiment scoring
        text_lower = review_text.lower() if review_text else ""
        pos_hits = [kw for kw in POSITIVE_KEYWORDS if kw in text_lower]
        neg_hits = [kw for kw in NEGATIVE_KEYWORDS if kw in text_lower]
        talent_hits = [kw for kw in TALENT_KEYWORDS if kw in text_lower]

        # Sentiment: -1 to +1 scale, weighted by rating and keywords
        base_sentiment = (rating - 3) / 2 if rating else 0  # maps 1-5 to -1 to +1
        keyword_boost = (len(pos_hits) - len(neg_hits)) * 0.1
        sentiment_score = max(-1, min(1, base_sentiment + keyword_boost))

        all_keywords = pos_hits + neg_hits + talent_hits
        keywords_str = ", ".join(all_keywords) if all_keywords else None

        con.execute(
            """INSERT INTO review_snapshots
               (id, competitor_id, platform, rating, review_text, reviewer_name,
                review_date, sentiment_score, keywords)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [rid, competitor_id, platform, rating, review_text, reviewer_name,
             review_date, round(sentiment_score, 2), keywords_str],
        )
        con.close()
        self.records_processed += 1

        # Alert on talent movement signals
        if talent_hits:
            self.create_alert(
                alert_type="talent_signal",
                title=f"Talent movement signal in {platform} review",
                detail=f"Keywords found: {talent_hits}. Review: {review_text[:200]}",
                severity="warning",
                competitor_id=competitor_id,
                data_json=json.dumps({"keywords": talent_hits, "rating": rating}),
            )

        # Alert on very negative reviews (potential opportunity)
        if rating and rating <= 2 and neg_hits:
            self.create_alert(
                alert_type="competitor_weakness",
                title=f"Negative review ({rating}/5) on {platform}",
                detail=f"Issues: {neg_hits}. Review: {review_text[:200]}",
                severity="info",
                competitor_id=competitor_id,
            )

        return rid

    def bulk_ingest(self, competitor_id, reviews):
        """Ingest a list of reviews. Each review is a dict with keys:
        platform, rating, review_text, reviewer_name (opt), review_date (opt)
        """
        for r in reviews:
            self.ingest_review(
                competitor_id,
                r["platform"],
                r.get("rating"),
                r.get("review_text", ""),
                r.get("reviewer_name"),
                r.get("review_date"),
            )

    def get_sentiment_summary(self, competitor_id=None, days=30):
        """Get average sentiment by competitor over a time window."""
        con = get_connection()
        query = """
            SELECT c.company_name, r.platform,
                   COUNT(*) as review_count,
                   ROUND(AVG(r.rating), 1) as avg_rating,
                   ROUND(AVG(r.sentiment_score), 2) as avg_sentiment
            FROM review_snapshots r
            JOIN competitors c ON c.competitor_id = r.competitor_id
            WHERE r.collected_at >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY
        """.format(days=days)
        params = []
        if competitor_id:
            query += " AND r.competitor_id = ?"
            params.append(competitor_id)
        query += " GROUP BY c.company_name, r.platform ORDER BY avg_sentiment DESC"
        rows = con.execute(query, params).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()
        return [dict(zip(columns, row)) for row in rows]

    def detect_reputation_shift(self, competitor_id, window_hours=48, threshold=3):
        """Check if a competitor got a burst of negative reviews recently."""
        con = get_connection()
        rows = con.execute("""
            SELECT COUNT(*) as neg_count,
                   GROUP_CONCAT(keywords, '; ') as issues
            FROM review_snapshots
            WHERE competitor_id = ?
              AND rating <= 2
              AND collected_at >= CURRENT_TIMESTAMP - INTERVAL '{hrs}' HOUR
        """.format(hrs=window_hours), [competitor_id]).fetchall()
        con.close()

        if rows and rows[0][0] >= threshold:
            self.create_alert(
                alert_type="reputation_crisis",
                title=f"Reputation shift: {rows[0][0]} negative reviews in {window_hours}hrs",
                detail=f"Common issues: {rows[0][1]}",
                severity="critical",
                competitor_id=competitor_id,
            )
            return True
        return False

    def execute(self):
        self.log("Review Harvester ready. Use ingest_review() or bulk_ingest() to feed review data.")
        self.log(f"Tracking {len(POSITIVE_KEYWORDS)} positive, {len(NEGATIVE_KEYWORDS)} negative, "
                 f"{len(TALENT_KEYWORDS)} talent keywords")
