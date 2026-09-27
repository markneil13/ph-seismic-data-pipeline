import os
import duckdb
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "crypto_warehouse.duckdb")

def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Computes technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, Volatility) for OHLCV data."""
    df = df.sort_values(by=["symbol", "timestamp"]).reset_index(drop=True)
    
    # Process per coin symbol
    processed_dfs = []
    for symbol, group in df.groupby("symbol"):
        g = group.copy()
        
        # Returns
        g["daily_return"] = g["close_price"].pct_change()
        g["log_return"] = np.log(g["close_price"] / g["close_price"].shift(1))
        
        # Moving Averages
        g["sma_7"] = g["close_price"].rolling(window=7).mean()
        g["sma_14"] = g["close_price"].rolling(window=14).mean()
        g["sma_50"] = g["close_price"].rolling(window=50).mean()
        
        g["ema_12"] = g["close_price"].ewm(span=12, adjust=False).mean()
        g["ema_26"] = g["close_price"].ewm(span=26, adjust=False).mean()
        
        # MACD
        g["macd"] = g["ema_12"] - g["ema_26"]
        g["macd_signal"] = g["macd"].ewm(span=9, adjust=False).mean()
        g["macd_hist"] = g["macd"] - g["macd_signal"]
        
        # RSI (14-day)
        delta = g["close_price"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        g["rsi_14"] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands (20-day, 2 std dev)
        g["bb_middle"] = g["close_price"].rolling(window=20).mean()
        g["bb_std"] = g["close_price"].rolling(window=20).std()
        g["bb_upper"] = g["bb_middle"] + (2 * g["bb_std"])
        g["bb_lower"] = g["bb_middle"] - (2 * g["bb_std"])
        g["bb_pct_b"] = (g["close_price"] - g["bb_lower"]) / ((g["bb_upper"] - g["bb_lower"]) + 1e-9)
        
        # Rolling Volatility (14-day std dev of log returns)
        g["volatility_14d"] = g["log_return"].rolling(window=14).std() * np.sqrt(365)
        
        # Target for ML: Next day price direction (1 if next day close > current day close, 0 otherwise)
        g["next_close"] = g["close_price"].shift(-1)
        g["target_return_24h"] = (g["next_close"] - g["close_price"]) / g["close_price"]
        g["target_direction_24h"] = (g["target_return_24h"] > 0).astype(int)
        
        processed_dfs.append(g)
        
    final_df = pd.concat(processed_dfs, ignore_index=True)
    return final_df

def run_transformation():
    """Transforms Bronze raw data into Silver schema with rich feature engineering."""
    print("[SILVER TRANSFORMATION] Processing Technical Indicators & Features...")
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    
    # Fetch raw candles
    raw_df = con.execute("SELECT * FROM bronze.raw_ohlcv_klines").fetchdf()
    
    # Clean & Transform
    silver_df = compute_technical_indicators(raw_df)
    
    # Store into Silver schema
    con.execute("CREATE OR REPLACE TABLE silver.fact_crypto_daily AS SELECT * FROM silver_df")
    
    # Store Enriched Tickers Summary
    con.execute("""
        CREATE OR REPLACE TABLE silver.dim_crypto_assets AS
        SELECT 
            symbol,
            coin_id,
            coin_name,
            MIN(timestamp) AS history_start_date,
            MAX(timestamp) AS history_end_date,
            COUNT(*) AS total_candle_count
        FROM silver.fact_crypto_daily
        GROUP BY symbol, coin_id, coin_name
    """)
    
    print(f"  -> Engineered technical indicators for {len(silver_df)} daily candles across {silver_df['symbol'].nunique()} assets")
    print("[SILVER TRANSFORMATION] Completed successfully.\n")
    con.close()

if __name__ == "__main__":
    run_transformation()
