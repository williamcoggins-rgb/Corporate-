# Corporate Governance — Competitive Intelligence Warehouse

## Mission

Build and maintain a data-driven competitive intelligence system for the Charlotte, NC barber industry. Track local competitors — primarily leading Black barbershops in minority-serving zip codes — and monitor national/global tech innovators reshaping the barber trade.

---

## Scope

### Local Intelligence (Charlotte Metro)

**Priority Zip Codes (Minority-Serving):**

| Zip   | Area                        | Notes                          |
|-------|-----------------------------|--------------------------------|
| 28202 | Uptown / Center City        | High foot traffic, professional clientele |
| 28203 | South End / Wilmore         | Rapid growth corridor          |
| 28205 | Plaza Midwood / NoDa        | Culture-heavy, younger demos   |
| 28208 | West Charlotte / Seversville| Deep community roots           |
| 28206 | North Charlotte / Hidden Valley | Legacy neighborhood shops   |
| 28212 | East Charlotte / Albemarle Rd | Diverse, underserved market  |
| 28215 | Eastway / Shamrock          | High-density residential       |
| 28216 | Beatties Ford / University City | Historic Black business corridor |
| 28217 | Steele Creek / Arrowood     | Suburban growth area           |
| 28269 | University Area / Mallard Creek | College + family market     |

> Expand as needed. Surrounding towns: Gastonia, Concord, Kannapolis, Monroe, Huntersville, Matthews, Mint Hill.

**Target Competitors:**
- Independent Black-owned barbershops (primary focus)
- Multi-chair shops and mini-chains (2-5 locations)
- Premium/luxury barbershops (Scissors & Scotch, etc.)
- Mobile barbers and house-call operators
- Hybrid concepts (barber + lounge, barber + retail)

**Named Competitors to Seed First:**
1. No Grease Barber & Beauty Lounge (multiple CLT locations)
2. Modern Classics Barbershop
3. The Man Cave Barbershop
4. Shear Excellence Barbershop
5. Midwood Barbers
6. Fade Factory
7. Colonial Barbershop
8. Fresh Kutz
9. Major League Barber Lounge
10. Prestige Barbershop

> This list grows as the warehouse discovers new competitors through reviews, social, and local search.

### Broad Intelligence (Industry-Wide)

**Tech Innovators to Track:**
- Booking platforms: Booksy, Vagaro, Squire, Boulevard
- POS / shop management: theCut, Square for Barbershops
- Education / content: Andis, Wahl, BabylissPRO (influencer programs)
- Marketplace disruptors: mobile barber apps, subscription grooming
- AI/tech plays: virtual try-on, style recommendation engines

---

## Data Collection Framework

### Tier 1 — Street-Level Scouts (Extraction)

| Bot Role | Cadence | What It Pulls | Primary Sources |
|----------|---------|---------------|-----------------|
| **Pricing & Services Scout** | Daily (heavy on weekends) | Haircut prices (regular, fade, skin fade, beard trim, hot shave, line-up), packages, add-ons (scalp massage, hot towel), memberships | Google Business, Booksy, Vagaro, shop websites |
| **Review & Vibe Harvester** | Every 4-8 hours | Ratings, review text, keywords ("clean fade", "long wait", "vibe"), reviewer photos | Google Reviews, Yelp, Facebook, Booksy |
| **Social & Content Listener** | Hourly | Posts, before/after photos, barber highlights, events, promos, engagement metrics | Instagram, TikTok (public), Facebook, X |
| **Shop Status Watcher** | Weekly + triggered | Hours changes, new locations, remodel photos, hiring posts, closures | Google Business, social, job boards |

**Key Signals to Flag:**
- Price undercuts (competitor drops fade below your rate)
- Flash promos ("$10 off first cut this week")
- Viral content (line-up videos breaking 10K+ views)
- New barber hires or departures
- Shop openings within 2 miles of your location

### Tier 2 — Detail Crew (Transformation & Enrichment)

| Bot Role | Trigger | What It Does |
|----------|---------|-------------|
| **Normalization Agent** | On every ingest | Standardize shop names, service names ("fade" vs "taper fade" vs "drop fade"), prices to numbers, locations to neighborhoods. Handle multi-location chains correctly. |
| **Barber-Level Enricher** | When data available | Tag individual barbers by name, specialties (fades, razor work, beard sculpting), client sentiment. Build a talent map — who's drawing crowds, who's rising. |
| **Delta & Trend Spotter** | After each load | Detect price changes, review volume spikes, rating shifts, new services added. Score threat level per competitor. |

### Tier 3 — Analytics Team (Loading & KPIs)

| Bot Role | Cadence | Output |
|----------|---------|--------|
| **Warehouse Loader** | Nightly | Merge raw data into warehouse tables. Version price/service history (slowly changing dimensions). |
| **Competitor Scorecard** | Post-load | Per-competitor scores: avg price, review sentiment index, social engagement rank, momentum score. |
| **Neighborhood Ranker** | Weekly | Aggregate by zip/neighborhood — who dominates NoDa? Who's rising on Beatties Ford? |

### Tier 4 — Early Warning System (Alerts)

| Alert | Trigger | Action |
|-------|---------|--------|
| **Price War Alert** | Competitor drops key service >10% | Notify with suggested counter-move |
| **Reputation Radar** | 3+ negative reviews in 48hrs mentioning same issue | Flag issue and affected competitor |
| **Talent Movement** | Barber departure/hire detected | Alert — poaching risk or recruitment opportunity |
| **Expansion Alert** | New shop opens within target zip codes | Map proximity, assess threat |
| **Weekly Digest** | Every Sunday | Top price movers, new hires, review trends, social winners, "what to watch" |

---

## Data Model

### Core Entities

```
competitors          — Shop profiles (name, location, zip, type, owner demographics)
competitor_products  — Services & pricing (fade $35, beard trim $15, packages)
competitor_financials — Revenue estimates, funding (for tech companies), growth signals
competitor_moves     — Strategic timeline (new location, rebrand, barber hire, promo launch)
competitor_social    — Platform metrics over time (IG followers, engagement, review counts)
```

### Planned Extensions

```
barbers              — Individual barber profiles linked to shops
barber_specialties   — Tagged skills per barber (fades, razor, kids, etc.)
neighborhoods        — Zip code / area metadata, demographics, market saturation
price_history        — Time-series of service prices per competitor
review_snapshots     — Raw review data with sentiment scores
alerts_log           — History of all triggered alerts and responses taken
```

---

## Governance Rules

### Data Quality

1. **No fabricated data.** Every record must trace to a public source (URL, screenshot, or API response).
2. **Freshness standards.** Pricing data older than 30 days gets flagged stale. Reviews processed within 24 hours.
3. **Deduplication.** Normalization agent runs on every ingest. No duplicate shop entries.
4. **Source attribution.** Every `competitor_move` and `competitor_financial` record must include a `source_url` or `source_note`.

### Ethical Collection

1. **Public data only.** Scrape only publicly available information (Google Business, public social profiles, public review sites).
2. **No fake reviews.** Never post, solicit, or manipulate competitor reviews.
3. **No impersonation.** Never create fake accounts to access competitor systems.
4. **Respect robots.txt and rate limits.** Throttle all automated collection.
5. **Community first.** This warehouse exists to compete smarter, not to harm other Black-owned businesses. Intelligence informs strategy — it doesn't drive hostility.

### Access & Security

1. **Warehouse file lives local.** The DuckDB database stays in `data/` (gitignored). No competitor data in version control.
2. **Exports are controlled.** JSON exports go to `data/exports/` (also gitignored).
3. **No PII collection.** Do not store customer names, phone numbers, or private information from reviews.

---

## Implementation Phases

### Phase 1 — Foundation (Current)
- [x] Data warehouse schema (DuckDB)
- [x] CLI interface
- [x] Bulk load API
- [ ] Seed top 10-15 Charlotte competitors
- [ ] Add barber-level and neighborhood tables
- [ ] Populate initial pricing data

### Phase 2 — Collection
- [ ] Pricing Scout (manual-assisted, then automated)
- [ ] Review Harvester (Google + Yelp)
- [ ] Social Listener (Instagram focus)
- [ ] Normalization Agent

### Phase 3 — Analysis
- [ ] Delta & Trend Spotter
- [ ] Competitor Scorecards
- [ ] Neighborhood rankings
- [ ] Price comparison reports

### Phase 4 — Alerts & Automation
- [ ] Price War alerts
- [ ] Reputation Radar
- [ ] Weekly Digest generation
- [ ] Talent movement tracking

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-08 | Built warehouse on DuckDB (local, no cloud dependency) | Zero cost, fast analytics, full control over data |
| 2026-03-08 | Focus on minority zip codes + Black barbershops first | Core competitive set — this is where the real battle is |
| 2026-03-08 | Track tech innovators separately from local competitors | Different data signals — funding/product launches vs. pricing/reviews |

---

*This document is the single source of truth for how competitive intelligence is collected, stored, and used. Update it as the warehouse evolves.*
