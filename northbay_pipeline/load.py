"""
Northbay Capital ETL Pipeline - Load Module
==========================================
Mentor Note for Beginners:
The 'L' in ETL stands for Load. We write our clean, structured DataFrames into a
relational database (SQLite).

Senior Data Engineering Best Practices demonstrated here:
1. Strict DDL (Data Definition Language):
   Never rely solely on pandas `to_sql()` default schemas. Pandas will create generic
   tables without PRIMARY KEY constraints or FOREIGN KEY definitions. We define
   explicit `CREATE TABLE` DDL statements to guarantee data integrity.
2. Indexing for Query Performance:
   We build B-Tree indexes on every foreign key column (`account_id`, `customer_id`,
   `date_key`, `symbol`). In analytical queries, joins against unindexed columns cause
   costly full-table scans. Indexes make joins near-instantaneous.
3. Idempotency (Safe to Re-Run):
   An ETL pipeline must be idempotent: running it once or ten times produces the exact
   same final state with zero duplicated rows. We achieve this using transactional
   table replacement (`DROP TABLE IF EXISTS` followed by atomic recreation).
4. Analytical Views:
   Instead of forcing analysts to write repetitive, 20-line multi-table JOINs,
   data engineers package curated business metrics into reusable SQL Views.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

try:
    from .config import DATABASE_PATH
except ImportError:
    from config import DATABASE_PATH

logger = logging.getLogger("northbay_pipeline")

# ==============================================================================
# 1. DDL SCHEMAS WITH CONSTRAINTS AND INDEXES
# ==============================================================================

DDL_STATEMENTS = [
    # Dimension: Customers
    """
    CREATE TABLE IF NOT EXISTS dim_customers (
        customer_id VARCHAR(20) PRIMARY KEY,
        full_name VARCHAR(100) NOT NULL,
        gender VARCHAR(10) NOT NULL,
        birth_date DATE NOT NULL,
        customer_age INTEGER NOT NULL,
        city VARCHAR(50) NOT NULL,
        region VARCHAR(50) NOT NULL,
        country VARCHAR(50) NOT NULL,
        occupation VARCHAR(100) NOT NULL,
        annual_income_php REAL,
        risk_profile VARCHAR(20) NOT NULL,
        kyc_status VARCHAR(20) NOT NULL,
        signup_date DATE NOT NULL,
        acquisition_channel VARCHAR(50) NOT NULL,
        is_active INTEGER NOT NULL,
        is_flagged INTEGER DEFAULT 0,
        flag_reason TEXT,
        raw_value TEXT
    );
    """,

    # Dimension: Accounts
    """
    CREATE TABLE IF NOT EXISTS dim_accounts (
        account_id VARCHAR(20) PRIMARY KEY,
        customer_id VARCHAR(20) NOT NULL,
        account_type VARCHAR(20) NOT NULL,
        currency VARCHAR(10) NOT NULL,
        open_date DATE NOT NULL,
        close_date DATE,
        status VARCHAR(20) NOT NULL,
        current_balance REAL NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES dim_customers (customer_id)
    );
    """,

    # Dimension: Date
    """
    CREATE TABLE IF NOT EXISTS dim_date (
        date_key INTEGER PRIMARY KEY,
        full_date DATE NOT NULL,
        year INTEGER NOT NULL,
        quarter INTEGER NOT NULL,
        month INTEGER NOT NULL,
        month_name VARCHAR(20) NOT NULL,
        day INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        day_name VARCHAR(20) NOT NULL,
        is_weekend INTEGER NOT NULL,
        is_month_end INTEGER NOT NULL
    );
    """,

    # Dimension: Symbol
    """
    CREATE TABLE IF NOT EXISTS dim_symbol (
        symbol VARCHAR(10) PRIMARY KEY,
        symbol_name VARCHAR(50) NOT NULL,
        asset_class VARCHAR(30) NOT NULL,
        market_region VARCHAR(30) NOT NULL,
        base_currency VARCHAR(10) NOT NULL
    );
    """,

    # Fact: Transactions
    """
    CREATE TABLE IF NOT EXISTS fact_transactions (
        transaction_id VARCHAR(20) PRIMARY KEY,
        account_id VARCHAR(20) NOT NULL,
        date_key INTEGER NOT NULL,
        timestamp DATETIME NOT NULL,
        transaction_type VARCHAR(30) NOT NULL,
        amount REAL,
        currency VARCHAR(10) NOT NULL,
        payment_method VARCHAR(30) NOT NULL,
        status VARCHAR(20) NOT NULL,
        description TEXT,
        is_flagged INTEGER DEFAULT 0,
        flag_reason TEXT,
        raw_value TEXT,
        FOREIGN KEY (account_id) REFERENCES dim_accounts (account_id),
        FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
    );
    """,

    # Fact: Trades
    """
    CREATE TABLE IF NOT EXISTS fact_trades (
        trade_id VARCHAR(20) PRIMARY KEY,
        account_id VARCHAR(20) NOT NULL,
        symbol VARCHAR(10) NOT NULL,
        date_key INTEGER NOT NULL,
        direction VARCHAR(10) NOT NULL,
        open_time DATETIME NOT NULL,
        close_time DATETIME NOT NULL,
        trade_duration_hours REAL NOT NULL,
        trade_month VARCHAR(10) NOT NULL,
        lot_size REAL,
        open_price REAL NOT NULL,
        close_price REAL NOT NULL,
        stop_loss REAL NOT NULL,
        take_profit REAL NOT NULL,
        leverage INTEGER NOT NULL,
        swap_fee REAL NOT NULL,
        commission REAL NOT NULL,
        profit_loss REAL NOT NULL,
        is_win INTEGER NOT NULL,
        close_reason VARCHAR(30) NOT NULL,
        is_flagged INTEGER DEFAULT 0,
        flag_reason TEXT,
        raw_value TEXT,
        FOREIGN KEY (account_id) REFERENCES dim_accounts (account_id),
        FOREIGN KEY (symbol) REFERENCES dim_symbol (symbol),
        FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
    );
    """,

    # Fact: Loans
    """
    CREATE TABLE IF NOT EXISTS fact_loans (
        loan_id VARCHAR(20) PRIMARY KEY,
        customer_id VARCHAR(20) NOT NULL,
        date_key INTEGER NOT NULL,
        loan_type VARCHAR(20) NOT NULL,
        principal REAL,
        interest_rate REAL NOT NULL,
        term_months INTEGER NOT NULL,
        start_date DATE NOT NULL,
        monthly_payment REAL NOT NULL,
        amount_paid REAL NOT NULL,
        days_past_due INTEGER NOT NULL,
        status VARCHAR(20) NOT NULL,
        credit_score INTEGER,
        credit_score_missing INTEGER DEFAULT 0,
        credit_band VARCHAR(30),
        is_flagged INTEGER DEFAULT 0,
        flag_reason TEXT,
        raw_value TEXT,
        FOREIGN KEY (customer_id) REFERENCES dim_customers (customer_id),
        FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
    );
    """,

    # Fact: Index Prices (Daily Market OHLC)
    """
    CREATE TABLE IF NOT EXISTS fact_index_prices (
        date DATE NOT NULL,
        symbol VARCHAR(10) NOT NULL,
        date_key INTEGER NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume INTEGER NOT NULL,
        PRIMARY KEY (date, symbol),
        FOREIGN KEY (symbol) REFERENCES dim_symbol (symbol),
        FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
    );
    """
]

# Indexes on Foreign Keys and Query Filter Columns
INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_accounts_customer ON dim_accounts (customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_tx_account ON fact_transactions (account_id);",
    "CREATE INDEX IF NOT EXISTS idx_tx_date_key ON fact_transactions (date_key);",
    "CREATE INDEX IF NOT EXISTS idx_trades_account ON fact_trades (account_id);",
    "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON fact_trades (symbol);",
    "CREATE INDEX IF NOT EXISTS idx_trades_date_key ON fact_trades (date_key);",
    "CREATE INDEX IF NOT EXISTS idx_loans_customer ON fact_loans (customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_loans_date_key ON fact_loans (date_key);",
    "CREATE INDEX IF NOT EXISTS idx_index_date_key ON fact_index_prices (date_key);"
]

# ==============================================================================
# 2. ANALYTICAL SQL VIEWS
# ==============================================================================

VIEW_STATEMENTS = [
    # View 1: Trader Performance by Customer Risk Profile
    # Mentor Note: SQL AVG() automatically ignores NULLs (bad values set to NULL).
    # All metrics operate on the same consistent row population.
    """
    CREATE VIEW IF NOT EXISTS v_pnl_by_risk_profile AS
    SELECT 
        c.risk_profile,
        COUNT(t.trade_id) AS total_trades,
        SUM(t.is_win) AS winning_trades,
        ROUND(100.0 * SUM(t.is_win) / COUNT(t.trade_id), 2) AS win_rate_pct,
        ROUND(SUM(t.profit_loss), 2) AS total_pnl_usd,
        ROUND(AVG(t.profit_loss), 2) AS avg_pnl_usd,
        ROUND(AVG(t.lot_size), 2) AS avg_lot_size,
        ROUND(AVG(t.leverage), 1) AS avg_leverage
    FROM fact_trades t
    JOIN dim_accounts a ON t.account_id = a.account_id
    JOIN dim_customers c ON a.customer_id = c.customer_id
    GROUP BY c.risk_profile
    ORDER BY total_pnl_usd DESC;
    """,

    # View 2: Monthly Deposit Liquidity Flows
    """
    CREATE VIEW IF NOT EXISTS v_monthly_deposits AS
    SELECT 
        d.year,
        d.month,
        d.month_name,
        tx.currency,
        COUNT(tx.transaction_id) AS deposit_count,
        ROUND(SUM(tx.amount), 2) AS total_deposit_volume,
        ROUND(AVG(tx.amount), 2) AS avg_deposit_amount
    FROM fact_transactions tx
    JOIN dim_date d ON tx.date_key = d.date_key
    WHERE tx.transaction_type = 'Deposit' 
      AND tx.status = 'Completed'
    GROUP BY d.year, d.month, d.month_name, tx.currency
    ORDER BY d.year, d.month, tx.currency;
    """,

    # View 3: Loan Default Rates by Credit Score Band (excludes missing credit scores)
    """
    CREATE VIEW IF NOT EXISTS v_loan_default_rate_by_credit_band AS
    SELECT 
        l.credit_band,
        COUNT(l.loan_id) AS total_loans,
        SUM(CASE WHEN l.status = 'Default' THEN 1 ELSE 0 END) AS default_count,
        ROUND(100.0 * SUM(CASE WHEN l.status = 'Default' THEN 1 ELSE 0 END) / COUNT(l.loan_id), 2) AS default_rate_pct,
        ROUND(AVG(l.principal), 2) AS avg_principal_php,
        ROUND(AVG(l.interest_rate) * 100.0, 2) AS avg_interest_rate_pct,
        ROUND(AVG(l.credit_score), 1) AS avg_credit_score
    FROM fact_loans l
    WHERE l.credit_score_missing = 0 AND l.credit_score IS NOT NULL
    GROUP BY l.credit_band
    ORDER BY avg_credit_score ASC;
    """
]


# ==============================================================================
# 3. DATABASE LOADER ENGINE
# ==============================================================================

def load_to_sqlite(transformed_tables: Dict[str, pd.DataFrame], db_path: Path = DATABASE_PATH) -> None:
    """
    Load cleaned DataFrames into SQLite Star Schema tables inside a single atomic transaction.

    Parameters:
        transformed_tables (Dict[str, pd.DataFrame]): Dictionary of cleaned DataFrames.
        db_path (Path): Destination SQLite database file path.
    """
    logger.info("=" * 60)
    logger.info(f"STEP 4: LOAD - Writing Star Schema to SQLite ({db_path.name})")
    logger.info("=" * 60)

    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Enable Foreign Key enforcement in SQLite
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Drop existing views and tables to guarantee idempotent re-runnability
        logger.info("Enforcing idempotency: dropping existing views and tables...")
        views = ["v_pnl_by_risk_profile", "v_monthly_deposits", "v_loan_default_rate_by_credit_band"]
        for v in views:
            cursor.execute(f"DROP VIEW IF EXISTS {v};")

        # Drop tables in child -> parent dependency order
        tables = [
            "fact_trades", "fact_transactions", "fact_loans", "fact_index_prices",
            "dim_accounts", "dim_customers", "dim_symbol", "dim_date"
        ]
        for t in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {t};")

        # Execute DDL statements
        logger.info("Creating Star Schema tables with Primary and Foreign Keys...")
        for ddl in DDL_STATEMENTS:
            cursor.execute(ddl)

        # Bulk load cleaned DataFrames using append
        # Load order: Dimensions first, then Facts
        load_order = [
            "dim_customers", "dim_accounts", "dim_date", "dim_symbol",
            "fact_transactions", "fact_trades", "fact_loans", "fact_index_prices"
        ]

        for table_name in load_order:
            if table_name in transformed_tables:
                df = transformed_tables[table_name]
                logger.info(f"Loading {len(df):,} records into table: '{table_name}'...")
                df.to_sql(name=table_name, con=conn, if_exists="append", index=False, chunksize=1000)

        # Create Indexes
        logger.info("Building B-Tree indexes on foreign keys...")
        for idx in INDEX_STATEMENTS:
            cursor.execute(idx)

        # Create Analytical Views
        logger.info("Creating business SQL views...")
        for v_sql in VIEW_STATEMENTS:
            cursor.execute(v_sql)

        # Commit entire transaction
        conn.commit()
        logger.info(f"Successfully loaded Star Schema and views into {db_path}!")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to load data into SQLite: {str(e)}", exc_info=True)
        raise RuntimeError(f"Database loading failed: {str(e)}") from e
    finally:
        conn.close()


def query_views(db_path: Path = DATABASE_PATH) -> Dict[str, pd.DataFrame]:
    """Query each of the 3 analytical SQL views and return results as DataFrames."""
    conn = sqlite3.connect(db_path)
    view_names = ["v_pnl_by_risk_profile", "v_monthly_deposits", "v_loan_default_rate_by_credit_band"]
    results = {}
    for v in view_names:
        results[v] = pd.read_sql_query(f"SELECT * FROM {v};", conn)
    conn.close()
    return results
