import os
import sys
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.config_ph import (
    RAIN_DAY_THRESHOLD_MM,
    ONI_ANOMALY_THRESHOLD,
    ONI_MIN_CONSECUTIVE_SEASONS
)

BRONZE_NINO = os.path.join(BASE_DIR, "data", "bronze", "el_nino_ph", "raw_noaa_nino34.parquet").replace("\\", "/")
BRONZE_ONI = os.path.join(BASE_DIR, "data", "bronze", "el_nino_ph", "raw_noaa_oni.parquet").replace("\\", "/")
BRONZE_CLIMATE = os.path.join(BASE_DIR, "data", "bronze", "el_nino_ph", "raw_ph_climate_daily.parquet").replace("\\", "/")
BRONZE_CLIMATOLOGY = os.path.join(BASE_DIR, "data", "bronze", "el_nino_ph", "climatology", "*.parquet").replace("\\", "/")
DB_PATH = os.path.join(BASE_DIR, "data", "ph_el_nino_warehouse.duckdb")

def run_ph_el_nino_transformation():
    """Transforms Bronze NOAA indices, historical climatology, and recent climate into Silver tables in DuckDB."""
    print("[SILVER] Starting Silver Layer Transformation & Hydrological Calculations...")
    
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    
    # 1. Transform NOAA ONI & Classify ENSO state according to official NOAA 5-consecutive-season rule
    # Seasons order in a year: DJF, JFM, FMA, MAM, AMJ, MJJ, JJA, JAS, ASO, SON, OND, NDJ
    con.execute(f"""
    CREATE OR REPLACE TABLE silver.enso_monthly AS
    WITH raw_oni AS (
        SELECT 
            season,
            CAST(year AS INTEGER) AS year,
            season_year,
            CAST(oni_total AS DOUBLE) AS oni_total,
            CAST(oni_anomaly AS DOUBLE) AS oni_anomaly,
            ROW_NUMBER() OVER (
                ORDER BY year ASC, 
                CASE season
                    WHEN 'DJF' THEN 1 WHEN 'JFM' THEN 2 WHEN 'FMA' THEN 3 WHEN 'MAM' THEN 4
                    WHEN 'AMJ' THEN 5 WHEN 'MJJ' THEN 6 WHEN 'JJA' THEN 7 WHEN 'JAS' THEN 8
                    WHEN 'ASO' THEN 9 WHEN 'SON' THEN 10 WHEN 'OND' THEN 11 WHEN 'NDJ' THEN 12
                END ASC
            ) AS season_seq
        FROM read_parquet('{BRONZE_ONI}')
    ),
    oni_streaks AS (
        SELECT 
            *,
            CASE WHEN oni_anomaly >= {ONI_ANOMALY_THRESHOLD} THEN 1 ELSE 0 END AS is_warm,
            CASE WHEN oni_anomaly <= -{ONI_ANOMALY_THRESHOLD} THEN 1 ELSE 0 END AS is_cold,
            -- Group consecutive warm / cold runs
            SUM(CASE WHEN oni_anomaly < {ONI_ANOMALY_THRESHOLD} THEN 1 ELSE 0 END) OVER (
                ORDER BY season_seq ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS warm_group,
            SUM(CASE WHEN oni_anomaly > -{ONI_ANOMALY_THRESHOLD} THEN 1 ELSE 0 END) OVER (
                ORDER BY season_seq ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS cold_group
        FROM raw_oni
    ),
    streak_counts AS (
        SELECT 
            *,
            CASE 
                WHEN is_warm = 1 THEN SUM(is_warm) OVER (PARTITION BY warm_group ORDER BY season_seq ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                ELSE 0 
            END AS warm_streak,
            CASE 
                WHEN is_cold = 1 THEN SUM(is_cold) OVER (PARTITION BY cold_group ORDER BY season_seq ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                ELSE 0 
            END AS cold_streak
        FROM oni_streaks
    ),
    classified_oni AS (
        SELECT 
            season,
            year,
            season_year,
            season_seq,
            oni_total,
            oni_anomaly,
            CASE 
                WHEN warm_streak >= {ONI_MIN_CONSECUTIVE_SEASONS} THEN 'El Niño'
                WHEN cold_streak >= {ONI_MIN_CONSECUTIVE_SEASONS} THEN 'La Niña'
                ELSE 'Neutral'
            END AS enso_state,
            CASE 
                WHEN warm_streak >= {ONI_MIN_CONSECUTIVE_SEASONS} THEN 
                    CASE 
                        WHEN oni_anomaly >= 2.0 THEN 'Very Strong (informal ''Super'')'
                        WHEN oni_anomaly >= 1.5 THEN 'Strong'
                        WHEN oni_anomaly >= 1.0 THEN 'Moderate'
                        ELSE 'Weak'
                    END
                WHEN cold_streak >= {ONI_MIN_CONSECUTIVE_SEASONS} THEN
                    CASE 
                        WHEN oni_anomaly <= -2.0 THEN 'Very Strong'
                        WHEN oni_anomaly <= -1.5 THEN 'Strong'
                        WHEN oni_anomaly <= -1.0 THEN 'Moderate'
                        ELSE 'Weak'
                    END
                ELSE 'Neutral'
            END AS intensity
        FROM streak_counts
    ),
    latest_nino34 AS (
        SELECT 
            year_month,
            CAST(year AS INTEGER) AS year,
            CAST(month AS INTEGER) AS month,
            CAST(nino34_sst AS DOUBLE) AS nino34_sst_c,
            CAST(nino34_anom AS DOUBLE) AS nino34_anomaly_c,
            ROW_NUMBER() OVER (PARTITION BY year, month ORDER BY ingested_at DESC) AS rn
        FROM read_parquet('{BRONZE_NINO}')
    ),
    deduped_nino34 AS (
        SELECT year_month, year, month, nino34_sst_c, nino34_anomaly_c 
        FROM latest_nino34 WHERE rn = 1
    ),
    -- Map each month to its corresponding 3-month centered season
    month_to_season AS (
        SELECT 
            n.*,
            CASE n.month
                WHEN 1 THEN 'DJF' WHEN 2 THEN 'JFM' WHEN 3 THEN 'FMA' WHEN 4 THEN 'MAM'
                WHEN 5 THEN 'AMJ' WHEN 6 THEN 'MJJ' WHEN 7 THEN 'JJA' WHEN 8 THEN 'JAS'
                WHEN 9 THEN 'ASO' WHEN 10 THEN 'SON' WHEN 11 THEN 'OND' WHEN 12 THEN 'NDJ'
            END AS matching_season
        FROM deduped_nino34 n
    )
    SELECT 
        m.year_month,
        m.year,
        m.month,
        m.nino34_sst_c,
        m.nino34_anomaly_c,
        COALESCE(o.oni_anomaly, m.nino34_anomaly_c) AS oni_anomaly,
        COALESCE(o.season, m.matching_season) AS oni_season,
        COALESCE(o.enso_state, 'Neutral') AS enso_state,
        COALESCE(o.intensity, 'Neutral') AS intensity
    FROM month_to_season m
    LEFT JOIN classified_oni o ON m.year = o.year AND m.matching_season = o.season
    ORDER BY m.year_month DESC;
    """)
    
    # 2. Transform Historical Climatology (2005-2025)
    # Corrected CDD calculation with SUM(is_dry_day)
    print("  -> Transforming historical climatology baseline in DuckDB...")
    con.execute(f"""
    CREATE OR REPLACE TABLE silver.ph_climatology_daily AS
    WITH raw_clim AS (
        SELECT 
            region_id,
            CAST(date AS DATE) AS date,
            CAST(year AS INTEGER) AS year,
            CAST(day_of_year AS INTEGER) AS day_of_year,
            CAST(temp_max_c AS DOUBLE) AS temp_max_c,
            CAST(temp_mean_c AS DOUBLE) AS temp_mean_c,
            CAST(precipitation_mm AS DOUBLE) AS precipitation_mm,
            CAST(soil_moisture_rootzone AS DOUBLE) AS soil_moisture_rootzone,
            ROW_NUMBER() OVER (PARTITION BY region_id, date ORDER BY date) AS rn
        FROM read_parquet('{BRONZE_CLIMATOLOGY}')
        WHERE region_id IS NOT NULL AND date IS NOT NULL
    ),
    deduped_clim AS (
        SELECT * FROM raw_clim WHERE rn = 1
    ),
    dry_day_flags AS (
        SELECT 
            *,
            CASE WHEN precipitation_mm < {RAIN_DAY_THRESHOLD_MM} THEN 1 ELSE 0 END AS is_dry_day,
            SUM(CASE WHEN precipitation_mm >= {RAIN_DAY_THRESHOLD_MM} THEN 1 ELSE 0 END) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS rain_reset_group
        FROM deduped_clim
    ),
    with_cdd AS (
        SELECT 
            region_id,
            date,
            year,
            day_of_year,
            temp_max_c,
            temp_mean_c,
            precipitation_mm,
            soil_moisture_rootzone,
            is_dry_day,
            -- Exact CDD: rain day = 0, first dry day = 1, then 2, 3...
            CASE 
                WHEN is_dry_day = 1 THEN SUM(is_dry_day) OVER (
                    PARTITION BY region_id, rain_reset_group ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )
                ELSE 0 
            END AS consecutive_dry_days,
            ROUND(SUM(precipitation_mm) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 1) AS rolling_30d_precip_mm,
            ROUND(AVG(soil_moisture_rootzone) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 3) AS rolling_30d_avg_soil_rootzone
        FROM dry_day_flags
    )
    SELECT * FROM with_cdd
    ORDER BY region_id, date;
    """)
    
    # 3. Calculate 90th percentile of Tmax per calendar day-of-year for each region
    con.execute("""
    CREATE OR REPLACE TABLE silver.ph_climatology_heat_p90 AS
    SELECT 
        region_id,
        day_of_year,
        ROUND(QUANTILE_CONT(temp_max_c, 0.90), 2) AS tmax_p90_c
    FROM silver.ph_climatology_daily
    WHERE temp_max_c IS NOT NULL
    GROUP BY region_id, day_of_year;
    """)
    
    # 4. Transform Recent Observed Daily Climate (Completed Days Only)
    # Apply identical CDD formula and 30-day rolling metrics
    print("  -> Transforming recent completed observed climate in DuckDB...")
    con.execute(f"""
    CREATE OR REPLACE TABLE silver.ph_daily_climate AS
    WITH raw_climate AS (
        SELECT 
            record_id,
            region_id,
            CAST(date AS DATE) AS date,
            dayofyear(CAST(date AS DATE)) AS day_of_year,
            CAST(temp_max_c AS DOUBLE) AS temp_max_c,
            CAST(temp_mean_c AS DOUBLE) AS temp_mean_c,
            CAST(precipitation_mm AS DOUBLE) AS precipitation_mm,
            CAST(soil_moisture_rootzone AS DOUBLE) AS soil_moisture_rootzone,
            CAST(ingested_at AS TIMESTAMP) AS ingested_at,
            ROW_NUMBER() OVER (PARTITION BY region_id, date ORDER BY ingested_at DESC) AS rn
        FROM read_parquet('{BRONZE_CLIMATE}')
        WHERE region_id IS NOT NULL AND date IS NOT NULL
    ),
    deduped_climate AS (
        SELECT * FROM raw_climate WHERE rn = 1
    ),
    dry_day_flags AS (
        SELECT 
            *,
            CASE WHEN precipitation_mm < {RAIN_DAY_THRESHOLD_MM} THEN 1 ELSE 0 END AS is_dry_day,
            SUM(CASE WHEN precipitation_mm >= {RAIN_DAY_THRESHOLD_MM} THEN 1 ELSE 0 END) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS rain_reset_group
        FROM deduped_climate
    ),
    with_cdd AS (
        SELECT 
            record_id,
            region_id,
            date,
            day_of_year,
            temp_max_c,
            temp_mean_c,
            precipitation_mm,
            soil_moisture_rootzone,
            is_dry_day,
            -- Exact CDD: rain day = 0, first dry day = 1, then 2, 3...
            CASE 
                WHEN is_dry_day = 1 THEN SUM(is_dry_day) OVER (
                    PARTITION BY region_id, rain_reset_group ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )
                ELSE 0 
            END AS consecutive_dry_days,
            ROUND(SUM(precipitation_mm) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 1) AS rolling_30d_precip_mm,
            ROUND(AVG(temp_max_c) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 1) AS rolling_30d_avg_tmax_c,
            ROUND(AVG(soil_moisture_rootzone) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 3) AS rolling_30d_avg_soil_rootzone,
            ingested_at
        FROM dry_day_flags
    ),
    with_heat_p90 AS (
        SELECT 
            c.*,
            p.tmax_p90_c,
            CASE WHEN c.temp_max_c >= p.tmax_p90_c THEN 1 ELSE 0 END AS is_extreme_heat_day
        FROM with_cdd c
        LEFT JOIN silver.ph_climatology_heat_p90 p ON c.region_id = p.region_id AND c.day_of_year = p.day_of_year
    ),
    with_rolling_heat AS (
        SELECT 
            record_id,
            region_id,
            date,
            day_of_year,
            temp_max_c,
            temp_mean_c,
            precipitation_mm,
            soil_moisture_rootzone,
            is_dry_day,
            consecutive_dry_days,
            rolling_30d_precip_mm,
            rolling_30d_avg_tmax_c,
            rolling_30d_avg_soil_rootzone,
            tmax_p90_c,
            is_extreme_heat_day,
            SUM(is_extreme_heat_day) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ) AS rolling_30d_extreme_heat_days,
            ingested_at
        FROM with_heat_p90
    )
    SELECT * FROM with_rolling_heat
    ORDER BY region_id, date DESC;
    """)
    
    enso_count = con.execute("SELECT COUNT(*) FROM silver.enso_monthly").fetchone()[0]
    latest_enso = con.execute("SELECT enso_state, intensity, oni_anomaly, oni_season FROM silver.enso_monthly WHERE oni_anomaly IS NOT NULL ORDER BY year_month DESC LIMIT 1").fetchone()
    climate_count = con.execute("SELECT COUNT(*) FROM silver.ph_daily_climate").fetchone()[0]
    clim_hist_count = con.execute("SELECT COUNT(*) FROM silver.ph_climatology_daily").fetchone()[0]
    
    print(f"  + Silver ENSO monthly series: {enso_count} records (Latest: {latest_enso[0]} {latest_enso[1]}, ONI {latest_enso[2]:+.2f} season {latest_enso[3]})")
    print(f"  + Silver Climatology baseline: {clim_hist_count} daily observations")
    print(f"  + Silver Philippine daily records: {climate_count} completed observations")
    con.close()
    print("[OK] Philippine Silver Layer Transformation Complete.\n")

if __name__ == "__main__":
    run_ph_el_nino_transformation()
