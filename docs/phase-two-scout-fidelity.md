# Phase Two: Scout Data Fidelity

## The Problem

The 5 Tier 1 scouts (pricing_scout, review_harvester, social_listener, shop_watcher, platform_scout) collect competitive intelligence by delegating to `run_agent_task()`, which launches a Claude managed agent session. The managed agent performs web searches and returns results that the scout's ingestion methods write to the warehouse.

The fidelity ceiling is determined by what Claude can find via web search in a single session. This works — the warehouse has real data — but it has structural limitations:

1. **Web search is broad, not targeted.** Claude searches Google for "barbershop prices Charlotte NC" rather than hitting a specific Booksy API endpoint. Results depend on what Google surfaces that day.
2. **No persistent scraping.** Each scout run starts fresh. There's no session continuity, no cookie state, no login to platforms that gate data behind accounts.
3. **Rate and coverage gaps.** A single managed agent session has a time and token budget. Covering 80+ competitors across 5 data dimensions (price, reviews, social, moves, platforms) in one session is ambitious. Some shops get skipped or get stale data.
4. **No structured API access.** Booksy, Yelp, Google Places, Instagram, and StyleSeat all have APIs (some official, some unofficial). The scouts don't use any of them — they rely on Claude interpreting search result snippets.
5. **Verification gap.** There's no automated way to confirm whether a price Claude found is current or from a cached/old page.

## Current Architecture

```
Scheduler (cron)
  -> run_tier1() -> run_tier("tier1")
     -> PricingScout.run()    -> run_agent_task("tier1") -> Claude web search -> ingest methods -> price_history
     -> ReviewHarvester.run() -> run_agent_task("tier1") -> Claude web search -> ingest methods -> review_snapshots
     -> SocialListener.run()  -> run_agent_task("tier1") -> Claude web search -> ingest methods -> competitor_social
     -> ShopWatcher.run()     -> run_agent_task("tier1") -> Claude web search -> ingest methods -> competitor_moves
     -> PlatformScout.run()   -> run_agent_task("tier1") -> Claude web search -> ingest methods -> platform_profiles
```

All 5 scouts share the same execution pattern: `execute()` calls `run_agent_task()` which creates a managed agent session, Claude searches the web, and calls tool functions that write to the warehouse. The data is real (not hallucinated), but it's only as fresh and complete as what a single web search session can find.

## Options for Improvement

### Option A: Structured API Integrations

Wire each scout to call real APIs instead of (or in addition to) web search.

| Scout | API Source | Access | Difficulty |
|---|---|---|---|
| pricing_scout | Booksy API, Squire API | Unofficial / requires auth | Medium |
| review_harvester | Google Places API (official), Yelp Fusion API (official) | API keys, rate limits | Low-Medium |
| social_listener | Instagram Graph API, Meta Business Suite | Requires business account | Medium-High |
| shop_watcher | Google Places API (place details, status) | API key | Low |
| platform_scout | Booksy search, StyleSeat search, Vagaro search | Unofficial scraping | Medium |

**What changes:**
- Each scout's `execute()` method calls the real API directly (via `requests` or the platform SDK) instead of delegating to `run_agent_task()`.
- API responses are structured JSON — no LLM interpretation needed for data extraction.
- The existing ingestion methods (`_ingest_price()`, `_ingest_review()`, etc.) stay the same; only the data source changes.
- `managed_agent.py` and `TIER_TASKS` are NOT touched. The scouts bypass the managed agent for API calls.

**Tradeoffs:**
- (+) Highest fidelity: structured data, no interpretation errors.
- (+) Repeatable: same query returns same results.
- (+) Faster: API call vs. multi-turn agent session.
- (-) API keys cost money (Google Places: $17/1K requests; Yelp Fusion: free tier 5K/day).
- (-) Some platforms (Booksy, StyleSeat) have no official public API — requires reverse-engineering or scraping.
- (-) Instagram Graph API requires a linked Facebook Business account and app review.
- (-) Each API has its own auth flow, rate limits, and error handling.
- (-) More code to maintain per scout.

**Recommended starting point:** Google Places API for review_harvester and shop_watcher. Official, well-documented, covers reviews + place status + hours + photos. One API key, two scouts improved.

### Option B: Headless Browser Scraping

Use Playwright or Selenium to visit actual competitor pages and extract structured data.

**What changes:**
- Add a `scraper` module with functions like `scrape_booksy_profile(url)`, `scrape_google_business(place_id)`.
- Each scout calls the scraper instead of `run_agent_task()`.
- The scraper runs headless Chrome, loads the page, extracts data via CSS selectors or XPath.
- Results feed into the same ingestion methods.

**Tradeoffs:**
- (+) Can access any public page, including platforms without APIs.
- (+) Sees exactly what a customer sees — prices, reviews, hours, photos.
- (-) Fragile: CSS selectors break when platforms redesign.
- (-) Slow: headless browser is 10-100x slower than an API call.
- (-) Resource-heavy: Chromium needs RAM. May not fit on Railway's container limits.
- (-) Legal gray area: scraping terms of service vary by platform.
- (-) Anti-bot detection: Booksy, Yelp, and Instagram actively block scrapers.

**When this makes sense:** For platforms with no API and no anti-bot measures. Useful as a fallback for the 2-3 sources where Option A isn't available.

### Option C: Hybrid — API Where Available, Claude Search as Fallback

Keep the current Claude web search as the default, and layer in API calls for sources where structured access exists.

**What changes:**
- Each scout gets a `_try_api()` method that attempts the structured API call first.
- If the API call succeeds, use that data (higher fidelity).
- If the API call fails (rate limit, key missing, platform unsupported), fall back to the existing `run_agent_task()` web search.
- Add a `source` field to each warehouse record indicating whether it came from API or web search.
- The `source` field lets downstream agents (Scorecard, Pricing Strategist) weight API-sourced data higher.

**Tradeoffs:**
- (+) Incremental: add one API at a time without breaking anything.
- (+) Graceful degradation: if an API key expires, the system still works via web search.
- (+) The `source` field creates a fidelity signal for analysis agents.
- (-) Two code paths per scout (API + fallback) means more complexity.
- (-) Still depends on Claude web search for uncovered sources.

**This is the recommended approach.** It lets you improve fidelity incrementally, starting with the highest-value API (Google Places), without a full rewrite.

### Option D: Community/Crowdsource Data Entry

For data that's hard to scrape (cash-only shops, word-of-mouth pricing, barber movement), add a manual ingestion path.

**What changes:**
- Add a `/submit-intel` endpoint in `app.py` (or a form in the dashboard) where you can manually enter a competitor's price, a shop closure, or a barber move.
- Manual entries go through the same ingestion methods and get `source='manual'`.
- This is especially useful for the 17 shops that were "Discovered by managed agent web search" with no real data.

**Tradeoffs:**
- (+) Fills gaps that no API or scraper can reach.
- (+) Your own observations (driving past a shop, hearing from a client) are the most reliable intel.
- (-) Manual effort — doesn't scale.
- (-) Only as current as the last time you entered data.

**Best used alongside Option C**, not instead of it.

## Recommended Roadmap

| Phase | What | Effort | Impact |
|---|---|---|---|
| 2a | Google Places API for review_harvester + shop_watcher | 1-2 days | High — covers reviews, ratings, place status, hours for all competitors with a Google listing |
| 2b | Add `source` column to price_history, review_snapshots, competitor_social, competitor_moves | 1 hour | Medium — enables fidelity-aware analysis |
| 2c | Manual intel submission form in dashboard | 1 day | Medium — fills gaps for cash-only and unlisted shops |
| 2d | Yelp Fusion API for review_harvester (second source) | 1 day | Medium — cross-references Google reviews |
| 2e | Booksy profile scraper (lightweight, no headless browser — just HTTP + HTML parsing) | 1-2 days | High — Booksy is the dominant booking platform in this market |
| 2f | Instagram Basic Display API for social_listener | 2-3 days | Low-Medium — requires Meta app review, limited data |

**Do NOT attempt:** Full headless browser scraping of Instagram or Yelp. Anti-bot detection will make it unreliable and the maintenance burden isn't worth it for this scale.

## What Does NOT Change

- `managed_agent.py` — not touched. CUSTOM_TOOLS, AGENT_SYSTEM_PROMPT, TIER_TASKS stay as-is.
- The managed agent can still be used for ad-hoc web research via the chat assistant.
- All existing warehouse tables and schemas stay the same.
- The Phase One agents (Snapshotter, Pricing Strategist, Market Pulse) consume whatever data the scouts produce regardless of source — they're source-agnostic.
- The 29 retired warehouse_divisions agents remain retired unless booking-OS integration happens.

## Prerequisites

- Google Cloud Platform account with Places API enabled (for phases 2a/2d).
- Yelp Fusion API key (free tier: 5,000 requests/day).
- Environment variables for API keys (`GOOGLE_PLACES_API_KEY`, `YELP_API_KEY`) added to Railway.
- Decision on whether to add the `source` column as a schema migration or as a new column with default `'web_search'`.
