"""Operations for products, financials, moves, and social data."""

from warehouse.db import get_connection


def _rows_to_dicts(cursor):
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# --- Products ---

def add_product(competitor_id, product_name, category=None, pricing_model=None,
                price_range=None, target_market=None, strengths=None, weaknesses=None):
    con = get_connection()
    pid = con.execute("SELECT nextval('seq_product')").fetchone()[0]
    con.execute("""
        INSERT INTO competitor_products (product_id, competitor_id, product_name,
            category, pricing_model, price_range, target_market, strengths, weaknesses)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [pid, competitor_id, product_name, category, pricing_model,
          price_range, target_market, strengths, weaknesses])
    con.close()
    print(f"Added product: {product_name} (ID: {pid})")
    return pid


# --- Financials ---

def add_financial(competitor_id, period, revenue_estimate=None, funding_total=None,
                  last_funding_round=None, valuation_estimate=None):
    con = get_connection()
    fid = con.execute("SELECT nextval('seq_financial')").fetchone()[0]
    con.execute("""
        INSERT INTO competitor_financials (id, competitor_id, period,
            revenue_estimate, funding_total, last_funding_round, valuation_estimate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [fid, competitor_id, period, revenue_estimate, funding_total,
          last_funding_round, valuation_estimate])
    con.close()
    print(f"Added financial record for competitor {competitor_id}, period {period}")
    return fid


# --- Strategic Moves ---

def add_move(competitor_id, move_date, move_type, description,
             source_url=None, impact_rating=None):
    con = get_connection()
    mid = con.execute("SELECT nextval('seq_move')").fetchone()[0]
    con.execute("""
        INSERT INTO competitor_moves (move_id, competitor_id, move_date,
            move_type, description, source_url, impact_rating)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [mid, competitor_id, move_date, move_type, description,
          source_url, impact_rating])
    con.close()
    print(f"Added move: {move_type} for competitor {competitor_id}")
    return mid


# --- Social Presence ---

def add_social(competitor_id, platform, followers, engagement_rate=None):
    con = get_connection()
    sid = con.execute("SELECT nextval('seq_social')").fetchone()[0]
    con.execute("""
        INSERT INTO competitor_social (id, competitor_id, platform,
            followers, engagement_rate)
        VALUES (?, ?, ?, ?, ?)
    """, [sid, competitor_id, platform, followers, engagement_rate])
    con.close()
    print(f"Added social: {platform} for competitor {competitor_id}")
    return sid


# --- Cross-competitor Queries ---

def compare_products(category=None):
    """Compare products across all competitors, optionally filtered by category."""
    con = get_connection()
    query = """
        SELECT c.company_name, p.product_name, p.category,
               p.pricing_model, p.price_range, p.target_market
        FROM competitor_products p
        JOIN competitors c ON c.competitor_id = p.competitor_id
    """
    params = []
    if category:
        query += " WHERE p.category ILIKE ?"
        params.append(f"%{category}%")
    query += " ORDER BY c.company_name, p.product_name"
    results = _rows_to_dicts(con.execute(query, params))
    con.close()
    return results


def recent_moves(limit=20):
    """Get the most recent strategic moves across all competitors."""
    con = get_connection()
    results = _rows_to_dicts(con.execute("""
        SELECT c.company_name, m.move_date, m.move_type,
               m.description, m.impact_rating
        FROM competitor_moves m
        JOIN competitors c ON c.competitor_id = m.competitor_id
        ORDER BY m.move_date DESC
        LIMIT ?
    """, [limit]))
    con.close()
    return results


def competitive_landscape():
    """Overview of all competitors with key metrics."""
    con = get_connection()
    results = _rows_to_dicts(con.execute("""
        SELECT
            c.company_name, c.industry, c.status, c.annual_revenue,
            c.employee_count, c.business_model,
            COUNT(DISTINCT p.product_id) AS num_products,
            COUNT(DISTINCT m.move_id) AS num_tracked_moves
        FROM competitors c
        LEFT JOIN competitor_products p ON p.competitor_id = c.competitor_id
        LEFT JOIN competitor_moves m ON m.competitor_id = c.competitor_id
        GROUP BY ALL
        ORDER BY c.company_name
    """))
    con.close()
    return results
