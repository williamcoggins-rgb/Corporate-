"""Bulk/quick add functions for programmatic use — no interactive prompts."""

import inspect
from datetime import datetime, timezone

from warehouse.competitors import add_competitor, update_competitor
from warehouse.intel import (
    add_product, add_financial, add_move, add_social,
    add_review, add_platform_profile, add_platform_solo,
)


# Competitor master columns add_competitor accepts. 'status' is handled
# separately (add_competitor uses the table default, so we set it afterward
# via update_competitor).
MASTER_FIELDS = {
    "industry", "website", "hq_location", "zip_code", "neighborhood",
    "ownership_type", "primary_clientele", "founded_year", "employee_count",
    "annual_revenue", "business_model", "notes",
}


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def _call_filtered(fn, **kwargs):
    """Call fn with only the kwargs it accepts — enriched fields that have no
    matching column are dropped gracefully instead of raising a TypeError."""
    allowed = set(inspect.signature(fn).parameters)
    return fn(**{k: v for k, v in kwargs.items() if k in allowed})


def bulk_add_competitor(data: dict) -> int:
    """Add a competitor from a dict. Returns competitor_id.

    Only the recognized master fields are forwarded; unknown keys (and nested
    sub-structures) are ignored here so an enriched payload never gets rejected.
    'status' is applied after creation since add_competitor uses the default.
    """
    data = dict(data)
    name = data.pop("company_name")
    status = data.get("status")
    fields = {k: v for k, v in data.items() if k in MASTER_FIELDS and v is not None}
    cid = add_competitor(name, **fields)
    if status:
        update_competitor(cid, status=status)
    return cid


# (accepted keys) -> (writer, needs competitor_id, observation-date kwarg or None)
# Accepts both the short key ("social") and the table-name key
# ("competitor_social") that an external enriched payload might use.
_COLLECTIONS = [
    (("products", "competitor_products"), add_product, True, None),
    (("financials", "competitor_financials"), add_financial, True, None),
    (("moves", "competitor_moves"), add_move, True, "move_date"),
    (("social", "competitor_social"), add_social, True, "snapshot_date"),
    (("reviews", "review_snapshots"), add_review, True, "review_date"),
    (("platform_profiles",), add_platform_profile, True, "collected_at"),
    (("platform_solo_barbers", "solo_barbers"), add_platform_solo, False, "collected_at"),
]


def _records_for(profile, keys):
    for k in keys:
        v = profile.get(k)
        if v:
            return v
    return []


def attach_profile_records(cid, profile):
    """Append every nested observation sub-structure in `profile` to the right
    warehouse table.

    - Accepts short keys ('social') and table-name keys ('competitor_social').
    - Maps a generic 'date_observed' onto each table's observation-date column,
      falling back to today, so freshness reflects when data was seen.
    - Filters unknown fields per record (nothing rejected for an extra field).
    - Best-effort per record: one bad row is logged and skipped, not fatal.

    Returns {collection: written_count}.
    """
    written = {}
    for keys, fn, needs_cid, date_kw in _COLLECTIONS:
        recs = _records_for(profile, keys)
        n = 0
        for rec in recs:
            try:
                rec = dict(rec)
                if date_kw:
                    rec[date_kw] = rec.get(date_kw) or rec.get("date_observed") or _today()
                rec.pop("date_observed", None)
                if needs_cid:
                    _call_filtered(fn, competitor_id=cid, **rec)
                else:
                    _call_filtered(fn, **rec)
                n += 1
            except Exception as e:
                print(f"[attach_profile_records] skipped a {keys[0]} record for "
                      f"competitor {cid}: {e}")
        if n:
            written[keys[0]] = n
    return written


def load_full_profile(profile: dict) -> int:
    """Load a complete competitor profile in one call. Returns competitor_id.

    Creates the competitor with all master fields (including status) and appends
    every nested observation sub-structure it carries:

        products, financials, moves, social, reviews (review_snapshots),
        platform_profiles, platform_solo_barbers

    Short keys and table-name keys are both accepted, a generic 'date_observed'
    is honored per record, and unrecognized fields are dropped gracefully.
    """
    profile = dict(profile)
    cid = bulk_add_competitor(profile)
    attach_profile_records(cid, profile)
    return cid
