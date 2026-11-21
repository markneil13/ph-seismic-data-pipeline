import os
import sys
import pandas as pd
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino.quality import check_enso_bronze, check_climate_bronze
from src.el_nino.regions import SEA_REGIONS

def test_el_nino_quality_suite():
    assert run_failure_proof_unit_tests() == 6

def run_failure_proof_unit_tests():
    print("==========================================================================")
    print("  UNIT TESTS: PROVING EL NIÑO DATA QUALITY CHECKS FAIL ON BAD DATA  ")
    print("==========================================================================\n")
    
    passed_tests = 0
    total_tests = 6

    # 1. Test Empty ENSO DataFrame Failure
    empty_df = pd.DataFrame()
    ok, msg = check_enso_bronze(empty_df)
    if not ok:
        print("  [PROVED FAIL 1/6] Empty ENSO DataFrame Check correctly FAILED:")
        print(f"    -> Response: {msg}")
        passed_tests += 1
    else:
        print("  [ERROR] Empty ENSO DataFrame check unexpectedly passed!")

    # 2. Test ENSO Out-of-Bounds SST (e.g. 55.0°C)
    bad_sst_df = pd.DataFrame([
        {"year_month": "2026-11", "nino34_sst": 55.0, "nino34_anom": 2.5}
    ])
    ok, msg = check_enso_bronze(bad_sst_df)
    if not ok:
        print("\n  [PROVED FAIL 2/6] Out-of-Bounds SST Check correctly FAILED:")
        print(f"    -> Response: {msg}")
        passed_tests += 1
    else:
        print("  [ERROR] Out-of-Bounds SST check unexpectedly passed!")

    # 3. Test Negative Precipitation Failure (-15.0 mm)
    bad_precip_df = pd.DataFrame([
        {
            "record_id": f"{r['region_id']}_{i}",
            "region_id": r["region_id"],
            "date": f"2026-11-{i+1:02d}",
            "temp_max_c": 32.0,
            "precipitation_mm": -15.0 if i == 0 else 5.0,
            "soil_moisture_rootzone": 0.25
        } for r in SEA_REGIONS for i in range(10)
    ])
    ok, msg = check_climate_bronze(bad_precip_df)
    if not ok:
        print("\n  [PROVED FAIL 3/6] Negative Precipitation Check correctly FAILED:")
        print(f"    -> Response: {msg}")
        passed_tests += 1
    else:
        print("  [ERROR] Negative Precipitation check unexpectedly passed!")

    # 4. Test Extreme Tropical Temperature Failure (65.0°C)
    bad_temp_df = pd.DataFrame([
        {
            "record_id": f"{r['region_id']}_{i}",
            "region_id": r["region_id"],
            "date": f"2026-11-{i+1:02d}",
            "temp_max_c": 65.0 if i == 0 else 32.0,
            "precipitation_mm": 5.0,
            "soil_moisture_rootzone": 0.25
        } for r in SEA_REGIONS for i in range(10)
    ])
    ok, msg = check_climate_bronze(bad_temp_df)
    if not ok:
        print("\n  [PROVED FAIL 4/6] Extreme Temperature Check correctly FAILED:")
        print(f"    -> Response: {msg}")
        passed_tests += 1
    else:
        print("  [ERROR] Extreme Temperature check unexpectedly passed!")

    # 5. Test Missing SEA Regions Failure
    missing_region_df = pd.DataFrame([
        {
            "record_id": "test_1",
            "region_id": "PH_CENTRAL_LUZON", # Only 1 region out of 12
            "date": "2026-11-20",
            "temp_max_c": 32.0,
            "precipitation_mm": 5.0,
            "soil_moisture_rootzone": 0.25
        }
    ] * 120)
    ok, msg = check_climate_bronze(missing_region_df)
    if not ok:
        print("\n  [PROVED FAIL 5/6] Missing SEA Regions Check correctly FAILED:")
        print(f"    -> Response: {msg}")
        passed_tests += 1
    else:
        print("  [ERROR] Missing SEA Regions check unexpectedly passed!")

    # 6. Test Clean Valid Data Passes
    clean_enso_df = pd.DataFrame([
        {"year_month": "2026-10", "nino34_sst": 30.01, "nino34_anom": 3.25}
    ])
    clean_climate_df = pd.DataFrame([
        {
            "record_id": f"{r['region_id']}_{i}",
            "region_id": r["region_id"],
            "date": f"2026-11-{i+1:02d}",
            "temp_max_c": 33.5,
            "precipitation_mm": 2.0,
            "soil_moisture_rootzone": 0.28
        } for r in SEA_REGIONS for i in range(15)
    ])
    all_clean_ok = check_enso_bronze(clean_enso_df)[0] and check_climate_bronze(clean_climate_df)[0]
    if all_clean_ok:
        print("\n  [PROVED PASS 6/6] Clean Real-World Data correctly PASSED all assertions!")
        passed_tests += 1

    print("\n" + "=" * 74)
    print(f"  UNIT TEST RESULTS: {passed_tests} / {total_tests} TEST PROOFS PASSED")
    print("=" * 74 + "\n")

    if passed_tests != total_tests:
        sys.exit(1)
    return passed_tests

if __name__ == "__main__":
    run_failure_proof_unit_tests()
