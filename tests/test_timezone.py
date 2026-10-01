import os
import sys
import duckdb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_timezone_consistency():
    print("==========================================================================")
    print("  TIMEZONE TEST: VERIFYING timezone('Asia/Manila', ...) UNDER UTC & PHT ")
    print("==========================================================================\n")
    
    # Test Epoch MS: 1700000000000 -> 2023-11-14 22:13:20 UTC -> 2023-11-15 06:13:20 PHT (+8h)
    test_epoch_ms = 1700000000000
    
    # Session 1: UTC Session
    con_utc = duckdb.connect()
    con_utc.execute("SET TimeZone = 'UTC';")
    pht_from_utc_session = con_utc.execute(f"""
        SELECT strftime(timezone('Asia/Manila', to_timestamp(CAST({test_epoch_ms} AS BIGINT) / 1000)), '%Y-%m-%d %H:%M:%S PHT')
    """).fetchone()[0]
    con_utc.close()

    # Session 2: Asia/Manila Session
    con_pht = duckdb.connect()
    con_pht.execute("SET TimeZone = 'Asia/Manila';")
    pht_from_pht_session = con_pht.execute(f"""
        SELECT strftime(timezone('Asia/Manila', to_timestamp(CAST({test_epoch_ms} AS BIGINT) / 1000)), '%Y-%m-%d %H:%M:%S PHT')
    """).fetchone()[0]
    con_pht.close()

    print(f"  + UTC Session Output:         {pht_from_utc_session}")
    print(f"  + Asia/Manila Session Output: {pht_from_pht_session}")
    
    if pht_from_utc_session == pht_from_pht_session == "2023-11-15 06:13:20 PHT":
        print("\n  [PROVED PASS] Timezone output is 100% consistent across UTC and Asia/Manila sessions!")
        print("==========================================================================\n")
    else:
        print("\n  [ERROR] Timezone outputs mismatch!")
        sys.exit(1)

if __name__ == "__main__":
    test_timezone_consistency()
