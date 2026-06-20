"""Database connection and schema management for the competitive intelligence warehouse."""

import os
import duckdb

_LOCAL_FALLBACK = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "competitive_intel.duckdb")


def _get_db_path():
    """Resolve the DuckDB file path from environment, falling back to local."""
    explicit = os.environ.get("WAREHOUSE_DB_PATH")
    if explicit:
        return explicit
    vol = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    if vol:
        return os.path.join(vol, "warehouse.duckdb")
    return _LOCAL_FALLBACK


DB_PATH = _get_db_path()


def get_connection():
    """Return a DuckDB connection, creating the data directory if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return duckdb.connect(DB_PATH)


def init_schema():
    """Create all warehouse tables if they don't exist."""
    con = get_connection()

    con.execute("""
        CREATE TABLE IF NOT EXISTS competitors (
            competitor_id INTEGER PRIMARY KEY,
            company_name VARCHAR NOT NULL,
            industry VARCHAR,
            website VARCHAR,
            hq_location VARCHAR,
            zip_code VARCHAR,
            neighborhood VARCHAR,
            ownership_type VARCHAR,
            primary_clientele VARCHAR,
            founded_year INTEGER,
            employee_count INTEGER,
            annual_revenue VARCHAR,
            business_model VARCHAR,
            status VARCHAR DEFAULT 'Active',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS competitor_products (
            product_id INTEGER PRIMARY KEY,
            competitor_id INTEGER REFERENCES competitors(competitor_id),
            product_name VARCHAR NOT NULL,
            category VARCHAR,
            pricing_model VARCHAR,
            price_range VARCHAR,
            target_market VARCHAR,
            strengths TEXT,
            weaknesses TEXT
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS competitor_financials (
            id INTEGER PRIMARY KEY,
            competitor_id INTEGER REFERENCES competitors(competitor_id),
            period VARCHAR,
            revenue_estimate DECIMAL(15,2),
            funding_total DECIMAL(15,2),
            last_funding_round VARCHAR,
            valuation_estimate DECIMAL(15,2),
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS competitor_moves (
            move_id INTEGER PRIMARY KEY,
            competitor_id INTEGER REFERENCES competitors(competitor_id),
            move_date DATE,
            move_type VARCHAR,
            description TEXT,
            source_url VARCHAR,
            impact_rating INTEGER CHECK (impact_rating BETWEEN 1 AND 5)
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS competitor_social (
            id INTEGER PRIMARY KEY,
            competitor_id INTEGER REFERENCES competitors(competitor_id),
            platform VARCHAR,
            followers INTEGER,
            engagement_rate DECIMAL(5,2),
            snapshot_date DATE DEFAULT CURRENT_DATE
        );
    """)

    # --- Extended tables for agent system ---

    con.execute("""
        CREATE TABLE IF NOT EXISTS neighborhoods (
            neighborhood_id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            zip_code VARCHAR,
            city VARCHAR DEFAULT 'Charlotte',
            state VARCHAR DEFAULT 'NC',
            demographics_notes TEXT,
            market_saturation VARCHAR
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS barbers (
            barber_id INTEGER PRIMARY KEY,
            competitor_id INTEGER REFERENCES competitors(competitor_id),
            name VARCHAR NOT NULL,
            instagram_handle VARCHAR,
            specialties TEXT,
            seniority VARCHAR,
            notes TEXT,
            first_seen DATE DEFAULT CURRENT_DATE,
            last_seen DATE DEFAULT CURRENT_DATE,
            status VARCHAR DEFAULT 'Active'
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS barber_specialties (
            id INTEGER PRIMARY KEY,
            barber_id INTEGER REFERENCES barbers(barber_id),
            specialty VARCHAR NOT NULL,
            skill_level VARCHAR,
            source VARCHAR
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY,
            competitor_id INTEGER REFERENCES competitors(competitor_id),
            service_name VARCHAR NOT NULL,
            price DECIMAL(8,2),
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source VARCHAR
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS review_snapshots (
            id INTEGER PRIMARY KEY,
            competitor_id INTEGER REFERENCES competitors(competitor_id),
            platform VARCHAR NOT NULL,
            rating DECIMAL(2,1),
            review_text TEXT,
            reviewer_name VARCHAR,
            review_date DATE,
            sentiment_score DECIMAL(4,2),
            keywords TEXT,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS alerts_log (
            alert_id INTEGER PRIMARY KEY,
            alert_type VARCHAR NOT NULL,
            severity VARCHAR DEFAULT 'info',
            competitor_id INTEGER,
            title VARCHAR NOT NULL,
            detail TEXT,
            data_json TEXT,
            acknowledged BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            run_id INTEGER PRIMARY KEY,
            agent_name VARCHAR NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            status VARCHAR DEFAULT 'running',
            records_processed INTEGER DEFAULT 0,
            notes TEXT
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS competitor_scores (
            id INTEGER PRIMARY KEY,
            competitor_id INTEGER REFERENCES competitors(competitor_id),
            score_type VARCHAR NOT NULL,
            score DECIMAL(5,2),
            components TEXT,
            scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # --- Booking Platform Intelligence tables ---

    con.execute("""
        CREATE TABLE IF NOT EXISTS platform_profiles (
            id INTEGER PRIMARY KEY,
            competitor_id INTEGER REFERENCES competitors(competitor_id),
            platform VARCHAR NOT NULL,
            profile_url VARCHAR,
            rating DECIMAL(2,1),
            review_count INTEGER DEFAULT 0,
            is_verified BOOLEAN DEFAULT FALSE,
            accepts_online_booking BOOLEAN DEFAULT TRUE,
            payment_methods VARCHAR,
            profile_completeness VARCHAR,
            last_active DATE,
            notes TEXT,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS platform_solo_barbers (
            id INTEGER PRIMARY KEY,
            barber_name VARCHAR NOT NULL,
            platform VARCHAR NOT NULL,
            profile_url VARCHAR,
            zip_code VARCHAR,
            neighborhood VARCHAR,
            rating DECIMAL(2,1),
            review_count INTEGER DEFAULT 0,
            years_experience VARCHAR,
            specialties TEXT,
            price_range VARCHAR,
            fade_price DECIMAL(8,2),
            haircut_price DECIMAL(8,2),
            beard_price DECIMAL(8,2),
            combo_price DECIMAL(8,2),
            accepts_walkins BOOLEAN DEFAULT FALSE,
            chair_rental BOOLEAN DEFAULT FALSE,
            instagram_handle VARCHAR,
            ownership_type VARCHAR,
            primary_clientele VARCHAR,
            status VARCHAR DEFAULT 'Active',
            notes TEXT,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # --- Phase One: Market Intelligence tables ---

    con.execute("""
        CREATE TABLE IF NOT EXISTS weekly_competitor_snapshots (
            snapshot_id INTEGER PRIMARY KEY,
            competitor_id INTEGER NOT NULL,
            snapshot_week DATE NOT NULL,
            avg_price REAL,
            rating REAL,
            review_count INTEGER,
            follower_count INTEGER,
            barber_count INTEGER,
            price_delta REAL,
            rating_delta REAL,
            review_delta INTEGER,
            follower_delta INTEGER,
            barber_delta INTEGER,
            narrative TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (competitor_id, snapshot_week)
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS market_period_summaries (
            summary_id INTEGER PRIMARY KEY,
            period_type VARCHAR NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            neighborhood VARCHAR,
            competitor_count INTEGER,
            avg_market_price REAL,
            median_market_price REAL,
            avg_rating REAL,
            total_reviews INTEGER,
            new_shops INTEGER,
            closed_shops INTEGER,
            price_range_low REAL,
            price_range_high REAL,
            narrative TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (period_type, period_start, neighborhood)
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS competitor_trends (
            trend_id INTEGER PRIMARY KEY,
            competitor_id INTEGER NOT NULL,
            trend_type VARCHAR NOT NULL,
            detected_date DATE NOT NULL,
            metric_name VARCHAR,
            metric_value REAL,
            metric_prior REAL,
            severity VARCHAR DEFAULT 'info',
            narrative TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS pricing_recommendations (
            recommendation_id INTEGER PRIMARY KEY,
            recommendation_date DATE NOT NULL,
            service_name VARCHAR NOT NULL,
            your_current_price REAL,
            market_avg_price REAL,
            market_median_price REAL,
            recommended_action VARCHAR NOT NULL,
            confidence VARCHAR DEFAULT 'medium',
            competitor_context TEXT,
            narrative TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (recommendation_date, service_name)
        );
    """)

    con.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_competitor START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_product START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_financial START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_move START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_social START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_neighborhood START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_barber START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_barber_spec START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_price_history START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_review START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_alert START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_agent_run START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_score START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_platform_profile START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_platform_solo START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_weekly_snapshot START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_market_summary START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_competitor_trend START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_pricing_rec START 1;
    """)

    con.close()
    print("Warehouse schema initialized.")


if __name__ == "__main__":
    init_schema()
