import os
import sys
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "warehouse.duckdb")

class SeismicQualityChecker:
    def __init__(self, db_path):
        self.con = duckdb.connect(db_path)
        self.failures = 0
        self.passed = 0

    def assert_unique(self, table_name, column_name):
        query = f"""
        SELECT {column_name}, COUNT(*) as cnt 
        FROM {table_name} 
        GROUP BY {column_name} 
        HAVING COUNT(*) > 1
        """
        duplicates = self.con.execute(query).fetchall()
        if len(duplicates) == 0:
            print(f"  [PASS] Uniqueness check on {table_name}.{column_name}")
            self.passed += 1
        else:
            print(f"  [FAIL] Uniqueness failed on {table_name}.{column_name}! Found {len(duplicates)} duplicate keys.")
            self.failures += 1

    def assert_no_nulls(self, table_name, column_name):
        query = f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL"
        null_count = self.con.execute(query).fetchone()[0]
        if null_count == 0:
            print(f"  [PASS] Non-NULL check on {table_name}.{column_name}")
            self.passed += 1
        else:
            print(f"  [FAIL] Non-NULL check failed on {table_name}.{column_name}! Found {null_count} NULLs.")
            self.failures += 1

    def assert_coordinate_bounds(self, table_name):
        query = f"""
        SELECT COUNT(*) FROM {table_name}
        WHERE latitude NOT BETWEEN 4.0 AND 22.0
           OR longitude NOT BETWEEN 115.0 AND 128.0
        """
        out_of_bounds = self.con.execute(query).fetchone()[0]
        if out_of_bounds == 0:
            print(f"  [PASS] Philippine Geospatial Bounding Box check on {table_name}")
            self.passed += 1
        else:
            print(f"  [FAIL] Bounding box check failed on {table_name}! {out_of_bounds} events outside PH bounds.")
            self.failures += 1

    def assert_magnitude_range(self, table_name):
        query = f"SELECT COUNT(*) FROM {table_name} WHERE magnitude < 0 OR magnitude > 10"
        invalid = self.con.execute(query).fetchone()[0]
        if invalid == 0:
            print(f"  [PASS] Richter Magnitude sanity range check (0-10) on {table_name}")
            self.passed += 1
        else:
            print(f"  [FAIL] Magnitude range check failed! {invalid} invalid values.")
            self.failures += 1

    def close(self):
        self.con.close()

def run_quality_checks():
    print("[QUALITY] Running Seismic Data Quality Assertions...")
    checker = SeismicQualityChecker(DB_PATH)
    
    # Silver Layer Checks
    checker.assert_unique("silver.earthquakes_with_nearest_city", "usgs_event_id")
    checker.assert_no_nulls("silver.earthquakes_with_nearest_city", "usgs_event_id")
    checker.assert_no_nulls("silver.earthquakes_with_nearest_city", "nearest_ph_city")
    checker.assert_coordinate_bounds("silver.earthquakes_with_nearest_city")
    checker.assert_magnitude_range("silver.earthquakes_with_nearest_city")
    
    # Gold Layer Checks
    checker.assert_unique("gold.fact_earthquakes", "usgs_event_id")
    checker.assert_unique("gold.dim_ph_cities", "city_name")
    checker.assert_no_nulls("gold.fact_earthquakes", "event_time_pht")
    
    print(f"\n[SUMMARY] Seismic Quality Suite: {checker.passed} Passed, {checker.failures} Failed.")
    checker.close()
    
    if checker.failures > 0:
        print("[FAIL] Quality Checks Failed!")
        return False
    else:
        print("[OK] All Seismic Data Quality Assertions Passed!\n")
        return True

if __name__ == "__main__":
    success = run_quality_checks()
    if not success:
        sys.exit(1)
