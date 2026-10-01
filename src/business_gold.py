import os
import sys
import duckdb

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SILVER_PARQUET = r"c:\Users\marki\Desktop\uncloud\Personal\AI Pursuits\data engineering lol\data\silver\business_sales\transactions_cleaned.parquet"
GOLD_DIR = r"c:\Users\marki\Desktop\uncloud\Personal\AI Pursuits\data engineering lol\data\gold\business_sales"

def run_gold_star_schema():
    print("--- 🥇 GOLD LAYER: Building Star Schema & Analytical Data Marts ---")
    if not os.path.exists(SILVER_PARQUET):
        raise FileNotFoundError(f"Silver file missing: {SILVER_PARQUET}")
    
    os.makedirs(GOLD_DIR, exist_ok=True)
    con = duckdb.connect(database=':memory:')
    con.execute(f"CREATE TABLE silver AS SELECT * FROM read_parquet('{SILVER_PARQUET}')")
    
    # 1. Dim Geography
    con.execute("""
    CREATE OR REPLACE TABLE dim_geography AS
    SELECT DISTINCT
        MD5(CONCAT(region, '_', country, '_', state_province)) AS geography_id,
        region,
        country,
        state_province
    FROM silver;
    """)
    
    # 2. Dim Customers
    con.execute("""
    CREATE OR REPLACE TABLE dim_customers AS
    SELECT
        customer_id,
        MAX(customer_segment) AS customer_segment,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(net_sales) AS total_lifetime_spend,
        SUM(gross_profit) AS total_lifetime_profit,
        AVG(net_sales) AS avg_order_value,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date,
        DATEDIFF('day', MAX(order_date), CURRENT_DATE) AS recency_days
    FROM silver
    GROUP BY customer_id;
    """)
    
    # 3. Dim Products
    con.execute("""
    CREATE OR REPLACE TABLE dim_products AS
    SELECT
        product_id,
        MAX(product_name) AS product_name,
        MAX(category) AS category,
        MAX(sub_category) AS sub_category,
        AVG(unit_price) AS avg_unit_price,
        AVG(unit_cost) AS avg_unit_cost,
        COUNT(*) AS total_times_ordered,
        SUM(quantity) AS total_units_sold
    FROM silver
    GROUP BY product_id;
    """)
    
    # 4. Fact Sales Transactions
    con.execute("""
    CREATE OR REPLACE TABLE fact_sales AS
    SELECT
        s.order_id,
        s.order_date,
        s.ship_date,
        s.shipping_lead_days,
        s.customer_id,
        s.product_id,
        g.geography_id,
        s.ship_mode,
        s.quantity,
        s.discount_rate,
        s.gross_sales,
        s.discount_amount,
        s.net_sales,
        s.total_cogs,
        s.gross_profit,
        s.profit_margin_pct,
        s.order_value_segment,
        s.profit_tier,
        s.payment_method,
        s.order_status
    FROM silver s
    JOIN dim_geography g
      ON s.region = g.region
     AND s.country = g.country
     AND s.state_province = g.state_province;
    """)
    
    # 5. Executive Monthly KPI Mart
    con.execute("""
    CREATE OR REPLACE TABLE dm_monthly_executive_kpis AS
    SELECT
        STRFTIME(order_date, '%Y-%m') AS year_month,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(quantity) AS total_units_sold,
        SUM(gross_sales) AS gross_sales,
        SUM(discount_amount) AS total_discounts,
        SUM(net_sales) AS net_sales,
        SUM(total_cogs) AS total_cogs,
        SUM(gross_profit) AS gross_profit,
        (SUM(gross_profit) / SUM(net_sales)) * 100 AS profit_margin_pct,
        AVG(net_sales) AS avg_order_value
    FROM silver
    GROUP BY STRFTIME(order_date, '%Y-%m')
    ORDER BY year_month ASC;
    """)
    
    # Export all tables to Gold Parquet directory
    tables = ['fact_sales', 'dim_customers', 'dim_products', 'dim_geography', 'dm_monthly_executive_kpis']
    for tbl in tables:
        out_file = os.path.join(GOLD_DIR, f"{tbl}.parquet")
        con.execute(f"COPY {tbl} TO '{out_file}' (FORMAT PARQUET);")
        row_cnt = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  └─ Gold Table '{tbl}': {row_cnt:,} rows -> {os.path.basename(out_file)}")
    
    con.close()
    print("✅ Gold Layer Star Schema & Data Marts Built Successfully.")

if __name__ == "__main__":
    run_gold_star_schema()
