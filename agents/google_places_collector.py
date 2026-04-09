"""Google Places Collector — Live Data Feed

Pulls real pricing, ratings, and shop data from Google Places API
and injects it directly into the DuckDB warehouse.

Usage:
    from agents.google_places_collector import GooglePlacesCollector

    collector = GooglePlacesCollector(api_key=GOOGLE_PLACES_KEY)
    collector.sync_watchlist()
    collector.ingest_agent_output(json_str)
"""

import os
import json
import time
import requests
import logging
from datetime import date, datetime
from agents.base import BaseAgent
from warehouse.db import get_connection

log = logging.getLogger("google_places_collector")

GOOGLE_PLACES_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")

WATCHLIST = [
    {"name": "Goodfellas Barbershop", "address": "4005-B Sunset Road, Charlotte, NC 28216"},
    {"name": "No Grease Mosaic Village", "address": "1635 W Trade St, Charlotte, NC 28216"},
    {"name": "No Grease Northlake", "address": "6801 Northlake Mall Drive, Charlotte, NC 28216"},
    {"name": "Gordon's Historic Barbershop", "address": "601 Baldwin Ave, Charlotte, NC 28204"},
    {"name": "Da Lucky Spot Barbershop", "address": "3240 Wilkinson Blvd, Charlotte, NC 28208"},
    {"name": "The Man Cave Barbershop", "address": "926 Westmere Ave, Charlotte, NC 28208"},
    {"name": "Gillespie Barber & Stylist", "address": "2601 N Tryon St, Charlotte, NC 28206"},
    {"name": "Victory Cutz Barber Lounge", "address": "3110 West Blvd, Charlotte, NC 28208"},
    {"name": "Clipper Kingz Barbershop", "address": "4108 North Tryon St, Charlotte, NC 28206"},
    {"name": "Major League Barber Lounge", "address": "Charlotte, NC"},
    {"name": "Fade Factory", "address": "Charlotte, NC"},
    {"name": "Modern Classics Barbershop", "address": "Charlotte, NC"},
]


class GooglePlacesCollector(BaseAgent):

    name = "google_places_collector"
    description = "Syncs live Google Places data into the warehouse"
    tier = 1

    def __init__(self, api_key=None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or GOOGLE_PLACES_KEY
        self._place_cache = {}

    def _find_place(self, name, address):
        if not self.api_key:
            self.log("No Google Places API key set (GOOGLE_PLACES_API_KEY)")
            return None

        cache_key = f"{name}|{address}"
        if cache_key in self._place_cache:
            return self._place_cache[cache_key]

        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            "input": f"{name} {address}",
            "inputtype": "textquery",
            "fields": "place_id,name,formatted_address,rating,user_ratings_total",
            "key": self.api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                place = candidates[0]
                self._place_cache[cache_key] = place
                return place
        except Exception as e:
            self.log(f"Places API error for {name}: {e}")

        return None

    def _get_place_details(self, place_id):
        if not self.api_key:
            return None

        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": (
                "name,rating,user_ratings_total,reviews,formatted_address,"
                "formatted_phone_number,website,opening_hours,price_level"
            ),
            "key": self.api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            return data.get("result")
        except Exception as e:
            self.log(f"Place details error for {place_id}: {e}")
            return None

    def _get_or_create_competitor(self, name, address=None, zip_code=None,
                                  neighborhood=None, ownership_type=None):
        con = get_connection()
        row = con.execute(
            "SELECT competitor_id FROM competitors WHERE company_name ILIKE ?",
            [f"%{name}%"]
        ).fetchone()

        if row:
            con.close()
            return row[0]

        cid = con.execute("SELECT nextval('seq_competitor')").fetchone()[0]
        con.execute("""
            INSERT INTO competitors
            (competitor_id, company_name, industry, hq_location, zip_code,
             neighborhood, ownership_type, business_model)
            VALUES (?, ?, 'Barbershop', ?, ?, ?, ?, 'Service')
        """, [cid, name, address, zip_code, neighborhood,
              ownership_type or "Black-owned"])
        con.close()
        self.log(f"Created competitor record: {name} (ID: {cid})")
        return cid

    def sync_shop(self, shop_name, address):
        self.log(f"Syncing: {shop_name}")

        place = self._find_place(shop_name, address)
        if not place:
            self.log(f"  Could not find on Google Places: {shop_name}")
            return False

        place_id = place.get("place_id")
        if not place_id:
            return False

        details = self._get_place_details(place_id)
        if not details:
            return False

        addr = details.get("formatted_address", address)
        zip_code = None
        for part in addr.split(","):
            part = part.strip()
            if part.startswith("NC "):
                zip_code = part.split(" ")[-1]

        cid = self._get_or_create_competitor(
            shop_name, address=addr, zip_code=zip_code
        )

        rating = details.get("rating")
        review_count = details.get("user_ratings_total", 0)
        if rating:
            con = get_connection()
            sid = con.execute("SELECT nextval('seq_social')").fetchone()[0]
            con.execute("""
                INSERT INTO competitor_social
                (id, competitor_id, platform, followers, engagement_rate, snapshot_date)
                VALUES (?, ?, 'Google', ?, ?, ?)
            """, [sid, cid, review_count, round(rating / 5 * 100, 1), date.today()])
            con.close()
            self.log(f"  Rating: {rating}/5 ({review_count} reviews)")
            self.records_processed += 1

        reviews = details.get("reviews", [])
        for review in reviews[:5]:
            self._ingest_review(cid, review)

        con = get_connection()
        mid = con.execute("SELECT nextval('seq_move')").fetchone()[0]
        con.execute("""
            INSERT INTO competitor_moves
            (move_id, competitor_id, move_date, move_type, description, impact_rating)
            VALUES (?, ?, ?, 'data_sync', ?, 2)
        """, [mid, cid, date.today(),
              f"Google Places sync: {rating}/5 stars, {review_count} reviews"])
        con.close()

        self.log(f"  ✓ Synced {shop_name}: {rating}★, {review_count} reviews")
        return True

    def _ingest_review(self, competitor_id, review_data):
        text = review_data.get("text", "")
        rating = review_data.get("rating", 3)
        author = review_data.get("author_name", "Anonymous")
        review_time = review_data.get("time", 0)

        review_date = None
        if review_time:
            review_date = datetime.fromtimestamp(review_time).date()

        con = get_connection()
        exists = con.execute("""
            SELECT COUNT(*) FROM review_snapshots
            WHERE competitor_id = ? AND reviewer_name = ? AND platform = 'Google'
        """, [competitor_id, author]).fetchone()[0]

        if exists:
            con.close()
            return

        TALENT_KEYWORDS = ["new barber", "left", "moved", "different shop", "followed",
                           "switched from", "hired", "quit"]
        POSITIVE_KEYWORDS = ["clean fade", "sharp", "best barber", "fire cut", "on point",
                             "fresh", "crispy", "talented", "worth the wait", "great conversation"]
        NEGATIVE_KEYWORDS = ["long wait", "no show", "rude", "rushed", "uneven",
                             "overpriced", "dirty", "unprofessional", "never again"]

        text_lower = text.lower()
        pos_hits = [kw for kw in POSITIVE_KEYWORDS if kw in text_lower]
        neg_hits = [kw for kw in NEGATIVE_KEYWORDS if kw in text_lower]
        talent_hits = [kw for kw in TALENT_KEYWORDS if kw in text_lower]

        base_sentiment = (rating - 3) / 2
        keyword_boost = (len(pos_hits) - len(neg_hits)) * 0.1
        sentiment_score = max(-1, min(1, base_sentiment + keyword_boost))
        all_keywords = pos_hits + neg_hits + talent_hits

        rid = con.execute("SELECT nextval('seq_review')").fetchone()[0]
        con.execute("""
            INSERT INTO review_snapshots
            (id, competitor_id, platform, rating, review_text, reviewer_name,
             review_date, sentiment_score, keywords)
            VALUES (?, ?, 'Google', ?, ?, ?, ?, ?, ?)
        """, [rid, competitor_id, rating, text, author, review_date,
              round(sentiment_score, 2), ", ".join(all_keywords) or None])
        con.close()
        self.records_processed += 1

        if talent_hits:
            self.create_alert(
                alert_type="talent_signal",
                title=f"Talent movement signal in Google review",
                detail=f"Keywords: {talent_hits}. Review: {text[:200]}",
                severity="warning",
                competitor_id=competitor_id,
                data_json=json.dumps({"keywords": talent_hits, "review": text[:500]})
            )

    def sync_watchlist(self):
        self.log(f"Starting watchlist sync ({len(WATCHLIST)} shops)...")
        success = 0
        for shop in WATCHLIST:
            ok = self.sync_shop(shop["name"], shop["address"])
            if ok:
                success += 1
            time.sleep(0.5)
        self.log(f"Watchlist sync complete: {success}/{len(WATCHLIST)} shops synced")
        return success

    def ingest_agent_output(self, output_text):
        """Parse and ingest structured JSON output from a Managed Agent session."""
        json_blocks = []
        depth = 0
        start = -1
        for i, char in enumerate(output_text):
            if char == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    json_blocks.append(output_text[start:i+1])
                    start = -1

        ingested = 0
        for block in json_blocks:
            try:
                data = json.loads(block)
                agent_type = data.get("agent", "")

                if agent_type == "pricing_scout" or "services" in data:
                    self._ingest_pricing_data(data)
                    ingested += 1
                elif agent_type == "review_harvester" or "sentiment" in data:
                    self._ingest_review_data(data)
                    ingested += 1
                elif "alert_type" in data:
                    self._ingest_alert_data(data)
                    ingested += 1

            except (json.JSONDecodeError, KeyError):
                continue

        self.log(f"Ingested {ingested} structured records from agent output")
        return ingested

    def _ingest_pricing_data(self, data):
        competitor_name = data.get("competitor", "Unknown")
        zip_code = data.get("zip_code")
        services = data.get("services", {})
        source_url = data.get("source_url", "Managed Agent web search")

        if not services:
            return

        cid = self._get_or_create_competitor(competitor_name, zip_code=zip_code)

        con = get_connection()
        for service_name, price in services.items():
            if price and isinstance(price, (int, float)):
                pid = con.execute("SELECT nextval('seq_price_history')").fetchone()[0]
                con.execute("""
                    INSERT INTO price_history
                    (id, competitor_id, service_name, price, source)
                    VALUES (?, ?, ?, ?, ?)
                """, [pid, cid, service_name, float(price), source_url])
                self.records_processed += 1
        con.close()
        self.log(f"Ingested pricing for {competitor_name}: {len(services)} services")

    def _ingest_review_data(self, data):
        competitor_name = data.get("competitor", "Unknown")
        rating = data.get("rating")
        review_count = data.get("review_count", 0)

        if not rating:
            return

        cid = self._get_or_create_competitor(competitor_name)

        con = get_connection()
        sid = con.execute("SELECT nextval('seq_social')").fetchone()[0]
        con.execute("""
            INSERT INTO competitor_social
            (id, competitor_id, platform, followers, engagement_rate, snapshot_date)
            VALUES (?, ?, 'Google', ?, ?, ?)
        """, [sid, cid, review_count, round(rating / 5 * 100, 1), date.today()])
        con.close()
        self.records_processed += 1

    def _ingest_alert_data(self, data):
        alert_type = data.get("alert_type", "general")
        severity = data.get("severity", "info")
        competitor_name = data.get("competitor")
        detail = data.get("detail", "")
        action = data.get("recommended_action", "")

        competitor_id = None
        if competitor_name:
            con = get_connection()
            row = con.execute(
                "SELECT competitor_id FROM competitors WHERE company_name ILIKE ?",
                [f"%{competitor_name}%"]
            ).fetchone()
            con.close()
            competitor_id = row[0] if row else None

        self.create_alert(
            alert_type=alert_type,
            title=data.get("title", f"{alert_type} detected"),
            detail=f"{detail}\nRecommended: {action}",
            severity=severity,
            competitor_id=competitor_id,
            data_json=json.dumps(data)
        )

    def execute(self):
        if self.api_key:
            self.sync_watchlist()
        else:
            self.log("No Google Places API key — skipping live sync")
            self.log("Set GOOGLE_PLACES_API_KEY env variable to enable live data")
