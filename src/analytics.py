import os
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "warehouse.duckdb")

def run_analytics():
    """Builds Star Schema facts, city dimensions, and high-risk seismic alert data marts (Gold Layer)."""
    print("[GOLD] Starting Analytics Phase & Alert Engine...")
    
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    
    # 1. Fact Table: Earthquakes
    con.execute("""
    CREATE OR REPLACE TABLE gold.fact_earthquakes AS
    SELECT 
        usgs_event_id,
        event_time_pht,
        event_date_pht,
        place,
        magnitude,
        richter_category,
        depth_km,
        depth_category,
        latitude,
        longitude,
        nearest_reference_city,
        island_group,
        distance_to_reference_city_km,
        oceanic_event,
        sig_score
    FROM silver.earthquakes_with_nearest_city;
    """)
    
    # 2. Dimension Table: Philippine Reference Cities & Exposure
    con.execute("""
    CREATE OR REPLACE TABLE gold.dim_ph_cities AS
    SELECT 
        c.city_name,
        c.region AS island_group,
        c.latitude,
        c.longitude,
        COUNT(f.usgs_event_id) AS total_recent_earthquakes,
        COUNT(CASE WHEN f.distance_to_reference_city_km <= 150 THEN 1 END) AS quakes_within_150km,
        ROUND(MAX(f.magnitude), 1) AS max_magnitude_nearby,
        MAX(f.event_time_pht) AS latest_quake_at_pht
    FROM silver.ph_ref_cities c
    LEFT JOIN gold.fact_earthquakes f ON f.nearest_reference_city = c.city_name
    GROUP BY c.city_name, c.region, c.latitude, c.longitude;
    """)
    
    # 3. Gold Alert Mart: High Risk Seismic Alert Bulletin (Seismic Magnitude & Population Proximity)
    con.execute("""
    CREATE OR REPLACE TABLE gold.seismic_high_risk_alerts AS
    SELECT 
        usgs_event_id,
        event_time_pht,
        place,
        magnitude,
        richter_category,
        depth_km,
        depth_category,
        nearest_reference_city,
        island_group,
        distance_to_reference_city_km,
        oceanic_event,
        CASE 
            WHEN magnitude >= 6.5 THEN 'CRITICAL: MAJOR SEISMIC EVENT'
            WHEN magnitude >= 5.5 THEN 'HIGH: STRONG SHAKING'
            WHEN magnitude >= 4.5 AND distance_to_reference_city_km <= 100 THEN 'MODERATE: NEARBY POPULATION CENTER'
            ELSE 'INFORMATIONAL'
        END AS alert_severity
    FROM gold.fact_earthquakes
    WHERE magnitude >= 4.0 OR (magnitude >= 3.5 AND distance_to_reference_city_km <= 50)
    ORDER BY event_time_pht DESC, magnitude DESC;
    """)
    
    fact_cnt = con.execute("SELECT COUNT(*) FROM gold.fact_earthquakes").fetchone()[0]
    cities_cnt = con.execute("SELECT COUNT(*) FROM gold.dim_ph_cities").fetchone()[0]
    alerts_cnt = con.execute("SELECT COUNT(*) FROM gold.seismic_high_risk_alerts").fetchone()[0]
    
    print(f"  + Gold Fact `fact_earthquakes`: {fact_cnt} events stored.")
    print(f"  + Gold Dimension `dim_ph_cities`: {cities_cnt} reference cities with exposure metrics.")
    print(f"  + Gold Data Mart `seismic_high_risk_alerts`: {alerts_cnt} active alerts flagged.")
    
    con.close()
    print("[OK] Gold Layer Analytics & Alert Modeling Complete.\n")

if __name__ == "__main__":
    run_analytics()
