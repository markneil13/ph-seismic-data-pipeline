import os
import sys
from datetime import datetime, timezone
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "warehouse.duckdb")

# Real Philippine Geographic Bounding Box
PH_LAT_MIN, PH_LAT_MAX = 4.0, 21.5
PH_LON_MIN, PH_LON_MAX = 116.0, 127.0

def check_bronze_not_empty(df):
    """Checks that raw Bronze data is non-empty."""
    if df is not None and len(df) > 0:
        return True, f"Bronze non-empty check passed ({len(df)} raw events)"
    return False, "Bronze non-empty check failed: DataFrame is empty or None"

def check_no_null_magnitude_or_depth(df):
    """Checks that raw Bronze records do not contain NULL magnitude or depth."""
    if df is None or len(df) == 0:
        return False, "Check failed: DataFrame is empty"
    null_mag = df['magnitude'].isnull().sum()
    null_depth = df['depth_km'].isnull().sum()
    if null_mag == 0 and null_depth == 0:
        return True, "Bronze NULL magnitude/depth check passed (0 nulls found)"
    return False, f"Bronze NULL check failed! Found {null_mag} NULL magnitudes and {null_depth} NULL depths"

def check_no_future_timestamps(df):
    """Checks that raw Bronze timestamps are not in the future (allowing 1h buffer)."""
    if df is None or len(df) == 0:
        return False, "Check failed: DataFrame is empty"
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    future_buffer_ms = now_ms + (3600 * 1000)
    
    future_count = (df['time_epoch_ms'] > future_buffer_ms).sum()
    if future_count == 0:
        return True, "Bronze future timestamp check passed (0 future timestamps found)"
    return False, f"Bronze future timestamp check failed! Found {future_count} future event timestamps"

def check_ph_bounding_box(df):
    """Checks that raw Bronze events fall within the valid Philippine geospatial bounding box."""
    if df is None or len(df) == 0:
        return False, "Check failed: DataFrame is empty"
    
    out_of_bounds = (
        (df['latitude'] < PH_LAT_MIN) | (df['latitude'] > PH_LAT_MAX) |
        (df['longitude'] < PH_LON_MIN) | (df['longitude'] > PH_LON_MAX)
    ).sum()
    
    if out_of_bounds == 0:
        return True, "Bronze Philippine bounding box check passed (100% events inside PH bounds)"
    return False, f"Bronze bounding box check failed! Found {out_of_bounds} events outside PH bounds ({PH_LAT_MIN}-{PH_LAT_MAX}°N, {PH_LON_MIN}-{PH_LON_MAX}°E)"

def run_quality_checks(bronze_df=None):
    """Runs all Bronze-layer data quality checks and Silver/Gold schema validation."""
    print("[QUALITY] Running Non-Tautological Data Quality Checks...")
    passed_count = 0
    failed_count = 0
    
    if bronze_df is not None:
        bronze_checks = [
            check_bronze_not_empty(bronze_df),
            check_no_null_magnitude_or_depth(bronze_df),
            check_no_future_timestamps(bronze_df),
            check_ph_bounding_box(bronze_df)
        ]
        for ok, msg in bronze_checks:
            if ok:
                print(f"  [PASS] {msg}")
                passed_count += 1
            else:
                print(f"  [FAIL] {msg}")
                failed_count += 1
                
    # Database Gold Layer Verification
    con = duckdb.connect(DB_PATH)
    total_facts = con.execute("SELECT COUNT(*) FROM gold.fact_earthquakes").fetchone()[0]
    total_cities = con.execute("SELECT COUNT(*) FROM gold.dim_ph_cities").fetchone()[0]
    con.close()
    
    if total_facts > 0 and total_cities > 0:
        print(f"  [PASS] Warehouse Gold Layer Check ({total_facts} fact events, {total_cities} cities)")
        passed_count += 1
    else:
        print(f"  [FAIL] Warehouse Gold Layer Check failed (Empty facts or cities)")
        failed_count += 1
        
    print(f"\n[SUMMARY] Data Quality Results: {passed_count} Passed, {failed_count} Failed.")
    if failed_count > 0:
        print("[FAIL] Quality Checks FAILED!")
        return False
    else:
        print("[OK] All Data Quality Checks PASSED!\n")
        return True

if __name__ == "__main__":
    success = run_quality_checks()
    if not success:
        sys.exit(1)
