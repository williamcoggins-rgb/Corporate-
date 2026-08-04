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

def add_social(competitor_id, platform, followers=None, engagement_rate=None,
               snapshot_date=None):
    """Append a social snapshot. snapshot_date is the observation date (defaults
    to today) so freshness reflects when the data was seen, not insert time."""
    con = get_connection()
    sid = con.execute("SELECT nextval('seq_social')").fetchone()[0]
    con.execute("""
        INSERT INTO competitor_social (id, competitor_id, platform,
            followers, engagement_rate, snapshot_date)
        VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_DATE))
    """, [sid, competitor_id, platform, followers, engagement_rate, snapshot_date])
    con.close()
    print(f"Added social: {platform} for competitor {competitor_id}")
    return sid


# --- Review snapshots ---

def add_review(competitor_id, platform, rating=None, review_text=None,
               reviewer_name=None, review_date=None, sentiment_score=None,
               keywords=None):
    """Append one review snapshot. review_date is the observation date."""
    if isinstance(keywords, (list, tuple)):
        keywords = ", ".join(str(k) for k in keywords)
    con = get_connection()
    rid = con.execute("SELECT nextval('seq_review')").fetchone()[0]
    con.execute("""
        INSERT INTO review_snapshots (id, competitor_id, platform, rating,
            review_text, reviewer_name, review_date, sentiment_score, keywords)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [rid, competitor_id, platform, rating, review_text, reviewer_name,
          review_date, sentiment_score, keywords])
    con.close()
    print(f"Added review snapshot for competitor {competitor_id}")
    return rid


# --- Booking-platform presence ---

def add_platform_profile(competitor_id, platform, profile_url=None, rating=None,
                         review_count=None, is_verified=None,
                         accepts_online_booking=None, payment_methods=None,
                         profile_completeness=None, last_active=None,
                         notes=None, collected_at=None):
    """Append a competitor's booking-platform profile. collected_at is the
    observation timestamp (defaults to now)."""
    con = get_connection()
    pid = con.execute("SELECT nextval('seq_platform_profile')").fetchone()[0]
    con.execute("""
        INSERT INTO platform_profiles (id, competitor_id, platform, profile_url,
            rating, review_count, is_verified, accepts_online_booking,
            payment_methods, profile_completeness, last_active, notes, collected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
    """, [pid, competitor_id, platform, profile_url, rating, review_count,
          is_verified, accepts_online_booking, payment_methods,
          profile_completeness, last_active, notes, collected_at])
    con.close()
    print(f"Added platform profile ({platform}) for competitor {competitor_id}")
    return pid


def add_platform_solo(barber_name, platform, profile_url=None, zip_code=None,
                      neighborhood=None, rating=None, review_count=None,
                      years_experience=None, specialties=None, price_range=None,
                      fade_price=None, haircut_price=None, beard_price=None,
                      combo_price=None, accepts_walkins=None, chair_rental=None,
                      instagram_handle=None, ownership_type=None,
                      primary_clientele=None, status="Active", notes=None,
                      collected_at=None):
    """Append an independent (solo) barber found on a booking platform. These
    are not tied to a competitor_id."""
    if isinstance(specialties, (list, tuple)):
        specialties = ", ".join(str(s) for s in specialties)
    con = get_connection()
    bid = con.execute("SELECT nextval('seq_platform_solo')").fetchone()[0]
    con.execute("""
        INSERT INTO platform_solo_barbers (id, barber_name, platform, profile_url,
            zip_code, neighborhood, rating, review_count, years_experience,
            specialties, price_range, fade_price, haircut_price, beard_price,
            combo_price, accepts_walkins, chair_rental, instagram_handle,
            ownership_type, primary_clientele, status, notes, collected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
    """, [bid, barber_name, platform, profile_url, zip_code, neighborhood, rating,
          review_count, years_experience, specialties, price_range, fade_price,
          haircut_price, beard_price, combo_price, accepts_walkins, chair_rental,
          instagram_handle, ownership_type, primary_clientele, status, notes,
          collected_at])
    con.close()
    print(f"Added solo barber: {barber_name} ({platform})")
    return bid


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
