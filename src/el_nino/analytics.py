import os
import sys
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino.regions import SEA_REGIONS

DB_PATH = os.path.join(BASE_DIR, "data", "el_nino_warehouse.duckdb")

def run_el_nino_analytics():
    """Builds Gold Star Schema dimensions, facts, and the Super El Niño Drought Bulletin."""
    print("[GOLD] Starting Analytics Modeling & Super El Niño Bulletin Generation...")
    
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    
    # 1. Dimension Table: Southeast Asia Monitored Regions
    regions_tuples = []
    for r in SEA_REGIONS:
        regions_tuples.append(
            f"('{r['region_id']}', '{r['region_name']}', '{r['country']}', {r['latitude']}, {r['longitude']}, "
            f"'{r['economic_role']}', '{r['critical_infrastructure']}', {r['baseline_monthly_rain_mm']}, "
            f"{r['field_capacity_moisture']}, {r['wilting_point_moisture']})"
        )
    regions_sql = ", ".join(regions_tuples)
    
    con.execute(f"""
    CREATE OR REPLACE TABLE gold.dim_sea_regions AS
    SELECT * FROM (VALUES {regions_sql}) AS t(
        region_id, region_name, country, latitude, longitude, 
        economic_role, critical_infrastructure, baseline_monthly_rain_mm,
        field_capacity_moisture, wilting_point_moisture
    );
    """)
    
    # 2. Fact Table: NOAA ENSO Monthly Indicators
    con.execute("""
    CREATE OR REPLACE TABLE gold.fact_enso_monthly AS
    SELECT 
        year_month,
        year,
        month,
        nino34_sst_c,
        nino34_anomaly_c,
        enso_phase
    FROM silver.enso_monthly;
    """)
    
    # 3. Fact Table: Regional Daily Climate & Soil
    con.execute("""
    CREATE OR REPLACE TABLE gold.fact_sea_climate_daily AS
    SELECT 
        c.record_id,
        c.region_id,
        r.country,
        r.region_name,
        c.date,
        c.temp_max_c,
        c.temp_mean_c,
        c.precipitation_mm,
        c.consecutive_dry_days,
        c.rolling_30d_precip_mm,
        c.rolling_30d_avg_tmax_c,
        c.soil_moisture_surface,
        c.soil_moisture_rootzone,
        c.rolling_30d_avg_soil_rootzone,
        c.rolling_30d_extreme_heat_days
    FROM silver.sea_daily_climate c
    JOIN gold.dim_sea_regions r ON c.region_id = r.region_id;
    """)
    
    # 4. Gold Data Mart: Super El Niño Real-Time Drought Severity Bulletin
    con.execute("""
    CREATE OR REPLACE TABLE gold.dm_super_el_nino_bulletin AS
    WITH latest_date_per_region AS (
        SELECT region_id, MAX(date) AS max_date
        FROM silver.sea_daily_climate
        GROUP BY region_id
    ),
    latest_enso AS (
        SELECT nino34_anomaly_c, enso_phase
        FROM silver.enso_monthly
        ORDER BY year_month DESC
        LIMIT 1
    ),
    latest_status AS (
        SELECT 
            c.region_id,
            r.region_name,
            r.country,
            r.latitude,
            r.longitude,
            r.economic_role,
            r.critical_infrastructure,
            c.date AS as_of_date,
            e.nino34_anomaly_c,
            e.enso_phase,
            c.temp_max_c AS current_tmax_c,
            c.consecutive_dry_days,
            c.rolling_30d_precip_mm,
            r.baseline_monthly_rain_mm,
            -- Precipitation Deficit % vs Regional Climatology
            GREATEST(0.0, ROUND((r.baseline_monthly_rain_mm - c.rolling_30d_precip_mm) / r.baseline_monthly_rain_mm * 100.0, 1)) AS precip_deficit_pct,
            c.soil_moisture_rootzone AS current_rootzone_moisture,
            r.field_capacity_moisture,
            r.wilting_point_moisture,
            -- Soil Moisture Depletion %
            GREATEST(0.0, LEAST(100.0, ROUND(
                (r.field_capacity_moisture - c.soil_moisture_rootzone) / 
                NULLIF(r.field_capacity_moisture - r.wilting_point_moisture, 0) * 100.0, 1
            ))) AS soil_moisture_depletion_pct,
            c.rolling_30d_extreme_heat_days
        FROM silver.sea_daily_climate c
        JOIN latest_date_per_region l ON c.region_id = l.region_id AND c.date = l.max_date
        JOIN gold.dim_sea_regions r ON c.region_id = r.region_id
        CROSS JOIN latest_enso e
    )
    SELECT 
        region_id,
        region_name,
        country,
        latitude,
        longitude,
        economic_role,
        critical_infrastructure,
        as_of_date,
        nino34_anomaly_c,
        enso_phase,
        current_tmax_c,
        consecutive_dry_days,
        rolling_30d_precip_mm,
        baseline_monthly_rain_mm,
        precip_deficit_pct,
        current_rootzone_moisture,
        soil_moisture_depletion_pct,
        rolling_30d_extreme_heat_days,
        -- Composite Drought Severity Index (SEDI: 0 to 100)
        ROUND(
            (0.35 * precip_deficit_pct) + 
            (0.30 * soil_moisture_depletion_pct) + 
            (0.20 * LEAST(100.0, consecutive_dry_days * 3.33)) + 
            (0.15 * LEAST(100.0, rolling_30d_extreme_heat_days * 5.0)),
            1
        ) AS drought_severity_index,
        CASE 
            WHEN (0.35 * precip_deficit_pct) + (0.30 * soil_moisture_depletion_pct) + 
                 (0.20 * LEAST(100.0, consecutive_dry_days * 3.33)) + (0.15 * LEAST(100.0, rolling_30d_extreme_heat_days * 5.0)) >= 80.0
                THEN 'CRISIS: SUPER EL NIÑO DROUGHT'
            WHEN (0.35 * precip_deficit_pct) + (0.30 * soil_moisture_depletion_pct) + 
                 (0.20 * LEAST(100.0, consecutive_dry_days * 3.33)) + (0.15 * LEAST(100.0, rolling_30d_extreme_heat_days * 5.0)) >= 65.0
                THEN 'SEVERE DROUGHT'
            WHEN (0.35 * precip_deficit_pct) + (0.30 * soil_moisture_depletion_pct) + 
                 (0.20 * LEAST(100.0, consecutive_dry_days * 3.33)) + (0.15 * LEAST(100.0, rolling_30d_extreme_heat_days * 5.0)) >= 45.0
                THEN 'MODERATE DROUGHT'
            WHEN (0.35 * precip_deficit_pct) + (0.30 * soil_moisture_depletion_pct) + 
                 (0.20 * LEAST(100.0, consecutive_dry_days * 3.33)) + (0.15 * LEAST(100.0, rolling_30d_extreme_heat_days * 5.0)) >= 25.0
                THEN 'DRY SPELL WATCH'
            ELSE 'NORMAL / SATISFACTORY'
        END AS drought_tier
    FROM latest_status
    ORDER BY drought_severity_index DESC;
    """)
    
    bulletin_count = con.execute("SELECT COUNT(*) FROM gold.dm_super_el_nino_bulletin").fetchone()[0]
    avg_sedi = con.execute("SELECT ROUND(AVG(drought_severity_index), 1) FROM gold.dm_super_el_nino_bulletin").fetchone()[0]
    top_stressed = con.execute("SELECT region_name, country, drought_severity_index, drought_tier FROM gold.dm_super_el_nino_bulletin LIMIT 1").fetchone()
    
    print(f"  + Gold Dimension `dim_sea_regions`: 12 key SEA agricultural & reservoir hubs modeled.")
    print(f"  + Gold Fact `fact_sea_climate_daily`: daily time series with 30-day rolling indicators.")
    print(f"  + Gold Data Mart `dm_super_el_nino_bulletin`: {bulletin_count} regional drought assessments.")
    print(f"  + Average Regional Drought Index (SEDI): {avg_sedi}/100")
    print(f"  + Highest Vulnerability Region: {top_stressed[0]}, {top_stressed[1]} (Score: {top_stressed[2]}/100 -> {top_stressed[3]})")
    
    con.close()
    print("[OK] Gold Layer Analytics & Drought Modeling Complete.\n")

if __name__ == "__main__":
    run_el_nino_analytics()
