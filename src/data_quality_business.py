import os
import sys
import duckdb

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

GOLD_DIR = r"c:\Users\marki\Desktop\uncloud\Personal\AI Pursuits\data engineering lol\data\gold\business_sales"

def run_data_quality_suite():
    print("--- 🛡️ DATA QUALITY SUITE: Executing SQL Assertions ---")
    
    con = duckdb.connect(database=':memory:')
    
    # Load Gold tables
    fact_path = os.path.join(GOLD_DIR, "fact_sales.parquet")
    cust_path = os.path.join(GOLD_DIR, "dim_customers.parquet")
    prod_path = os.path.join(GOLD_DIR, "dim_products.parquet")
    geo_path = os.path.join(GOLD_DIR, "dim_geography.parquet")
    
    con.execute(f"CREATE TABLE fact_sales AS SELECT * FROM read_parquet('{fact_path}')")
    con.execute(f"CREATE TABLE dim_customers AS SELECT * FROM read_parquet('{cust_path}')")
    con.execute(f"CREATE TABLE dim_products AS SELECT * FROM read_parquet('{prod_path}')")
    con.execute(f"CREATE TABLE dim_geography AS SELECT * FROM read_parquet('{geo_path}')")
    
    assertions = [
        {
            "name": "Assertion 1: Fact Table Non-Empty Check",
            "query": "SELECT COUNT(*) FROM fact_sales",
            "check": lambda res: res[0][0] > 10000,
            "error_msg": "Fact table is empty or has fewer than 10k rows"
        },
        {
            "name": "Assertion 2: Primary Key Uniqueness (order_id)",
            "query": "SELECT COUNT(order_id) - COUNT(DISTINCT order_id) FROM fact_sales",
            "check": lambda res: res[0][0] == 0,
            "error_msg": "Duplicate order_id values detected in fact table"
        },
        {
            "name": "Assertion 3: Non-Negative Net Sales Sanity",
            "query": "SELECT COUNT(*) FROM fact_sales WHERE net_sales < 0",
            "check": lambda res: res[0][0] == 0,
            "error_msg": "Negative net sales detected"
        },
        {
            "name": "Assertion 4: Customer Foreign Key Referential Integrity",
            "query": "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_customers c ON f.customer_id = c.customer_id WHERE c.customer_id IS NULL",
            "check": lambda res: res[0][0] == 0,
            "error_msg": "Orphan customer_id records found in fact table"
        },
        {
            "name": "Assertion 5: Product Foreign Key Referential Integrity",
            "query": "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_products p ON f.product_id = p.product_id WHERE p.product_id IS NULL",
            "check": lambda res: res[0][0] == 0,
            "error_msg": "Orphan product_id records found in fact table"
        },
        {
            "name": "Assertion 6: Geography Foreign Key Referential Integrity",
            "query": "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_geography g ON f.geography_id = g.geography_id WHERE g.geography_id IS NULL",
            "check": lambda res: res[0][0] == 0,
            "error_msg": "Orphan geography_id records found in fact table"
        },
        {
            "name": "Assertion 7: Profit Margin Bound Assertions (-100% to +100%)",
            "query": "SELECT COUNT(*) FROM fact_sales WHERE profit_margin_pct > 1.0 OR profit_margin_pct < -1.0",
            "check": lambda res: res[0][0] == 0,
            "error_msg": "Unrealistic profit margin percentages detected"
        },
        {
            "name": "Assertion 8: Order Status Enum Integrity",
            "query": "SELECT COUNT(*) FROM fact_sales WHERE order_status NOT IN ('Completed', 'Shipped', 'Pending', 'Returned')",
            "check": lambda res: res[0][0] == 0,
            "error_msg": "Invalid order_status enum values detected"
        }
    ]
    
    passed_count = 0
    total = len(assertions)
    
    for test in assertions:
        res = con.execute(test["query"]).fetchall()
        if test["check"](res):
            print(f"  [PASS] {test['name']}")
            passed_count += 1
        else:
            print(f"  [FAIL] {test['name']} - {test['error_msg']}")
            raise ValueError(f"Data Quality Assertion Failed: {test['name']}")
            
    con.close()
    print(f"✅ Data Quality Engine: {passed_count}/{total} SQL Assertions Passed Successfully.")
    return True

if __name__ == "__main__":
    run_data_quality_suite()
