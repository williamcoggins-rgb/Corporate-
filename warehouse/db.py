"""Database connection and schema management for the competitive intelligence warehouse."""

import os
import duckdb

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "competitive_intel.duckdb")


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

    con.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_competitor START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_product START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_financial START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_move START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_social START 1;
    """)

    con.close()
    print("Warehouse schema initialized.")


if __name__ == "__main__":
    init_schema()
