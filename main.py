import os
import sys
import duckdb
from src.ingestion import run_ingestion
from src.transformation import run_transformation
from src.analytics import run_analytics
from src.data_science import run_data_science
from src.quality import run_quality_checks
from generate_dashboard_html import build_dashboard

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "warehouse.duckdb")

def print_ph_seismic_bulletin():
    """Prints formatted Seismic Bulletin using nearest_reference_city and oceanic_event."""
    print("[BULLETIN] PHILIPPINE REAL-TIME SEISMIC & DATA SCIENCE BULLETIN")
    print("=" * 95)
    
    con = duckdb.connect(DB_PATH)
    
    alerts_df = con.execute("""
        SELECT 
            strftime(f.event_time_pht, '%Y-%m-%d %H:%M PHT') AS time_pht,
            ROUND(f.magnitude, 1) AS mag,
            f.place,
            f.nearest_reference_city AS nearest_ref_city,
            f.distance_to_reference_city_km AS dist_km,
            c.fault_zone_label AS fault_cluster,
            m.ml_risk_probability AS ml_risk_pct,
            a.alert_severity
        FROM gold.fact_earthquakes f
        LEFT JOIN gold.seismic_high_risk_alerts a ON f.usgs_event_id = a.usgs_event_id
        LEFT JOIN gold.ds_seismic_clusters c ON f.usgs_event_id = c.usgs_event_id
        LEFT JOIN gold.ds_ml_predictions m ON f.usgs_event_id = m.usgs_event_id
        ORDER BY f.magnitude DESC, f.event_time_pht DESC
        LIMIT 10
    """).fetchdf()
    
    print(alerts_df.to_string(index=False))
    print("=" * 95)
    
    eda_df = con.execute("""
        SELECT 
            island_group,
            total_events,
            ROUND(avg_magnitude, 2) AS avg_mag,
            ROUND(max_magnitude, 1) AS max_mag
        FROM gold.ds_regional_eda
        ORDER BY total_events DESC
    """).fetchdf()
    
    print("\n[DATA SCIENCE] Regional Statistical Profile (EDA):")
    print("-" * 65)
    print(eda_df.to_string(index=False))
    print("-" * 65 + "\n")
    con.close()

def main():
    print("==========================================================================")
    print("   PHILIPPINE SEISMIC ENGINE: DATA ENGINEERING + DATA SCIENCE & ML FEED    ")
    print("==========================================================================\n")
    
    try:
        # Step 1: Live Ingestion (Bronze)
        bronze_df = run_ingestion()
        
        # Step 2: Non-Tautological Bronze Quality Checks
        quality_passed = run_quality_checks(bronze_df=bronze_df)
        if not quality_passed:
            print("[STOP] Pipeline halted due to Bronze Data Quality failure.")
            sys.exit(1)
            
        # Step 3: Spatial & Time Transformation (Silver)
        run_transformation()
        
        # Step 4: Analytics & Star Schema (Gold)
        run_analytics()
        
        # Step 5: Data Science & ML Engine
        run_data_science()
        
        # Step 6: Print Live Terminal Bulletin
        print_ph_seismic_bulletin()
        
        # Step 7: Export dashboard_data.json and build HTML Dashboard dynamically
        build_dashboard()
        
        print("[SUCCESS] REFACTORED PIPELINE EXECUTED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"[ERROR] Error during pipeline execution: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
