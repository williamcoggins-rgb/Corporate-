"""CRUD operations for competitor records."""

from warehouse.db import get_connection


def _rows_to_dicts(cursor):
    """Convert cursor results to a list of dicts without pandas."""
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def add_competitor(company_name, industry=None, website=None, hq_location=None,
                   founded_year=None, employee_count=None, annual_revenue=None,
                   business_model=None, notes=None):
    """Add a new competitor to the warehouse. Returns the new competitor_id."""
    con = get_connection()
    cid = con.execute("SELECT nextval('seq_competitor')").fetchone()[0]
    con.execute("""
        INSERT INTO competitors (competitor_id, company_name, industry, website,
            hq_location, founded_year, employee_count, annual_revenue,
            business_model, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [cid, company_name, industry, website, hq_location, founded_year,
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
    allowed = {"company_name", "industry", "website", "hq_location", "founded_year",
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
