"""RETIRED — Warehouse Intelligence Divisions

STATUS: RETIRED as of Phase One (June 2026).
SUPERSEDED BY: agents/weekly_snapshotter.py, agents/pricing_strategist.py,
               agents/market_pulse.py (registered in runner.py, Tier 3).

These 7 divisions (29 agents) were the original analysis-layer design.
They are NOT registered in the AGENTS registry, NOT scheduled, and NOT
imported by runner.py. They remain here intact for reference and in case
any division needs to be revived — no code was deleted.

To revive a division: import its classes in runner.py, add them to AGENTS
and TIERS, and wire them into scheduler.py. See agents/warehouse_divisions/README.md.

Original design:
    Seven divisions, each with four agents (Scout/Researcher/Analyst/Auditor).
    Six of seven divisions required booking-OS tables that were never created
    in the schema. Only Pricing Intelligence could run on existing warehouse data.

Divisions:
    1. Pricing Intelligence  → absorbed by pricing_strategist.py
    2. Client Acquisition    → blocked on booking-OS (client_origins table)
    3. Demand Forecasting    → blocked on booking-OS (daily_booking_volume table)
    4. Revenue per Service   → blocked on booking-OS (service_economics table)
    5. Chair Renter Valuation → blocked on booking-OS (chair_utilization table)
    6. Market Share          → blocked on booking-OS (your_monthly_volume table)
    7. Site Selection        → blocked on booking-OS (site_candidates table)
"""
