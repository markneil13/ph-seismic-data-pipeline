import os
import sys
import duckdb
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.regions_ph import PH_REGIONS

def check_enso_bronze(df_enso):
    """Validates NOAA Niño 3.4 SST index Bronze dataset."""
    if df_enso is None or len(df_enso) == 0:
        return False, "ENSO Bronze check failed: DataFrame is empty or None"
    
    if df_enso['nino34_sst'].isnull().sum() > 0 or df_enso['nino34_anom'].isnull().sum() > 0:
        return False, "ENSO Bronze check failed: NULL values found in SST or Anomaly columns"
        
    invalid_sst = ((df_enso['nino34_sst'] < 20.0) | (df_enso['nino34_sst'] > 35.0)).sum()
    if invalid_sst > 0:
        return False, f"ENSO Bronze check failed: {invalid_sst} records with physical SST out of bounds (20-35°C)"
        
    invalid_anom = ((df_enso['nino34_anom'] < -4.5) | (df_enso['nino34_anom'] > 5.5)).sum()
    if invalid_anom > 0:
        return False, f"ENSO Bronze check failed: {invalid_anom} records with anomaly out of bounds (-4.5 to +5.5°C)"
        
    return True, f"ENSO Bronze checks passed ({len(df_enso)} monthly records validated)"

def check_ph_climate_bronze(df_climate):
    """Validates Open-Meteo Philippine climate observations Bronze dataset."""
    if df_climate is None or len(df_climate) == 0:
        return False, "Climate Bronze check failed: DataFrame is empty or None"
        
    if len(df_climate) < 150:
        return False, f"Climate Bronze check failed: expected at least 150 observations, got {len(df_climate)}"
        
    neg_precip = (df_climate['precipitation_mm'] < 0.0).sum()
    if neg_precip > 0:
        return False, f"Climate Bronze check failed: {neg_precip} negative precipitation records found"
        
    invalid_temp = ((df_climate['temp_max_c'] < 12.0) | (df_climate['temp_max_c'] > 48.0)).sum()
    if invalid_temp > 0:
        return False, f"Climate Bronze check failed: {invalid_temp} records with extreme/unphysical max temperatures"
        
    valid_soil = df_climate['soil_moisture_rootzone'].dropna()
    invalid_soil = ((valid_soil < 0.0) | (valid_soil > 0.85)).sum()
    if invalid_soil > 0:
        return False, f"Climate Bronze check failed: {invalid_soil} records with unphysical soil moisture"
        
    present_regions = set(df_climate['region_id'].unique())
    expected_regions = set([r['region_id'] for r in PH_REGIONS])
    missing = expected_regions - present_regions
    if len(missing) > 0:
        return False, f"Climate Bronze check failed: missing expected regions: {missing}"
        
    return True, f"Climate Bronze checks passed ({len(df_climate)} daily observations across {len(present_regions)} Philippine regions)"

def run_ph_quality_checks(df_enso=None, df_climate=None, db_path=None):
    """Executes the full suite of non-tautological data quality checks for Philippines pipeline."""
    print("[QUALITY] Running Philippine Super El Niño Data Quality Assertions...")
    passed = 0
    failed = 0
    
    # Check 1: In-memory Bronze ENSO
    if df_enso is not None:
        ok, msg = check_enso_bronze(df_enso)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 1: {msg}")
        if ok: passed += 1
        else: failed += 1
        
    # Check 2: In-memory Bronze Philippine Climate
    if df_climate is not None:
        ok, msg = check_ph_climate_bronze(df_climate)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 2: {msg}")
        if ok: passed += 1
        else: failed += 1

    # Check 3-6: Silver & Gold Warehouse assertions
    if db_path and os.path.exists(db_path):
        con = duckdb.connect(db_path)
        
        # Check 3: Silver daily climate record uniqueness
        dup_count = con.execute("""
            SELECT COUNT(*) - COUNT(DISTINCT record_id) FROM silver.ph_daily_climate
        """).fetchone()[0]
        ok = (dup_count == 0)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 3: Silver daily climate uniqueness (Duplicates found: {dup_count})")
        if ok: passed += 1
        else: failed += 1
        
        # Check 4: Consecutive dry days logical consistency
        cdd_errors = con.execute("""
            SELECT COUNT(*) FROM silver.ph_daily_climate
            WHERE is_dry_day = 0 AND consecutive_dry_days > 0
        """).fetchone()[0]
        ok = (cdd_errors == 0)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 4: CDD calculation logic integrity (Violations: {cdd_errors})")
        if ok: passed += 1
        else: failed += 1
        
        # Check 5: Gold Bulletin score range bounds (0 to 100)
        score_oob = con.execute("""
            SELECT COUNT(*) FROM gold.dm_ph_el_nino_bulletin
            WHERE drought_severity_index < 0.0 OR drought_severity_index > 100.0
        """).fetchone()[0]
        ok = (score_oob == 0)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 5: Gold SEDI score boundary check [0, 100] (Out of bounds: {score_oob})")
        if ok: passed += 1
        else: failed += 1
        
        # Check 6: All 16 Philippine regions represented in Gold bulletin
        gold_reg_count = con.execute("SELECT COUNT(DISTINCT region_id) FROM gold.dm_ph_el_nino_bulletin").fetchone()[0]
        ok = (gold_reg_count == len(PH_REGIONS))
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 6: Regional completeness ({gold_reg_count}/{len(PH_REGIONS)} regions populated)")
        if ok: passed += 1
        else: failed += 1
        
        con.close()
        
    print(f"[QUALITY] Finished: {passed} PASSED, {failed} FAILED\n")
    return (failed == 0)
