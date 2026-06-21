"""CRUD operations for Phase One market intelligence tables."""

import json
from warehouse.db import get_connection


def insert_weekly_snapshot(competitor_id, snapshot_week, avg_price=None,
                           rating=None, review_count=None, follower_count=None,
                           barber_count=None, price_delta=None, rating_delta=None,
                           review_delta=None, follower_delta=None,
                           barber_delta=None, narrative=None):
    con = get_connection()
    sid = con.execute("SELECT nextval('seq_weekly_snapshot')").fetchone()[0]
    con.execute("""
        INSERT INTO weekly_competitor_snapshots
            (snapshot_id, competitor_id, snapshot_week, avg_price, rating,
             review_count, follower_count, barber_count, price_delta,
             rating_delta, review_delta, follower_delta, barber_delta, narrative)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [sid, competitor_id, snapshot_week, avg_price, rating, review_count,
          follower_count, barber_count, price_delta, rating_delta, review_delta,
          follower_delta, barber_delta, narrative])
    con.close()
    return sid


def get_prior_snapshot(competitor_id, before_date):
    con = get_connection()
    row = con.execute("""
        SELECT avg_price, rating, review_count, follower_count, barber_count
        FROM weekly_competitor_snapshots
        WHERE competitor_id = ? AND snapshot_week < ?
        ORDER BY snapshot_week DESC LIMIT 1
    """, [competitor_id, before_date]).fetchone()
    con.close()
    if not row:
        return None
    return {
        "avg_price": row[0], "rating": row[1], "review_count": row[2],
        "follower_count": row[3], "barber_count": row[4],
    }


def insert_market_summary(period_type, period_start, period_end,
                           neighborhood=None, competitor_count=None,
                           avg_market_price=None, median_market_price=None,
                           avg_rating=None, total_reviews=None,
                           new_shops=None, closed_shops=None,
                           price_range_low=None, price_range_high=None,
                           narrative=None):
    con = get_connection()
    sid = con.execute("SELECT nextval('seq_market_summary')").fetchone()[0]
    con.execute("""
        INSERT INTO market_period_summaries
            (summary_id, period_type, period_start, period_end, neighborhood,
             competitor_count, avg_market_price, median_market_price,
             avg_rating, total_reviews, new_shops, closed_shops,
             price_range_low, price_range_high, narrative)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [sid, period_type, period_start, period_end, neighborhood,
          competitor_count, avg_market_price, median_market_price,
          avg_rating, total_reviews, new_shops, closed_shops,
          price_range_low, price_range_high, narrative])
    con.close()
    return sid


def insert_trend(competitor_id, trend_type, detected_date, metric_name=None,
                  metric_value=None, metric_prior=None, severity="info",
                  narrative=None):
    con = get_connection()
    tid = con.execute("SELECT nextval('seq_competitor_trend')").fetchone()[0]
    con.execute("""
        INSERT INTO competitor_trends
            (trend_id, competitor_id, trend_type, detected_date, metric_name,
             metric_value, metric_prior, severity, narrative)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [tid, competitor_id, trend_type, detected_date, metric_name,
          metric_value, metric_prior, severity, narrative])
    con.close()
    return tid


def insert_pricing_recommendation(recommendation_date, service_name,
                                    your_current_price, market_avg_price,
                                    market_median_price, recommended_action,
                                    confidence="medium", competitor_context=None,
                                    narrative=None):
    con = get_connection()
    rid = con.execute("SELECT nextval('seq_pricing_rec')").fetchone()[0]
    ctx = json.dumps(competitor_context) if isinstance(competitor_context, (list, dict)) else competitor_context
    con.execute("""
        INSERT INTO pricing_recommendations
            (recommendation_id, recommendation_date, service_name,
             your_current_price, market_avg_price, market_median_price,
             recommended_action, confidence, competitor_context, narrative)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [rid, recommendation_date, service_name, your_current_price,
          market_avg_price, market_median_price, recommended_action,
          confidence, ctx, narrative])
    con.close()
    return rid


def get_latest_snapshots(competitor_id, limit=4):
    con = get_connection()
    cursor = con.execute("""
        SELECT * FROM weekly_competitor_snapshots
        WHERE competitor_id = ?
        ORDER BY snapshot_week DESC LIMIT ?
    """, [competitor_id, limit])
    cols = [d[0] for d in cursor.description]
    rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
    con.close()
    return rows


def get_latest_recommendations(limit=10):
    con = get_connection()
    cursor = con.execute("""
        SELECT * FROM pricing_recommendations
        ORDER BY recommendation_date DESC, service_name
        LIMIT ?
    """, [limit])
    cols = [d[0] for d in cursor.description]
    rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
    con.close()
    return rows
