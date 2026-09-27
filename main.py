import os
import sys
import duckdb
from src.ingestion import run_ingestion
from src.transformation import run_transformation
from src.analytics import run_analytics
from src.quality import run_quality_checks

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "warehouse.duckdb")

def print_ph_seismic_bulletin():
    """Prints a formatted Real-Time Philippine Earthquake Alert Bulletin."""
    print("[BULLETIN] PHILIPPINE REAL-TIME SEISMIC ALERT BULLETIN")
    print("=" * 90)
    
    con = duckdb.connect(DB_PATH)
    
    # 1. High Risk & Recent Alerts
    alerts_df = con.execute("""
        SELECT 
            strftime(event_time_pht, '%Y-%m-%d %H:%M PHT') AS time_pht,
            ROUND(magnitude, 1) AS mag,
            richter_category AS richter,
            place,
            depth_km AS depth,
            nearest_ph_city AS nearest_city,
            distance_to_city_km AS dist_km,
            alert_severity
        FROM gold.seismic_high_risk_alerts
        ORDER BY event_time_pht DESC
        LIMIT 10
    """).fetchdf()
    
    if len(alerts_df) > 0:
        print(alerts_df.to_string(index=False))
    else:
        print("No recent high-risk seismic alerts recorded (Magnitude < 4.0 and normal depth).")
        
    print("=" * 90)
    
    # 2. Regional Exposure Summary by PH City
    summary_df = con.execute("""
        SELECT 
            city_name,
            island_group,
            total_recent_earthquakes AS total_quakes,
            quakes_within_150km AS quakes_lt_150km,
            COALESCE(max_magnitude_nearby, 0) AS max_mag,
            COALESCE(strftime(latest_quake_at_pht, '%Y-%m-%d %H:%M PHT'), 'N/A') AS latest_event_pht
        FROM gold.dim_ph_cities
        ORDER BY quakes_within_150km DESC, max_magnitude_nearby DESC
    """).fetchdf()
    
    print("\n[EXPOSURE] Regional Seismic Activity & Major City Proximity Summary:")
    print("-" * 90)
    print(summary_df.to_string(index=False))
    print("-" * 90)
    
    total_events = con.execute("SELECT COUNT(*) FROM gold.fact_earthquakes").fetchone()[0]
    max_mag_event = con.execute("SELECT MAX(magnitude) FROM gold.fact_earthquakes").fetchone()[0]
    
    print(f"\nTotal Live Seismic Events Tracked across PH Archipelago: {total_events}")
    print(f"Strongest Recent Earthquake Magnitude: M {max_mag_event:.1f}\n")
    con.close()

def main():
    print("==========================================================================")
    print("     PHILIPPINE REAL-TIME SEISMIC & EARTHQUAKE DATA ENGINE (LIVE FEED)    ")
    print("==========================================================================\n")
    
    try:
        # Step 1: Live USGS Ingestion (Bronze)
        run_ingestion()
        
        # Step 2: Spatial & Time Transformation (Silver)
        run_transformation()
        
        # Step 3: Star Schema & Alert Data Marts (Gold)
        run_analytics()
        
        # Step 4: Quality Assertions
        quality_passed = run_quality_checks()
        if not quality_passed:
            print("[STOP] Pipeline halted due to quality check failure.")
            sys.exit(1)
            
        # Step 5: Print Live Bulletin
        print_ph_seismic_bulletin()
        print("[SUCCESS] REAL-TIME PHILIPPINE SEISMIC PIPELINE EXECUTED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"[ERROR] Error during pipeline execution: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
