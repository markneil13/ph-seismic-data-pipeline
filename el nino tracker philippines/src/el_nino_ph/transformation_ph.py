import os
import sys
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

BRONZE_ENSO = os.path.join(BASE_DIR, "data", "bronze", "el_nino_ph", "raw_noaa_nino34.parquet").replace("\\", "/")
BRONZE_CLIMATE = os.path.join(BASE_DIR, "data", "bronze", "el_nino_ph", "raw_ph_climate_daily.parquet").replace("\\", "/")
DB_PATH = os.path.join(BASE_DIR, "data", "ph_el_nino_warehouse.duckdb")

def run_ph_el_nino_transformation():
    """Transforms raw Bronze ENSO and Philippine climate data into Silver tables in DuckDB."""
    print("[SILVER] Starting Silver Layer Transformation & Hydrological Calculations for Philippines...")
    
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    
    # 1. Transform & Deduplicate NOAA ENSO Monthly Data
    con.execute(f"""
    CREATE OR REPLACE TABLE silver.enso_monthly AS
    WITH raw_enso AS (
        SELECT 
            year_month,
            CAST(year AS INTEGER) AS year,
            CAST(month AS INTEGER) AS month,
            CAST(nino34_sst AS DOUBLE) AS nino34_sst_c,
            CAST(nino34_anom AS DOUBLE) AS nino34_anomaly_c,
            CAST(ingested_at AS TIMESTAMP) AS ingested_at,
            ROW_NUMBER() OVER (PARTITION BY year_month ORDER BY ingested_at DESC) AS row_num
        FROM read_parquet('{BRONZE_ENSO}')
        WHERE year_month IS NOT NULL AND nino34_sst IS NOT NULL
    ),
    deduped_enso AS (
        SELECT * FROM raw_enso WHERE row_num = 1
    )
    SELECT 
        year_month,
        year,
        month,
        nino34_sst_c,
        nino34_anomaly_c,
        CASE 
            WHEN nino34_anomaly_c >= 2.0 THEN 'Super El Niño'
            WHEN nino34_anomaly_c >= 1.5 AND nino34_anomaly_c < 2.0 THEN 'Strong El Niño'
            WHEN nino34_anomaly_c >= 1.0 AND nino34_anomaly_c < 1.5 THEN 'Moderate El Niño'
            WHEN nino34_anomaly_c >= 0.5 AND nino34_anomaly_c < 1.0 THEN 'Weak El Niño'
            WHEN nino34_anomaly_c > -0.5 AND nino34_anomaly_c < 0.5 THEN 'Neutral'
            WHEN nino34_anomaly_c <= -0.5 AND nino34_anomaly_c > -1.0 THEN 'Weak La Niña'
            WHEN nino34_anomaly_c <= -1.0 AND nino34_anomaly_c > -1.5 THEN 'Moderate La Niña'
            ELSE 'Strong La Niña'
        END AS enso_phase,
        ingested_at
    FROM deduped_enso
    ORDER BY year_month DESC;
    """)
    
    # 2. Transform Philippine Climate Data & Calculate Consecutive Dry Days (CDD) and Rolling Metrics
    con.execute(f"""
    CREATE OR REPLACE TABLE silver.ph_daily_climate AS
    WITH raw_climate AS (
        SELECT 
            record_id,
            region_id,
            CAST(date AS DATE) AS date,
            CAST(temp_max_c AS DOUBLE) AS temp_max_c,
            CAST(temp_mean_c AS DOUBLE) AS temp_mean_c,
            CAST(precipitation_mm AS DOUBLE) AS precipitation_mm,
            CAST(et0_evapotranspiration_mm AS DOUBLE) AS et0_evapotranspiration_mm,
            CAST(soil_moisture_surface AS DOUBLE) AS soil_moisture_surface,
            CAST(soil_moisture_rootzone AS DOUBLE) AS soil_moisture_rootzone,
            CAST(ingested_at AS TIMESTAMP) AS ingested_at,
            ROW_NUMBER() OVER (PARTITION BY region_id, date ORDER BY ingested_at DESC) AS row_num
        FROM read_parquet('{BRONZE_CLIMATE}')
        WHERE region_id IS NOT NULL AND date IS NOT NULL
    ),
    deduped_climate AS (
        SELECT * FROM raw_climate WHERE row_num = 1
    ),
    dry_day_flags AS (
        SELECT 
            *,
            CASE WHEN precipitation_mm < 1.0 THEN 1 ELSE 0 END AS is_dry_day,
            SUM(CASE WHEN precipitation_mm >= 1.0 THEN 1 ELSE 0 END) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS rain_reset_group
        FROM deduped_climate
    ),
    with_cdd AS (
        SELECT 
            record_id,
            region_id,
            date,
            temp_max_c,
            temp_mean_c,
            precipitation_mm,
            et0_evapotranspiration_mm,
            soil_moisture_surface,
            soil_moisture_rootzone,
            is_dry_day,
            CASE 
                WHEN is_dry_day = 1 THEN ROW_NUMBER() OVER (
                    PARTITION BY region_id, rain_reset_group ORDER BY date
                )
                ELSE 0 
            END AS consecutive_dry_days,
            -- Rolling 30-day cumulative precipitation
            ROUND(SUM(precipitation_mm) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 1) AS rolling_30d_precip_mm,
            -- Rolling 30-day average max temperature
            ROUND(AVG(temp_max_c) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 1) AS rolling_30d_avg_tmax_c,
            -- Rolling 30-day average rootzone soil moisture
            ROUND(AVG(soil_moisture_rootzone) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 3) AS rolling_30d_avg_soil_rootzone,
            -- Count of extreme heat days (Tmax >= 35°C) in last 30 days
            SUM(CASE WHEN temp_max_c >= 35.0 THEN 1 ELSE 0 END) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ) AS rolling_30d_extreme_heat_days,
            ingested_at
        FROM dry_day_flags
    )
    SELECT * FROM with_cdd
    ORDER BY region_id, date DESC;
    """)
    
    enso_count = con.execute("SELECT COUNT(*) FROM silver.enso_monthly").fetchone()[0]
    climate_count = con.execute("SELECT COUNT(*) FROM silver.ph_daily_climate").fetchone()[0]
    
    print(f"  + Silver ENSO records loaded: {enso_count}")
    print(f"  + Silver Philippine daily records transformed: {climate_count}")
    con.close()
    print("[OK] Philippine Silver Layer Transformation Complete.\n")

if __name__ == "__main__":
    run_ph_el_nino_transformation()
