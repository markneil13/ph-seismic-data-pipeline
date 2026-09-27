import os
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "crypto_warehouse.duckdb")

def run_quality_checks() -> bool:
    """Executes automated Data Quality Assertions on Bronze, Silver, and Gold schemas."""
    print("[QUALITY ASSURANCE] Running Data Quality Assertions...")
    con = duckdb.connect(DB_PATH)
    passed = True
    checks = []
    
    # Check 1: Bronze table non-empty
    raw_count = con.execute("SELECT COUNT(*) FROM bronze.raw_ohlcv_klines").fetchone()[0]
    c1 = raw_count > 0
    checks.append(("Bronze raw OHLCV count > 0", c1, f"Count = {raw_count}"))
    
    # Check 2: Silver no negative or zero prices
    bad_prices = con.execute("SELECT COUNT(*) FROM silver.fact_crypto_daily WHERE close_price <= 0 OR close_price IS NULL").fetchone()[0]
    c2 = bad_prices == 0
    checks.append(("Silver close_price non-null and > 0", c2, f"Bad records = {bad_prices}"))
    
    # Check 3: RSI range check [0, 100]
    invalid_rsi = con.execute("SELECT COUNT(*) FROM silver.fact_crypto_daily WHERE rsi_14 IS NOT NULL AND (rsi_14 < 0 OR rsi_14 > 100)").fetchone()[0]
    c3 = invalid_rsi == 0
    checks.append(("Silver RSI_14 bounded in [0, 100]", c3, f"Invalid RSI records = {invalid_rsi}"))
    
    # Check 4: Gold ML Forecast count matches coin count
    forecast_count = con.execute("SELECT COUNT(*) FROM gold.ml_crypto_forecasts").fetchone()[0]
    c4 = forecast_count > 0
    checks.append(("Gold ML Forecast records > 0", c4, f"Forecast count = {forecast_count}"))
    
    # Check 5: Gold ML Bullish Probability range check [0, 100]
    invalid_prob = con.execute("SELECT COUNT(*) FROM gold.ml_crypto_forecasts WHERE ml_bullish_prob_pct < 0 OR ml_bullish_prob_pct > 100").fetchone()[0]
    c5 = invalid_prob == 0
    checks.append(("Gold ML Bullish Prob bounded in [0, 100]%", c5, f"Invalid prob records = {invalid_prob}"))
    
    print("-" * 75)
    for desc, is_pass, detail in checks:
        status = "[PASS]" if is_pass else "[FAIL]"
        print(f"  {status:7s} | {desc:45s} | {detail}")
        if not is_pass:
            passed = False
    print("-" * 75)
    
    con.close()
    if passed:
        print("[QUALITY ASSURANCE] All Data Quality Checks Passed Successfully!\n")
    else:
        print("[QUALITY ASSURANCE] WARNING: Quality check failures detected!\n")
    return passed

if __name__ == "__main__":
    run_quality_checks()
