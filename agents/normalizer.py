"""Tier 2 — Normalization & Dedupe Agent

Standardizes names, service names ("fade" vs "taper fade"), prices as
numbers, locations with neighborhoods. Handles Charlotte specifics like
multi-location chains (No Grease has several spots).

Trigger: On every ingest
"""

import re
from agents.base import BaseAgent
from warehouse.db import get_connection


# Service name normalization map — maps common variants to canonical names
SERVICE_ALIASES = {
    # Fades
    "fade": "Fade",
    "regular fade": "Fade",
    "classic fade": "Fade",
    "skin fade": "Skin Fade",
    "bald fade": "Skin Fade",
    "zero fade": "Skin Fade",
    "taper fade": "Taper Fade",
    "taper": "Taper Fade",
    "drop fade": "Drop Fade",
    "burst fade": "Burst Fade",
    "temp fade": "Temp Fade",
    "mid fade": "Mid Fade",
    "high fade": "High Fade",
    "low fade": "Low Fade",
    # Cuts
    "haircut": "Regular Haircut",
    "regular cut": "Regular Haircut",
    "men's haircut": "Regular Haircut",
    "mens haircut": "Regular Haircut",
    "men's cut": "Regular Haircut",
    "mens cut": "Regular Haircut",
    "kids cut": "Kids Haircut",
    "kid's haircut": "Kids Haircut",
    "child haircut": "Kids Haircut",
    "senior cut": "Senior Haircut",
    "senior haircut": "Senior Haircut",
    # Beard
    "beard trim": "Beard Trim",
    "beard shape": "Beard Trim",
    "beard lineup": "Beard Trim",
    "beard sculpt": "Beard Sculpting",
    "beard sculpting": "Beard Sculpting",
    "beard design": "Beard Sculpting",
    # Shave
    "hot towel shave": "Hot Towel Shave",
    "straight razor shave": "Straight Razor Shave",
    "razor shave": "Straight Razor Shave",
    "hot shave": "Hot Towel Shave",
    "shave": "Straight Razor Shave",
    # Line-up
    "line-up": "Line-Up / Edge-Up",
    "lineup": "Line-Up / Edge-Up",
    "line up": "Line-Up / Edge-Up",
    "edge up": "Line-Up / Edge-Up",
    "edge-up": "Line-Up / Edge-Up",
    "shape up": "Line-Up / Edge-Up",
    "shape-up": "Line-Up / Edge-Up",
    # Combos
    "haircut and beard": "Haircut + Beard Combo",
    "cut and beard": "Haircut + Beard Combo",
    "haircut + beard": "Haircut + Beard Combo",
    "combo": "Haircut + Beard Combo",
    # Treatments
    "scalp treatment": "Scalp Treatment",
    "scalp massage": "Scalp Treatment",
    "hair design": "Hair Design / Part",
    "part design": "Hair Design / Part",
    "design": "Hair Design / Part",
    "shampoo": "Shampoo & Condition",
    "wash": "Shampoo & Condition",
}

# Charlotte neighborhood normalization
NEIGHBORHOOD_ALIASES = {
    "south end": "South End",
    "southend": "South End",
    "noda": "NoDa",
    "north davidson": "NoDa",
    "plaza midwood": "Plaza Midwood",
    "uptown": "Uptown",
    "center city": "Uptown",
    "downtown": "Uptown",
    "west charlotte": "West Charlotte",
    "seversville": "Seversville",
    "beatties ford": "Beatties Ford",
    "university": "University City",
    "university city": "University City",
    "uncc": "University City",
    "eastway": "Eastway",
    "shamrock": "Shamrock",
    "hidden valley": "Hidden Valley",
    "north charlotte": "North Charlotte",
    "steele creek": "Steele Creek",
    "arrowood": "Arrowood",
    "ballantyne": "Ballantyne",
    "mint hill": "Mint Hill",
    "matthews": "Matthews",
    "huntersville": "Huntersville",
    "gastonia": "Gastonia",
    "concord": "Concord",
    "kannapolis": "Kannapolis",
    "monroe": "Monroe",
    "pineville": "Pineville",
    "indian trail": "Indian Trail",
    "mooresville": "Mooresville",
    "dilworth": "Dilworth",
    "myers park": "Myers Park",
    "elizabeth": "Elizabeth",
    "cherry": "Cherry",
    "wilmore": "Wilmore",
}


class Normalizer(BaseAgent):
    name = "normalizer"
    description = "Standardizes service names, shop names, and locations"
    tier = 2

    def normalize_service_name(self, raw_name):
        """Normalize a service name to its canonical form."""
        key = raw_name.strip().lower()
        return SERVICE_ALIASES.get(key, raw_name.strip().title())

    def normalize_neighborhood(self, raw_name):
        """Normalize a Charlotte neighborhood name."""
        if not raw_name:
            return None
        key = raw_name.strip().lower()
        return NEIGHBORHOOD_ALIASES.get(key, raw_name.strip().title())

    def normalize_price(self, raw_price):
        """Extract a numeric price from various formats."""
        if raw_price is None:
            return None
        if isinstance(raw_price, (int, float)):
            return float(raw_price)
        # Extract number from strings like "$35", "35.00", "$35-45"
        match = re.search(r'\$?(\d+\.?\d*)', str(raw_price))
        return float(match.group(1)) if match else None

    def normalize_shop_name(self, raw_name):
        """Clean up shop name — trim whitespace, normalize known multi-location names."""
        name = raw_name.strip()
        # Known multi-location normalization
        known_chains = {
            "no grease": "No Grease Barber & Beauty Lounge",
            "no grease barber": "No Grease Barber & Beauty Lounge",
            "scissors & scotch": "Scissors & Scotch",
            "scissors and scotch": "Scissors & Scotch",
        }
        key = name.lower()
        for alias, canonical in known_chains.items():
            if alias in key:
                return canonical
        return name

    def dedupe_competitors(self):
        """Find potential duplicate competitor entries."""
        con = get_connection()
        rows = con.execute("""
            SELECT a.competitor_id as id_a, a.company_name as name_a,
                   b.competitor_id as id_b, b.company_name as name_b
            FROM competitors a
            JOIN competitors b ON a.competitor_id < b.competitor_id
            WHERE LOWER(REPLACE(a.company_name, ' ', ''))
                  = LOWER(REPLACE(b.company_name, ' ', ''))
               OR JARO_WINKLER_SIMILARITY(LOWER(a.company_name), LOWER(b.company_name)) > 0.85
        """).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()

        dupes = [dict(zip(columns, row)) for row in rows]
        if dupes:
            self.log(f"Found {len(dupes)} potential duplicate pairs")
            for d in dupes:
                self.create_alert(
                    alert_type="duplicate_detected",
                    title=f"Possible duplicate: '{d['name_a']}' vs '{d['name_b']}'",
                    detail=f"IDs: {d['id_a']} and {d['id_b']}",
                    severity="info",
                )
        else:
            self.log("No duplicates found")
        return dupes

    def normalize_all_prices(self):
        """Run normalization on all price_history service names."""
        con = get_connection()
        rows = con.execute("SELECT DISTINCT service_name FROM price_history").fetchall()
        updated = 0
        for (raw_name,) in rows:
            canonical = self.normalize_service_name(raw_name)
            if canonical != raw_name:
                con.execute(
                    "UPDATE price_history SET service_name = ? WHERE service_name = ?",
                    [canonical, raw_name],
                )
                updated += 1
                self.log(f"Normalized: '{raw_name}' → '{canonical}'")
        con.close()
        self.records_processed = updated
        self.log(f"Normalized {updated} service name variants")

    def execute(self):
        self.log("Running normalization pass...")
        self.normalize_all_prices()
        self.dedupe_competitors()
