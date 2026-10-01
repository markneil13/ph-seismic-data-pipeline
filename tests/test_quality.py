import os
import sys
import pandas as pd
from datetime import datetime, timezone

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.quality import (
    check_bronze_not_empty,
    check_no_null_magnitude_or_depth,
    check_no_future_timestamps,
    check_ph_bounding_box
)

def run_failure_proof_unit_tests():
    print("==========================================================================")
    print("  UNIT TESTS: PROVING BRONZE DATA QUALITY CHECKS FAIL ON BAD DATA  ")
    print("==========================================================================\n")
    
    passed_test_cases = 0
    total_test_cases = 5

    # 1. Test Empty DataFrame Failure
    empty_df = pd.DataFrame()
    ok, msg = check_bronze_not_empty(empty_df)
    if not ok:
        print("  [PROVED FAIL 1/4] Empty DataFrame Check correctly FAILED:")
        print(f"    -> Response: {msg}")
        passed_test_cases += 1
    else:
        print("  [ERROR] Empty DataFrame Check unexpectedly passed!")

    # 2. Test NULL Magnitude / Depth Failure
    bad_null_df = pd.DataFrame([
        {"usgs_event_id": "tx1", "magnitude": None, "depth_km": 15.0, "time_epoch_ms": 1700000000000, "latitude": 14.5, "longitude": 121.0},
        {"usgs_event_id": "tx2", "magnitude": 4.5, "depth_km": None, "time_epoch_ms": 1700000000000, "latitude": 14.5, "longitude": 121.0}
    ])
    ok, msg = check_no_null_magnitude_or_depth(bad_null_df)
    if not ok:
        print("\n  [PROVED FAIL 2/4] NULL Magnitude/Depth Check correctly FAILED:")
        print(f"    -> Response: {msg}")
        passed_test_cases += 1
    else:
        print("  [ERROR] NULL Magnitude/Depth Check unexpectedly passed!")

    # 3. Test Future Timestamp Failure (Year 2099)
    future_time_ms = datetime(2099, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
    bad_time_df = pd.DataFrame([
        {"usgs_event_id": "tx3", "magnitude": 4.2, "depth_km": 10.0, "time_epoch_ms": future_time_ms, "latitude": 14.5, "longitude": 121.0}
    ])
    ok, msg = check_no_future_timestamps(bad_time_df)
    if not ok:
        print("\n  [PROVED FAIL 3/4] Future Timestamp Check correctly FAILED:")
        print(f"    -> Response: {msg}")
        passed_test_cases += 1
    else:
        print("  [ERROR] Future Timestamp Check unexpectedly passed!")

    # 4. Test Out-of-Bounds Coordinates Failure (Alaska Coordinates: 64.0°N, -150.0°W)
    bad_coords_df = pd.DataFrame([
        {"usgs_event_id": "tx4", "magnitude": 5.0, "depth_km": 20.0, "time_epoch_ms": 1700000000000, "latitude": 64.0, "longitude": -150.0}
    ])
    ok, msg = check_ph_bounding_box(bad_coords_df)
    if not ok:
        print("\n  [PROVED FAIL 4/4] Out-of-Bounds Coordinates Check correctly FAILED:")
        print(f"    -> Response: {msg}")
        passed_test_cases += 1
    else:
        print("  [ERROR] Out-of-Bounds Coordinates Check unexpectedly passed!")

    # 5. Test Clean Data Passing
    clean_df = pd.DataFrame([
        {"usgs_event_id": "tx_clean", "magnitude": 4.5, "depth_km": 12.0, "time_epoch_ms": 1700000000000, "latitude": 14.5995, "longitude": 120.9842}
    ])
    all_clean_ok = (
        check_bronze_not_empty(clean_df)[0] and
        check_no_null_magnitude_or_depth(clean_df)[0] and
        check_no_future_timestamps(clean_df)[0] and
        check_ph_bounding_box(clean_df)[0]
    )
    if all_clean_ok:
        print("\n  [PROVED PASS 5/5] Clean Data correctly PASSED all checks!")
        passed_test_cases += 1

    print("\n" + "=" * 74)
    print(f"  UNIT TEST RESULTS: {passed_test_cases} / {total_test_cases} TEST PROOFS PASSED")
    print("=" * 74 + "\n")

    if passed_test_cases != total_test_cases:
        sys.exit(1)

if __name__ == "__main__":
    run_failure_proof_unit_tests()
