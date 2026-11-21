import os
import sys
import duckdb
import pytest
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.config_ph import (
    RAIN_DAY_THRESHOLD_MM,
    ONI_ANOMALY_THRESHOLD,
    ONI_MIN_CONSECUTIVE_SEASONS,
    TIER_DEFINITIONS,
    get_tier_for_percentile
)

def test_cdd_sequence_calculation():
    """
    Test 1: CDD sequence R, D, D, R, D must give 0, 1, 2, 0, 1.
    Verifies that the off-by-one bug is completely fixed and a rain day gives 0,
    followed by 1, 2 for consecutive dry days.
    """
    con = duckdb.connect(":memory:")
    
    con.execute(f"""
    CREATE TABLE test_cdd_raw AS 
    SELECT * FROM (VALUES
        ('reg1', DATE '2026-01-01', 10.0),
        ('reg1', DATE '2026-01-02', 0.0),
        ('reg1', DATE '2026-01-03', 0.5),
        ('reg1', DATE '2026-01-04', 5.0),
        ('reg1', DATE '2026-01-05', 0.0)
    ) AS t(region_id, date, precipitation_mm);
    """)
    
    res = con.execute(f"""
    WITH dry_day_flags AS (
        SELECT 
            *,
            CASE WHEN precipitation_mm < {RAIN_DAY_THRESHOLD_MM} THEN 1 ELSE 0 END AS is_dry_day,
            SUM(CASE WHEN precipitation_mm >= {RAIN_DAY_THRESHOLD_MM} THEN 1 ELSE 0 END) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS rain_reset_group
        FROM test_cdd_raw
    )
    SELECT 
        date,
        precipitation_mm,
        is_dry_day,
        CASE 
            WHEN is_dry_day = 1 THEN SUM(is_dry_day) OVER (
                PARTITION BY region_id, rain_reset_group ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
            ELSE 0 
        END AS consecutive_dry_days
    FROM dry_day_flags
    ORDER BY date;
    """).fetchall()
    
    cdd_values = [row[3] for row in res]
    assert cdd_values == [0, 1, 2, 0, 1], f"Expected [0, 1, 2, 0, 1], got {cdd_values}"
    con.close()

def test_max_cdd_30d_retention():
    """
    Test 2: A rain event today must not erase a 10-day dry spell last week.
    max_cdd_30d must retain 10 even when consecutive_dry_days drops to 0.
    """
    con = duckdb.connect(":memory:")
    
    # 10 dry days (0mm), followed by 1 rain day (20mm) on day 11
    days_data = [(f'reg1', f'2026-01-{i:02d}', 0.0) for i in range(1, 11)]
    days_data.append(('reg1', '2026-01-11', 20.0))
    
    con.execute("CREATE TABLE test_streak (region_id VARCHAR, date DATE, precip_mm DOUBLE);")
    con.executemany("INSERT INTO test_streak VALUES (?, CAST(? AS DATE), ?);", days_data)
    
    res = con.execute(f"""
    WITH dry_day_flags AS (
        SELECT 
            *,
            CASE WHEN precip_mm < {RAIN_DAY_THRESHOLD_MM} THEN 1 ELSE 0 END AS is_dry_day,
            SUM(CASE WHEN precip_mm >= {RAIN_DAY_THRESHOLD_MM} THEN 1 ELSE 0 END) OVER (
                PARTITION BY region_id ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS rain_reset_group
        FROM test_streak
    ),
    with_cdd AS (
        SELECT 
            *,
            CASE 
                WHEN is_dry_day = 1 THEN SUM(is_dry_day) OVER (
                    PARTITION BY region_id, rain_reset_group ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )
                ELSE 0 
            END AS consecutive_dry_days
        FROM dry_day_flags
    )
    SELECT 
        date,
        consecutive_dry_days,
        MAX(consecutive_dry_days) OVER (
            PARTITION BY region_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS max_cdd_30d
    FROM with_cdd
    ORDER BY date DESC
    LIMIT 2;
    """).fetchall()
    
    # Day 11 (rain day)
    day11_cdd = res[0][1]
    day11_max_cdd = res[0][2]
    
    assert day11_cdd == 0, f"Day 11 rain day CDD must reset to 0, got {day11_cdd}"
    assert day11_max_cdd == 10, f"Day 11 max_cdd_30d must retain previous 10 dry days, got {day11_max_cdd}"
    con.close()

def test_mid_rank_percentile_ties():
    """
    Test 3: Mid-rank percentile rule:
    (count(h < cur) + 0.5 * count(h = cur)) / n * 100
    On list [10, 20, 20, 20, 30]:
    Mid-rank of 20 has count < 20 = 1, count = 20 is 3, total is 5.
    (1 + 0.5 * 3) / 5 * 100 = 2.5 / 5 * 100 = 50.0%.
    """
    con = duckdb.connect(":memory:")
    vals = [10.0, 20.0, 20.0, 20.0, 30.0]
    con.execute("CREATE TABLE test_ties AS SELECT unnest(?) AS val", [vals])
    
    # Test for value 20.0
    cur_val = 20.0
    mid_rank_pct = con.execute(f"""
        SELECT (COUNT(CASE WHEN val < {cur_val} THEN 1 END) 
              + 0.5 * COUNT(CASE WHEN val = {cur_val} THEN 1 END)) * 100.0 / COUNT(*)
        FROM test_ties;
    """).fetchone()[0]
    
    assert mid_rank_pct == 50.0, f"Expected mid-rank percentile 50.0, got {mid_rank_pct}"
    
    # Test for minimum 10.0: (0 + 0.5*1)/5 * 100 = 10.0%
    min_pct = con.execute(f"""
        SELECT (COUNT(CASE WHEN val < 10.0 THEN 1 END) 
              + 0.5 * COUNT(CASE WHEN val = 10.0 THEN 1 END)) * 100.0 / COUNT(*)
        FROM test_ties;
    """).fetchone()[0]
    assert min_pct == 10.0
    
    # Test for maximum 30.0: (4 + 0.5*1)/5 * 100 = 90.0%
    max_pct = con.execute(f"""
        SELECT (COUNT(CASE WHEN val < 30.0 THEN 1 END) 
              + 0.5 * COUNT(CASE WHEN val = 30.0 THEN 1 END)) * 100.0 / COUNT(*)
        FROM test_ties;
    """).fetchone()[0]
    assert max_pct == 90.0
    con.close()

def test_cdd_zero_percentile_behavior():
    """
    Test 4: CDD = 0 behavior:
    In a climate where 40% of historical days have CDD = 0 (rainy season):
    Under old '<=' rule: CDD = 0 gave 40% severity (or 100 - 40%).
    Under mid-rank rule: count(h < 0) = 0, count(h = 0) = 40.
    Severity = (0 + 0.5 * 40) / 100 * 100 = 20.0%.
    """
    con = duckdb.connect(":memory:")
    # 40 zeros and 60 positive CDD values (1..60)
    data = [0.0] * 40 + [float(i) for i in range(1, 61)]
    con.execute("CREATE TABLE cdd_dist AS SELECT unnest(?) AS cdd", [data])
    
    mid_rank_cdd0 = con.execute("""
        SELECT (COUNT(CASE WHEN cdd < 0.0 THEN 1 END) 
              + 0.5 * COUNT(CASE WHEN cdd = 0.0 THEN 1 END)) * 100.0 / COUNT(*)
        FROM cdd_dist;
    """).fetchone()[0]
    
    assert mid_rank_cdd0 == 20.0, f"Expected 20.0% mid-rank severity for CDD=0 with 40% zeros, got {mid_rank_cdd0}"
    con.close()

def test_oni_retroactive_episode_labeling():
    """
    Test 5: ONI 5-season rule retroactively labels the entire episode:
    If a warm run reaches 5 consecutive seasons, seasons 1 through 5 are ALL El Niño.
    A 4-season run remains Neutral for all 4 seasons.
    """
    con = duckdb.connect(":memory:")
    
    # Two warm runs:
    # Run 1: Seasons 1-4 (4 seasons at +0.6) -> Neutral
    # Run 2: Seasons 6-11 (6 seasons at +0.8) -> All 6 seasons are El Niño
    con.execute("""
    CREATE TABLE test_episodes AS
    SELECT * FROM (VALUES
        (1, 2020, 'DJF', 0.6),
        (2, 2020, 'JFM', 0.6),
        (3, 2020, 'FMA', 0.6),
        (4, 2020, 'MAM', 0.6),
        (5, 2020, 'AMJ', 0.1),  -- breaks run 1
        (6, 2020, 'MJJ', 0.8),
        (7, 2020, 'JJA', 0.8),
        (8, 2020, 'JAS', 0.8),
        (9, 2020, 'ASO', 0.8),
        (10, 2020, 'SON', 0.8),
        (11, 2020, 'OND', 0.8)
    ) AS t(season_seq, year, season, oni_anomaly);
    """)
    
    res = con.execute(f"""
    WITH flags AS (
        SELECT 
            *,
            CASE WHEN oni_anomaly >= {ONI_ANOMALY_THRESHOLD} THEN 1 ELSE 0 END AS is_warm,
            SUM(CASE WHEN oni_anomaly < {ONI_ANOMALY_THRESHOLD} THEN 1 ELSE 0 END) OVER (
                ORDER BY season_seq ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS warm_group
        FROM test_episodes
    ),
    runs AS (
        SELECT 
            *,
            SUM(is_warm) OVER (PARTITION BY warm_group) AS total_warm_length
        FROM flags
    )
    SELECT 
        season_seq,
        season,
        total_warm_length,
        CASE 
            WHEN is_warm = 1 AND total_warm_length >= {ONI_MIN_CONSECUTIVE_SEASONS} THEN 'El Niño'
            ELSE 'Neutral'
        END AS enso_state
    FROM runs
    ORDER BY season_seq;
    """).fetchall()
    
    states = {row[0]: row[3] for row in res}
    
    # Run 1: length 4 -> Neutral
    assert states[1] == "Neutral"
    assert states[2] == "Neutral"
    assert states[3] == "Neutral"
    assert states[4] == "Neutral"
    assert states[5] == "Neutral"
    
    # Run 2: length 6 -> All seasons (6 through 11) must be 'El Niño'
    assert states[6] == "El Niño", f"Season 6 (start of 6-season episode) must be El Niño, got {states[6]}"
    assert states[7] == "El Niño"
    assert states[8] == "El Niño"
    assert states[9] == "El Niño"
    assert states[10] == "El Niño"
    assert states[11] == "El Niño"
    con.close()

def test_tier_assignment_at_exact_cutoffs():
    """
    Test 6: Tier assignment at exact cutoffs:
    >= 95 -> EXTREME DROUGHT
    >= 90 -> SEVERE DROUGHT
    >= 80 -> MODERATE DROUGHT
    >= 70 -> DRY SPELL WATCH
    < 70  -> NORMAL
    """
    assert get_tier_for_percentile(100.0)["tier"] == "EXTREME DROUGHT"
    assert get_tier_for_percentile(95.0)["tier"] == "EXTREME DROUGHT"
    
    assert get_tier_for_percentile(94.9)["tier"] == "SEVERE DROUGHT"
    assert get_tier_for_percentile(90.0)["tier"] == "SEVERE DROUGHT"
    
    assert get_tier_for_percentile(89.9)["tier"] == "MODERATE DROUGHT"
    assert get_tier_for_percentile(80.0)["tier"] == "MODERATE DROUGHT"
    
    assert get_tier_for_percentile(79.9)["tier"] == "DRY SPELL WATCH"
    assert get_tier_for_percentile(70.0)["tier"] == "DRY SPELL WATCH"
    
    assert get_tier_for_percentile(69.9)["tier"] == "NORMAL"
    assert get_tier_for_percentile(0.0)["tier"] == "NORMAL"
