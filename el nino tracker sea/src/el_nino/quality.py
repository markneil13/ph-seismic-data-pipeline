import os
import sys
from datetime import datetime, timezone
import pandas as pd
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino.regions import SEA_REGIONS

def check_enso_bronze(df_enso):
    """Validates NOAA Niño 3.4 SST index Bronze dataset."""
    if df_enso is None or len(df_enso) == 0:
        return False, "ENSO Bronze check failed: DataFrame is empty or None"
    
    if df_enso['nino34_sst'].isnull().sum() > 0 or df_enso['nino34_anom'].isnull().sum() > 0:
        return False, "ENSO Bronze check failed: NULL values found in SST or Anomaly columns"
        
    # Physical limits for equatorial Pacific SST
    invalid_sst = ((df_enso['nino34_sst'] < 20.0) | (df_enso['nino34_sst'] > 35.0)).sum()
    if invalid_sst > 0:
        return False, f"ENSO Bronze check failed: {invalid_sst} records with physical SST out of bounds (20-35°C)"
        
    invalid_anom = ((df_enso['nino34_anom'] < -4.5) | (df_enso['nino34_anom'] > 5.5)).sum()
    if invalid_anom > 0:
        return False, f"ENSO Bronze check failed: {invalid_anom} records with anomaly out of bounds (-4.5 to +5.5°C)"
        
    return True, f"ENSO Bronze checks passed ({len(df_enso)} monthly records validated)"

def check_climate_bronze(df_climate):
    """Validates Open-Meteo regional climate observations Bronze dataset."""
    if df_climate is None or len(df_climate) == 0:
        return False, "Climate Bronze check failed: DataFrame is empty or None"
        
    if len(df_climate) < 100:
        return False, f"Climate Bronze check failed: expected at least 100 observations, got {len(df_climate)}"
        
    # Non-negative precipitation
    neg_precip = (df_climate['precipitation_mm'] < 0.0).sum()
    if neg_precip > 0:
        return False, f"Climate Bronze check failed: {neg_precip} negative precipitation records found"
        
    # Temperature sanity bounds (15°C to 50°C for tropical SEA)
    invalid_temp = ((df_climate['temp_max_c'] < 15.0) | (df_climate['temp_max_c'] > 50.0)).sum()
    if invalid_temp > 0:
        return False, f"Climate Bronze check failed: {invalid_temp} records with extreme/unphysical max temperatures"
        
    # Soil moisture bounds (0.0 to 0.85 m3/m3)
    valid_soil = df_climate['soil_moisture_rootzone'].dropna()
    invalid_soil = ((valid_soil < 0.0) | (valid_soil > 0.85)).sum()
    if invalid_soil > 0:
        return False, f"Climate Bronze check failed: {invalid_soil} records with unphysical soil moisture"
        
    # Ensure regions coverage
    present_regions = set(df_climate['region_id'].unique())
    expected_regions = set([r['region_id'] for r in SEA_REGIONS])
    missing = expected_regions - present_regions
    if len(missing) > 0:
        return False, f"Climate Bronze check failed: missing expected regions: {missing}"
        
    return True, f"Climate Bronze checks passed ({len(df_climate)} daily observations across {len(present_regions)} SEA regions)"

def run_el_nino_quality_checks(df_enso=None, df_climate=None):
    """Executes the full suite of non-tautological data quality checks."""
    print("[QUALITY] Running Super El Niño Data Quality Assertions...")
    passed = 0
    failed = 0
    
    if df_enso is not None:
        ok, msg = check_enso_bronze(df_enso)
        if ok:
            print(f"  [PASS] {msg}")
            passed += 1
        else:
            print(f"  [FAIL] {msg}")
            failed += 1
            
    if df_climate is not None:
        ok, msg = check_climate_bronze(df_climate)
        if ok:
            print(f"  [PASS] {msg}")
            passed += 1
        else:
            print(f"  [FAIL] {msg}")
            failed += 1
            
    print(f"\n[SUMMARY] Data Quality Results: {passed} Passed, {failed} Failed.")
    if failed > 0:
        print("[FAIL] Quality Checks FAILED!\n")
        return False
    else:
        print("[OK] All Data Quality Checks PASSED!\n")
        return True

if __name__ == "__main__":
    from src.el_nino.ingestion import fetch_noaa_enso_data, fetch_sea_climate_data
    df_e = fetch_noaa_enso_data()
    df_c = fetch_sea_climate_data(past_days=10)
    success = run_el_nino_quality_checks(df_e, df_c)
    if not success:
        sys.exit(1)
