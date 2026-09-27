import os
import time
import requests
import pandas as pd
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "crypto_warehouse.duckdb")

COINS = [
    {"symbol": "BTCUSDT", "id": "bitcoin", "name": "Bitcoin"},
    {"symbol": "ETHUSDT", "id": "ethereum", "name": "Ethereum"},
    {"symbol": "SOLUSDT", "id": "solana", "name": "Solana"},
    {"symbol": "BNBUSDT", "id": "binancecoin", "name": "BNB"},
    {"symbol": "XRPUSDT", "id": "ripple", "name": "XRP"},
    {"symbol": "ADAUSDT", "id": "cardano", "name": "Cardano"},
]

def fetch_binance_klines(symbol: str, interval: str = "1d", limit: int = 120) -> pd.DataFrame:
    """Fetches historical OHLCV candlestick data from Binance public API."""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    # Binance kline format: [open_time, open, high, low, close, volume, close_time, quote_vol, trades, ...]
    rows = []
    for item in data:
        rows.append({
            "symbol": symbol,
            "open_time_ms": item[0],
            "open_price": float(item[1]),
            "high_price": float(item[2]),
            "low_price": float(item[3]),
            "close_price": float(item[4]),
            "volume": float(item[5]),
            "quote_asset_volume": float(item[7]),
            "number_of_trades": int(item[8])
        })
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["open_time_ms"], unit="ms")
    return df

def fetch_coingecko_markets() -> pd.DataFrame:
    """Fetches live market metrics (price, 24h change, market cap, rank) from CoinGecko public API."""
    ids = ",".join([c["id"] for c in COINS])
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids}&order=market_cap_desc&sparkline=false&price_change_percentage=24h"
    headers = {"User-Agent": "CryptoEngine/1.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    rows = []
    for coin in data:
        rows.append({
            "coin_id": coin["id"],
            "symbol": coin["symbol"].upper() + "USDT",
            "name": coin["name"],
            "current_price": float(coin.get("current_price") or 0.0),
            "market_cap": float(coin.get("market_cap") or 0.0),
            "market_cap_rank": int(coin.get("market_cap_rank") or 0),
            "total_volume": float(coin.get("total_volume") or 0.0),
            "high_24h": float(coin.get("high_24h") or 0.0),
            "low_24h": float(coin.get("low_24h") or 0.0),
            "price_change_percentage_24h": float(coin.get("price_change_percentage_24h") or 0.0),
            "fetched_at": pd.Timestamp.utcnow()
        })
    return pd.DataFrame(rows)

def run_ingestion():
    """Ingests live market data & historical OHLCV candles into DuckDB Bronze Layer."""
    print("[BRONZE INGESTION] Ingesting Live Crypto Market Data...")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = duckdb.connect(DB_PATH)
    
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze;")
    
    # 1. Fetch & Store Live Market Summary
    try:
        df_markets = fetch_coingecko_markets()
        con.execute("CREATE OR REPLACE TABLE bronze.raw_market_tickers AS SELECT * FROM df_markets")
        print(f"  -> Ingested {len(df_markets)} live tickers into bronze.raw_market_tickers")
    except Exception as e:
        print(f"  [WARN] CoinGecko market fetch fallback: {e}")
        # Fallback dummy ticker schema if API rate limited
        con.execute("""
            CREATE TABLE IF NOT EXISTS bronze.raw_market_tickers (
                coin_id VARCHAR, symbol VARCHAR, name VARCHAR, current_price DOUBLE,
                market_cap DOUBLE, market_cap_rank INTEGER, total_volume DOUBLE,
                high_24h DOUBLE, low_24h DOUBLE, price_change_percentage_24h DOUBLE,
                fetched_at TIMESTAMP
            );
        """)

    # 2. Fetch & Store OHLCV Historical Candle Series per Coin
    all_klines = []
    for coin in COINS:
        try:
            df_kline = fetch_binance_klines(coin["symbol"], interval="1d", limit=120)
            df_kline["coin_id"] = coin["id"]
            df_kline["coin_name"] = coin["name"]
            all_klines.append(df_kline)
            print(f"  -> Ingested {len(df_kline)} candles for {coin['name']} ({coin['symbol']})")
            time.sleep(0.1)
        except Exception as e:
            print(f"  [WARN] Failed to fetch klines for {coin['symbol']}: {e}")
            
    if all_klines:
        full_klines_df = pd.concat(all_klines, ignore_index=True)
        con.execute("CREATE OR REPLACE TABLE bronze.raw_ohlcv_klines AS SELECT * FROM full_klines_df")
        print(f"  -> Total {len(full_klines_df)} candle records stored in bronze.raw_ohlcv_klines")
    else:
        raise RuntimeError("No historical candle data could be ingested.")
        
    con.close()
    print("[BRONZE INGESTION] Completed successfully.\n")

if __name__ == "__main__":
    run_ingestion()
