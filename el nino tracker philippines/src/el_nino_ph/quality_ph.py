import os
import sys
import duckdb
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.config_ph import (
    MAX_PRECIPITATION_NULL_PCT,
    MAX_SOIL_NULL_PCT,
    MAX_DATA_LATENCY_DAYS
)
from src.el_nino_ph.regions_ph import PH_REGIONS

def check_enso_bronze(df_enso):
    """Validates NOAA Niño 3.4 SST index Bronze dataset."""
    if df_enso is None or len(df_enso) == 0:
        return False, "ENSO Bronze check failed: DataFrame is empty or None"
    
    if df_enso['nino34_sst'].isnull().sum() > 0 or df_enso['nino34_anom'].isnull().sum() > 0:
        return False, "ENSO Bronze check failed: NULL values found in SST or Anomaly columns"
        
    invalid_sst = ((df_enso['nino34_sst'] < 18.0) | (df_enso['nino34_sst'] > 35.0)).sum()
    if invalid_sst > 0:
        return False, f"ENSO Bronze check failed: {invalid_sst} records with physical SST out of bounds (18-35°C)"
        
    invalid_anom = ((df_enso['nino34_anom'] < -4.5) | (df_enso['nino34_anom'] > 5.5)).sum()
    if invalid_anom > 0:
        return False, f"ENSO Bronze check failed: {invalid_anom} records with anomaly out of bounds (-4.5 to +5.5°C)"
        
    return True, f"ENSO Bronze checks passed ({len(df_enso)} monthly records validated)"

def check_oni_bronze(df_oni):
    """Validates NOAA ONI Bronze dataset."""
    if df_oni is None or len(df_oni) == 0:
        return False, "ONI Bronze check failed: DataFrame is empty or None"
        
    if df_oni['oni_anomaly'].isnull().sum() > 0:
        return False, "ONI Bronze check failed: NULL values found in ONI anomaly"
        
    valid_seasons = {"DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"}
    present_seasons = set(df_oni['season'].unique())
    if not present_seasons.issubset(valid_seasons):
        return False, f"ONI Bronze check failed: invalid season codes found: {present_seasons - valid_seasons}"
        
    return True, f"ONI Bronze checks passed ({len(df_oni)} seasonal records validated)"

def check_ph_climate_bronze(df_climate):
    """Validates Open-Meteo Philippine completed climate observations Bronze dataset."""
    if df_climate is None or len(df_climate) == 0:
        return False, "Climate Bronze check failed: DataFrame is empty or None"
        
    total_expected = len(PH_REGIONS)
    if len(df_climate) < total_expected * 20:
        return False, f"Climate Bronze check failed: expected at least {total_expected * 20} observations, got {len(df_climate)}"
        
    neg_precip = (df_climate['precipitation_mm'] < 0.0).sum()
    if neg_precip > 0:
        return False, f"Climate Bronze check failed: {neg_precip} negative precipitation records found"
        
    invalid_temp = ((df_climate['temp_max_c'] < 10.0) | (df_climate['temp_max_c'] > 50.0)).sum()
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
        
    return True, f"Climate Bronze checks passed ({len(df_climate)} daily observations across {len(present_regions)}/{total_expected} Philippine regions)"

def run_ph_quality_checks(df_enso=None, df_oni=None, df_climate=None, db_path=None):
    """
    Executes the full suite of non-tautological data quality and integrity checks.
    Returns (True, passed, failed) if all checks pass, otherwise (False, passed, failed).
    """
    print("[QUALITY] Running Philippine Super El Niño Data Quality Assertions...")
    passed = 0
    failed = 0
    total_regions = len(PH_REGIONS)
    
    # Check 1: In-memory Bronze ENSO
    if df_enso is not None:
        ok, msg = check_enso_bronze(df_enso)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 1: {msg}")
        if ok: passed += 1
        else: failed += 1
        
    # Check 2: In-memory Bronze ONI
    if df_oni is not None:
        ok, msg = check_oni_bronze(df_oni)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 2: {msg}")
        if ok: passed += 1
        else: failed += 1
        
    # Check 3: In-memory Bronze Philippine Climate
    if df_climate is not None:
        ok, msg = check_ph_climate_bronze(df_climate)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 3: {msg}")
        if ok: passed += 1
        else: failed += 1

    # Warehouse checks (Silver & Gold)
    if db_path and os.path.exists(db_path):
        con = duckdb.connect(db_path)
        
        # Check 4: CDD recurrence with LAG (rain day = 0, dry day = prev CDD + 1)
        cdd_recurrence_errors = con.execute("""
            WITH lag_eval AS (
                SELECT 
                    region_id,
                    date,
                    is_dry_day,
                    consecutive_dry_days,
                    LAG(consecutive_dry_days, 1, 0) OVER (PARTITION BY region_id ORDER BY date) AS prev_cdd
                FROM silver.ph_daily_climate
            )
            SELECT COUNT(*) FROM lag_eval
            WHERE (is_dry_day = 0 AND consecutive_dry_days != 0)
               OR (is_dry_day = 1 AND consecutive_dry_days != prev_cdd + 1);
        """).fetchone()[0]
        ok = (cdd_recurrence_errors == 0)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 4: CDD recurrence logic with LAG (Violations found: {cdd_recurrence_errors})")
        if ok: passed += 1
        else: failed += 1
        
        # Check 5: Continuous daily series with no date gaps
        date_gaps = con.execute("""
            WITH date_diffs AS (
                SELECT 
                    region_id,
                    date,
                    LAG(date) OVER (PARTITION BY region_id ORDER BY date) AS prev_date
                FROM silver.ph_daily_climate
            )
            SELECT COUNT(*) FROM date_diffs
            WHERE prev_date IS NOT NULL AND DATEDIFF('day', prev_date, date) != 1;
        """).fetchone()[0]
        ok = (date_gaps == 0)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 5: Continuous daily series (Gaps found: {date_gaps})")
        if ok: passed += 1
        else: failed += 1
        
        # Check 6: Null rate for precipitation & soil moisture below configurable limit
        null_stats = con.execute("""
            SELECT 
                ROUND(AVG(CASE WHEN precipitation_mm IS NULL THEN 1.0 ELSE 0.0 END) * 100.0, 2) AS precip_null_pct,
                ROUND(AVG(CASE WHEN soil_moisture_rootzone IS NULL THEN 1.0 ELSE 0.0 END) * 100.0, 2) AS soil_null_pct
            FROM silver.ph_daily_climate;
        """).fetchone()
        precip_null_pct, soil_null_pct = null_stats[0], null_stats[1]
        ok = (precip_null_pct <= MAX_PRECIPITATION_NULL_PCT and soil_null_pct <= MAX_SOIL_NULL_PCT)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 6: Null rates (Precip: {precip_null_pct}% <= {MAX_PRECIPITATION_NULL_PCT}%, Soil: {soil_null_pct}% <= {MAX_SOIL_NULL_PCT}%)")
        if ok: passed += 1
        else: failed += 1
        
        # Check 7: Data freshness (as_of_date within MAX_DATA_LATENCY_DAYS)
        max_latency = con.execute("SELECT MAX(data_latency_days) FROM gold.dm_ph_el_nino_bulletin").fetchone()[0]
        ok = (max_latency is not None and max_latency <= MAX_DATA_LATENCY_DAYS)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 7: Data freshness (Max latency: {max_latency} days <= {MAX_DATA_LATENCY_DAYS} days)")
        if ok: passed += 1
        else: failed += 1
        
        # Check 8: All percentile and severity columns lie within [0, 100]
        oob_severities = con.execute("""
            SELECT COUNT(*) FROM gold.dm_ph_el_nino_bulletin
            WHERE rain_severity < 0.0 OR rain_severity > 100.0
               OR soil_severity < 0.0 OR soil_severity > 100.0
               OR dry_spell_severity < 0.0 OR dry_spell_severity > 100.0
               OR heat_severity < 0.0 OR heat_severity > 100.0
               OR drought_severity_index < 0.0 OR drought_severity_index > 100.0;
        """).fetchone()[0]
        ok = (oob_severities == 0)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 8: Severity score boundary check [0, 100] (Out of bounds: {oob_severities})")
        if ok: passed += 1
        else: failed += 1
        
        # Check 9: Regional completeness uses len(PH_REGIONS)
        gold_reg_count = con.execute("SELECT COUNT(DISTINCT region_id) FROM gold.dm_ph_el_nino_bulletin").fetchone()[0]
        ok = (gold_reg_count == total_regions)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 9: Regional completeness ({gold_reg_count}/{total_regions} basins populated)")
        if ok: passed += 1
        else: failed += 1
        
        # Check 10: Contiguous ONI seasons
        oni_sequence_breaks = con.execute("""
            WITH season_order AS (
                SELECT 
                    year, 
                    oni_season,
                    LAG(oni_season) OVER (ORDER BY year, 
                        CASE oni_season
                            WHEN 'DJF' THEN 1 WHEN 'JFM' THEN 2 WHEN 'FMA' THEN 3 WHEN 'MAM' THEN 4
                            WHEN 'AMJ' THEN 5 WHEN 'MJJ' THEN 6 WHEN 'JJA' THEN 7 WHEN 'JAS' THEN 8
                            WHEN 'ASO' THEN 9 WHEN 'SON' THEN 10 WHEN 'OND' THEN 11 WHEN 'NDJ' THEN 12
                        END
                    ) AS prev_season
                FROM silver.enso_monthly
                WHERE oni_anomaly IS NOT NULL
            )
            SELECT COUNT(*) FROM season_order
            WHERE prev_season IS NOT NULL
              AND NOT (
                (prev_season = 'DJF' AND oni_season = 'JFM') OR (prev_season = 'JFM' AND oni_season = 'FMA') OR
                (prev_season = 'FMA' AND oni_season = 'MAM') OR (prev_season = 'MAM' AND oni_season = 'AMJ') OR
                (prev_season = 'AMJ' AND oni_season = 'MJJ') OR (prev_season = 'MJJ' AND oni_season = 'JJA') OR
                (prev_season = 'JJA' AND oni_season = 'JAS') OR (prev_season = 'JAS' AND oni_season = 'ASO') OR
                (prev_season = 'ASO' AND oni_season = 'SON') OR (prev_season = 'SON' AND oni_season = 'OND') OR
                (prev_season = 'OND' AND oni_season = 'NDJ') OR (prev_season = 'NDJ' AND oni_season = 'DJF')
              );
        """).fetchone()[0]
        ok = (oni_sequence_breaks == 0)
        print(f"  [{'PASS' if ok else 'FAIL'}] Check 10: Contiguous ONI seasons sequence (Gaps found: {oni_sequence_breaks})")
        if ok: passed += 1
        else: failed += 1
        
        con.close()
        
    print(f"[QUALITY] Finished: {passed} PASSED, {failed} FAILED\n")
    return (failed == 0)
