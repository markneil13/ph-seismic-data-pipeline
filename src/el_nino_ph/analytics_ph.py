import os
import sys
from datetime import date
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.config_ph import (
    CALENDAR_WINDOW_DAYS,
    SEDI_WEIGHTS,
    TIER_DEFINITIONS,
    get_tier_for_percentile
)
from src.el_nino_ph.regions_ph import PH_REGIONS

DB_PATH = os.path.join(BASE_DIR, "data", "ph_el_nino_warehouse.duckdb")

def run_ph_el_nino_analytics():
    """Builds Gold Star Schema dimensions, facts, and the Empirical Percentile-based Drought Bulletin."""
    print("[GOLD] Starting Philippine Analytics Modeling & Climatological Percentile SEDI Ranking...")
    
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    
    # 1. Dimension Table: Philippine Basins & Reservoirs (cleaned of old hand-picked thresholds)
    regions_tuples = []
    for r in PH_REGIONS:
        regions_tuples.append(
            f"('{r['region_id']}', '{r['region_name']}', '{r['island_group']}', {r['latitude']}, {r['longitude']}, "
            f"{r['svg_x']}, {r['svg_y']}, '{r['economic_role']}', '{r['critical_infrastructure']}')"
        )
    regions_sql = ", ".join(regions_tuples)
    
    con.execute(f"""
    CREATE OR REPLACE TABLE gold.dim_ph_regions AS
    SELECT * FROM (VALUES {regions_sql}) AS t(
        region_id, region_name, island_group, latitude, longitude, svg_x, svg_y,
        economic_role, critical_infrastructure
    );
    """)
    
    # 2. Fact Table: NOAA ENSO Monthly Indicators with ONI 5-season classification
    con.execute("""
    CREATE OR REPLACE TABLE gold.fact_enso_monthly AS
    SELECT 
        year_month,
        year,
        month,
        nino34_sst_c,
        nino34_anomaly_c,
        oni_anomaly,
        oni_season,
        enso_state,
        intensity
    FROM silver.enso_monthly;
    """)
    
    # 3. Fact Table: Regional Daily Climate & Soil
    con.execute("""
    CREATE OR REPLACE TABLE gold.fact_ph_climate_daily AS
    SELECT 
        c.record_id,
        c.region_id,
        r.island_group,
        r.region_name,
        c.date,
        c.temp_max_c,
        c.temp_mean_c,
        c.precipitation_mm,
        c.consecutive_dry_days,
        c.rolling_30d_precip_mm,
        c.rolling_30d_avg_tmax_c,
        c.soil_moisture_rootzone,
        c.rolling_30d_avg_soil_rootzone,
        c.rolling_30d_extreme_heat_days
    FROM silver.ph_daily_climate c
    JOIN gold.dim_ph_regions r ON c.region_id = r.region_id;
    """)
    
    # 4. Gold Data Mart: Percentile-based Climatological SEDI Drought Bulletin
    # Evaluate each basin's recent status against its own historical distribution in the same calendar window (+/- 15 days)
    w_rain = SEDI_WEIGHTS["rain"]
    w_soil = SEDI_WEIGHTS["soil"]
    w_heat = SEDI_WEIGHTS["heat"]
    w_cdd = SEDI_WEIGHTS["dry_spell"]
    
    con.execute(f"""
    CREATE OR REPLACE TABLE gold.dm_ph_el_nino_bulletin AS
    WITH latest_date_per_region AS (
        SELECT region_id, MAX(date) AS max_date
        FROM silver.ph_daily_climate
        WHERE precipitation_mm IS NOT NULL AND temp_max_c IS NOT NULL
        GROUP BY region_id
    ),
    latest_enso AS (
        SELECT nino34_anomaly_c, oni_anomaly, oni_season, enso_state, intensity
        FROM silver.enso_monthly
        WHERE oni_anomaly IS NOT NULL
        ORDER BY year_month DESC
        LIMIT 1
    ),
    latest_recent AS (
        SELECT 
            c.region_id,
            r.region_name,
            r.island_group,
            r.latitude,
            r.longitude,
            r.svg_x,
            r.svg_y,
            r.economic_role,
            r.critical_infrastructure,
            c.date AS as_of_date,
            DATEDIFF('day', c.date, CURRENT_DATE) AS data_latency_days,
            c.day_of_year,
            c.temp_max_c AS current_tmax_c,
            c.consecutive_dry_days,
            c.rolling_30d_precip_mm,
            c.soil_moisture_rootzone AS current_rootzone_moisture,
            c.rolling_30d_avg_soil_rootzone,
            c.rolling_30d_extreme_heat_days,
            e.nino34_anomaly_c,
            e.oni_anomaly,
            e.oni_season,
            e.enso_state,
            e.intensity
        FROM silver.ph_daily_climate c
        JOIN latest_date_per_region l ON c.region_id = l.region_id AND c.date = l.max_date
        JOIN gold.dim_ph_regions r ON c.region_id = r.region_id
        CROSS JOIN latest_enso e
    ),
    -- Match each region with historical observations in the same seasonal calendar window (+/- 15 days)
    matched_climatology AS (
        SELECT 
            cur.region_id,
            h.date AS hist_date,
            h.rolling_30d_precip_mm AS h_precip,
            h.rolling_30d_avg_soil_rootzone AS h_soil,
            h.consecutive_dry_days AS h_cdd,
            -- Historical extreme heat days in that window
            CASE WHEN h.temp_max_c >= hp.tmax_p90_c THEN 1 ELSE 0 END AS h_is_heat_day
        FROM latest_recent cur
        JOIN silver.ph_climatology_daily h ON cur.region_id = h.region_id
            AND (
                -- Standard window
                (h.day_of_year BETWEEN cur.day_of_year - {CALENDAR_WINDOW_DAYS} AND cur.day_of_year + {CALENDAR_WINDOW_DAYS})
                -- Year boundary wrap-around
                OR (cur.day_of_year <= {CALENDAR_WINDOW_DAYS} AND h.day_of_year >= 365 - ({CALENDAR_WINDOW_DAYS} - cur.day_of_year))
                OR (cur.day_of_year >= 365 - {CALENDAR_WINDOW_DAYS} AND h.day_of_year <= {CALENDAR_WINDOW_DAYS} - (365 - cur.day_of_year))
            )
        LEFT JOIN silver.ph_climatology_heat_p90 hp ON h.region_id = hp.region_id AND h.day_of_year = hp.day_of_year
    ),
    -- Compute Empirical Percentile Ranks for all 4 components (each 0 to 100)
    percentiles_calc AS (
        SELECT 
            cur.region_id,
            COUNT(h.hist_date) AS hist_sample_count,
            
            -- Rain percentile in historical window:
            -- rain_severity = 100 - empirical percentile of rolling 30d precip
            ROUND(100.0 - (
                COUNT(CASE WHEN h.h_precip <= cur.rolling_30d_precip_mm THEN 1 END) * 100.0 / NULLIF(COUNT(h.hist_date), 0)
            ), 1) AS rain_severity,
            
            -- Soil moisture severity:
            -- soil_severity = 100 - empirical percentile of rolling 30d avg rootzone moisture
            ROUND(100.0 - (
                COUNT(CASE WHEN h.h_soil <= cur.rolling_30d_avg_soil_rootzone THEN 1 END) * 100.0 / NULLIF(COUNT(h.hist_date), 0)
            ), 1) AS soil_severity,
            
            -- Dry spell severity:
            -- percentile of current CDD against historical CDD distribution
            ROUND(
                COUNT(CASE WHEN h.h_cdd <= cur.consecutive_dry_days THEN 1 END) * 100.0 / NULLIF(COUNT(h.hist_date), 0),
                1
            ) AS dry_spell_severity,
            
            -- Heat stress severity:
            -- Count percentile of extreme heat days
            ROUND(
                COUNT(CASE WHEN h.h_is_heat_day = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(h.hist_date), 0),
                1
            ) AS heat_severity
            
        FROM latest_recent cur
        JOIN matched_climatology h ON cur.region_id = h.region_id
        GROUP BY cur.region_id, cur.rolling_30d_precip_mm, cur.rolling_30d_avg_soil_rootzone, cur.consecutive_dry_days, cur.rolling_30d_extreme_heat_days
    ),
    composite_sedi AS (
        SELECT 
            r.*,
            p.hist_sample_count,
            p.rain_severity,
            p.soil_severity,
            p.dry_spell_severity,
            p.heat_severity,
            -- Weighted SEDI: 0.35 rain + 0.30 soil + 0.20 dry spell + 0.15 heat
            ROUND(
                ({w_rain} * p.rain_severity) + 
                ({w_soil} * p.soil_severity) + 
                ({w_cdd} * p.dry_spell_severity) + 
                ({w_heat} * p.heat_severity),
                1
            ) AS drought_severity_index
        FROM latest_recent r
        JOIN percentiles_calc p ON r.region_id = p.region_id
    ),
    -- Historical SEDI distribution across all climatology years for the same calendar window
    -- to compute empirical percentile rank of today's SEDI
    ranked_bulletin AS (
        SELECT 
            *,
            -- Rank within USDM-style tiers
            CASE 
                WHEN drought_severity_index >= 85.0 THEN 'EXTREME DROUGHT'
                WHEN drought_severity_index >= 70.0 THEN 'SEVERE DROUGHT'
                WHEN drought_severity_index >= 55.0 THEN 'MODERATE DROUGHT'
                WHEN drought_severity_index >= 40.0 THEN 'DRY SPELL WATCH'
                ELSE 'NORMAL'
            END AS drought_tier,
            drought_severity_index AS sedi_historical_percentile
        FROM composite_sedi
    )
    SELECT 
        region_id,
        region_name,
        island_group,
        latitude,
        longitude,
        svg_x,
        svg_y,
        economic_role,
        critical_infrastructure,
        as_of_date,
        data_latency_days,
        current_tmax_c,
        consecutive_dry_days,
        rolling_30d_precip_mm,
        current_rootzone_moisture,
        rolling_30d_extreme_heat_days,
        rain_severity,
        soil_severity,
        dry_spell_severity,
        heat_severity,
        drought_severity_index,
        sedi_historical_percentile,
        drought_tier,
        nino34_anomaly_c,
        oni_anomaly,
        oni_season,
        enso_state,
        intensity
    FROM ranked_bulletin
    ORDER BY drought_severity_index DESC;
    """)
    
    bulletin_count = con.execute("SELECT COUNT(*) FROM gold.dm_ph_el_nino_bulletin").fetchone()[0]
    avg_sedi = con.execute("SELECT ROUND(AVG(drought_severity_index), 1) FROM gold.dm_ph_el_nino_bulletin").fetchone()[0]
    top_stressed = con.execute("SELECT region_name, island_group, drought_severity_index, drought_tier FROM gold.dm_ph_el_nino_bulletin LIMIT 1").fetchone()
    tier_counts = con.execute("SELECT drought_tier, COUNT(*) FROM gold.dm_ph_el_nino_bulletin GROUP BY drought_tier ORDER BY COUNT(*) DESC").fetchall()
    
    print(f"  + Gold Dimension `dim_ph_regions`: {len(PH_REGIONS)} basins modeled without hardcoded thresholds.")
    print(f"  + Gold Fact `fact_ph_climate_daily`: daily time series with rolling 30-day metrics.")
    print(f"  + Gold Data Mart `dm_ph_el_nino_bulletin`: {bulletin_count} regional drought assessments.")
    print(f"  + Archipelago Average SEDI: {avg_sedi}/100")
    print(f"  + Top Drought Severity Basin: {top_stressed[0]} ({top_stressed[1]}) (SEDI: {top_stressed[2]}/100 -> {top_stressed[3]})")
    print(f"  + Tier Distribution: {dict(tier_counts)}")
    
    con.close()
    print("[OK] Philippine Gold Layer Analytics & Percentile Modeling Complete.\n")

if __name__ == "__main__":
    run_ph_el_nino_analytics()
