"""Seed the warehouse with real Charlotte Black-owned barbershop data.

Data sourced from: Google, Yelp, Booksy, Squire, Fresha, YellowPages,
I Am Black Business directory, QCity Metro, Axios Charlotte, WCNC.

Run: python seed_charlotte.py
"""

from warehouse.db import get_connection, init_schema


def seed():
    init_schema()
    con = get_connection()

    # ── COMPETITORS ──────────────────────────────────────────────────────
    shops = [
        # (name, address, zip, neighborhood, phone, website, ownership, notes)
        # ZIP 28216 — Beatties Ford / Northlake
        ("Goodfellas Barbershop", "4005-B Sunset Road, Charlotte, NC 28216", "28216", "Beatties Ford", "(704) 399-3299", "https://goodfellasbarbershop.us/", "Black-owned", "Est 2007. Owner: Garinger HS grad, master barber since 2000, trained at Hair Styling Institute of Charlotte (1999). 8 barbers. 4.5 stars, 302 reviews. Booking via Square + Booksy. Complimentary warm towels."),
        ("Anderton Barber & Stylists", "2119 Beatties Ford Rd B, Charlotte, NC 28216", "28216", "Beatties Ford", None, None, "Black-owned", "Barbers Rodney and Derrick. Fresha booking."),
        ("B & J Barber Stylist", "2200 Beatties Ford Rd, Charlotte, NC 28216", "28216", "Beatties Ford", "(704) 394-3303", None, "Black-owned", "Beatties Ford corridor."),
        ("Edwards' Barber Shop", "3201 Beatties Ford Rd, Ste D, Charlotte, NC 28216", "28216", "Beatties Ford", "(704) 392-6906", None, "Black-owned", "Owner Nathaniel Edwards. Cash only."),
        ("M & M Barber Studio", "4425 Brookshire Blvd, Charlotte, NC 28216", "28216", "Brookshire", "(704) 526-6249", None, "Black-owned", "Men's haircuts, head shaves, beard trims."),
        ("No Grease - Mosaic Village", "1635 W Trade St, Ste 1E, Charlotte, NC 28216", "28216", "Mosaic Village", "(704) 333-6311", "https://nogrease.com/", "Black-owned", "FLAGSHIP. Founded June 1997 by twins Damian & Jermaine Johnson (Buffalo NY, JCSU grads) + Charlie Petty. First Black-owned franchise barbershop in US (2017). 14 locations in 4+ states. Franchise fee $132K-$278K. Multi-million dollar business. Licensed in 36 states. Mon-Fri 9am-7pm, Sat 7:30am-5pm."),
        ("No Grease - Northlake", "6801 Northlake Mall Drive, Charlotte, NC 28216", "28216", "Northlake", "(704) 247-5508", "https://nogreasenorthlake.com/", "Black-owned", "Franchisee: Ed Washington (Gardner-Webb grad, Microsoft exec). Gives lead barbers 10% equity. Invested ~$180K."),
        # ZIP 28208 — West Charlotte
        ("The Man Cave Barbershop Charlotte", "926 Westmere Ave, Charlotte, NC 28208", "28208", "West Charlotte", "(704) 333-2283", None, "Black-owned", "12+ years in business. 4.6 stars, 153 reviews. Walk-ins welcome. Booksy. 2nd location at 516 W 10th St, Uptown. Mon 12-7, Tue-Thu 9-7, Fri 7-7, Sat 7-4. Serves men and women."),
        ("Ideal Barber Shop", "1520 West Blvd, Ste G, Charlotte, NC 28208", "28208", "West Blvd", "(704) 372-3037", None, "Black-owned", "Family oriented. Fair prices."),
        ("Victory Cutz Barber Lounge CLT", "3110 West Blvd, Charlotte, NC 28208", "28208", "West Blvd", "(704) 449-0997", None, "Black-owned", "5.0 stars, 29 reviews on Squire."),
        ("Da Lucky Spot Barbershop", "3240 Wilkinson Blvd #3, Charlotte, NC 28208", "28208", "Wilkinson Blvd", "(704) 333-7325", "https://www.luckyspotbarbershop.com/", "Black-owned", "Owner Shaun 'Lucky' Corbett. First Black-owned barbershop inside Walmart (Sep 26, 2019, $25K Walmart check). 5 Walmart locations across NC/SC/GA. Ex-felon turned entrepreneur. No Grease school grad 2005. Academy Dec 2023. Cops & Barbers 501(c)(3) cofounder with Det. Garry McFadden."),
        # ZIP 28206 — North Charlotte / N Tryon
        ("Gillespie Barber & Stylist", "2601 N Tryon St, Ste C, Charlotte, NC 28206", "28206", "North Charlotte", "(704) 342-9919", None, "Black-owned", "Owner Richard Gillespie. 6 employees. BBB since 2007. Community institution."),
        ("Head Quarters Barbershop", "3631 Statesville Ave, Charlotte, NC 28206", "28206", "Statesville Ave", "(704) 606-3637", None, "Black-owned", "Fresha booking."),
        ("Clipper Kingz Barbershop", "4108 North Tryon St, Suite E, Charlotte, NC 28206", "28206", "North Tryon", None, None, "Black-owned", "5.0 stars on Booksy."),
        ("Swag Barber Shop", "3720 N Tryon St, Charlotte, NC 28206", "28206", "North Tryon", "(516) 497-6805", None, "Black-owned", "Mon-Wed 9-6, Thu 9-7, Fri 9-8."),
        ("Da Lucky Spot - N Tryon", "3720 N Tryon St, Charlotte, NC 28206", "28206", "North Tryon", "(704) 333-7325", "https://www.luckyspotbarbershop.com/", "Black-owned", "Original Lucky Spot location, opened 2010."),
        # ZIP 28215 — Eastway / Plaza
        ("Edward's Boyz Barber Shop", "6307 The Plaza, Charlotte, NC 28215", "28215", "Plaza-Eastway", None, None, "Black-owned", "Fresha listing."),
        # ZIP 28204 — Cherry
        ("Gordon's Historic Barbershop", "601 Baldwin Ave, Charlotte, NC 28204", "28204", "Cherry", "(704) 358-4648", "http://www.gordonshistoricbarbershop.com/", "Black-owned", "EST. 1935 (founded by Clemon Morris). Oldest barbershop in Charlotte. Owner Michael Gordon (33+ yrs). Historic Cherry neighborhood — building was dance hall, Girl Scout meeting place during segregation. Michael wears grandfather Mancel Gordon's WWII dog tags daily. Trained No Grease founders. 5.0 Booksy, 478 reviews. Tue-Sat 9am-6pm."),
        # ZIP 28202 — Uptown
        ("No Grease - Uptown", "333 E. Trade St, Suite D, Charlotte, NC 28202", "28202", "Uptown", "(980) 355-0191", "https://nogrease.com/", "Black-owned", "Knights of the Razor concept. Mon-Thu 9am-7pm, Fri 7:30am-7pm, Sat 7:30am-5pm. 'The Royal Treatment' — facials + skin shaves."),
        ("The CUT Barbershop", "121 W Trade St, Charlotte, NC 28202", "28202", "Uptown", "(704) 405-0800", "https://www.cutbarbershop.com/", "Black-owned", "Owner Jill Matthews, opened 2010. Beer on-site. From $30."),
        # ZIP 28211 — SouthPark
        ("No Grease - SouthPark (Knights of the Razor)", "4400 Sharon Rd, Ste L01A, Charlotte, NC 28211", "28211", "SouthPark", "(704) 777-3292", "https://nogrease.com/", "Black-owned", "Premium concept inside SouthPark Mall. 2021 lease controversy — terminated then reversed after public outcry. Mon-Thu 10am-8pm, Fri-Sat 10am-9pm, Sun 11am-7pm."),
        # ZIP 28203 — South End
        ("Hawk & Fade Barbershop", "1422 S Tryon St #150, Charlotte, NC 28203", "28203", "South End", "(704) 412-3100", "https://hawkfade.com/", "Black-owned", "4.9 Booksy, 289 reviews."),
        # ZIP 28212 — Independence Blvd
        ("Headlines Barbershop", "5309 E Independence Blvd, Charlotte, NC 28212", "28212", "Independence Blvd", "(704) 537-1510", "https://www.headlinesbarbershop.com/", "Black-owned", "Founded 2008. 9 barbers. People, Essence, NewsOne. 5.0 Booksy, 203 reviews."),
        ("No Grease - Eastland", "5741 Central Ave, Charlotte, NC 28212", "28212", "Eastland", None, "https://nogrease.com/", "Black-owned", "Central Ave location."),
        # ZIP 28213 — University City / N Tryon
        ("Fade Factory Barbershop", "1920 Back Creek Dr, Suite A, Charlotte, NC 28213", "28213", "University City", "(704) 598-8080", None, "Black-owned", "4.6 stars, 243 reviews. I Am Black Business verified."),
        ("Overton's Barber & Styling", "5430 North Tryon Rd, Suite #2, Charlotte, NC 28213", "28213", "Hidden Valley", "(704) 509-1240", "http://www.overtonsbarbershop.com/", "Black-owned", "Owner Tait Overton. 20+ years master barber. Engineering graphics degree. 5 employees."),
        ("LNB Tapers Barbershop", "6324 N Tryon St, Ste 102, Charlotte, NC 28213", "28213", "North Tryon", "(704) 910-4722", None, "Black-owned", "Owner Yusef Spate. 5.0 stars."),
        ("Kutt Masters Barbershop", "10901 University City Blvd, Charlotte, NC 28213", "28213", "University City", "(704) 595-7800", "http://kuttmasters.com/", "Black-owned", "University City Blvd."),
        # ZIP 28214 — West Charlotte
        ("Kingdom Cuts", "9115 Samlen Ln #107, Charlotte, NC 28214", "28214", "West Charlotte", "(980) 498-1912", "https://www.kingdomcutsclt.com/", "Black-owned", "Owner Clarence Moore. Grooming You For Success."),
        # ZIP 28262 — University City North
        ("NY 2 QC Kutz", "11915 North Tryon St, Unit F, Charlotte, NC 28262", "28262", "University City", "(704) 910-4574", "https://www.ny2qckutz.com/", "Black-owned", "Since 2016."),
        ("Kut Masters - N Tryon", "9605 N Tryon St, Charlotte, NC 28262", "28262", "University City", "(704) 548-1800", None, "Black-owned", "Second Kut Masters location."),
        # ZIP 28273 — South Charlotte
        ("King Hut Cuts Barbershop", "11130 South Tryon St, Suite 209, Charlotte, NC 28273", "28273", "South Tryon", "(704) 906-2570", None, "Black-owned", "Top Yelp Black-owned."),
        # ZIP 28204 — Dilworth
        ("Major Barbershop", "650 B E Stonewall St, Charlotte, NC 28204", "28204", "Dilworth", "(704) 778-1187", None, "Black-owned", "Salon Lofts. 28 Yelp reviews. Upscale: neck shave, scalp massage, steam towel, beer. Barbers: Niki, Victoria."),
        # ZIP 28205 — Plaza Midwood / Sharon Amity
        ("Charlotte Barber & Beard", "1200 The Plaza Rd, Ste. B, Charlotte, NC 28205", "28205", "Plaza Midwood", None, None, "Black-owned", "5.0 Squire, 92 reviews. Barbers: Terrance Josey, Marcus C., Sean Anderson."),
        ("No Grease School of Tonsorial Arts", "3731 North Sharon Amity Rd, Charlotte, NC 28205", "28205", "Sharon Amity", "(980) 819-9481", "https://nogreasebarberschool.com/", "Black-owned", "Barber school. 3,000+ graduates. 4,200 sq ft. 12-18 month program, 1,528 clock hours. ~15 full-time students. $150K/yr scholarship goal. 'Who Wants to Be a Barber' annual competition. Opened Oct 2016. Tue-Fri 9am-5pm, Sat 9am-1pm."),
        # ZIP 28212 — Independence Blvd (additional)
        ("Diamond Image Cutz", "6721 East Independence Blvd, Charlotte, NC 28212", "28212", "Independence Blvd", None, None, "Black-owned", "Squire listing. Regular Cut $45. Barbers: Aleman, Steven."),
        # ZIP 28270 — Ballantyne
        ("All Cutz Matter Barbershop", "1810 Galleria Blvd, Suite 305, Charlotte, NC 28270", "28270", "Ballantyne", None, None, "Black-owned", "5.0 Booksy, 171 reviews. Solo operator Angie Thompson. $30-$85."),
        # ZIP 28078 — Cornelius
        ("Potts Barber Shop", "Cornelius, NC 28078", "28078", "Cornelius", None, None, "Black-owned", "Est. 1952. Oldest Black-owned business in Cornelius. Historic landmark."),
        # ZIP 28027 — Concord (No Grease franchise)
        ("No Grease - Concord Mills", "8111 Concord Mills Blvd, Ste 149, Concord, NC 28027", "28027", "Concord Mills", "(704) 688-5499", "https://nogrease.com/", "Black-owned", "Concord Mills Mall. Mon-Thu 11am-7pm, Fri-Sat 10am-8pm, Sun 12pm-6pm."),
        # No Grease - Charlotte Premium Outlets
        ("No Grease - Premium Outlets", "5512 New Fashion Way, Charlotte, NC 28278", "28278", "Steele Creek", "(980) 498-7058", "https://nogrease.com/", "Black-owned", "Franchisee Ed Washington. Charlotte Premium Outlets."),
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
        "Goodfellas": [("Regular Haircut", 25), ("Fade", 30), ("Skin Fade", 40), ("Beard Trim", 15), ("Kids Haircut", 20)],
        "Man Cave": [("Regular Haircut", 40), ("Fade", 40), ("Skin Fade", 45), ("Kids Haircut", 25), ("Line-Up / Edge-Up", 15)],
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
        "Major Barbershop": [("Regular Haircut", 35), ("Fade", 40), ("Skin Fade", 45), ("Beard Trim", 20)],
        "Charlotte Barber & Beard": [("Regular Haircut", 40), ("Haircut + Beard Combo", 55), ("Hot Towel Razor Shave", 65), ("Beard Trim", 25), ("Kids Haircut", 30)],
        "Diamond Image": [("Regular Haircut", 45), ("Haircut + Beard Combo", 60)],
        "All Cutz Matter": [("Regular Haircut", 30), ("Fade", 35), ("Head Shave", 70)],
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
        # Bot 4 additions
        ("No Grease - SouthPark (Knights of the Razor)", "Instagram", 24000, 4.5),
        ("No Grease - SouthPark (Knights of the Razor)", "Facebook", 2187, 2.0),
        ("No Grease School of Tonsorial Arts", "Instagram", 24000, 4.5),
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

    # ── BARBERS (real names from Booksy/Yelp/Google/LinkedIn + Bot 5 enrichment) ──
    # Format: (shop_name, barber_name, specialties, notes, instagram, seniority)
    barber_entries = [
        # No Grease — Damian & Jermaine Johnson (founders)
        ("No Grease - Mosaic Village", "Damian Johnson", "Founder, master barber, franchise operations", "Co-founder w/ brother Jermaine. First Black-owned franchise barbershop in US. 13 locations in 4 states. 2,000+ licensed barbers through No Grease Barber School.", "@nogreasebarbershop", "20+ years"),
        ("No Grease - Mosaic Village", "Jermaine Johnson", "Founder, master barber, education", "Co-founder. Runs No Grease Barber School. Trained at Gordon's Historic under mentor.", "@nogreasebarbershop", "20+ years"),
        ("No Grease - Mosaic Village", "Tyler", "Line-ups, professional cuts", "Top-class line-up skills. Consistently praised in reviews.", None, None),
        ("No Grease - Mosaic Village", "Tre", "All-around, loyal clientele", "Clients drive 2+ hours for him. Cult following.", None, None),
        ("No Grease - Mosaic Village", "Alicia Pryor", "Women's cuts, chemical services", "No Grease staff", None, None),
        # Gordon's Historic — celebrity hub
        ("Gordon's Historic Barbershop", "Damu Gordon", "Celebrity barber, NFL clients, precision fades", "Son of shop owner. Listed on Booksy as 'Celebrity NFL Barber Moo Gordon'. Cuts NFL players. Instagram presence. Gordon's is EST. 1935 — trained the No Grease founders.", "@moo_gordon", "10+ years"),
        ("Gordon's Historic Barbershop", "Mr. Smalls", "Creative cuts, The Mad Scientist", "Known as 'The Mad Scientist' for creative designs. Longtime Gordon's barber.", None, "10+ years"),
        ("Gordon's Historic Barbershop", "The Boujie Barber", "Premium cuts, styling", "Gordon's Historic staff. Upscale clientele.", None, None),
        ("Gordon's Historic Barbershop", "Uncle Pete", "Traditional cuts", "Gordon's Historic staff. Old-school technique.", None, "20+ years"),
        # Man Cave
        ("The Man Cave Barbershop Charlotte", "Asa", "Fades, precision cuts", "Never disappoints per reviews. Consistent 5-star Booksy.", None, None),
        ("The Man Cave Barbershop Charlotte", "Dray", "Creative styles, consultations", "Master Barber. Talent and creativity praised in Yelp reviews.", None, "Master Barber"),
        ("The Man Cave Barbershop Charlotte", "Reggie", "Fades, all-around", "5.0 rating, 193 Booksy reviews. Walk-in friendly.", None, None),
        ("The Man Cave Barbershop Charlotte", "Juan", "General cuts", "Man Cave staff", None, None),
        # Da Lucky Spot — Shaun "Lucky" Corbett
        ("Da Lucky Spot Barbershop", "Shaun 'Lucky' Corbett", "Owner, master barber, community leader", "Charlottean of the Year 2015. Obama White House recognition. First Black barber Walmart partnership (2020). Opened Da Lucky Spot Academy Dec 2023. Community pillar.", "@daluckyspot", "15+ years"),
        ("Da Lucky Spot Barbershop", "Reese", "General cuts", "Lucky Spot staff", None, None),
        ("Da Lucky Spot Barbershop", "Ron", "General cuts", "Lucky Spot staff", None, None),
        ("Da Lucky Spot Barbershop", "Toni", "Women's cuts", "Lucky Spot staff. One of few female barbers at Lucky Spot.", None, None),
        # Fade Factory
        ("Fade Factory Barbershop", "Tara Smith (Miss T)", "Owner, all services, bridal/event", "Owner/operator. 4x award-winning barber. Customer of 5+ years loyalty common.", "@fadefactorybarbershop", "10+ years"),
        ("Fade Factory Barbershop", "Phil", "Quick fades", "Fast service. Known for speed + precision.", None, None),
        ("Fade Factory Barbershop", "Odell", "Professional cuts", "Very professional and talented per reviews.", None, None),
        ("Fade Factory Barbershop", "Val", "Kids cuts specialist", "Great with children. Patient.", None, None),
        ("Fade Factory Barbershop", "Walter", "General cuts", "Fade Factory staff", None, None),
        ("Fade Factory Barbershop", "Nicole", "General cuts", "Fade Factory staff", None, None),
        # Goodfellas
        ("Goodfellas Barbershop", "Howard", "Fades, lineups", "Part of 8-barber team. Sunset Road location.", None, None),
        ("Goodfellas Barbershop", "Jazz", "Fades, lineups", "Part of 8-barber team.", None, None),
        ("Goodfellas Barbershop", "Sidney Drake", "Fades, general cuts", "LinkedIn confirmed Goodfellas barber. Professional profile.", None, None),
        # Overton's
        ("Overton's Barber & Styling", "Tait Overton", "Owner, master barber, all services", "20+ year master barber. Engineering graphics degree. 5 employees. Hidden Valley institution.", "@overtonsbarbershop", "20+ years"),
        # Gillespie
        ("Gillespie Barber & Stylist", "Richard Gillespie", "Owner, traditional cuts, styling", "Owner. 6 employees. BBB accredited since 2007. Community institution on N Tryon.", None, "20+ years"),
        ("Gillespie Barber & Stylist", "Kornelius Gillespie", "Co-owner, cuts, styling", "Co-owner with Richard. Family business.", None, "10+ years"),
        # Charlotte Barber & Beard
        ("Charlotte Barber & Beard", "Marcus C.", "Owner, beard sculpt, dye, haircuts", "Owner. 'Marcus The Beard Barber'. 10+ years experience. Cash only. 5.0 Squire, 18 reviews. $45 haircut.", "@marcusthebeardbarber", "10+ years"),
        ("Charlotte Barber & Beard", "Terrance Josey", "Haircuts, beard work, hot towel shave", "5.0 rating, 92 Squire reviews. Most-reviewed barber at the shop.", None, None),
        ("Charlotte Barber & Beard", "Sean Anderson", "General cuts", "Charlotte Barber & Beard staff", None, None),
        # Headlines
        ("Headlines Barbershop", "Steve the Barber", "Owner, precision fades, designs", "4x award-winning. 40K Instagram followers. Featured in People, Essence, NewsOne. 9 barbers on staff.", "@steve_the_barber", "15+ years"),
        # Major Barbershop
        ("Major Barbershop", "Niki", "Upscale cuts, neck shave, scalp massage", "Mentioned in 8+ Yelp reviews. Loyal 4+ year clients. Salon Lofts location.", None, None),
        ("Major Barbershop", "Victoria", "Cuts, shaves", "Major Barbershop staff", None, None),
        # Kingdom Cuts
        ("Kingdom Cuts", "Clarence Moore", "Owner, fades, grooming", "Owner. Motto: 'Grooming You For Success'. West Charlotte.", "@kingdomcutsclt", None),
        # All Cutz Matter
        ("All Cutz Matter Barbershop", "Angie Thompson", "Solo operator, fades, head shaves, designs", "Solo operator. 5.0 Booksy, 171 reviews. Range $30-$85. Ballantyne area.", None, None),
        # Hawk & Fade
        ("Hawk & Fade Barbershop", "Owner (unnamed)", "Fades, beard trims, lineups", "4.9 Booksy, 289 reviews. South End location. Premium positioning.", "@hawkandfade", None),
        # LNB Tapers
        ("LNB Tapers Barbershop", "Yusef Spate", "Owner, tapers, fades", "Owner. 5.0 stars. North Tryon.", None, None),
        # NY 2 QC
        ("NY 2 QC Kutz", "Owner (unnamed)", "NY-style cuts, fades", "Since 2016. University City. NY transplant style.", "@ny2qckutz", None),
        # Bot 4 additions — franchise operators & key staff
        ("No Grease - Northlake", "Ed Washington", "Franchisee, business operations", "Gardner-Webb grad. Microsoft technical exec. Invested ~$180K per location. Gives lead barbers 10% equity. Also runs Premium Outlets + upcoming Houston Galleria.", None, None),
        ("No Grease - Mosaic Village", "Tre Trimz", "Fades, all styles", "Listed on Booksy at Mosaic location. Dedicated clientele.", None, None),
        ("No Grease - Mosaic Village", "Charlie Petty", "Co-founder, visionary", "Co-founder alongside Damian & Jermaine Johnson. Visionary owner.", None, "20+ years"),
        ("Gordon's Historic Barbershop", "Michael Gordon", "Owner, traditional cuts, mentorship", "Owner 33+ years. Wears grandfather Mancel Gordon's WWII dog tags daily. Mentored No Grease founders. Cherry neighborhood institution.", None, "33+ years"),
        ("Goodfellas Barbershop", "Owner (Garinger HS)", "Owner, master barber, all services", "Garinger HS grad. Trained at Hair Styling Institute of Charlotte (graduated 1999). Master Barber since 2000. Won trophies at local hair shows.", None, "20+ years"),
        ("Goodfellas Barbershop", "Co-barber (Savannah)", "Master barber, fades, designs", "Raised in Savannah GA. Cutting hair since age 13. Master Barber License 1996. Moved to Charlotte 2002. Hair show trophy winner.", None, "25+ years"),
    ]

    barber_count = 0
    for comp_name, bname, specs, notes, instagram, seniority in barber_entries:
        if comp_name in shop_ids:
            bid = con.execute("SELECT nextval('seq_barber')").fetchone()[0]
            con.execute(
                "INSERT INTO barbers (barber_id, competitor_id, name, instagram_handle, specialties, seniority, notes, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')",
                [bid, shop_ids[comp_name], bname, instagram, specs, seniority, notes],
            )
            barber_count += 1

    print(f"Loaded {barber_count} barber profiles")

    # ── REVIEWS (real quotes from Google/Yelp/Booksy) ────────────────────
    review_entries = [
        ("No Grease - Mosaic Village", "Google", 5.0, "All the barbers are knowledgeable and will provide a great experience.", 0.9),
        ("No Grease - Mosaic Village", "Yelp", 5.0, "From booking the appt to being offered a beverage, the entire visit was a pleasure!", 0.95),
        ("No Grease - Mosaic Village", "Booksy", 5.0, "One of the best barbershops in Charlotte. Staff is attentive and timely.", 0.9),
        ("No Grease - Mosaic Village", "Birdeye", 4.8, "Tyler is a cool barber that actually listens. His line-up skills are top class.", 0.85),
        ("The Man Cave Barbershop Charlotte", "Booksy", 5.0, "Asa is my barber and he never disappoints.", 0.85),
        ("The Man Cave Barbershop Charlotte", "Yelp", 5.0, "Dray is a Master Barber with talent and creativity.", 0.9),
        ("The Man Cave Barbershop Charlotte", "Google", 4.5, "Professional but yet fun. Rate for a cut beats anyone else.", 0.8),
        ("Fade Factory Barbershop", "Yelp", 5.0, "Absolutely the best barbershop. Customer of 5+ years.", 0.95),
        ("Fade Factory Barbershop", "Yelp", 5.0, "Tara did EXACTLY what I wanted with creative freedom.", 0.95),
        ("Fade Factory Barbershop", "Google", 5.0, "Best southern hospitality barber shop in the Carolinas.", 0.9),
        ("Fade Factory Barbershop", "Google", 5.0, "Haircut, scalp massage, facial before wedding. Complimented for glowing skin.", 0.95),
        ("Goodfellas Barbershop", "Google", 5.0, "Great barbers, great location, great prices, and great service!", 0.9),
        ("Goodfellas Barbershop", "Birdeye", 4.5, "Always met with a friendly smile and the service is exceptional.", 0.85),
        ("Da Lucky Spot Barbershop", "Google", 4.5, "Affordable prices, expertise and attention to detail.", 0.8),
        ("Major Barbershop", "Yelp", 5.0, "A treasure for those who truly desire a PROFESSIONAL Barber.", 0.95),
        ("Major Barbershop", "Yelp", 5.0, "Best men's haircut, shave, and beard trim in the city!", 0.9),
        ("Major Barbershop", "Yelp", 5.0, "Niki is the only one I trust. Been getting cut for over 4 years.", 0.85),
    ]

    review_count = 0
    for comp_name, platform, rating, text, sentiment in review_entries:
        if comp_name in shop_ids:
            rid = con.execute("SELECT nextval('seq_review')").fetchone()[0]
            con.execute(
                "INSERT INTO review_snapshots (id, competitor_id, platform, rating, review_text, sentiment_score) VALUES (?, ?, ?, ?, ?, ?)",
                [rid, shop_ids[comp_name], platform, rating, text, sentiment],
            )
            review_count += 1

    print(f"Loaded {review_count} reviews")

    # ── STRATEGIC MOVES (from Bot 4 deep research) ─────────────────────
    move_entries = [
        # (shop_name, date, move_type, description, source, impact)
        ("No Grease - Mosaic Village", "1997-06-01", "Launch", "No Grease founded by Damian & Jermaine Johnson in Charlotte, NC. Name comes from barbers disliking grease in clients' hair.", "Axios Charlotte", 5),
        ("No Grease - Mosaic Village", "2016-10-01", "Expansion", "No Grease School of Tonsorial Arts opens at 3731 N Sharon Amity Rd. 1,528 clock hours, 12-18 month program.", "nogreasebarberschool.com", 4),
        ("No Grease - Mosaic Village", "2017-01-01", "Franchise", "No Grease begins franchising — first Black-owned franchise barbershop in US. $132K-$278K investment. Licensed in 36 states.", "QCity Metro", 5),
        ("No Grease - SouthPark (Knights of the Razor)", "2021-02-26", "Launch", "Knights of the Razor opens inside SouthPark Mall — premium concept with 'The Royal Treatment' service.", "Axios Charlotte", 4),
        ("No Grease - SouthPark (Knights of the Razor)", "2021-03-03", "Controversy", "SouthPark Mall terminates No Grease lease early. Public outcry forces reversal. Mall allows Knights of the Razor to stay.", "WCNC / WFAE", 3),
        ("No Grease - Northlake", "2021-10-14", "Franchise", "Ed Washington (Gardner-Webb grad, Microsoft exec) becomes franchisee. Invested ~$180K per location. Gives lead barbers 10% equity in business.", "Axios Charlotte", 4),
        ("No Grease - Mosaic Village", "2022-01-01", "Expansion", "No Grease opens Arundel Mills Mall location in Maryland — first location outside the Carolinas.", "Simon Properties", 4),
        ("Da Lucky Spot Barbershop", "2019-09-26", "Launch", "First Black-owned barbershop inside a Walmart opens at Wilkinson Blvd. Walmart presents $25K check.", "Atlanta Black Star / Walmart Corporate", 5),
        ("Da Lucky Spot Barbershop", "2023-12-01", "Expansion", "Da Lucky Spot Academy opens. Now 5 Walmart locations across NC, SC, GA.", "Voyage South Carolina", 4),
        ("Da Lucky Spot Barbershop", "2015-01-01", "Community", "Shaun Corbett cofounds Cops & Barbers 501(c)(3) with Det. Garry McFadden. Bridges police-community relations.", "WCNC", 3),
        ("Goodfellas Barbershop", "2007-01-01", "Launch", "Goodfellas opens at 4005 Sunset Rd. Owner: Garinger HS grad, master barber since 2000.", "goodfellasbarbershop.us", 3),
        ("The Man Cave Barbershop Charlotte", "2014-01-01", "Launch", "Man Cave Barbershop opens on Westmere Ave. 12+ years in business by 2026.", "Booksy", 3),
    ]

    move_count = 0
    for comp_name, mdate, mtype, desc, source, impact in move_entries:
        if comp_name in shop_ids:
            mid = con.execute("SELECT nextval('seq_move')").fetchone()[0]
            con.execute(
                "INSERT INTO competitor_moves (move_id, competitor_id, move_date, move_type, description, source_url, impact_rating) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [mid, shop_ids[comp_name], mdate, mtype, desc, source, impact],
            )
            move_count += 1

    print(f"Loaded {move_count} strategic moves")

    # ── SUMMARY ──────────────────────────────────────────────────────────
    total = con.execute("SELECT COUNT(*) FROM competitors").fetchone()[0]
    print(f"\n{'='*60}")
    print(f"  SEED COMPLETE")
    print(f"  {total} competitors | {price_count} prices | {social_count} social")
    print(f"  {barber_count} barbers | {review_count} reviews | {move_count} moves")
    print(f"  Database: {DB_PATH}")
    print(f"{'='*60}")

    con.close()


if __name__ == "__main__":
    seed()
