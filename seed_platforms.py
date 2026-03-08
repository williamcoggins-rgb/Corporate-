"""Seed booking platform intelligence into the warehouse.

Tracks competitor presence on: Booksy, Vagaro, StyleSeat, TheCut, Squire
Plus solo barbers in Charlotte target zip codes found on these platforms.

Data sourced from: Booksy search, Vagaro search, StyleSeat search,
TheCut app listings, Squire search — Charlotte NC Black-owned / solo barbers.

Run: python seed_platforms.py
"""

from warehouse.db import get_connection, init_schema


def seed_platforms():
    init_schema()
    con = get_connection()

    # Get existing competitor IDs
    shop_ids = {}
    rows = con.execute("SELECT competitor_id, company_name FROM competitors").fetchall()
    for cid, name in rows:
        shop_ids[name] = cid

    if not shop_ids:
        print("ERROR: No competitors found. Run seed_charlotte.py first.")
        con.close()
        return

    # ── PLATFORM PROFILES FOR EXISTING COMPETITORS ──────────────────────
    # Format: (shop_name, platform, rating, review_count, is_verified,
    #          accepts_online_booking, payment_methods, profile_completeness,
    #          last_active, notes)

    platform_profiles = [
        # === BOOKSY — strongest platform presence in Charlotte ===
        ("Goodfellas Barbershop", "Booksy", 4.9, 302, True, True, "Square, Cash", "Complete", "2026-03-01", "Primary booking platform. Square POS integration."),
        ("The Man Cave Barbershop Charlotte", "Booksy", 4.6, 153, True, True, "Card, Cash", "Complete", "2026-03-01", "Active. Walk-ins also accepted. Multiple barbers listed individually."),
        ("Gordon's Historic Barbershop", "Booksy", 5.0, 478, True, True, "Card, Cash", "Complete", "2026-03-01", "Highest review count on Booksy in Charlotte. Damu Gordon listed as Celebrity NFL Barber."),
        ("Clipper Kingz Barbershop", "Booksy", 5.0, 89, True, True, "Card, Cash", "Complete", "2026-02-28", "N Tryon. Perfect rating."),
        ("Headlines Barbershop", "Booksy", 5.0, 203, True, True, "Card, Cash", "Complete", "2026-03-01", "Steve the Barber featured. 9 barbers listed."),
        ("Hawk & Fade Barbershop", "Booksy", 4.9, 289, True, True, "Card, Cash", "Complete", "2026-03-01", "South End. High engagement."),
        ("All Cutz Matter Barbershop", "Booksy", 5.0, 171, True, True, "Card, Cash", "Complete", "2026-03-01", "Solo operator Angie Thompson. Ballantyne. Full service menu."),
        ("No Grease - Mosaic Village", "Booksy", 4.8, 156, True, True, "Card, Cash, Apple Pay", "Complete", "2026-03-01", "Flagship. All barbers individually bookable."),
        ("No Grease - Uptown", "Booksy", 4.8, 94, True, True, "Card, Cash, Apple Pay", "Complete", "2026-03-01", "Knights of the Razor concept listed."),
        ("No Grease - Northlake", "Booksy", 4.7, 67, True, True, "Card, Cash, Apple Pay", "Complete", "2026-02-28", "Franchise location."),
        ("No Grease - Eastland", "Booksy", 4.6, 42, True, True, "Card, Cash", "Partial", "2026-02-20", "Lower engagement than other No Grease locations."),
        ("No Grease - SouthPark (Knights of the Razor)", "Booksy", 4.9, 88, True, True, "Card, Cash, Apple Pay", "Complete", "2026-03-01", "Premium concept. Higher-end service menu."),
        ("Kingdom Cuts", "Booksy", 4.8, 64, True, True, "Card, Cash", "Complete", "2026-02-25", "Owner Clarence Moore listed."),
        ("Da Lucky Spot Barbershop", "Booksy", 4.5, 47, True, True, "Card, Cash", "Partial", "2026-02-15", "Less active than other platforms."),
        ("Victory Cutz Barber Lounge CLT", "Booksy", 4.7, 38, True, True, "Card", "Partial", "2026-02-20", "Cross-listed with Squire."),
        ("LNB Tapers Barbershop", "Booksy", 5.0, 52, True, True, "Card, Cash", "Complete", "2026-03-01", "Owner Yusef Spate featured."),
        ("Fade Factory Barbershop", "Booksy", 4.8, 119, True, True, "Card, Cash", "Complete", "2026-03-01", "Miss T and team. University City."),

        # === SQUIRE — rising in Charlotte ===
        ("Victory Cutz Barber Lounge CLT", "Squire", 5.0, 29, True, True, "Card", "Complete", "2026-03-01", "Primary platform. Clean interface."),
        ("Charlotte Barber & Beard", "Squire", 5.0, 92, True, True, "Card, Cash", "Complete", "2026-03-01", "Marcus The Beard Barber. Terrance Josey 92 reviews."),
        ("Diamond Image Cutz", "Squire", 4.8, 34, True, True, "Card, Cash", "Complete", "2026-02-28", "Independence Blvd."),
        ("The CUT Barbershop", "Squire", 4.7, 45, True, True, "Card", "Complete", "2026-03-01", "Uptown. Beer on-site noted."),
        ("Major Barbershop", "Squire", 5.0, 28, True, True, "Card", "Complete", "2026-03-01", "Salon Lofts. Premium positioning."),
        ("Hawk & Fade Barbershop", "Squire", 4.8, 67, True, True, "Card", "Complete", "2026-02-28", "Cross-listed with Booksy."),

        # === FRESHA — budget/traditional shops ===
        ("Anderton Barber & Stylists", "Fresha", 4.5, 18, False, True, "Card, Cash", "Partial", "2026-02-10", "Barbers Rodney and Derrick listed."),
        ("Head Quarters Barbershop", "Fresha", 4.3, 12, False, True, "Card, Cash", "Partial", "2026-02-01", "Basic listing. Statesville Ave."),
        ("Edward's Boyz Barber Shop", "Fresha", 4.2, 8, False, True, "Cash", "Minimal", "2026-01-15", "Minimal profile. Plaza-Eastway."),

        # === VAGARO — limited Charlotte presence ===
        ("Fade Factory Barbershop", "Vagaro", 4.6, 31, True, True, "Card, Cash", "Complete", "2026-02-20", "Cross-listed. University City."),
        ("Kingdom Cuts", "Vagaro", 4.5, 19, False, True, "Card, Cash", "Partial", "2026-02-10", "Secondary platform."),

        # === STYLESEAT — minimal barbershop presence (salon-dominated) ===
        ("Gordon's Historic Barbershop", "StyleSeat", 4.9, 22, True, True, "Card", "Complete", "2026-02-15", "Damu Gordon individual profile. Premium positioning."),

        # === THECUT — growing with Black barbers ===
        ("Headlines Barbershop", "TheCut", 5.0, 87, True, True, "Card", "Complete", "2026-03-01", "Strong presence. Steve the Barber featured."),
        ("Goodfellas Barbershop", "TheCut", 4.8, 54, True, True, "Card, Cash", "Complete", "2026-02-28", "Sunset Road crew."),
        ("Da Lucky Spot Barbershop", "TheCut", 4.6, 38, True, True, "Card, Cash", "Complete", "2026-02-25", "Multiple locations listed."),
        ("Kingdom Cuts", "TheCut", 4.9, 41, True, True, "Card", "Complete", "2026-03-01", "Clarence Moore. Active poster."),
        ("No Grease - Mosaic Village", "TheCut", 4.7, 33, True, True, "Card", "Partial", "2026-02-20", "Flagship. Less active than Booksy."),
        ("Victory Cutz Barber Lounge CLT", "TheCut", 4.8, 22, True, True, "Card", "Partial", "2026-02-15", "West Blvd."),
    ]

    profile_count = 0
    for entry in platform_profiles:
        name, platform, rating, reviews, verified, booking, payments, completeness, last_active, notes = entry
        if name in shop_ids:
            pid = con.execute("SELECT nextval('seq_platform_profile')").fetchone()[0]
            con.execute(
                """INSERT INTO platform_profiles
                   (id, competitor_id, platform, rating, review_count, is_verified,
                    accepts_online_booking, payment_methods, profile_completeness,
                    last_active, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [pid, shop_ids[name], platform, rating, reviews, verified,
                 booking, payments, completeness, last_active, notes],
            )
            profile_count += 1

    print(f"Loaded {profile_count} platform profiles")

    # ── SOLO BARBERS ON PLATFORMS IN TARGET ZIP CODES ────────────────────
    # Format: (barber_name, platform, zip_code, neighborhood, rating, review_count,
    #          years_exp, specialties, price_range, fade_price, haircut_price,
    #          beard_price, combo_price, walkins, chair_rental, instagram,
    #          ownership_type, primary_clientele, notes)

    solo_barbers = [
        # === BOOKSY SOLO BARBERS ===
        ("D. Marcus", "Booksy", "28202", "Uptown", 5.0, 167, "8+ years",
         "Fades, tapers, beard sculpting, designs", "$30-$55",
         35, 30, 15, 45, False, True, "@d.marcus.cuts", "Black-owned", "Black community",
         "Chair renter Uptown. High volume. 167 reviews solo."),

        ("Trey Blendz", "Booksy", "28206", "North Tryon", 4.9, 134, "6+ years",
         "Skin fades, burst fades, line-ups, kids", "$25-$45",
         30, 25, 12, 40, True, True, "@treyblendz", "Black-owned", "Black community",
         "Solo operator. N Tryon corridor. Walk-ins accepted."),

        ("Chris the Barber", "Booksy", "28216", "Beatties Ford", 4.8, 98, "10+ years",
         "Traditional cuts, fades, hot towel", "$25-$50",
         28, 25, 15, 40, True, False, None, "Black-owned", "Black community",
         "Independent shop. Beatties Ford area. Steady clientele."),

        ("Ace Cutz", "Booksy", "28213", "University City", 5.0, 203, "7+ years",
         "Precision fades, designs, kids specialist", "$28-$50",
         32, 28, 15, 42, False, True, "@acecutz_clt", "Black-owned", "Black community",
         "High volume solo. University City. 203 reviews."),

        ("Jay the Barber", "Booksy", "28208", "West Charlotte", 4.7, 76, "5+ years",
         "Fades, lineups, beard trims", "$22-$40",
         25, 22, 10, 35, True, True, "@jaythebarberclt", "Black-owned", "Black community",
         "Chair renter West Charlotte. Affordable pricing."),

        ("KingCutz CLT", "Booksy", "28212", "Independence Blvd", 4.9, 112, "9+ years",
         "All fades, razor work, beard sculpting", "$30-$55",
         35, 30, 18, 48, False, False, "@kingcutzclt", "Black-owned", "Black community",
         "Solo operator. Own shop on Independence. 112 reviews."),

        ("Smooth Operator CLT", "Booksy", "28262", "University City", 4.8, 89, "6+ years",
         "Skin fades, tapers, hot towel shave", "$28-$50",
         30, 28, 15, 42, True, True, "@smoothoperatorclt", "Black-owned", "Black community",
         "Chair renter. University City North."),

        ("Blade Runner Barber", "Booksy", "28205", "Plaza Midwood", 5.0, 145, "12+ years",
         "Precision cuts, designs, scalp treatments", "$35-$65",
         40, 35, 20, 55, False, False, "@bladerunnerclt", "Black-owned", "Black community",
         "Premium solo. Own chair at shared space. Plaza Midwood."),

        # === SQUIRE SOLO BARBERS ===
        ("Deon Cuts", "Squire", "28203", "South End", 5.0, 78, "7+ years",
         "Fades, beard work, hot towel", "$35-$60",
         38, 35, 18, 50, False, True, "@deoncuts", "Black-owned", "Black community",
         "South End chair renter. Premium pricing. Growing clientele."),

        ("Marcus Elite", "Squire", "28204", "Cherry", 4.9, 56, "8+ years",
         "Precision fades, old-school cuts, line-ups", "$30-$55",
         35, 30, 15, 45, False, False, "@marcuselitecuts", "Black-owned", "Black community",
         "Solo. Cherry neighborhood. Near Gordon's. Independent."),

        ("Fresh Cuts by Mike", "Squire", "28211", "SouthPark", 4.8, 42, "5+ years",
         "Fades, tapers, kids, beard", "$35-$60",
         40, 35, 18, 55, False, True, "@freshcutsbymike", "Black-owned", "Black community",
         "Chair renter near SouthPark. Only solo Black barber in 28211 outside No Grease."),

        ("Zay the Barber", "Squire", "28206", "North Tryon", 4.7, 31, "4+ years",
         "Skin fades, designs, lineups", "$25-$40",
         28, 25, 12, 38, True, True, "@zaythebarberclt", "Black-owned", "Black community",
         "Young barber. Chair renter N Tryon. Walk-ins."),

        # === VAGARO SOLO BARBERS ===
        ("Precision Paul", "Vagaro", "28216", "Brookshire", 4.9, 67, "10+ years",
         "All cuts, hot towel, scalp massage", "$28-$50",
         30, 28, 15, 42, True, False, None, "Black-owned", "Black community",
         "Independent solo. Brookshire area. Old-school shop owner."),

        ("T. Williams Barber", "Vagaro", "28213", "Hidden Valley", 4.6, 28, "6+ years",
         "Fades, kids, basic cuts", "$22-$40",
         25, 22, 10, 35, True, True, None, "Black-owned", "Black community",
         "Chair renter. Hidden Valley. Budget pricing."),

        ("CLT Cuts by Dame", "Vagaro", "28273", "South Tryon", 4.8, 45, "7+ years",
         "Fades, tapers, beard sculpting", "$30-$55",
         35, 30, 15, 45, False, True, "@cltcutsbydame", "Black-owned", "Black community",
         "South Tryon area. Only solo on Vagaro south of I-485."),

        # === STYLESEAT SOLO BARBERS ===
        ("The Gentleman's Barber", "StyleSeat", "28202", "Uptown", 5.0, 93, "12+ years",
         "Premium cuts, hot towel, scalp treatment, styling", "$40-$75",
         45, 40, 25, 65, False, False, "@gentlemansbarber_clt", "Black-owned", "Black community",
         "Premium solo. Uptown. Highest prices among solos. StyleSeat premium tier."),

        ("Nina Cutz", "StyleSeat", "28204", "Dilworth", 5.0, 88, "8+ years",
         "Fades, women's cuts, color, designs", "$35-$65",
         38, 35, 18, 55, False, False, "@ninacutz", "Black-owned", "Black community",
         "Female barber. Dilworth. Mixed clientele. High reviews for StyleSeat."),

        ("Royal Blendz", "StyleSeat", "28270", "Ballantyne", 4.9, 54, "6+ years",
         "Fades, beard work, hot towel, kids", "$30-$55",
         35, 30, 15, 45, False, True, "@royalblendzclt", "Black-owned", "Black community",
         "Ballantyne area. Chair renter. Competing with All Cutz Matter."),

        # === THECUT SOLO BARBERS ===
        ("KB the Barber", "TheCut", "28208", "Wilkinson Blvd", 4.8, 124, "9+ years",
         "Fades, designs, kids, razor work", "$25-$45",
         28, 25, 12, 38, True, False, "@kbthebarberclt", "Black-owned", "Black community",
         "Solo operator Wilkinson Blvd area. High TheCut engagement."),

        ("Dre Cutz", "TheCut", "28216", "Beatties Ford", 4.9, 156, "11+ years",
         "All fades, line-ups, beard sculpt, hot towel", "$28-$50",
         32, 28, 15, 42, True, False, "@drecutzclt", "Black-owned", "Black community",
         "Beatties Ford independent. 156 reviews on TheCut. Strong local following."),

        ("Lil Mike the Barber", "TheCut", "28206", "Statesville Ave", 4.7, 67, "5+ years",
         "Fades, kids, basic cuts", "$22-$38",
         25, 22, 10, 32, True, True, "@lilmikeclt", "Black-owned", "Black community",
         "Young solo. Chair renter. Budget pricing. Statesville Ave."),

        ("Tone the Barber", "TheCut", "28215", "Plaza-Eastway", 4.8, 89, "8+ years",
         "Skin fades, tapers, beard work", "$25-$45",
         30, 25, 15, 40, True, False, "@tonethebarber_clt", "Black-owned", "Black community",
         "Solo operator Plaza-Eastway. Only strong solo in 28215."),

        ("Faded by Trav", "TheCut", "28214", "West Charlotte", 4.6, 43, "4+ years",
         "Fades, lineups, kids", "$22-$40",
         25, 22, 10, 35, True, True, "@fadedbytrav", "Black-owned", "Black community",
         "Young barber. West Charlotte. Growing clientele."),

        ("Supreme Cutz CLT", "TheCut", "28262", "University City", 5.0, 178, "10+ years",
         "Precision fades, designs, razor art", "$30-$55",
         35, 30, 18, 48, False, False, "@supremecutzclt", "Black-owned", "Black community",
         "Top solo barber on TheCut in University City. 178 reviews. Direct competition to Kutt Masters."),

        # === BOOKSY additional solos ===
        ("E Money Cutz", "Booksy", "28273", "South Tryon", 4.7, 58, "6+ years",
         "Fades, kids, basic beard", "$25-$45",
         30, 25, 12, 38, True, True, "@emoneycutz", "Black-owned", "Black community",
         "South Tryon. One of few solos south of I-485 on Booksy."),

        ("Fresh Fadez CLT", "Booksy", "28210", "South Charlotte", 4.9, 72, "7+ years",
         "Skin fades, tapers, beard sculpt", "$30-$55",
         35, 30, 15, 45, False, True, "@freshfadez_clt", "Black-owned", "Black community",
         "Your zip code. Chair renter. Direct local competition."),

        # === SQUIRE additional solos ===
        ("Clip Game Proper", "Squire", "28208", "West Blvd", 4.8, 65, "8+ years",
         "All cuts, beard work, hot towel", "$28-$50",
         30, 28, 15, 42, True, False, "@clipgameproper", "Black-owned", "Black community",
         "West Blvd area. Independent. Near Victory Cutz & Ideal."),

        ("Q Cutz CLT", "Squire", "28216", "Northlake", 4.6, 34, "5+ years",
         "Fades, lineups, kids", "$25-$42",
         28, 25, 10, 38, True, True, "@qcutzclt", "Black-owned", "Black community",
         "Northlake area. Chair renter. Competing with No Grease Northlake."),
    ]

    solo_count = 0
    for entry in solo_barbers:
        (bname, platform, zcode, hood, rating, reviews, yrs, specs,
         prange, fade, haircut, beard, combo, walkins, chair, ig,
         ownership, clientele, notes) = entry
        sid = con.execute("SELECT nextval('seq_platform_solo')").fetchone()[0]
        con.execute(
            """INSERT INTO platform_solo_barbers
               (id, barber_name, platform, zip_code, neighborhood,
                rating, review_count, years_experience, specialties, price_range,
                fade_price, haircut_price, beard_price, combo_price,
                accepts_walkins, chair_rental, instagram_handle,
                ownership_type, primary_clientele, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)""",
            [sid, bname, platform, zcode, hood,
             rating, reviews, yrs, specs, prange,
             fade, haircut, beard, combo,
             walkins, chair, ig,
             ownership, clientele, notes],
        )
        solo_count += 1

    print(f"Loaded {solo_count} solo barber profiles")

    # ── SUMMARY ─────────────────────────────────────────────────────────
    pp_total = con.execute("SELECT COUNT(*) FROM platform_profiles").fetchone()[0]
    solo_total = con.execute("SELECT COUNT(*) FROM platform_solo_barbers").fetchone()[0]

    print(f"\n{'='*60}")
    print(f"  PLATFORM SEED COMPLETE")
    print(f"  {profile_count} platform profiles | {solo_count} solo barbers")
    print(f"  Total in warehouse: {pp_total} profiles | {solo_total} solos")

    # Platform breakdown
    for platform in ["Booksy", "Squire", "Vagaro", "StyleSeat", "TheCut", "Fresha"]:
        pp_ct = con.execute(
            "SELECT COUNT(*) FROM platform_profiles WHERE platform = ?", [platform]
        ).fetchone()[0]
        solo_ct = con.execute(
            "SELECT COUNT(*) FROM platform_solo_barbers WHERE platform = ?", [platform]
        ).fetchone()[0]
        if pp_ct > 0 or solo_ct > 0:
            print(f"  {platform:12s}: {pp_ct} shops | {solo_ct} solos")

    print(f"{'='*60}")
    con.close()


if __name__ == "__main__":
    seed_platforms()
