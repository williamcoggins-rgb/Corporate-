"""Bulk/quick add functions for programmatic use — no interactive prompts."""

from warehouse.competitors import add_competitor
from warehouse.intel import add_product, add_financial, add_move, add_social


def bulk_add_competitor(data: dict) -> int:
    """Add a competitor from a dictionary. Returns competitor_id.

    Expected keys: company_name (required), plus any optional fields:
    industry, website, hq_location, founded_year, employee_count,
    annual_revenue, business_model, notes
    """
    name = data.pop("company_name")
    return add_competitor(name, **data)


def load_full_profile(profile: dict) -> int:
    """Load a complete competitor profile in one call.

    profile = {
        "company_name": "Acme Corp",
        "industry": "SaaS",
        "website": "https://acme.com",
        ...
        "products": [
            {"product_name": "Widget Pro", "category": "Widgets", "pricing_model": "Subscription", ...},
        ],
        "financials": [
            {"period": "FY 2025", "revenue_estimate": 5000000, ...},
        ],
        "moves": [
            {"move_date": "2025-06-01", "move_type": "Launch", "description": "Launched v2", ...},
        ],
        "social": [
            {"platform": "LinkedIn", "followers": 50000, ...},
        ],
    }
    """
    # Extract nested data
    products = profile.pop("products", [])
    financials = profile.pop("financials", [])
    moves = profile.pop("moves", [])
    social = profile.pop("social", [])

    # Add the competitor
    cid = bulk_add_competitor(profile)

    # Add related records
    for p in products:
        add_product(cid, **p)

    for f in financials:
        add_financial(cid, **f)

    for m in moves:
        add_move(cid, **m)

    for s in social:
        add_social(cid, **s)

    print(f"Loaded full profile for competitor {cid}: "
          f"{len(products)} products, {len(financials)} financials, "
          f"{len(moves)} moves, {len(social)} social records")
    return cid
