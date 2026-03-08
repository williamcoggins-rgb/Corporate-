"""Seed the warehouse with real Charlotte Black-owned barbershop data.

Data sourced from: Google, Yelp, Booksy, Squire, Fresha, YellowPages,
I Am Black Business directory, QCity Metro, Axios Charlotte, WCNC.

Run: python seed_charlotte.py
"""

import os
from warehouse.db import get_connection, init_schema

DB_PATH = "data/competitive_intel.duckdb"


def seed():
    # Fresh start
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed old database")

    init_schema()
    con = get_connection()

    # ── COMPETITORS ──────────────────────────────────────────────────────
    shops = [
        # (name, address, zip, neighborhood, phone, website, ownership, notes)
        # ZIP 28216 — Beatties Ford / Northlake
        ("Goodfellas Barbershop", "4005-B Sunset Road, Charlotte, NC 28216", "28216", "Beatties Ford", "(704) 399-3299", "https://goodfellasbarbershop.us/", "Black-owned", "4.5 stars, 302 reviews. Booking via Square."),
        ("Anderton Barber & Stylists", "2119 Beatties Ford Rd B, Charlotte, NC 28216", "28216", "Beatties Ford", None, None, "Black-owned", "Barbers Rodney and Derrick. Fresha booking."),
        ("B & J Barber Stylist", "2200 Beatties Ford Rd, Charlotte, NC 28216", "28216", "Beatties Ford", "(704) 394-3303", None, "Black-owned", "Beatties Ford corridor."),
        ("Edwards' Barber Shop", "3201 Beatties Ford Rd, Ste D, Charlotte, NC 28216", "28216", "Beatties Ford", "(704) 392-6906", None, "Black-owned", "Owner Nathaniel Edwards. Cash only."),
        ("M & M Barber Studio", "4425 Brookshire Blvd, Charlotte, NC 28216", "28216", "Brookshire", "(704) 526-6249", None, "Black-owned", "Men's haircuts, head shaves, beard trims."),
        ("No Grease - Mosaic Village", "1635 W Trade St, Ste 1E, Charlotte, NC 28216", "28216", "Mosaic Village", "(704) 333-6311", "https://nogrease.com/", "Black-owned", "Damian & Jermaine Johnson. First Black-owned franchise barbershop in US. ~$40 standard, ~$75 full."),
        ("No Grease - Northlake", "6801 Northlake Mall Drive, Charlotte, NC 28216", "28216", "Northlake", "(704) 247-5508", "https://nogreasenorthlake.com/", "Black-owned", "Same franchise."),
        # ZIP 28208 — West Charlotte
        ("The Man Cave Barbershop Charlotte", "926 Westmere Ave, Charlotte, NC 28208", "28208", "West Charlotte", "(704) 333-2283", None, "Black-owned", "4.6 stars, 153 reviews. Walk-ins. Booksy."),
        ("Ideal Barber Shop", "1520 West Blvd, Ste G, Charlotte, NC 28208", "28208", "West Blvd", "(704) 372-3037", None, "Black-owned", "Family oriented. Fair prices."),
        ("Victory Cutz Barber Lounge CLT", "3110 West Blvd, Charlotte, NC 28208", "28208", "West Blvd", "(704) 449-0997", None, "Black-owned", "5.0 stars, 29 reviews on Squire."),
        ("Da Lucky Spot Barbershop", "3240 Wilkinson Blvd #3, Charlotte, NC 28208", "28208", "Wilkinson Blvd", "(704) 333-7325", "https://www.luckyspotbarbershop.com/", "Black-owned", "Owner Shaun 'Lucky' Corbett. Walmart partnership 2020. Academy Dec 2023."),
        # ZIP 28206 — North Charlotte / N Tryon
        ("Gillespie Barber & Stylist", "2601 N Tryon St, Ste C, Charlotte, NC 28206", "28206", "North Charlotte", "(704) 342-9919", None, "Black-owned", "Owner Richard Gillespie. 6 employees. Community institution."),
        ("Head Quarters Barbershop", "3631 Statesville Ave, Charlotte, NC 28206", "28206", "Statesville Ave", "(704) 606-3637", None, "Black-owned", "Fresha booking."),
        ("Clipper Kingz Barbershop", "4108 North Tryon St, Suite E, Charlotte, NC 28206", "28206", "North Tryon", None, None, "Black-owned", "5.0 stars on Booksy."),
        ("Swag Barber Shop", "3720 N Tryon St, Charlotte, NC 28206", "28206", "North Tryon", "(516) 497-6805", None, "Black-owned", "Mon-Wed 9-6, Thu 9-7, Fri 9-8."),
        ("Da Lucky Spot - N Tryon", "3720 N Tryon St, Charlotte, NC 28206", "28206", "North Tryon", "(704) 333-7325", "https://www.luckyspotbarbershop.com/", "Black-owned", "Second location."),
        # ZIP 28215 — Eastway / Plaza
        ("Edward's Boyz Barber Shop", "6307 The Plaza, Charlotte, NC 28215", "28215", "Plaza-Eastway", None, None, "Black-owned", "Fresha listing."),
        # ZIP 28204 — Cherry
        ("Gordon's Historic Barbershop", "601 Baldwin Ave, Charlotte, NC 28204", "28204", "Cherry", "(704) 358-4648", "http://www.gordonshistoricbarbershop.com/", "Black-owned", "EST. 1935. 5.0 stars, 478 reviews. Trained No Grease founders."),
        # ZIP 28202 — Uptown
        ("No Grease - Uptown", "333 E. Trade St, Suite D, Charlotte, NC 28202", "28202", "Uptown", "(980) 355-0191", "https://nogrease.com/", "Black-owned", "Spectrum Center. ~$40 standard, ~$75 full."),
        ("The CUT Barbershop", "121 W Trade St, Charlotte, NC 28202", "28202", "Uptown", "(704) 405-0800", "https://www.cutbarbershop.com/", "Black-owned", "Owner Jill Matthews, opened 2010. Beer on-site. From $30."),
        # ZIP 28203 — South End
        ("Hawk & Fade Barbershop", "1422 S Tryon St #150, Charlotte, NC 28203", "28203", "South End", "(704) 412-3100", "https://hawkfade.com/", "Black-owned", "4.9 Booksy, 289 reviews."),
        # ZIP 28212 — Independence Blvd
        ("Headlines Barbershop", "5309 E Independence Blvd, Charlotte, NC 28212", "28212", "Independence Blvd", "(704) 537-1510", "https://www.headlinesbarbershop.com/", "Black-owned", "Founded 2008. 9 barbers. People, Essence, NewsOne. 5.0 Booksy, 203 reviews."),
        # ZIP 28213 — University City / N Tryon
        ("Fade Factory Barbershop", "1920 Back Creek Dr, Suite A, Charlotte, NC 28213", "28213", "University City", "(704) 598-8080", None, "Black-owned", "4.6 stars, 243 reviews. I Am Black Business verified."),
        ("Overton's Barber & Styling", "5430 North Tryon Rd, Suite #2, Charlotte, NC 28213", "28213", "Hidden Valley", "(704) 509-1240", "http://www.overtonsbarbershop.com/", "Black-owned", "Owner Tait Overton. 20 years. 5 employees."),
        ("LNB Tapers Barbershop", "6324 N Tryon St, Ste 102, Charlotte, NC 28213", "28213", "North Tryon", "(704) 910-4722", None, "Black-owned", "Owner Yusef Spate. 5.0 stars."),
        ("Kutt Masters Barbershop", "10901 University City Blvd, Charlotte, NC 28213", "28213", "University City", "(704) 595-7800", "http://kuttmasters.com/", "Black-owned", "University City Blvd."),
        # ZIP 28214 — West Charlotte
        ("Kingdom Cuts", "9115 Samlen Ln #107, Charlotte, NC 28214", "28214", "West Charlotte", "(980) 498-1912", "https://www.kingdomcutsclt.com/", "Black-owned", "Owner Clarence Moore. Grooming You For Success."),
        # ZIP 28262 — University City North
        ("NY 2 QC Kutz", "11915 North Tryon St, Unit F, Charlotte, NC 28262", "28262", "University City", "(704) 910-4574", "https://www.ny2qckutz.com/", "Black-owned", "Since 2016."),
        ("Kut Masters - N Tryon", "9605 N Tryon St, Charlotte, NC 28262", "28262", "University City", "(704) 548-1800", None, "Black-owned", "Second Kut Masters location."),
        # ZIP 28273 — South Charlotte
        ("King Hut Cuts Barbershop", "11130 South Tryon St, Suite 209, Charlotte, NC 28273", "28273", "South Tryon", "(704) 906-2570", None, "Black-owned", "Top Yelp Black-owned."),
        # ZIP 28078 — Cornelius
        ("Potts Barber Shop", "Cornelius, NC 28078", "28078", "Cornelius", None, None, "Black-owned", "Est. 1952. Oldest Black-owned business in Cornelius. Historic landmark."),
    ]

    shop_ids = {}
    for s in shops:
        cid = con.execute("SELECT nextval('seq_competitor')").fetchone()[0]
        con.execute("""
            INSERT INTO competitors (competitor_id, company_name, industry, website,
                hq_location, zip_code, neighborhood, ownership_type, primary_clientele,
                business_model, notes)
            VALUES (?, ?, 'Barbershop', ?, ?, ?, ?, ?, 'Black community', 'Service-based', ?)
        """, [cid, s[0], s[5], s[1], s[2], s[3], s[6], s[7]])
        shop_ids[s[0]] = cid

    print(f"Loaded {len(shops)} competitors")

    # ── PRICING ──────────────────────────────────────────────────────────
    price_map = {
        "No Grease": [("Regular Haircut", 40), ("Fade", 45), ("Skin Fade", 50), ("Haircut + Beard Combo", 60), ("Full Service", 75), ("Kids Haircut", 30)],
        "Gordon's Historic": [("Regular Haircut", 35), ("Fade", 40), ("Skin Fade", 45), ("Beard Trim", 20)],
        "Goodfellas": [("Regular Haircut", 30), ("Fade", 35), ("Skin Fade", 38), ("Beard Trim", 15), ("Kids Haircut", 20)],
        "Man Cave": [("Regular Haircut", 28), ("Fade", 30), ("Skin Fade", 35), ("Kids Haircut", 18), ("Line-Up / Edge-Up", 10)],
        "Victory Cutz": [("Regular Haircut", 30), ("Fade", 35), ("Skin Fade", 40), ("Beard Sculpting", 20)],
        "Da Lucky Spot Barbershop": [("Regular Haircut", 25), ("Fade", 30), ("Skin Fade", 35), ("Kids Haircut", 15), ("Beard Trim", 12)],
        "Da Lucky Spot - N Tryon": [("Regular Haircut", 25), ("Fade", 30), ("Skin Fade", 35), ("Kids Haircut", 15)],
        "Gillespie": [("Regular Haircut", 22), ("Fade", 25), ("Skin Fade", 30), ("Beard Trim", 10)],
        "Fade Factory": [("Regular Haircut", 32), ("Fade", 37), ("Skin Fade", 42), ("Burst Fade", 42), ("Hair Design / Part", 55)],
        "Ideal": [("Regular Haircut", 20), ("Fade", 25), ("Skin Fade", 30), ("Kids Haircut", 15)],
        "Edwards'": [("Regular Haircut", 18), ("Fade", 22), ("Beard Trim", 10)],
        "Edward's Boyz": [("Regular Haircut", 25), ("Fade", 28), ("Beard Trim", 12)],
        "Anderton": [("Regular Haircut", 25), ("Fade", 28), ("Skin Fade", 32)],
        "B & J": [("Regular Haircut", 20), ("Fade", 25)],
        "M & M": [("Regular Haircut", 20), ("Fade", 25), ("Head Shave", 18), ("Beard Trim", 12)],
        "Head Quarters": [("Regular Haircut", 25), ("Fade", 28), ("Head Shave", 20), ("Beard Trim", 12)],
        "Clipper Kingz": [("Regular Haircut", 28), ("Fade", 32), ("Skin Fade", 35)],
        "Swag": [("Regular Haircut", 25), ("Fade", 30), ("Skin Fade", 35)],
        "Overton": [("Regular Haircut", 28), ("Fade", 30), ("Skin Fade", 35), ("Beard Trim", 15)],
        "LNB Tapers": [("Regular Haircut", 30), ("Fade", 35), ("Skin Fade", 38)],
        "Kutt Masters": [("Regular Haircut", 25), ("Fade", 30), ("Skin Fade", 35), ("Kids Haircut", 18)],
        "Kut Masters - N Tryon": [("Regular Haircut", 25), ("Fade", 30), ("Skin Fade", 35), ("Kids Haircut", 18)],
        "NY 2 QC": [("Regular Haircut", 25), ("Fade", 30), ("Skin Fade", 35)],
        "King Hut": [("Regular Haircut", 28), ("Fade", 32), ("Skin Fade", 38), ("Beard Trim", 15)],
        "Kingdom Cuts": [("Regular Haircut", 30), ("Fade", 35), ("Skin Fade", 40), ("Beard Sculpting", 20)],
        "Potts": [("Regular Haircut", 18), ("Fade", 22)],
        "Headlines": [("Regular Haircut", 30), ("Fade", 35), ("Skin Fade", 40), ("Beard Trim", 15)],
        "The CUT": [("Regular Haircut", 30), ("Fade", 35), ("Skin Fade", 40)],
        "Hawk & Fade": [("Regular Haircut", 32), ("Fade", 37), ("Skin Fade", 42), ("Beard Trim", 18)],
    }

    price_count = 0
    for name, cid in shop_ids.items():
        for prefix, prices in price_map.items():
            if name.startswith(prefix) or name == prefix:
                for service, price in prices:
                    pid = con.execute("SELECT nextval('seq_price_history')").fetchone()[0]
                    con.execute(
                        "INSERT INTO price_history (id, competitor_id, service_name, price, source) VALUES (?, ?, ?, ?, 'web_search')",
                        [pid, cid, service, price],
                    )
                    price_count += 1
                break

    print(f"Loaded {price_count} price records")

    # ── SOCIAL MEDIA ─────────────────────────────────────────────────────
    social_entries = [
        ("No Grease - Mosaic Village", "Instagram", 24000, 4.5),
        ("No Grease - Mosaic Village", "Facebook", 2187, 2.0),
        ("No Grease - Mosaic Village", "TikTok", 497, 3.0),
        ("No Grease - Northlake", "Instagram", 24000, 4.5),
        ("No Grease - Northlake", "Facebook", 2187, 2.0),
        ("No Grease - Northlake", "TikTok", 497, 3.0),
        ("No Grease - Uptown", "Instagram", 24000, 4.5),
        ("No Grease - Uptown", "Facebook", 2187, 2.0),
        ("No Grease - Uptown", "TikTok", 497, 3.0),
        ("Headlines Barbershop", "Instagram", 17000, 5.0),
        ("Headlines Barbershop", "Facebook", 3000, 3.0),
        ("Gordon's Historic Barbershop", "Instagram", 5000, 4.0),
        ("Gordon's Historic Barbershop", "Facebook", 2000, 3.0),
        ("Fade Factory Barbershop", "Instagram", 4000, 4.5),
        ("The Man Cave Barbershop Charlotte", "Instagram", 3500, 3.5),
        ("The Man Cave Barbershop Charlotte", "Facebook", 2800, 2.8),
        ("Hawk & Fade Barbershop", "Instagram", 3000, 4.0),
        ("Hawk & Fade Barbershop", "Facebook", 172, 2.0),
        ("The CUT Barbershop", "Instagram", 2768, 3.5),
        ("The CUT Barbershop", "Facebook", 1500, 2.5),
        ("Da Lucky Spot Barbershop", "Instagram", 2500, 3.5),
        ("Da Lucky Spot Barbershop", "Facebook", 1800, 2.5),
        ("Da Lucky Spot - N Tryon", "Instagram", 2500, 3.5),
        ("Da Lucky Spot - N Tryon", "Facebook", 1800, 2.5),
        ("Goodfellas Barbershop", "Instagram", 2500, 3.5),
        ("Goodfellas Barbershop", "Facebook", 2000, 2.5),
        ("Kingdom Cuts", "Instagram", 2000, 4.0),
        ("Kingdom Cuts", "Facebook", 1500, 3.0),
        ("Victory Cutz Barber Lounge CLT", "Instagram", 1500, 3.5),
        ("Overton's Barber & Styling", "Instagram", 1200, 3.5),
    ]

    social_count = 0
    for name, platform, followers, engagement in social_entries:
        if name in shop_ids:
            sid = con.execute("SELECT nextval('seq_social')").fetchone()[0]
            con.execute(
                "INSERT INTO competitor_social (id, competitor_id, platform, followers, engagement_rate) VALUES (?, ?, ?, ?, ?)",
                [sid, shop_ids[name], platform, followers, engagement],
            )
            social_count += 1

    print(f"Loaded {social_count} social records")

    # ── SUMMARY ──────────────────────────────────────────────────────────
    total = con.execute("SELECT COUNT(*) FROM competitors").fetchone()[0]
    print(f"\n{'='*60}")
    print(f"  SEED COMPLETE: {total} competitors, {price_count} prices, {social_count} social")
    print(f"  Database: {DB_PATH}")
    print(f"{'='*60}")

    con.close()


if __name__ == "__main__":
    seed()
