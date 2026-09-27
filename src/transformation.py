import os
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze")
DB_PATH = os.path.join(BASE_DIR, "data", "warehouse.duckdb")

# Major PH Cities Reference Coordinates
PH_CITIES = [
    ("Manila", 14.5995, 120.9842, "Luzon"),
    ("Cebu City", 10.3157, 123.8854, "Visayas"),
    ("Davao City", 7.1907, 125.4553, "Mindanao"),
    ("Baguio", 16.4023, 120.5960, "Luzon"),
    ("Cagayan de Oro", 8.4542, 124.6319, "Mindanao"),
    ("Zamboanga City", 6.9214, 122.0790, "Mindanao"),
    ("Tacloban", 11.2444, 125.0039, "Visayas"),
    ("General Santos", 6.1164, 125.1716, "Mindanao")
]

def run_transformation():
    """Reads Bronze earthquake data, cleans, calculates spatial distances to PH cities, and populates Silver schema."""
    print("[SILVER] Starting Spatial & Time Transformation Phase...")
    
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    
    # 1. Register Major PH Cities Table
    cities_sql = ", ".join([f"('{name}', {lat}, {lon}, '{region}')" for name, lat, lon, region in PH_CITIES])
    con.execute(f"""
    CREATE OR REPLACE TABLE silver.ph_ref_cities AS
    SELECT * FROM (VALUES {cities_sql}) AS t(city_name, latitude, longitude, region);
    """)
    
    # 2. Read Bronze Parquet Files
    parquet_glob = os.path.join(BRONZE_DIR, "earthquakes", "**", "*.parquet").replace("\\", "/")
    
    # 3. Clean & Deduplicate Events + Convert Timestamps to PHT (+8 Hours)
    # Haversine distance formula implemented directly in DuckDB SQL:
    # 6371 * 2 * ASIN(SQRT(SIN(RAD(lat2-lat1)/2)^2 + COS(RAD(lat1))*COS(RAD(lat2))*SIN(RAD(lon2-lon1)/2)^2))
    silver_events_query = f"""
    CREATE OR REPLACE TABLE silver.earthquake_events AS
    WITH raw_data AS (
        SELECT 
            usgs_event_id,
            CAST(magnitude AS DOUBLE) AS magnitude,
            place,
            to_timestamp(CAST(time_epoch_ms AS BIGINT) / 1000) AS event_time_utc,
            to_timestamp(CAST(time_epoch_ms AS BIGINT) / 1000) + INTERVAL 8 HOUR AS event_time_pht,
            CAST(longitude AS DOUBLE) AS longitude,
            CAST(latitude AS DOUBLE) AS latitude,
            CAST(depth_km AS DOUBLE) AS depth_km,
            COALESCE(tsunami_alert, 0) AS tsunami_alert,
            sig_score,
            status,
            CAST(ingested_at AS TIMESTAMP) AS ingested_at,
            ROW_NUMBER() OVER(PARTITION BY usgs_event_id ORDER BY ingested_at DESC) AS row_num
        FROM read_parquet('{parquet_glob}')
        WHERE usgs_event_id IS NOT NULL AND latitude IS NOT NULL AND longitude IS NOT NULL
    ),
    deduped AS (
        SELECT * FROM raw_data WHERE row_num = 1
    )
    SELECT 
        e.usgs_event_id,
        e.magnitude,
        CASE 
            WHEN e.magnitude < 3.0 THEN 'Micro'
            WHEN e.magnitude BETWEEN 3.0 AND 4.4 THEN 'Light'
            WHEN e.magnitude BETWEEN 4.5 AND 5.4 THEN 'Moderate'
            WHEN e.magnitude BETWEEN 5.5 AND 6.4 THEN 'Strong'
            ELSE 'Major'
        END AS richter_category,
        e.place,
        e.event_time_utc,
        e.event_time_pht,
        CAST(e.event_time_pht AS DATE) AS event_date_pht,
        e.latitude,
        e.longitude,
        e.depth_km,
        CASE 
            WHEN e.depth_km < 70 THEN 'Shallow (<70km)'
            WHEN e.depth_km BETWEEN 70 AND 300 THEN 'Intermediate (70-300km)'
            ELSE 'Deep (>300km)'
        END AS depth_category,
        e.tsunami_alert,
        e.sig_score,
        e.ingested_at
    FROM deduped e;
    """
    con.execute(silver_events_query)
    
    # 4. Calculate Distance to Nearest PH City for Each Event
    con.execute("""
    CREATE OR REPLACE TABLE silver.earthquakes_with_nearest_city AS
    WITH distances AS (
        SELECT 
            e.usgs_event_id,
            c.city_name,
            c.region AS island_group,
            ROUND(
                6371 * 2 * ASIN(
                    SQRT(
                        POWER(SIN(RADIANS(c.latitude - e.latitude) / 2), 2) +
                        COS(RADIANS(e.latitude)) * COS(RADIANS(c.latitude)) *
                        POWER(SIN(RADIANS(c.longitude - e.longitude) / 2), 2)
                    )
                ), 1
            ) AS distance_to_city_km,
            ROW_NUMBER() OVER(PARTITION BY e.usgs_event_id ORDER BY 
                6371 * 2 * ASIN(
                    SQRT(
                        POWER(SIN(RADIANS(c.latitude - e.latitude) / 2), 2) +
                        COS(RADIANS(e.latitude)) * COS(RADIANS(c.latitude)) *
                        POWER(SIN(RADIANS(c.longitude - e.longitude) / 2), 2)
                    )
                ) ASC
            ) AS city_rank
        FROM silver.earthquake_events e
        CROSS JOIN silver.ph_ref_cities c
    )
    SELECT 
        e.*,
        d.city_name AS nearest_ph_city,
        d.island_group,
        d.distance_to_city_km
    FROM silver.earthquake_events e
    JOIN distances d ON e.usgs_event_id = d.usgs_event_id
    WHERE d.city_rank = 1;
    """)
    
    events_count = con.execute("SELECT COUNT(*) FROM silver.earthquakes_with_nearest_city").fetchone()[0]
    cities_count = con.execute("SELECT COUNT(*) FROM silver.ph_ref_cities").fetchone()[0]
    
    print(f"  + Registered {cities_count} Philippine Reference Cities.")
    print(f"  + Silver Table `earthquakes_with_nearest_city`: {events_count} deduplicated events with PHT time & spatial distances.")
    
    con.close()
    print("[OK] Silver Spatial Transformation Complete.\n")

if __name__ == "__main__":
    run_transformation()
