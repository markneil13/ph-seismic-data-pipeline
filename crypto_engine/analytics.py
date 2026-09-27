import os
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "crypto_warehouse.duckdb")

def run_analytics():
    """Builds Gold Data Marts in DuckDB for reporting and dashboard serving."""
    print("[GOLD ANALYTICS] Building Data Marts & Performance Aggregations...")
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    
    # 1. Asset Performance Data Mart
    con.execute("""
        CREATE OR REPLACE TABLE gold.mart_asset_performance AS
        WITH Base AS (
            SELECT 
                symbol,
                coin_name,
                timestamp,
                close_price,
                daily_return,
                volatility_14d,
                rsi_14,
                sma_50,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY timestamp DESC) AS rn_desc
            FROM silver.fact_crypto_daily
        ),
        Returns7d AS (
            SELECT 
                symbol,
                (FIRST(close_price ORDER BY timestamp DESC) - FIRST(close_price ORDER BY timestamp ASC)) / FIRST(close_price ORDER BY timestamp ASC) * 100 AS return_7d_pct
            FROM silver.fact_crypto_daily
            WHERE timestamp >= CURRENT_DATE - INTERVAL '7 DAYS'
            GROUP BY symbol
        ),
        Returns30d AS (
            SELECT 
                symbol,
                (FIRST(close_price ORDER BY timestamp DESC) - FIRST(close_price ORDER BY timestamp ASC)) / FIRST(close_price ORDER BY timestamp ASC) * 100 AS return_30d_pct
            FROM silver.fact_crypto_daily
            WHERE timestamp >= CURRENT_DATE - INTERVAL '30 DAYS'
            GROUP BY symbol
        )
        SELECT 
            b.symbol,
            b.coin_name,
            b.close_price AS latest_price_usd,
            ROUND(b.rsi_14, 2) AS rsi_14,
            ROUND(b.volatility_14d * 100, 2) AS volatility_14d_pct,
            ROUND(r7.return_7d_pct, 2) AS return_7d_pct,
            ROUND(r30.return_30d_pct, 2) AS return_30d_pct,
            ROUND((b.close_price - b.sma_50) / NULLIF(b.sma_50, 0) * 100, 2) AS vs_sma_50_pct
        FROM Base b
        LEFT JOIN Returns7d r7 ON b.symbol = r7.symbol
        LEFT JOIN Returns30d r30 ON b.symbol = r30.symbol
        WHERE b.rn_desc = 1
        ORDER BY b.symbol;
    """)
    print("  -> Created gold.mart_asset_performance")
    
    # 2. Complete Trading Signals Data Mart
    con.execute("""
        CREATE OR REPLACE TABLE gold.mart_trading_signals AS
        SELECT 
            f.symbol,
            f.coin_name,
            f.latest_close_price,
            f.rsi_14,
            f.macd_hist,
            f.volatility_annualized,
            f.ml_bullish_prob_pct,
            f.signal,
            f.volatility_risk,
            p.return_7d_pct,
            p.return_30d_pct,
            CASE 
                WHEN f.rsi_14 >= 70 THEN 'OVERBOUGHT'
                WHEN f.rsi_14 <= 30 THEN 'OVERSOLD'
                ELSE 'NEUTRAL'
            END AS rsi_status
        FROM gold.ml_crypto_forecasts f
        LEFT JOIN gold.mart_asset_performance p ON f.symbol = p.symbol
        ORDER BY f.ml_bullish_prob_pct DESC;
    """)
    print("  -> Created gold.mart_trading_signals")
    
    con.close()
    print("[GOLD ANALYTICS] Completed successfully.\n")

if __name__ == "__main__":
    run_analytics()
