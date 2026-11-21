import os
import sys
import json
import duckdb
import pandas as pd
import numpy as np
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.config_ph import CALENDAR_WINDOW_DAYS
from src.el_nino_ph.regions_ph import PH_REGIONS
from src.el_nino_ph.ingestion_ph import fetch_with_retry, ARCHIVE_API_URL

BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze", "el_nino_ph")
CLIMATOLOGY_DIR = os.path.join(BRONZE_DIR, "climatology")
DB_PATH = os.path.join(BASE_DIR, "data", "ph_el_nino_warehouse.duckdb")

def run_diagnosis():
    print("=" * 80)
    print("  DIAGNOSTIC 1: RECENT WINDOW VS CLIMATOLOGY SUMMARY (SOIL MOISTURE & TMAX)")
    print("=" * 80)

    con = duckdb.connect(DB_PATH)

    # 1. Recent vs Climatology min/median/max
    df_comp = con.execute(f"""
    WITH latest_date AS (
        SELECT MAX(date) as max_date FROM silver.ph_daily_climate
    ),
    recent_stats AS (
        SELECT 
            c.region_id,
            ROUND(AVG(c.soil_moisture_rootzone), 4) AS recent_mean_soil,
            ROUND(AVG(c.temp_max_c), 2) AS recent_mean_tmax
        FROM silver.ph_daily_climate c
        GROUP BY c.region_id
    ),
    ref_doy AS (
        SELECT dayofyear(max_date) AS doy FROM latest_date
    ),
    clim_stats AS (
        SELECT 
            h.region_id,
            ROUND(MIN(h.soil_moisture_rootzone), 4) AS clim_min_soil,
            ROUND(MEDIAN(h.soil_moisture_rootzone), 4) AS clim_med_soil,
            ROUND(MAX(h.soil_moisture_rootzone), 4) AS clim_max_soil,
            ROUND(MIN(h.temp_max_c), 2) AS clim_min_tmax,
            ROUND(MEDIAN(h.temp_max_c), 2) AS clim_med_tmax,
            ROUND(MAX(h.temp_max_c), 2) AS clim_max_tmax
        FROM silver.ph_climatology_daily h, ref_doy
        WHERE (h.day_of_year BETWEEN ref_doy.doy - {CALENDAR_WINDOW_DAYS} AND ref_doy.doy + {CALENDAR_WINDOW_DAYS})
        GROUP BY h.region_id
    )
    SELECT 
        r.region_id,
        r.recent_mean_soil,
        c.clim_min_soil,
        c.clim_med_soil,
        c.clim_max_soil,
        r.recent_mean_tmax,
        c.clim_min_tmax,
        c.clim_med_tmax,
        c.clim_max_tmax
    FROM recent_stats r
    JOIN clim_stats c ON r.region_id = c.region_id
    ORDER BY r.region_id;
    """).fetchdf()

    print(df_comp.to_string(index=False))

    print("\n" + "=" * 80)
    print("  DIAGNOSTIC 2: DAILY SOIL & TMAX PERCENTILE TRAJECTORY (LAST 60 DAYS)")
    print("  Checking for a sudden step change (splice) date...")
    print("=" * 80)

    # Let's inspect region PH_ANGAT_BASIN and PH_CENTRAL_LUZON over the 60 days
    df_ang = con.execute(f"""
    WITH ranked_daily AS (
        SELECT 
            c.date,
            c.day_of_year,
            c.soil_moisture_rootzone,
            c.temp_max_c,
            (SELECT COUNT(*) FROM silver.ph_climatology_daily h 
             WHERE h.region_id = c.region_id 
               AND ABS(h.day_of_year - c.day_of_year) <= {CALENDAR_WINDOW_DAYS}
               AND h.soil_moisture_rootzone <= c.soil_moisture_rootzone) * 100.0 /
            NULLIF((SELECT COUNT(*) FROM silver.ph_climatology_daily h 
             WHERE h.region_id = c.region_id 
               AND ABS(h.day_of_year - c.day_of_year) <= {CALENDAR_WINDOW_DAYS}), 0) AS soil_pct,
            (SELECT COUNT(*) FROM silver.ph_climatology_daily h 
             WHERE h.region_id = c.region_id 
               AND ABS(h.day_of_year - c.day_of_year) <= {CALENDAR_WINDOW_DAYS}
               AND h.temp_max_c <= c.temp_max_c) * 100.0 /
            NULLIF((SELECT COUNT(*) FROM silver.ph_climatology_daily h 
             WHERE h.region_id = c.region_id 
               AND ABS(h.day_of_year - c.day_of_year) <= {CALENDAR_WINDOW_DAYS}), 0) AS tmax_pct
        FROM silver.ph_daily_climate c
        WHERE c.region_id = 'PH_ANGAT_BASIN'
        ORDER BY c.date DESC
    )
    SELECT strftime(date, '%Y-%m-%d') as date, soil_moisture_rootzone, ROUND(soil_pct, 1) as soil_pct, temp_max_c, ROUND(tmax_pct, 1) as tmax_pct
    FROM ranked_daily
    LIMIT 25;
    """).fetchdf()

    print("\n[PH_ANGAT_BASIN Last 25 Days Percentiles]:")
    print(df_ang.to_string(index=False))

    con.close()

    print("\n" + "=" * 80)
    print("  DIAGNOSTIC 3: SPLICE TEST ON CACHED CLIMATOLOGY (OCT-DEC 2025)")
    print("  Re-fetching Oct-Dec 2025 via recent-window code path and comparing with cached values...")
    print("=" * 80)

    # Test on PH_ANGAT_BASIN and PH_CAGAYAN_VALLEY
    test_regions = [r for r in PH_REGIONS if r["region_id"] in ("PH_ANGAT_BASIN", "PH_CAGAYAN_VALLEY")]
    start_d = "2025-10-01"
    end_d = "2025-12-31"

    for reg in test_regions:
        reg_id = reg["region_id"]
        lat = reg["latitude"]
        lon = reg["longitude"]

        # Default URL (without models param)
        url_default = (
            f"{ARCHIVE_API_URL}?latitude={lat}&longitude={lon}"
            f"&start_date={start_d}&end_date={end_d}"
            "&daily=temperature_2m_max,temperature_2m_mean,precipitation_sum,soil_moisture_7_to_28cm_mean"
            "&timezone=auto"
        )
        print(f"\n-> Fetching default archive URL for {reg_id}...")
        raw_json = fetch_with_retry(url_default)
        data = json.loads(raw_json)
        daily = data.get("daily", {})

        new_df = pd.DataFrame({
            "date": daily.get("time", []),
            "tmax_new": daily.get("temperature_2m_max", []),
            "precip_new": daily.get("precipitation_sum", []),
            "soil_new": daily.get("soil_moisture_7_to_28cm_mean", [])
        })

        # Load cached parquet
        cached_path = os.path.join(CLIMATOLOGY_DIR, f"{reg_id}.parquet")
        cached_df = pd.read_parquet(cached_path)
        cached_sub = cached_df[(cached_df["date"] >= start_d) & (cached_df["date"] <= end_d)].copy()

        merged = pd.merge(cached_sub, new_df, on="date")
        
        # Differences
        soil_diff = np.abs(merged["soil_new"] - merged["soil_moisture_rootzone"])
        tmax_diff = np.abs(merged["tmax_new"] - merged["temp_max_c"])
        precip_diff = np.abs(merged["precip_new"] - merged["precipitation_mm"])

        print(f"  [{reg_id}] Default API vs Cached Parquet ({len(merged)} days):")
        print(f"    Soil Moisture Diff: Mean = {soil_diff.mean():.6f}, Max = {soil_diff.max():.6f}")
        print(f"    Tmax Diff:          Mean = {tmax_diff.mean():.6f}, Max = {tmax_diff.max():.6f}")
        print(f"    Precipitation Diff: Mean = {precip_diff.mean():.6f}, Max = {precip_diff.max():.6f}")

    print("\n" + "=" * 80)
    print("  DIAGNOSTIC 4: TESTING EXPLICIT MODEL PINNING (models=era5 vs era5_seamless)")
    print("=" * 80)
    for model_name in ["era5", "era5_seamless"]:
        reg = test_regions[0]
        url_model = (
            f"{ARCHIVE_API_URL}?latitude={reg['latitude']}&longitude={reg['longitude']}"
            f"&start_date={start_d}&end_date={end_d}"
            "&daily=temperature_2m_max,temperature_2m_mean,precipitation_sum,soil_moisture_7_to_28cm_mean"
            f"&timezone=auto&models={model_name}"
        )
        try:
            print(f"-> Testing {model_name}...")
            raw_json = fetch_with_retry(url_model)
            data = json.loads(raw_json)
            daily = data.get("daily", {})
            soil_vals = [s for s in daily.get("soil_moisture_7_to_28cm_mean", []) if s is not None]
            tmax_vals = [t for t in daily.get("temperature_2m_max", []) if t is not None]
            print(f"   [SUCCESS] model={model_name}: {len(soil_vals)} soil points, Mean Soil = {np.mean(soil_vals):.4f}, Mean Tmax = {np.mean(tmax_vals):.2f}")
        except Exception as e:
            print(f"   [FAIL] model={model_name} error: {e}")

if __name__ == "__main__":
    run_diagnosis()
