import os
import sys
import pandas as pd
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

EXCEL_FILE = r"c:\Users\marki\Desktop\uncloud\Personal\AI Pursuits\data engineering lol\Global_Business_Sales_Dataset_15k_Rows.xlsx"
BRONZE_DIR = r"c:\Users\marki\Desktop\uncloud\Personal\AI Pursuits\data engineering lol\data\bronze\business_sales"

def run_bronze_ingestion():
    print("--- 🥉 BRONZE LAYER: Ingesting Excel Raw Data ---")
    if not os.path.exists(EXCEL_FILE):
        raise FileNotFoundError(f"Input Excel file not found at {EXCEL_FILE}")
    
    os.makedirs(BRONZE_DIR, exist_ok=True)
    
    print(f"Reading sheet 'Sales Transactions (15k)' from {os.path.basename(EXCEL_FILE)}...")
    df_raw = pd.read_excel(EXCEL_FILE, sheet_name="Sales Transactions (15k)")
    
    # Ingestion Metadata
    df_raw["_ingested_at"] = datetime.now().isoformat()
    df_raw["_source_file"] = os.path.basename(EXCEL_FILE)
    
    output_path = os.path.join(BRONZE_DIR, "transactions_raw.parquet")
    df_raw.to_parquet(output_path, index=False)
    
    print(f"✅ Bronze Ingestion Complete: {len(df_raw):,} records saved to '{output_path}' ({os.path.getsize(output_path):,} bytes).")
    return output_path

if __name__ == "__main__":
    run_bronze_ingestion()
