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
    """Prints formatted Seismic Bulletin including DS & ML Risk Predictions."""
    print("[BULLETIN] PHILIPPINE REAL-TIME SEISMIC & DATA SCIENCE BULLETIN")
    print("=" * 95)
    
    con = duckdb.connect(DB_PATH)
    
    # Query Top Seismic Risk Events with ML Predictions & Fault Zone Clusters
    alerts_df = con.execute("""
        SELECT 
            strftime(f.event_time_pht, '%Y-%m-%d %H:%M PHT') AS time_pht,
            ROUND(f.magnitude, 1) AS mag,
            f.place,
            f.nearest_ph_city AS nearest_city,
            c.fault_zone_label AS fault_cluster,
            m.ml_risk_probability AS ml_risk_pct,
            m.anomaly_flag AS anomaly
        FROM gold.fact_earthquakes f
        LEFT JOIN gold.ds_seismic_clusters c ON f.usgs_event_id = c.usgs_event_id
        LEFT JOIN gold.ds_ml_predictions m ON f.usgs_event_id = m.usgs_event_id
        ORDER BY f.magnitude DESC, f.event_time_pht DESC
        LIMIT 8
    """).fetchdf()
    
    print(alerts_df.to_string(index=False))
    print("=" * 95)
    
    # Regional Group Stats from DS EDA
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
        run_ingestion()
        
        # Step 2: Spatial & Time Transformation (Silver)
        run_transformation()
        
        # Step 3: Analytics & Star Schema (Gold)
        run_analytics()
        
        # Step 4: Data Science, EDA, Spatial Clustering (DBSCAN) & ML (Random Forest)
        run_data_science()
        
        # Step 5: Data Quality Assertions
        quality_passed = run_quality_checks()
        if not quality_passed:
            print("[STOP] Pipeline halted due to quality check failure.")
            sys.exit(1)
            
        # Step 6: Print Live Terminal Bulletin
        print_ph_seismic_bulletin()
        
        # Step 7: Build Interactive Visual Dashboard HTML
        build_dashboard()
        
        print("[SUCCESS] FULL DE + DA + DS PIPELINE EXECUTED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"[ERROR] Error during pipeline execution: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
