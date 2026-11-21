import os
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.config_ph import SEDI_WEIGHTS
from src.el_nino_ph.regions_ph import PH_REGIONS
from src.el_nino_ph.ingestion_ph import ingest_ph_bronze_layer
from src.el_nino_ph.transformation_ph import run_ph_el_nino_transformation
from src.el_nino_ph.analytics_ph import run_ph_el_nino_analytics
from src.el_nino_ph.quality_ph import run_ph_quality_checks
from src.el_nino_ph.dashboard_ph import build_ph_el_nino_dashboard

DB_PATH = os.path.join(BASE_DIR, "data", "ph_el_nino_warehouse.duckdb")

def main():
    total_regions = len(PH_REGIONS)
    print("\n" + "="*70)
    print("  PHILIPPINES SUPER EL NINO & BASIN DROUGHT INTELLIGENCE PIPELINE")
    print(f"  Climatological Percentile Engine · {total_regions} Monitored Basins & Hydro Dams")
    print("  Zero-Cost Public Data: NOAA CPC + Open-Meteo ERA5 Reanalysis")
    print("="*70 + "\n")
    
    # 1. Ingestion (Bronze)
    nino_path, oni_path, climate_path, _ = ingest_ph_bronze_layer()
    df_enso = pd.read_parquet(nino_path)
    df_oni = pd.read_parquet(oni_path)
    df_climate = pd.read_parquet(climate_path)
    
    # 2. Bronze Quality Checks - Must abort on failure
    print("--- Phase 1: Bronze Data Quality Checks ---")
    bronze_ok = run_ph_quality_checks(df_enso=df_enso, df_oni=df_oni, df_climate=df_climate)
    if not bronze_ok:
        print("\n[CRITICAL ERROR] Bronze Quality Assertions Failed! Aborting pipeline before Silver transformation.")
        sys.exit(1)
    
    # 3. Transformation (Silver)
    print("--- Phase 2: Silver Hydrological Transformations ---")
    run_ph_el_nino_transformation()
    
    # 4. Analytics Modeling (Gold)
    print("--- Phase 3: Gold Dimensional Modeling & Percentile Drought Mart ---")
    run_ph_el_nino_analytics()
    
    # 5. Warehouse Data Quality Checks - Must abort on failure
    print("--- Phase 4: Gold Warehouse Integrity & Completeness Checks ---")
    warehouse_ok = run_ph_quality_checks(db_path=DB_PATH)
    if not warehouse_ok:
        print("\n[CRITICAL ERROR] Warehouse Quality Assertions Failed! Aborting before Dashboard compilation.")
        sys.exit(1)
    
    # 6. Interactive Visual Dashboard Compilation
    print("--- Phase 5: Compiling Colorful Philippines Interactive Dashboard ---")
    artifact_html = build_ph_el_nino_dashboard()
    
    print("\n" + "="*70)
    print(f"  [SUCCESS] Philippine Super El Nino Pipeline Completed Successfully ({total_regions} Basins)!")
    print(f"  Dashboard Output: {artifact_html}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
