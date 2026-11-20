import os
import sys
import duckdb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino.ingestion import run_el_nino_ingestion
from src.el_nino.quality import run_el_nino_quality_checks
from src.el_nino.transformation import run_el_nino_transformation
from src.el_nino.analytics import run_el_nino_analytics
from src.el_nino.dashboard import build_el_nino_dashboard

DB_PATH = os.path.join(BASE_DIR, "data", "el_nino_warehouse.duckdb")

def print_terminal_bulletin():
    """Prints a clean, formatted Super El Niño & Drought Bulletin directly in terminal."""
    con = duckdb.connect(DB_PATH)
    
    latest_enso = con.execute("""
        SELECT year_month, nino34_sst_c, nino34_anomaly_c, enso_phase
        FROM gold.fact_enso_monthly
        ORDER BY year_month DESC
        LIMIT 1
    """).fetchone()
    
    print("\n" + "=" * 105)
    print("        SOUTHEAST ASIA SUPER EL NIÑO & DROUGHT EARLY WARNING BULLETIN")
    print("=" * 105)
    print(f"  GLOBAL PACIFIC TRIGGER:  {latest_enso[3].upper()}  (Niño 3.4 SST: {latest_enso[1]:.2f}°C, Anomaly: +{latest_enso[2]:.2f}°C)")
    print(f"  AS-OF PERIOD:            {latest_enso[0]} (NOAA CPC ERSSTv5 Observation)")
    print("-" * 105)
    
    bulletin_df = con.execute("""
        SELECT 
            region_name,
            country,
            rolling_30d_precip_mm AS rain_30d_mm,
            baseline_monthly_rain_mm AS base_30d_mm,
            precip_deficit_pct AS deficit_pct,
            consecutive_dry_days AS cdd_days,
            current_rootzone_moisture AS root_soil_m3,
            drought_severity_index AS sedi,
            drought_tier AS alert_tier
        FROM gold.dm_super_el_nino_bulletin
        ORDER BY drought_severity_index DESC
        LIMIT 10
    """).fetchdf()
    
    print(bulletin_df.to_string(index=False))
    print("=" * 105 + "\n")
    con.close()

def main():
    print("==========================================================================")
    print("   SOUTHEAST ASIA SUPER EL NIÑO DATA ENGINE (BRONZE -> SILVER -> GOLD)   ")
    print("==========================================================================\n")
    
    try:
        # Step 1: Live Ingestion (Bronze Layer)
        df_enso, df_climate = run_el_nino_ingestion()
        
        # Step 2: Bronze Data Quality Suite
        quality_ok = run_el_nino_quality_checks(df_enso, df_climate)
        if not quality_ok:
            print("[STOP] Pipeline halted due to Data Quality failure.")
            sys.exit(1)
            
        # Step 3: Hydrological & Time Transformations (Silver Layer)
        run_el_nino_transformation()
        
        # Step 4: Star Schema & Drought Severity Modeling (Gold Layer)
        run_el_nino_analytics()
        
        # Step 5: Terminal Bulletin
        print_terminal_bulletin()
        
        # Step 6: Dynamic Interactive Visual Dashboard HTML
        build_el_nino_dashboard()
        
        print("\n[SUCCESS] SUPER EL NIÑO & DROUGHT PIPELINE EXECUTED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline execution failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
