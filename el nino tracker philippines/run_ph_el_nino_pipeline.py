import os
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.ingestion_ph import ingest_ph_bronze_layer
from src.el_nino_ph.transformation_ph import run_ph_el_nino_transformation
from src.el_nino_ph.analytics_ph import run_ph_el_nino_analytics
from src.el_nino_ph.quality_ph import run_ph_quality_checks
from src.el_nino_ph.dashboard_ph import build_ph_el_nino_dashboard

DB_PATH = os.path.join(BASE_DIR, "data", "ph_el_nino_warehouse.duckdb")

def main():
    print("\n" + "="*70)
    print("  PHILIPPINES SUPER EL NINO & BASIN DROUGHT INTELLIGENCE PIPELINE")
    print("  Zero-Cost Public Data: NOAA CPC + Open-Meteo High-Resolution Feeds")
    print("="*70 + "\n")
    
    # 1. Ingestion (Bronze)
    enso_path, climate_path, _ = ingest_ph_bronze_layer()
    df_enso = pd.read_parquet(enso_path)
    df_climate = pd.read_parquet(climate_path)
    
    # 2. Bronze Quality Checks
    print("\n--- Phase 1: Bronze Data Quality Checks ---")
    run_ph_quality_checks(df_enso=df_enso, df_climate=df_climate)
    
    # 3. Transformation (Silver)
    print("\n--- Phase 2: Silver Hydrological Transformations ---")
    run_ph_el_nino_transformation()
    
    # 4. Analytics Modeling (Gold)
    print("\n--- Phase 3: Gold Dimensional Modeling & Drought Mart ---")
    run_ph_el_nino_analytics()
    
    # 5. Warehouse Data Quality Checks
    print("\n--- Phase 4: Gold Warehouse Data Quality & Integrity Checks ---")
    run_ph_quality_checks(db_path=DB_PATH)
    
    # 6. Interactive Visual Dashboard Compilation
    print("\n--- Phase 5: Compiling Colorful Philippines Interactive Dashboard ---")
    artifact_html = build_ph_el_nino_dashboard()
    
    print("\n" + "="*70)
    print("  [SUCCESS] Philippine Super El Nino Pipeline Completed Successfully!")
    print(f"  Interactive Dashboard Artifact: {artifact_html}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
