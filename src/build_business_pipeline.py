import sys
import os
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add src and root to path
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from business_bronze import run_bronze_ingestion
from business_silver import run_silver_transformation
from business_gold import run_gold_star_schema
from data_quality_business import run_data_quality_suite
from generate_business_dashboard import generate_dashboard

def main():
    start_time = time.time()
    print("=" * 70)
    print("🚀 STARTING GLOBAL BUSINESS SALES MEDALLION DATA PIPELINE")
    print("=" * 70)
    
    try:
        # Step 1: Bronze Ingestion
        run_bronze_ingestion()
        print()
        
        # Step 2: Silver Cleaning & DuckDB Enrichment
        run_silver_transformation()
        print()
        
        # Step 3: Gold Star Schema Data Warehouse Modeling
        run_gold_star_schema()
        print()
        
        # Step 4: Data Quality Assertions
        run_data_quality_suite()
        print()
        
        # Step 5: Interactive Executive Dashboard
        dashboard_path = generate_dashboard()
        print()
        
        elapsed = time.time() - start_time
        print("=" * 70)
        print(f"🎉 PIPELINE EXECUTION SUCCESSFUL in {elapsed:.2f} seconds!")
        print(f"📄 Dashboard generated at: file:///{dashboard_path.replace(os.sep, '/')}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ PIPELINE ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
