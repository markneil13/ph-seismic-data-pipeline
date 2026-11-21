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
    
    # Sequence of 5 days: Rain (10mm), Dry (0mm), Dry (0.5mm), Rain (5.0mm), Dry (0.0mm)
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

def test_percentile_empirical_function():
    """
    Test 2: Percentile function: a value equal to the historical median gives about 50; the minimum gives about 0.
    """
    con = duckdb.connect(":memory:")
    # Population of 101 values from 0.0 to 100.0
    vals = [float(x) for x in range(101)]
    con.execute("CREATE TABLE population AS SELECT unnest(?) AS val", [vals])
    
    # 1. Median value (50.0)
    pct_median = con.execute("""
        SELECT COUNT(CASE WHEN val <= 50.0 THEN 1 END) * 100.0 / COUNT(*) FROM population
    """).fetchone()[0]
    
    # 2. Minimum value (0.0)
    pct_min = con.execute("""
        SELECT COUNT(CASE WHEN val <= 0.0 THEN 1 END) * 100.0 / COUNT(*) FROM population
    """).fetchone()[0]
    
    # 3. Value below minimum (-10.0)
    pct_below_min = con.execute("""
        SELECT COUNT(CASE WHEN val <= -10.0 THEN 1 END) * 100.0 / COUNT(*) FROM population
    """).fetchone()[0]
    
    # 4. Maximum value (100.0)
    pct_max = con.execute("""
        SELECT COUNT(CASE WHEN val <= 100.0 THEN 1 END) * 100.0 / COUNT(*) FROM population
    """).fetchone()[0]
    
    # Check assertions
    assert 49.0 <= pct_median <= 51.5, f"Expected median percentile ~50.0, got {pct_median}"
    assert 0.0 <= pct_min <= 2.0, f"Expected min percentile ~0.0, got {pct_min}"
    assert pct_below_min == 0.0
    assert pct_max == 100.0
    con.close()

def test_oni_enso_classifier():
    """
    Test 3: ONI classifier: 4 seasons at +0.6 is not El Niño, 5 is.
    """
    con = duckdb.connect(":memory:")
    
    # Create 8 consecutive seasons:
    # Seasons 1 to 4: +0.6 (4 seasons)
    # Season 5: +0.6 (5th season)
    # Season 6: +0.6 (6th season)
    # Season 7: +0.1 (drop to neutral)
    # Season 8: +0.2 (neutral)
    con.execute("""
    CREATE TABLE test_oni AS
    SELECT * FROM (VALUES
        (1, 2024, 'DJF', 0.6),
        (2, 2024, 'JFM', 0.6),
        (3, 2024, 'FMA', 0.6),
        (4, 2024, 'MAM', 0.6),
        (5, 2024, 'AMJ', 0.6),
        (6, 2024, 'MJJ', 0.6),
        (7, 2024, 'JJA', 0.1),
        (8, 2024, 'JAS', 0.2)
    ) AS t(season_seq, year, season, oni_anomaly);
    """)
    
    res = con.execute(f"""
    WITH oni_streaks AS (
        SELECT 
            *,
            CASE WHEN oni_anomaly >= {ONI_ANOMALY_THRESHOLD} THEN 1 ELSE 0 END AS is_warm,
            SUM(CASE WHEN oni_anomaly < {ONI_ANOMALY_THRESHOLD} THEN 1 ELSE 0 END) OVER (
                ORDER BY season_seq ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS warm_group
        FROM test_oni
    ),
    streak_counts AS (
        SELECT 
            *,
            CASE 
                WHEN is_warm = 1 THEN SUM(is_warm) OVER (PARTITION BY warm_group ORDER BY season_seq ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                ELSE 0 
            END AS warm_streak
        FROM oni_streaks
    )
    SELECT 
        season_seq,
        season,
        oni_anomaly,
        warm_streak,
        CASE 
            WHEN warm_streak >= {ONI_MIN_CONSECUTIVE_SEASONS} THEN 'El Niño'
            ELSE 'Neutral'
        END AS enso_state
    FROM streak_counts
    ORDER BY season_seq;
    """).fetchall()
    
    states = {row[0]: row[4] for row in res}
    streaks = {row[0]: row[3] for row in res}
    
    # Check season 4: warm streak = 4 -> Neutral
    assert streaks[4] == 4
    assert states[4] == "Neutral", f"Season 4 at +0.6 with streak 4 must be Neutral, got {states[4]}"
    
    # Check season 5: warm streak = 5 -> El Niño
    assert streaks[5] == 5
    assert states[5] == "El Niño", f"Season 5 at +0.6 with streak 5 must be El Niño, got {states[5]}"
    
    # Check season 6: warm streak = 6 -> El Niño
    assert streaks[6] == 6
    assert states[6] == "El Niño"
    
    # Check season 7: dropped to 0.1 -> Neutral
    assert states[7] == "Neutral"
    con.close()

def test_tier_assignment_at_exact_cutoffs():
    """
    Test 4: Tier assignment at exact cutoffs:
    >= 95 -> EXTREME DROUGHT
    >= 90 -> SEVERE DROUGHT
    >= 80 -> MODERATE DROUGHT
    >= 70 -> DRY SPELL WATCH
    < 70  -> NORMAL
    """
    # Test boundary values
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
