import os
import sys
import duckdb

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BRONZE_PARQUET = r"c:\Users\marki\Desktop\uncloud\Personal\AI Pursuits\data engineering lol\data\bronze\business_sales\transactions_raw.parquet"
SILVER_DIR = r"c:\Users\marki\Desktop\uncloud\Personal\AI Pursuits\data engineering lol\data\silver\business_sales"
SILVER_PARQUET = os.path.join(SILVER_DIR, "transactions_cleaned.parquet")

def run_silver_transformation():
    print("--- 🥈 SILVER LAYER: Data Cleaning & DuckDB Enrichment ---")
    if not os.path.exists(BRONZE_PARQUET):
        raise FileNotFoundError(f"Bronze file missing: {BRONZE_PARQUET}")
    
    os.makedirs(SILVER_DIR, exist_ok=True)
    con = duckdb.connect(database=':memory:')
    
    query = f"""
    CREATE OR REPLACE TABLE silver_transactions AS
    SELECT
        TRIM("Order ID") AS order_id,
        CAST("Order Date" AS DATE) AS order_date,
        CAST("Ship Date" AS DATE) AS ship_date,
        DATEDIFF('day', CAST("Order Date" AS DATE), CAST("Ship Date" AS DATE)) AS shipping_lead_days,
        TRIM("Ship Mode") AS ship_mode,
        TRIM("Customer ID") AS customer_id,
        TRIM("Customer Segment") AS customer_segment,
        TRIM("Region") AS region,
        TRIM("Country") AS country,
        TRIM("State/Province") AS state_province,
        TRIM("Category") AS category,
        TRIM("Sub-Category") AS sub_category,
        TRIM("Product ID") AS product_id,
        TRIM("Product Name") AS product_name,
        CAST("Unit Price ($)" AS DOUBLE) AS unit_price,
        CAST("Unit Cost ($)" AS DOUBLE) AS unit_cost,
        CAST("Quantity" AS INTEGER) AS quantity,
        CAST("Discount Rate" AS DOUBLE) AS discount_rate,
        CAST("Gross Sales ($)" AS DOUBLE) AS gross_sales,
        CAST("Discount Amount ($)" AS DOUBLE) AS discount_amount,
        CAST("Net Sales ($)" AS DOUBLE) AS net_sales,
        CAST("Total COGS ($)" AS DOUBLE) AS total_cogs,
        CAST("Gross Profit ($)" AS DOUBLE) AS gross_profit,
        CAST("Profit Margin (%)" AS DOUBLE) AS profit_margin_pct,
        CASE
            WHEN CAST("Net Sales ($)" AS DOUBLE) >= 1500 THEN 'Enterprise Order'
            WHEN CAST("Net Sales ($)" AS DOUBLE) >= 500 THEN 'Mid-Tier Order'
            ELSE 'Standard Order'
        END AS order_value_segment,
        CASE
            WHEN CAST("Profit Margin (%)" AS DOUBLE) >= 0.35 THEN 'High Margin'
            WHEN CAST("Profit Margin (%)" AS DOUBLE) >= 0.15 THEN 'Standard Margin'
            WHEN CAST("Profit Margin (%)" AS DOUBLE) >= 0.00 THEN 'Low Margin'
            ELSE 'Loss Making'
        END AS profit_tier,
        TRIM("Payment Method") AS payment_method,
        TRIM("Order Status") AS order_status,
        _ingested_at
    FROM read_parquet('{BRONZE_PARQUET}')
    WHERE "Order ID" IS NOT NULL
      AND "Net Sales ($)" >= 0;
    """
    
    con.execute(query)
    
    count = con.execute("SELECT COUNT(*) FROM silver_transactions").fetchone()[0]
    print(f"DuckDB processed {count:,} clean transactions.")
    
    con.execute(f"COPY silver_transactions TO '{SILVER_PARQUET}' (FORMAT PARQUET);")
    con.close()
    
    print(f"✅ Silver Transformation Complete: Cleaned Parquet saved to '{SILVER_PARQUET}' ({os.path.getsize(SILVER_PARQUET):,} bytes).")
    return SILVER_PARQUET

if __name__ == "__main__":
    run_silver_transformation()
