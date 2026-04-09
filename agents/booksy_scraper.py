"""Booksy Scraper — API Interception via Playwright

Intercepts Booksy's internal API responses to collect barbershop and
solo barber listings for the Charlotte, NC market.

Strategy:
  Booksy loads business data via XHR to:
    /api/us/customer_api/businesses/search
    /api/us/customer_api/businesses/{id}
    /api/us/customer_api/businesses/{id}/staff_members
    /api/us/customer_api/businesses/{id}/services

  We navigate Booksy's search pages with Playwright, intercept those
  XHR responses in-flight, and capture the raw JSON before it hits
  the DOM. No HTML parsing. No brittle CSS selectors. Just clean API data.

Output:
  Structured records ready for direct insertion into:
    - platform_profiles     (shop-level: rating, reviews, booking status)
    - platform_solo_barbers (individual barbers: pricing, specialties)
    - competitors           (new shops not yet in warehouse)
    - price_history         (service pricing time-series)

Usage:
  # Run full Charlotte scrape
  python -m agents.booksy_scraper

  # Run for specific zip codes only
  python -m agents.booksy_scraper --zips 28208 28216 28206

  # Dry run — collect but don't write to warehouse
  python -m agents.booksy_scraper --dry-run

  # Single business by Booksy ID
  python -m agents.booksy_scraper --business-id 12345

  # As agent (called by runner)
  from agents.booksy_scraper import BookSyScraper
  scraper = BookSyScraper()
  scraper.run()

Requirements:
  pip install playwright
  playwright install chromium
"""

import sys
import json
import time
import asyncio
import logging
import argparse
import re
from datetime import date, datetime
from typing import Optional

from agents.base import BaseAgent
from warehouse.db import get_connection

log = logging.getLogger("booksy_scraper")

# ── CONSTANTS ──────────────────────────────────────────────────────────

BOOKSY_BASE = "https://booksy.com"

# Charlotte search coordinates (city center)
CHARLOTTE_LAT = 35.2271
CHARLOTTE_LNG = -80.8431

# All target zip codes — drives search grid
TARGET_ZIPS = [
    "28202", "28203", "28204", "28205", "28206",
    "28208", "28210", "28211", "28212", "28215",
    "28216", "28217", "28262", "28269",
]

# Zip → approximate lat/lng for grid searches
ZIP_COORDS = {
    "28202": (35.2271, -80.8431),   # Uptown
    "28203": (35.2148, -80.8617),   # South End
    "28204": (35.2196, -80.8280),   # Cherry
    "28205": (35.2359, -80.8085),   # Plaza Midwood / NoDa
    "28206": (35.2703, -80.8275),   # North Charlotte / N Tryon
    "28208": (35.2368, -80.8930),   # West Charlotte
    "28210": (35.1548, -80.8588),   # South Park (operator location)
    "28211": (35.1820, -80.8062),   # Myers Park / Cotswold
    "28212": (35.1949, -80.7696),   # East Charlotte / Albemarle Rd
    "28215": (35.2319, -80.7696),   # Eastway / Shamrock
    "28216": (35.3104, -80.8882),   # Beatties Ford / Northlake
    "28217": (35.1548, -80.9138),   # Steele Creek / Arrowood
    "28262": (35.3292, -80.7512),   # University City
    "28269": (35.3481, -80.8127),   # Mallard Creek / University
}

# Booksy API endpoints (intercepted)
API_PATTERNS = [
    "customer_api/businesses",
    "customer_api/v2/businesses",
    "/businesses/search",
    "/staff_members",
    "/services",
]

# Service name normalization map — Booksy names → warehouse standard names
SERVICE_NAME_MAP = {
    # Combos — MUST be before "haircut" and "beard" entries
    "haircut and beard": "Haircut + Beard Combo",
    "cut and beard": "Haircut + Beard Combo",
    "hair and beard": "Haircut + Beard Combo",
    "full service": "Haircut + Beard Combo",
    "haircut + beard": "Haircut + Beard Combo",
    "cut + beard": "Haircut + Beard Combo",
    # Skin fades — before "fade"
    "skin fade": "Skin Fade",
    "bald fade": "Skin Fade",
    "zero fade": "Skin Fade",
    # Other fades
    "taper fade": "Taper Fade",
    "drop fade": "Fade",
    "burst fade": "Fade",
    "high fade": "Fade",
    "mid fade": "Fade",
    "low fade": "Fade",
    "fade": "Fade",
    # Haircuts — after combo entries
    "men's haircut": "Regular Haircut",
    "men haircut": "Regular Haircut",
    "haircut": "Regular Haircut",
    "cut": "Regular Haircut",
    "shape up": "Regular Haircut",
    "shape-up": "Regular Haircut",
    # Kids — before generic "cut"
    "kids haircut": "Kids Haircut",
    "kid haircut": "Kids Haircut",
    "children": "Kids Haircut",
    "child haircut": "Kids Haircut",
    "boy haircut": "Kids Haircut",
    # Beard sculpting before beard trim
    "beard sculpting": "Beard Trim",
    "beard shaping": "Beard Trim",
    "beard shape": "Beard Trim",
    "beard line up": "Beard Trim",
    "beard trim": "Beard Trim",
    "beard": "Beard Trim",
    # Line-up
    "line up": "Line-Up / Edge-Up",
    "lineup": "Line-Up / Edge-Up",
    "line-up": "Line-Up / Edge-Up",
    "edge up": "Line-Up / Edge-Up",
    "edge-up": "Line-Up / Edge-Up",
    # Hot towel / shave
    "hot towel shave": "Hot Towel Shave",
    "straight razor shave": "Hot Towel Shave",
    "hot towel": "Hot Towel Shave",
    "straight razor": "Hot Towel Shave",
    "shave": "Hot Towel Shave",
    # Scalp
    "scalp treatment": "Scalp Treatment",
    "scalp massage": "Scalp Treatment",
}

# Known barber-related keywords to filter non-barber businesses
BARBER_KEYWORDS = [
    "barber", "barbershop", "barber shop", "fade", "haircut",
    "hair cut", "cuts", "grooming", "men's hair", "mens hair",
]


# ── DATA STRUCTURES ────────────────────────────────────────────────────

class BooksyBusiness:
    """Parsed Booksy business record."""

    def __init__(self):
        self.booksy_id: Optional[int] = None
        self.name: str = ""
        self.profile_url: str = ""
        self.rating: Optional[float] = None
        self.review_count: int = 0
        self.address: str = ""
        self.city: str = ""
        self.state: str = ""
        self.zip_code: str = ""
        self.neighborhood: str = ""
        self.lat: Optional[float] = None
        self.lng: Optional[float] = None
        self.phone: str = ""
        self.website: str = ""
        self.instagram: str = ""
        self.is_verified: bool = False
        self.accepts_walkins: bool = False
        self.accepts_online_booking: bool = True
        self.payment_methods: str = ""
        self.profile_completeness: str = ""
        self.last_active: Optional[date] = None
        self.about: str = ""
        self.business_type: str = ""
        # Staff
        self.staff: list = []
        # Services with pricing
        self.services: list = []
        # Raw for debugging
        self._raw: dict = {}

    def is_barber_shop(self) -> bool:
        """Heuristic: does this look like a barbershop?"""
        text = f"{self.name} {self.about} {self.business_type}".lower()
        return any(kw in text for kw in BARBER_KEYWORDS)

    def _get_price_for(self, keywords: list) -> Optional[float]:
        """Find price for the first service whose normalized name matches any keyword.
        Searches normalized_name (not raw name) to avoid false partial matches.
        """
        for svc in self.services:
            # Use normalized name for matching — it's already de-ambiguated
            normalized = svc.get("normalized_name", "").lower()
            raw = svc.get("name", "").lower()
            # Match on either normalized or raw
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in normalized or kw_lower in raw:
                    price = svc.get("price")
                    if price is not None:
                        return float(price)
        return None

    def get_fade_price(self) -> Optional[float]:
        return self._get_price_for_normalized(["Fade", "Taper Fade"])

    def get_haircut_price(self) -> Optional[float]:
        return self._get_price_for_normalized(["Regular Haircut"])

    def get_beard_price(self) -> Optional[float]:
        return self._get_price_for_normalized(["Beard Trim"])

    def get_combo_price(self) -> Optional[float]:
        return self._get_price_for_normalized(["Haircut + Beard Combo"])

    def _get_price_for_normalized(self, normalized_names: list) -> Optional[float]:
        """Find price by matching exactly on normalized_name."""
        for svc in self.services:
            if svc.get("normalized_name") in normalized_names:
                price = svc.get("price")
                if price is not None:
                    return float(price)
        return None

    def price_range(self) -> str:
        prices = [
            self.get_fade_price(),
            self.get_haircut_price(),
            self._get_price_for_normalized(['Skin Fade']),
        ]
        prices = [p for p in prices if p is not None]
        if not prices:
            return ""
        lo = min(prices)
        hi = max(prices)
        if lo == hi:
            return f"${lo:.0f}"
        return f"${lo:.0f}–${hi:.0f}"

    def to_dict(self) -> dict:
        return {
            "booksy_id": self.booksy_id,
            "name": self.name,
            "profile_url": self.profile_url,
            "rating": self.rating,
            "review_count": self.review_count,
            "address": self.address,
            "zip_code": self.zip_code,
            "neighborhood": self.neighborhood,
            "lat": self.lat,
            "lng": self.lng,
            "phone": self.phone,
            "website": self.website,
            "instagram": self.instagram,
            "is_verified": self.is_verified,
            "accepts_walkins": self.accepts_walkins,
            "payment_methods": self.payment_methods,
            "profile_completeness": self.profile_completeness,
            "about": self.about[:300] if self.about else "",
            "staff_count": len(self.staff),
            "service_count": len(self.services),
            "fade_price": self.get_fade_price(),
            "haircut_price": self.get_haircut_price(),
            "beard_price": self.get_beard_price(),
            "combo_price": self.get_combo_price(),
            "price_range": self.price_range(),
        }


class BooksyStaff:
    """Parsed individual barber/staff member."""

    def __init__(self):
        self.booksy_id: Optional[int] = None
        self.business_id: Optional[int] = None
        self.name: str = ""
        self.profile_url: str = ""
        self.rating: Optional[float] = None
        self.review_count: int = 0
        self.about: str = ""
        self.instagram: str = ""
        self.specialties: list = []
        self.services: list = []
        self._raw: dict = {}

    def get_fade_price(self) -> Optional[float]:
        for svc in self.services:
            if "fade" in svc.get("name", "").lower():
                p = svc.get("price")
                return float(p) if p is not None else None
        return None

    def get_haircut_price(self) -> Optional[float]:
        for svc in self.services:
            name = svc.get("name", "").lower()
            if any(k in name for k in ["haircut", "cut", "men"]):
                p = svc.get("price")
                return float(p) if p is not None else None
        return None


# ── PARSER ─────────────────────────────────────────────────────────────

class BooksyResponseParser:
    """Parses raw Booksy API JSON into BooksyBusiness / BooksyStaff objects."""

    @staticmethod
    def normalize_service_name(raw_name: str) -> str:
        """Map Booksy service name to warehouse standard.
        Matches longest key first to prevent partial matches
        (e.g. 'haircut' must not swallow 'kids haircut').
        """
        lower = raw_name.lower().strip()
        # Sort by key length descending — longest/most-specific match wins
        for key in sorted(SERVICE_NAME_MAP.keys(), key=len, reverse=True):
            if key in lower:
                return SERVICE_NAME_MAP[key]
        return raw_name.strip().title()

    @staticmethod
    def parse_price(raw) -> Optional[float]:
        """Parse price from various Booksy formats."""
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw) if raw > 0 else None
        if isinstance(raw, str):
            # "$35", "35.00", "from $25", "35", ""
            cleaned = re.sub(r"[^\d.]", "", raw.split("from")[-1])
            try:
                val = float(cleaned)
                return val if val > 0 else None
            except ValueError:
                return None
        return None

    @classmethod
    def parse_business_list(cls, data: dict) -> list:
        """Parse a /businesses/search response. Returns list of BooksyBusiness."""
        businesses = []

        # Booksy wraps results in different keys across API versions
        items = (
            data.get("businesses") or
            data.get("items") or
            data.get("data", {}).get("businesses") or
            data.get("results") or
            []
        )

        for item in items:
            biz = cls.parse_business(item)
            if biz:
                businesses.append(biz)

        return businesses

    @classmethod
    def parse_business(cls, item: dict) -> Optional["BooksyBusiness"]:
        """Parse a single business record."""
        if not item or not isinstance(item, dict):
            return None

        biz = BooksyBusiness()
        biz._raw = item

        biz.booksy_id = item.get("id") or item.get("business_id")
        biz.name = item.get("name") or item.get("business_name") or ""

        if not biz.name:
            return None

        # Rating
        biz.rating = None
        rating_raw = item.get("rating") or item.get("score") or item.get("avg_rating")
        if rating_raw is not None:
            try:
                r = float(rating_raw)
                biz.rating = round(r, 1) if 1 <= r <= 5 else None
            except (ValueError, TypeError):
                pass

        biz.review_count = int(item.get("num_reviews") or item.get("reviews_count") or 0)

        # Location
        address_obj = item.get("address") or {}
        if isinstance(address_obj, dict):
            biz.address = address_obj.get("street") or address_obj.get("address1") or ""
            biz.city = address_obj.get("city") or ""
            biz.state = address_obj.get("state") or ""
            biz.zip_code = str(address_obj.get("zipcode") or address_obj.get("zip") or "")
            biz.neighborhood = address_obj.get("neighborhood") or address_obj.get("district") or ""
        elif isinstance(address_obj, str):
            biz.address = address_obj
            # Try to extract zip
            zip_match = re.search(r"\b(\d{5})\b", address_obj)
            if zip_match:
                biz.zip_code = zip_match.group(1)

        # Also check top-level location fields
        if not biz.zip_code:
            biz.zip_code = str(item.get("zip") or item.get("zipcode") or item.get("postal_code") or "")

        # Coordinates
        loc = item.get("location") or item.get("geo") or {}
        if isinstance(loc, dict):
            biz.lat = loc.get("lat") or loc.get("latitude")
            biz.lng = loc.get("lng") or loc.get("longitude")
        elif not loc:
            biz.lat = item.get("lat") or item.get("latitude")
            biz.lng = item.get("lng") or item.get("longitude")

        # Contact
        biz.phone = item.get("phone") or item.get("phone_number") or ""
        biz.website = item.get("website") or item.get("url") or ""

        # Social
        socials = item.get("social_media") or item.get("social") or {}
        if isinstance(socials, dict):
            biz.instagram = socials.get("instagram") or socials.get("ig") or ""
        biz.instagram = biz.instagram or item.get("instagram") or ""

        # Flags
        biz.is_verified = bool(item.get("is_verified") or item.get("verified"))
        biz.accepts_walkins = bool(
            item.get("accepts_walkins") or
            item.get("walk_ins") or
            item.get("walkin_available")
        )
        biz.accepts_online_booking = bool(
            item.get("online_booking") or
            item.get("booking_enabled") if item.get("booking_enabled") is not None
            else True
        )

        # Payment
        payments = item.get("payment_methods") or item.get("payments") or []
        if isinstance(payments, list):
            biz.payment_methods = ", ".join(str(p) for p in payments)
        elif isinstance(payments, str):
            biz.payment_methods = payments

        # Profile completeness heuristic
        fields_present = sum([
            bool(biz.rating),
            bool(biz.phone),
            bool(biz.website),
            bool(biz.instagram),
            biz.review_count > 0,
            bool(item.get("photos") or item.get("images")),
            bool(item.get("about") or item.get("description")),
        ])
        if fields_present >= 6:
            biz.profile_completeness = "High"
        elif fields_present >= 3:
            biz.profile_completeness = "Medium"
        else:
            biz.profile_completeness = "Low"

        # About / description
        biz.about = item.get("about") or item.get("description") or item.get("bio") or ""
        biz.business_type = item.get("type") or item.get("category") or ""

        # Profile URL
        slug = item.get("slug") or item.get("url_slug") or ""
        if slug:
            biz.profile_url = f"https://booksy.com/en-us/{slug}"
        elif biz.booksy_id:
            biz.profile_url = f"https://booksy.com/en-us/_/{biz.booksy_id}"

        # Last active
        last_active_raw = item.get("last_active") or item.get("updated_at") or item.get("last_booking")
        if last_active_raw:
            try:
                if isinstance(last_active_raw, str):
                    biz.last_active = datetime.fromisoformat(
                        last_active_raw.replace("Z", "+00:00")
                    ).date()
                elif isinstance(last_active_raw, (int, float)):
                    biz.last_active = datetime.fromtimestamp(last_active_raw).date()
            except (ValueError, TypeError, OSError):
                pass

        # Services (if embedded in response)
        raw_services = item.get("services") or item.get("service_list") or []
        biz.services = cls.parse_services(raw_services)

        # Staff (if embedded)
        raw_staff = item.get("staff") or item.get("staff_members") or []
        biz.staff = [s for s in [cls.parse_staff(s) for s in raw_staff] if s]

        return biz

    @classmethod
    def parse_services(cls, raw_services: list) -> list:
        """Parse service list into normalized records."""
        services = []
        for svc in raw_services:
            if not isinstance(svc, dict):
                continue
            name_raw = svc.get("name") or svc.get("service_name") or ""
            if not name_raw:
                continue

            price_raw = svc.get("price") or svc.get("price_from") or svc.get("amount")
            duration = svc.get("duration") or svc.get("time") or 0

            services.append({
                "id": svc.get("id"),
                "name": name_raw,
                "normalized_name": cls.normalize_service_name(name_raw),
                "price": cls.parse_price(price_raw),
                "duration_minutes": int(duration) if duration else None,
                "category": svc.get("category") or svc.get("type") or "",
            })
        return services

    @classmethod
    def parse_staff(cls, item: dict) -> Optional["BooksyStaff"]:
        """Parse a staff member record."""
        if not item or not isinstance(item, dict):
            return None

        staff = BooksyStaff()
        staff._raw = item

        staff.booksy_id = item.get("id") or item.get("staff_id")
        staff.business_id = item.get("business_id")
        staff.name = item.get("name") or item.get("nick") or item.get("display_name") or ""

        if not staff.name:
            return None

        rating_raw = item.get("rating") or item.get("score")
        if rating_raw is not None:
            try:
                r = float(rating_raw)
                staff.rating = round(r, 1) if 1 <= r <= 5 else None
            except (ValueError, TypeError):
                pass

        staff.review_count = int(item.get("num_reviews") or item.get("reviews_count") or 0)
        staff.about = item.get("about") or item.get("description") or item.get("bio") or ""

        socials = item.get("social_media") or item.get("social") or {}
        if isinstance(socials, dict):
            staff.instagram = socials.get("instagram") or ""

        raw_services = item.get("services") or []
        staff.services = BooksyResponseParser.parse_services(raw_services)

        return staff

    @classmethod
    def parse_staff_list(cls, data: dict) -> list:
        """Parse a /staff_members response."""
        items = (
            data.get("staff_members") or
            data.get("staff") or
            data.get("data") or
            []
        )
        return [s for s in [cls.parse_staff(s) for s in items] if s]

    @classmethod
    def parse_services_response(cls, data: dict) -> list:
        """Parse a /services response."""
        items = (
            data.get("services") or
            data.get("data") or
            data.get("items") or
            []
        )
        return cls.parse_services(items)


# ── PLAYWRIGHT SCRAPER ─────────────────────────────────────────────────

class BooksyScraper(BaseAgent):
    """
    Playwright-based Booksy scraper using API interception.

    Navigates Booksy search pages, intercepts XHR responses from
    Booksy's internal API, and returns structured business data.
    """

    name = "booksy_scraper"
    description = "Intercepts Booksy API responses to collect Charlotte barber listings"
    tier = 1

    def __init__(self, target_zips=None, dry_run=False,
                 headless=True, timeout=30000, **kwargs):
        super().__init__(dry_run=dry_run, **kwargs)
        self.target_zips = target_zips or TARGET_ZIPS
        self.headless = headless
        self.timeout = timeout          # ms
        self.page_wait = 4             # seconds to wait for XHR after navigation
        self._captured: dict = {}       # booksy_id → BooksyBusiness
        self._errors: list = []

    # ── ASYNC CORE ─────────────────────────────────────────────────────

    async def _scrape_async(self):
        """Main async scrape loop. Returns list of BooksyBusiness."""
        try:
            from playwright.async_api import async_playwright, TimeoutError as PwTimeout
        except ImportError:
            self.log("Playwright not installed.")
            self.log("Run: pip install playwright && playwright install chromium")
            raise

        self.log(f"Starting Booksy scrape — {len(self.target_zips)} zip codes")
        self.log(f"Headless: {self.headless} | Timeout: {self.timeout}ms")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-extensions",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )

            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="en-US",
                timezone_id="America/New_York",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "application/json, text/plain, */*",
                },
            )

            # Intercept API responses at context level (all pages)
            context.on("response", self._handle_response_sync)

            page = await context.new_page()

            # Block images and fonts to speed up scraping
            await page.route(
                "**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,otf}",
                lambda route: route.abort()
            )

            try:
                # Step 1: Load Booksy to get auth cookies/tokens
                await self._load_booksy_home(page)

                # Step 2: Search each target zip code
                for zip_code in self.target_zips:
                    await self._search_zip(page, zip_code)
                    await asyncio.sleep(self.page_wait)

                # Step 3: Fetch detailed info for any businesses that need it
                await self._enrich_businesses(page, context)

            finally:
                await browser.close()

        results = list(self._captured.values())
        self.log(f"Scrape complete — {len(results)} unique businesses captured")
        return results

    def _handle_response_sync(self, response):
        """Synchronous wrapper for response handler (Playwright callback style)."""
        # Schedule async processing without blocking
        try:
            url = response.url
            if any(pattern in url for pattern in API_PATTERNS):
                # Fire-and-forget — we'll process what lands
                asyncio.ensure_future(self._handle_api_response(response))
        except Exception:
            pass

    async def _handle_api_response(self, response):
        """Process an intercepted Booksy API response."""
        url = response.url
        status = response.status

        if status != 200:
            return

        try:
            body = await response.body()
            if not body:
                return

            text = body.decode("utf-8", errors="replace")

            # Quick bailout — if it doesn't look like JSON, skip
            stripped = text.strip()
            if not stripped or stripped[0] not in ("{", "["):
                return

            data = json.loads(text)

        except Exception as e:
            log.debug(f"Response parse error for {url}: {e}")
            return

        # Route to correct parser based on URL pattern
        try:
            if "/services" in url and "/businesses/" in url:
                # Service list for a specific business
                bid = self._extract_business_id(url)
                services = BooksyResponseParser.parse_services_response(data)
                if bid and services and bid in self._captured:
                    self._captured[bid].services = services
                    log.debug(f"Services for {bid}: {len(services)} services")

            elif "/staff_members" in url or "/staff" in url:
                # Staff list for a specific business
                bid = self._extract_business_id(url)
                staff = BooksyResponseParser.parse_staff_list(data)
                if bid and staff and bid in self._captured:
                    self._captured[bid].staff = staff
                    log.debug(f"Staff for {bid}: {len(staff)} members")

            elif "businesses" in url and ("search" in url or "list" in url or "near" in url):
                # Search results
                businesses = BooksyResponseParser.parse_business_list(data)
                for biz in businesses:
                    if biz.booksy_id and biz.booksy_id not in self._captured:
                        self._captured[biz.booksy_id] = biz
                        log.debug(f"Captured: {biz.name} ({biz.zip_code})")

            elif "/businesses/" in url and not any(
                sub in url for sub in ["/staff", "/services", "/reviews", "/photos"]
            ):
                # Single business detail
                biz = BooksyResponseParser.parse_business(data)
                if not biz:
                    # Sometimes wrapped
                    biz = BooksyResponseParser.parse_business(
                        data.get("business") or data.get("data") or {}
                    )
                if biz and biz.booksy_id:
                    # Merge with existing if we have it
                    if biz.booksy_id in self._captured:
                        existing = self._captured[biz.booksy_id]
                        # Prefer detail data over search data
                        if biz.services:
                            existing.services = biz.services
                        if biz.staff:
                            existing.staff = biz.staff
                        if biz.about and not existing.about:
                            existing.about = biz.about
                        if biz.phone and not existing.phone:
                            existing.phone = biz.phone
                    else:
                        self._captured[biz.booksy_id] = biz

        except Exception as e:
            log.debug(f"Response routing error: {e}")

    def _extract_business_id(self, url: str) -> Optional[int]:
        """Extract business ID from a URL like /businesses/12345/services."""
        match = re.search(r"/businesses/(\d+)", url)
        if match:
            return int(match.group(1))
        return None

    async def _load_booksy_home(self, page):
        """Navigate to Booksy home to establish session cookies."""
        self.log("Loading Booksy home page...")
        try:
            await page.goto(
                f"{BOOKSY_BASE}/en-us/",
                wait_until="domcontentloaded",
                timeout=self.timeout,
            )
            await asyncio.sleep(2)
            self.log("Booksy home loaded")
        except Exception as e:
            self.log(f"Home page load warning: {e}")

    async def _search_zip(self, page, zip_code: str):
        """Search Booksy for barbershops in a given zip code."""
        coords = ZIP_COORDS.get(zip_code, (CHARLOTTE_LAT, CHARLOTTE_LNG))
        lat, lng = coords

        self.log(f"Searching zip {zip_code} ({lat}, {lng})...")

        # Try the direct search URL — Booksy's search page triggers API calls
        search_url = (
            f"{BOOKSY_BASE}/en-us/search"
            f"?q=barber&location={zip_code}"
            f"&lat={lat}&lng={lng}"
            f"&category=barber"
        )

        try:
            await page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=self.timeout,
            )

            # Wait for XHR responses to land
            await asyncio.sleep(self.page_wait)

            # Scroll to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.5)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(1)

            # Try to load next page if pagination exists
            try:
                next_btn = page.locator(
                    "button[aria-label*='next'], a[aria-label*='next'], "
                    "[data-testid='pagination-next']"
                )
                if await next_btn.count() > 0 and await next_btn.is_enabled():
                    await next_btn.click()
                    await asyncio.sleep(self.page_wait)
            except Exception:
                pass

            count_before = len(self._captured)
            await asyncio.sleep(1)
            count_after = len(self._captured)
            new_count = count_after - count_before
            self.log(f"  Zip {zip_code}: +{new_count} businesses captured")

        except Exception as e:
            self._errors.append({"zip": zip_code, "error": str(e)})
            self.log(f"  Error searching zip {zip_code}: {e}")

        # Brief respectful delay between zip searches
        await asyncio.sleep(1.5)

    async def _enrich_businesses(self, page, context):
        """
        For businesses that lack service pricing, visit their profile
        page directly to trigger the /services and /staff_members API calls.
        """
        needs_enrichment = [
            biz for biz in self._captured.values()
            if not biz.services and biz.profile_url
        ]

        if not needs_enrichment:
            self.log("All businesses have service data — skipping enrichment")
            return

        self.log(f"Enriching {len(needs_enrichment)} businesses with service details...")

        for biz in needs_enrichment[:20]:  # Cap at 20 to stay respectful
            try:
                self.log(f"  Enriching: {biz.name}")
                await page.goto(
                    biz.profile_url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout,
                )
                await asyncio.sleep(self.page_wait)

                # Click "Services" tab if it exists
                try:
                    svc_tab = page.locator(
                        "button:has-text('Services'), a:has-text('Services'), "
                        "[data-testid='services-tab']"
                    )
                    if await svc_tab.count() > 0:
                        await svc_tab.first.click()
                        await asyncio.sleep(2)
                except Exception:
                    pass

                await asyncio.sleep(1)

            except Exception as e:
                self.log(f"  Enrichment error for {biz.name}: {e}")
                continue

            # Respectful delay
            await asyncio.sleep(1.5)

    # ── SYNC ENTRY POINT ───────────────────────────────────────────────

    def scrape(self) -> list:
        """Run the scraper synchronously. Returns list of BooksyBusiness."""
        return asyncio.run(self._scrape_async())

    def scrape_business_id(self, business_id: int) -> Optional[BooksyBusiness]:
        """Scrape a single Booksy business by ID."""
        async def _single():
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                self.log("Playwright not installed.")
                return None

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    )
                )
                context.on("response", self._handle_response_sync)
                page = await context.new_page()

                try:
                    url = f"{BOOKSY_BASE}/en-us/_/{business_id}"
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                    await asyncio.sleep(self.page_wait)

                    # Click Services tab
                    try:
                        svc = page.locator("button:has-text('Services')")
                        if await svc.count():
                            await svc.first.click()
                            await asyncio.sleep(2)
                    except Exception:
                        pass

                finally:
                    await browser.close()

            return self._captured.get(business_id)

        return asyncio.run(_single())

    # ── WAREHOUSE WRITE ────────────────────────────────────────────────

    def _get_or_create_competitor(self, biz: BooksyBusiness) -> Optional[int]:
        """Return competitor_id for this business, creating if needed."""
        con = get_connection()
        try:
            # Try exact name match first
            row = con.execute(
                "SELECT competitor_id FROM competitors WHERE company_name ILIKE ?",
                [f"%{biz.name}%"]
            ).fetchone()

            if row:
                return row[0]

            # Not in warehouse — create new record
            cid = con.execute("SELECT nextval('seq_competitor')").fetchone()[0]
            con.execute("""
                INSERT INTO competitors (
                    competitor_id, company_name, industry, hq_location,
                    zip_code, neighborhood, ownership_type, business_model,
                    website, status, notes
                ) VALUES (?, ?, 'Barbershop', ?, ?, ?, 'Unknown', 'Service', ?, 'Active', ?)
            """, [
                cid,
                biz.name,
                biz.address,
                biz.zip_code or None,
                biz.neighborhood or None,
                biz.website or None,
                f"Discovered via Booksy scrape. Phone: {biz.phone}",
            ])
            self.log(f"New competitor created: {biz.name} (ID: {cid})")
            return cid

        except Exception as e:
            self.log(f"Competitor lookup/create error for {biz.name}: {e}")
            return None
        finally:
            con.close()

    def write_platform_profile(self, biz: BooksyBusiness, competitor_id: int):
        """Write a record to platform_profiles."""
        if self.dry_run:
            self.log(f"[DRY RUN] platform_profile: {biz.name}")
            return

        con = get_connection()
        try:
            pid = con.execute("SELECT nextval('seq_platform_profile')").fetchone()[0]
            con.execute("""
                INSERT INTO platform_profiles (
                    id, competitor_id, platform, profile_url, rating, review_count,
                    is_verified, accepts_online_booking, payment_methods,
                    profile_completeness, last_active, notes
                ) VALUES (?, ?, 'Booksy', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                pid,
                competitor_id,
                biz.profile_url or None,
                biz.rating,
                biz.review_count,
                biz.is_verified,
                biz.accepts_online_booking,
                biz.payment_methods or None,
                biz.profile_completeness or None,
                biz.last_active,
                f"Staff: {len(biz.staff)} | Services: {len(biz.services)} | "
                f"Walk-ins: {biz.accepts_walkins}",
            ])
            self.records_processed += 1
        except Exception as e:
            self.log(f"platform_profile write error: {e}")
        finally:
            con.close()

    def write_solo_barbers(self, biz: BooksyBusiness):
        """Write individual barbers from a business to platform_solo_barbers."""
        if not biz.staff:
            return

        if self.dry_run:
            self.log(f"[DRY RUN] {len(biz.staff)} solo barbers from {biz.name}")
            return

        con = get_connection()
        try:
            for staff in biz.staff:
                if not staff.name:
                    continue

                # Check for duplicate (same name + zip on Booksy)
                exists = con.execute("""
                    SELECT COUNT(*) FROM platform_solo_barbers
                    WHERE barber_name ILIKE ? AND platform = 'Booksy' AND zip_code = ?
                """, [staff.name, biz.zip_code or ""]).fetchone()[0]

                if exists:
                    log.debug(f"Solo barber already exists: {staff.name} in {biz.zip_code}")
                    continue

                # Resolve pricing — prefer staff-level, fall back to business-level
                fade_price = staff.get_fade_price() or biz.get_fade_price()
                haircut_price = staff.get_haircut_price() or biz.get_haircut_price()

                specialties = self._infer_specialties(staff, biz)
                profile_url = (
                    staff.profile_url if hasattr(staff, "profile_url") and staff.profile_url
                    else biz.profile_url
                )

                sid = con.execute("SELECT nextval('seq_platform_solo')").fetchone()[0]
                con.execute("""
                    INSERT INTO platform_solo_barbers (
                        id, barber_name, platform, profile_url, zip_code,
                        neighborhood, rating, review_count, specialties,
                        price_range, fade_price, haircut_price, beard_price,
                        combo_price, accepts_walkins, instagram_handle,
                        ownership_type, primary_clientele, status, notes
                    ) VALUES (?, ?, 'Booksy', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Men', 'Active', ?)
                """, [
                    sid,
                    staff.name,
                    profile_url or None,
                    biz.zip_code or None,
                    biz.neighborhood or None,
                    staff.rating,
                    staff.review_count,
                    ", ".join(specialties) if specialties else None,
                    biz.price_range() or None,
                    fade_price,
                    haircut_price,
                    biz.get_beard_price(),
                    biz.get_combo_price(),
                    biz.accepts_walkins,
                    staff.instagram or biz.instagram or None,
                    "Unknown",
                    f"Works at {biz.name} | Booksy ID: {staff.booksy_id}",
                ])
                self.records_processed += 1
                self.log(f"  Solo barber saved: {staff.name} @ {biz.name}")

        except Exception as e:
            self.log(f"Solo barber write error: {e}")
        finally:
            con.close()

    def write_price_history(self, biz: BooksyBusiness, competitor_id: int):
        """Write service prices to price_history for time-series tracking."""
        if not biz.services or self.dry_run:
            return

        con = get_connection()
        try:
            for svc in biz.services:
                price = svc.get("price")
                if price is None:
                    continue

                normalized = svc.get("normalized_name") or svc.get("name", "")

                pid = con.execute("SELECT nextval('seq_price_history')").fetchone()[0]
                con.execute("""
                    INSERT INTO price_history (
                        id, competitor_id, service_name, price, source
                    ) VALUES (?, ?, ?, ?, ?)
                """, [
                    pid,
                    competitor_id,
                    normalized,
                    float(price),
                    biz.profile_url or "Booksy scrape",
                ])
                self.records_processed += 1

        except Exception as e:
            self.log(f"Price history write error: {e}")
        finally:
            con.close()

    def _infer_specialties(self, staff: BooksyStaff, biz: BooksyBusiness) -> list:
        """Infer barber specialties from their service list and bio."""
        specialties = []
        all_services = staff.services or biz.services
        service_names = [s.get("name", "").lower() for s in all_services]

        checks = [
            ("skin fade", "Skin Fade"),
            ("fade", "Fades"),
            ("beard sculpt", "Beard Sculpting"),
            ("beard", "Beard Work"),
            ("razor", "Straight Razor"),
            ("hot towel", "Hot Towel"),
            ("kids", "Kids Cuts"),
            ("design", "Hair Design"),
            ("braid", "Braids"),
            ("loc", "Locs"),
            ("natural", "Natural Hair"),
        ]
        for keyword, label in checks:
            if any(keyword in s for s in service_names):
                specialties.append(label)

        about_lower = (staff.about or "").lower()
        if "certified" in about_lower or "licensed" in about_lower:
            specialties.append("Licensed")
        if "master barber" in about_lower:
            specialties.append("Master Barber")

        return list(dict.fromkeys(specialties))  # dedup, preserve order

    # ── MAIN WRITE LOOP ────────────────────────────────────────────────

    def persist_all(self, businesses: list) -> dict:
        """Write all scraped businesses to the warehouse. Returns summary."""
        summary = {
            "total_scraped": len(businesses),
            "barber_shops": 0,
            "skipped_non_barber": 0,
            "platform_profiles_written": 0,
            "solo_barbers_written": 0,
            "price_records_written": 0,
            "errors": 0,
            "by_zip": {},
        }

        for biz in businesses:
            # Filter to barbershops only
            if not biz.is_barber_shop():
                summary["skipped_non_barber"] += 1
                log.debug(f"Skipped non-barber: {biz.name}")
                continue

            summary["barber_shops"] += 1

            # Track by zip
            z = biz.zip_code or "unknown"
            summary["by_zip"][z] = summary["by_zip"].get(z, 0) + 1

            try:
                competitor_id = self._get_or_create_competitor(biz)
                if not competitor_id:
                    summary["errors"] += 1
                    continue

                before = self.records_processed

                self.write_platform_profile(biz, competitor_id)
                self.write_solo_barbers(biz)
                self.write_price_history(biz, competitor_id)

                written = self.records_processed - before
                if written > 0:
                    summary["platform_profiles_written"] += 1

            except Exception as e:
                self.log(f"Persist error for {biz.name}: {e}")
                summary["errors"] += 1

        return summary

    # ── AGENT EXECUTE ──────────────────────────────────────────────────

    def execute(self):
        """Called by the agent runner. Scrapes and persists."""
        self.log("Booksy Scraper starting...")
        self.log(f"Target zips: {', '.join(self.target_zips)}")

        if self.dry_run:
            self.log("DRY RUN MODE — warehouse writes suppressed")

        # Run the scraper
        businesses = self.scrape()

        if not businesses:
            self.log("No businesses captured. Check Playwright installation and network.")
            return

        # Write to warehouse
        self.log(f"Persisting {len(businesses)} businesses to warehouse...")
        summary = self.persist_all(businesses)

        # Log summary
        self.log("═" * 50)
        self.log(f"SCRAPE SUMMARY:")
        self.log(f"  Total scraped:         {summary['total_scraped']}")
        self.log(f"  Barbershops found:     {summary['barber_shops']}")
        self.log(f"  Non-barber skipped:    {summary['skipped_non_barber']}")
        self.log(f"  Platform profiles:     {summary['platform_profiles_written']}")
        self.log(f"  Solo barbers written:  {summary['solo_barbers_written']}")
        self.log(f"  Price records:         {summary['price_records_written']}")
        self.log(f"  Errors:                {summary['errors']}")
        if summary["by_zip"]:
            self.log(f"  By zip:")
            for z, count in sorted(summary["by_zip"].items()):
                self.log(f"    {z}: {count} shops")
        self.log("═" * 50)

        # Alert if we found no pricing data
        priced = sum(1 for b in businesses if b.get_fade_price() or b.get_haircut_price())
        if priced == 0:
            self.create_alert(
                alert_type="scrape_no_pricing",
                title="Booksy scrape: no pricing data captured",
                detail=(
                    f"Scraped {len(businesses)} businesses but extracted 0 price records. "
                    "Booksy may have changed their API structure. Review intercepted URLs."
                ),
                severity="warning",
            )

        if self._errors:
            self.log(f"Scrape errors ({len(self._errors)}):")
            for err in self._errors[:5]:
                self.log(f"  {err}")

    # ── REPORTING ──────────────────────────────────────────────────────

    def get_booksy_coverage(self) -> list:
        """Query warehouse for all Booksy platform_profiles."""
        con = get_connection()
        try:
            rows = con.execute("""
                SELECT
                    c.company_name,
                    c.zip_code,
                    c.neighborhood,
                    pp.rating,
                    pp.review_count,
                    pp.is_verified,
                    pp.accepts_online_booking,
                    pp.profile_completeness,
                    pp.profile_url,
                    pp.collected_at
                FROM platform_profiles pp
                JOIN competitors c ON c.competitor_id = pp.competitor_id
                WHERE pp.platform = 'Booksy'
                ORDER BY pp.rating DESC NULLS LAST
            """).fetchall()
            cols = [d[0] for d in con.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            con.close()

    def get_booksy_solo_barbers(self, zip_code=None) -> list:
        """Query warehouse for solo barbers found on Booksy."""
        con = get_connection()
        try:
            query = """
                SELECT * FROM platform_solo_barbers
                WHERE platform = 'Booksy' AND status = 'Active'
            """
            params = []
            if zip_code:
                query += " AND zip_code = ?"
                params.append(zip_code)
            query += " ORDER BY rating DESC NULLS LAST, fade_price ASC NULLS LAST"
            rows = con.execute(query, params).fetchall()
            cols = [d[0] for d in con.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            con.close()

    def print_coverage_report(self):
        """Print a formatted coverage report to stdout."""
        profiles = self.get_booksy_coverage()
        solos = self.get_booksy_solo_barbers()

        print(f"\n{'═' * 70}")
        print(f"  BOOKSY COVERAGE REPORT")
        print(f"{'═' * 70}")
        print(f"  Shops on Booksy:   {len(profiles)}")
        print(f"  Solo barbers:      {len(solos)}")
        print()

        if profiles:
            print(f"  {'SHOP':<35} {'ZIP':6} {'RATING':8} {'REVIEWS':8} {'COMPLETE'}")
            print(f"  {'─' * 66}")
            for p in profiles:
                rating = f"{p['rating']:.1f}★" if p['rating'] else "N/A"
                print(
                    f"  {str(p['company_name'])[:34]:<35} "
                    f"{str(p['zip_code'] or '')[:5]:6} "
                    f"{rating:8} "
                    f"{p['review_count']:8} "
                    f"{p['profile_completeness'] or ''}"
                )

        if solos:
            print(f"\n  SOLO BARBERS (sample — top 10 by rating):")
            print(f"  {'NAME':<25} {'ZIP':6} {'RATING':8} {'FADE':8} {'SPECIALTIES'}")
            print(f"  {'─' * 70}")
            for s in solos[:10]:
                rating = f"{s['rating']:.1f}★" if s['rating'] else "N/A"
                fade = f"${s['fade_price']:.0f}" if s['fade_price'] else "N/A"
                specs = (s['specialties'] or "")[:25]
                print(
                    f"  {str(s['barber_name'])[:24]:<25} "
                    f"{str(s['zip_code'] or '')[:5]:6} "
                    f"{rating:8} "
                    f"{fade:8} "
                    f"{specs}"
                )

        print(f"\n{'═' * 70}\n")


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Corporate HQ — Booksy Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agents.booksy_scraper
  python -m agents.booksy_scraper --zips 28208 28216 28206
  python -m agents.booksy_scraper --dry-run
  python -m agents.booksy_scraper --business-id 12345
  python -m agents.booksy_scraper --report
  python -m agents.booksy_scraper --visible  # non-headless for debugging
        """
    )
    parser.add_argument(
        "--zips", nargs="+", default=None,
        help="Zip codes to scrape (default: all 14 target zips)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Collect data but don't write to warehouse"
    )
    parser.add_argument(
        "--visible", action="store_true",
        help="Run browser in visible mode (not headless) — useful for debugging"
    )
    parser.add_argument(
        "--business-id", type=int, default=None,
        help="Scrape a single Booksy business by ID"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Print coverage report from warehouse (no scraping)"
    )
    parser.add_argument(
        "--timeout", type=int, default=30000,
        help="Page load timeout in milliseconds (default: 30000)"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    scraper = BooksyScraper(
        target_zips=args.zips or TARGET_ZIPS,
        dry_run=args.dry_run,
        headless=not args.visible,
        timeout=args.timeout,
    )

    if args.report:
        scraper.print_coverage_report()
        return

    if args.business_id:
        print(f"Scraping single business: {args.business_id}")
        biz = scraper.scrape_business_id(args.business_id)
        if biz:
            print(json.dumps(biz.to_dict(), indent=2, default=str))
        else:
            print("No data captured for that business ID.")
        return

    # Full run via agent lifecycle
    scraper.run()
    scraper.print_coverage_report()


if __name__ == "__main__":
    main()
