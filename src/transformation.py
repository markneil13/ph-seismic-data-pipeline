import os
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze")
DB_PATH = os.path.join(BASE_DIR, "data", "warehouse.duckdb")

PH_CITIES = [
    ("Manila", 14.5995, 120.9842, "Luzon"),
    ("Cebu City", 10.3157, 123.8854, "Visayas"),
    ("Davao City", 7.1907, 125.4553, "Mindanao"),
    ("Baguio", 16.4023, 120.5960, "Luzon"),
    ("Cagayan de Oro", 8.4542, 124.6319, "Mindanao"),
    ("Zamboanga City", 6.9214, 122.0790, "Mindanao"),
    ("Tacloban", 11.2444, 125.0039, "Visayas"),
    ("General Santos", 6.1164, 125.1716, "Mindanao"),
    ("Legazpi", 13.1391, 123.7438, "Luzon"),
    ("Naga", 13.6218, 123.1948, "Luzon"),
    ("Puerto Princesa", 9.7392, 118.7353, "Palawan"),
    ("Laoag", 18.1960, 120.5927, "Luzon"),
    ("Calapan", 13.4116, 121.1803, "Mindoro"),
    ("Catbalogan", 11.7777, 124.8821, "Visayas")
]

def run_transformation():
    """Reads Bronze earthquake data, cleans, calculates spatial distances to PH reference cities, and populates Silver schema."""
    print("[SILVER] Starting Spatial & Time Transformation Phase...")
    
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    
    cities_sql = ", ".join([f"('{name}', {lat}, {lon}, '{region}')" for name, lat, lon, region in PH_CITIES])
    con.execute(f"""
    CREATE OR REPLACE TABLE silver.ph_ref_cities AS
    SELECT * FROM (VALUES {cities_sql}) AS t(city_name, latitude, longitude, region);
    """)
    
    parquet_glob = os.path.join(BRONZE_DIR, "earthquakes", "**", "*.parquet").replace("\\", "/")
    
    silver_events_query = f"""
    CREATE OR REPLACE TABLE silver.earthquake_events AS
    WITH raw_data AS (
        SELECT 
            usgs_event_id,
            CAST(magnitude AS DOUBLE) AS magnitude,
            place,
            to_timestamp(CAST(time_epoch_ms AS BIGINT) / 1000) AS event_time_utc,
            timezone('Asia/Manila', to_timestamp(CAST(time_epoch_ms AS BIGINT) / 1000)) AS event_time_pht,
            CAST(longitude AS DOUBLE) AS longitude,
            CAST(latitude AS DOUBLE) AS latitude,
            CAST(depth_km AS DOUBLE) AS depth_km,
            COALESCE(try_cast(oceanic_event AS BIGINT), try_cast(tsunami_alert AS BIGINT), 0) AS oceanic_event,
            sig_score,
            status,
            CAST(ingested_at AS TIMESTAMP) AS ingested_at,
            ROW_NUMBER() OVER(PARTITION BY usgs_event_id ORDER BY ingested_at DESC) AS row_num
        FROM read_parquet('{parquet_glob}', union_by_name=True)
        WHERE usgs_event_id IS NOT NULL 
          AND latitude IS NOT NULL 
          AND longitude IS NOT NULL
          AND latitude BETWEEN 4.0 AND 21.5
          AND longitude BETWEEN 116.0 AND 127.0
    ),
    deduped AS (
        SELECT * FROM raw_data WHERE row_num = 1
    )
    SELECT 
        e.usgs_event_id,
        e.magnitude,
        CASE 
            WHEN e.magnitude IS NULL THEN 'Unknown'
            WHEN e.magnitude < 3.0 THEN 'Micro'
            WHEN e.magnitude >= 3.0 AND e.magnitude < 4.5 THEN 'Light'
            WHEN e.magnitude >= 4.5 AND e.magnitude < 5.5 THEN 'Moderate'
            WHEN e.magnitude >= 5.5 AND e.magnitude < 6.5 THEN 'Strong'
            WHEN e.magnitude >= 6.5 AND e.magnitude < 8.0 THEN 'Major'
            WHEN e.magnitude >= 8.0 THEN 'Great'
            ELSE 'Unknown'
        END AS richter_category,
        e.place,
        e.event_time_utc,
        e.event_time_pht,
        CAST(e.event_time_pht AS DATE) AS event_date_pht,
        e.latitude,
        e.longitude,
        e.depth_km,
        CASE 
            WHEN e.depth_km IS NULL THEN 'Unknown'
            WHEN e.depth_km < 70.0 THEN 'Shallow (<70km)'
            WHEN e.depth_km >= 70.0 AND e.depth_km < 300.0 THEN 'Intermediate (70-300km)'
            WHEN e.depth_km >= 300.0 THEN 'Deep (>300km)'
            ELSE 'Unknown'
        END AS depth_category,
        e.oceanic_event,
        e.sig_score,
        e.ingested_at
    FROM deduped e;
    """
    con.execute(silver_events_query)
    
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
            ) AS distance_to_reference_city_km,
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
        d.city_name AS nearest_reference_city,
        d.island_group,
        d.distance_to_reference_city_km
    FROM silver.earthquake_events e
    JOIN distances d ON e.usgs_event_id = d.usgs_event_id
    WHERE d.city_rank = 1 AND d.distance_to_reference_city_km <= 450.0;
    """)
    
    events_count = con.execute("SELECT COUNT(*) FROM silver.earthquakes_with_nearest_city").fetchone()[0]
    cities_count = con.execute("SELECT COUNT(*) FROM silver.ph_ref_cities").fetchone()[0]
    
    print(f"  + Registered {cities_count} Philippine Reference Cities.")
    print(f"  + Silver Table `earthquakes_with_nearest_city`: {events_count} clean events within PH bounds.")
    
    con.close()
    print("[OK] Silver Spatial Transformation Complete.\n")

if __name__ == "__main__":
    run_transformation()
