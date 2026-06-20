# Warehouse Intelligence Divisions — RETIRED

**Status:** Retired as of Phase One (June 2026)

These 7 divisions (29 agents total) were the original analysis-layer design for bridging competitive intelligence with business intelligence. They have been superseded by the Phase One market intel agents:

| Old Division | Status | Replaced By |
|---|---|---|
| 1. Pricing Intelligence | Absorbed | `agents/pricing_strategist.py` |
| 2. Client Acquisition | Blocked on booking-OS | Phase Two |
| 3. Demand Forecasting | Blocked on booking-OS | Phase Two |
| 4. Revenue per Service | Blocked on booking-OS | Phase Two |
| 5. Chair Renter Valuation | Blocked on booking-OS | Phase Two |
| 6. Market Share | Blocked on booking-OS | Phase Two (partially covered by `agents/market_pulse.py`) |
| 7. Site Selection | Blocked on booking-OS | Phase Two |

## Why retired, not deleted

- No code was removed. Every file is intact and importable.
- Six of seven divisions require booking-OS tables (`client_origins`, `daily_booking_volume`, `service_economics`, `chair_utilization`, `market_chair_rates`, `your_monthly_volume`, `site_candidates`, `zip_demographics`) that do not exist in the warehouse schema yet.
- Once the booking-OS integration is built, these divisions can be revived or their logic folded into new Phase Two agents.

## How to revive a division

1. Add the required tables to `warehouse/db.py` inside `init_schema()`.
2. Import the division's agent classes in `agents/runner.py`.
3. Add them to the `AGENTS` dict and the appropriate tier in `TIERS`.
4. Wire cron jobs in `scheduler.py` if they need scheduled execution.
5. Remove the `RETIRED` prefix from the file's docstring.
6. Run `python -m py_compile` on every touched file.

## Active replacements (Phase One)

| Agent | File | Tier | Schedule |
|---|---|---|---|
| Weekly Snapshotter | `agents/weekly_snapshotter.py` | 3 | Sunday 11:30pm ET |
| Pricing Strategist | `agents/pricing_strategist.py` | 3 | Monday 12:00am ET |
| Market Pulse | `agents/market_pulse.py` | 3 | 1st of month 1:00am ET |
