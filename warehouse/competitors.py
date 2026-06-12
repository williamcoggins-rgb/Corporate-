"""CRUD operations for competitor records."""

import re

from warehouse.db import get_connection


# Charlotte ZIP → primary neighborhood, covering every ZIP in our coverage area.
# Used to resolve shops discovered with a ZIP but no neighborhood.
ZIP_NEIGHBORHOODS = {
    "28202": "Uptown",
    "28203": "South End",
    "28204": "Cherry",
    "28205": "Plaza Midwood",
    "28206": "North Charlotte",
    "28207": "Myers Park",
    "28208": "West Charlotte",
    "28209": "Madison Park",
    "28210": "SouthPark",
    "28211": "SouthPark",
    "28212": "Independence Blvd",
    "28213": "University City",
    "28214": "West Charlotte",
    "28215": "Plaza-Eastway",
    "28216": "Beatties Ford",
    "28217": "Yorkmount",
    "28226": "Carmel",
    "28262": "University City",
    "28269": "Highland Creek",
    "28270": "Ballantyne",
    "28273": "South Tryon",
    "28277": "Ballantyne",
    "28278": "Steele Creek",
    "28134": "Pineville",
    "28027": "Concord Mills",
    "28078": "Cornelius",
    "28031": "Cornelius",
    "28036": "Davidson",
    "28105": "Matthews",
}

# Neighborhood keywords found in shop names / addresses, checked before the
# ZIP map because a name mention is the most specific location signal
# (e.g. "Modern Classics Villa Heights" is Villa Heights, not generic 28205).
# Ordered most-specific first; matched on word boundaries.
NEIGHBORHOOD_KEYWORDS = [
    ("villa heights", "Villa Heights"),
    ("plaza midwood", "Plaza Midwood"),
    ("midwood", "Plaza Midwood"),
    ("noda", "NoDa"),
    ("south end", "South End"),
    ("southend", "South End"),
    ("uptown", "Uptown"),
    ("beatties ford", "Beatties Ford"),
    ("mosaic", "Mosaic Village"),
    ("wilkinson", "Wilkinson Blvd"),
    ("northlake", "Northlake"),
    ("eastland", "Eastland"),
    ("steele creek", "Steele Creek"),
    ("university city", "University City"),
    ("south park", "SouthPark"),
    ("southpark", "SouthPark"),
    ("ballantyne", "Ballantyne"),
    ("myers park", "Myers Park"),
    ("dilworth", "Dilworth"),
    ("cotswold", "Cotswold"),
    ("madison park", "Madison Park"),
    ("hidden valley", "Hidden Valley"),
    ("highland creek", "Highland Creek"),
    ("mallard creek", "Mallard Creek"),
    ("pineville", "Pineville"),
    ("matthews", "Matthews"),
    ("cornelius", "Cornelius"),
    ("davidson", "Davidson"),
    ("huntersville", "Huntersville"),
    ("concord", "Concord Mills"),
]


def resolve_neighborhood(neighborhood=None, zip_code=None, company_name=None,
                         hq_location=None):
    """Resolve the best real neighborhood for a competitor.

    Order: existing neighborhood if present, then a neighborhood keyword in
    the shop name or address (most specific signal), then the ZIP map.
    Returns None when there is genuinely no location signal.
    """
    if neighborhood and str(neighborhood).strip():
        return str(neighborhood).strip()

    text = f"{company_name or ''} {hq_location or ''}".lower()
    if text.strip():
        for keyword, hood in NEIGHBORHOOD_KEYWORDS:
            if re.search(r"\b" + re.escape(keyword) + r"\b", text):
                return hood

    zip5 = str(zip_code or "").strip()[:5]
    if zip5 in ZIP_NEIGHBORHOODS:
        return ZIP_NEIGHBORHOODS[zip5]

    # Last resort: a 5-digit ZIP inside the address text
    zip_in_text = re.search(r"\b(28\d{3})\b", text)
    if zip_in_text and zip_in_text.group(1) in ZIP_NEIGHBORHOODS:
        return ZIP_NEIGHBORHOODS[zip_in_text.group(1)]

    return None


def backfill_neighborhoods():
    """Fill blank neighborhood fields using the resolver. Returns count fixed."""
    con = get_connection()
    rows = con.execute("""
        SELECT competitor_id, neighborhood, zip_code, company_name, hq_location
        FROM competitors
        WHERE neighborhood IS NULL OR TRIM(neighborhood) = ''
    """).fetchall()
    fixed = 0
    for cid, hood, zip_code, name, hq in rows:
        resolved = resolve_neighborhood(hood, zip_code, name, hq)
        if resolved:
            con.execute(
                "UPDATE competitors SET neighborhood = ?, updated_at = CURRENT_TIMESTAMP WHERE competitor_id = ?",
                [resolved, cid],
            )
            fixed += 1
    con.close()
    return fixed


def _rows_to_dicts(cursor):
    """Convert cursor results to a list of dicts without pandas."""
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def add_competitor(company_name, industry=None, website=None, hq_location=None,
                   zip_code=None, neighborhood=None, ownership_type=None,
                   primary_clientele=None, founded_year=None, employee_count=None,
                   annual_revenue=None, business_model=None, notes=None):
    """Add a new competitor to the warehouse. Returns the new competitor_id."""
    if not (neighborhood and str(neighborhood).strip()):
        neighborhood = resolve_neighborhood(None, zip_code, company_name, hq_location)
    con = get_connection()
    cid = con.execute("SELECT nextval('seq_competitor')").fetchone()[0]
    con.execute("""
        INSERT INTO competitors (competitor_id, company_name, industry, website,
            hq_location, zip_code, neighborhood, ownership_type, primary_clientele,
            founded_year, employee_count, annual_revenue, business_model, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [cid, company_name, industry, website, hq_location, zip_code,
          neighborhood, ownership_type, primary_clientele, founded_year,
          employee_count, annual_revenue, business_model, notes])
    con.close()
    print(f"Added competitor: {company_name} (ID: {cid})")
    return cid


def get_competitor(identifier):
    """Pull a competitor's full file by ID or name."""
    con = get_connection()
    if isinstance(identifier, int):
        row = con.execute("SELECT * FROM competitors WHERE competitor_id = ?", [identifier]).fetchone()
    else:
        row = con.execute("SELECT * FROM competitors WHERE company_name ILIKE ?", [f"%{identifier}%"]).fetchone()

    if not row:
        con.close()
        print(f"No competitor found for: {identifier}")
        return None

    columns = [desc[0] for desc in con.description]
    result = dict(zip(columns, row))
    cid = result["competitor_id"]

    result["products"] = _rows_to_dicts(
        con.execute("SELECT * FROM competitor_products WHERE competitor_id = ?", [cid])
    )
    result["financials"] = _rows_to_dicts(
        con.execute("SELECT * FROM competitor_financials WHERE competitor_id = ? ORDER BY period DESC", [cid])
    )
    result["recent_moves"] = _rows_to_dicts(
        con.execute("SELECT * FROM competitor_moves WHERE competitor_id = ? ORDER BY move_date DESC LIMIT 10", [cid])
    )
    result["social"] = _rows_to_dicts(
        con.execute("SELECT * FROM competitor_social WHERE competitor_id = ? ORDER BY snapshot_date DESC", [cid])
    )

    con.close()
    return result


def list_competitors():
    """List all competitors in the warehouse."""
    con = get_connection()
    cursor = con.execute("""
        SELECT competitor_id, company_name, industry, status, annual_revenue, employee_count
        FROM competitors ORDER BY company_name
    """)
    results = _rows_to_dicts(cursor)
    con.close()
    return results


def update_competitor(competitor_id, **fields):
    """Update fields on an existing competitor."""
    if not fields:
        return
    allowed = {"company_name", "industry", "website", "hq_location", "zip_code",
               "neighborhood", "ownership_type", "primary_clientele", "founded_year",
               "employee_count", "annual_revenue", "business_model", "status", "notes"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        print("No valid fields to update.")
        return

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [competitor_id]

    con = get_connection()
    con.execute(f"UPDATE competitors SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE competitor_id = ?", values)
    con.close()
    print(f"Updated competitor {competitor_id}: {list(fields.keys())}")


def delete_competitor(competitor_id):
    """Remove a competitor and all related records."""
    con = get_connection()
    for table in ["competitor_social", "competitor_moves", "competitor_financials", "competitor_products"]:
        con.execute(f"DELETE FROM {table} WHERE competitor_id = ?", [competitor_id])
    con.execute("DELETE FROM competitors WHERE competitor_id = ?", [competitor_id])
    con.close()
    print(f"Deleted competitor {competitor_id} and all related records.")
