# Configuration for Philippine Super El Niño & Basin Drought Intelligence System
# Single Source of Truth for constants, thresholds, weights, and map projection

# Map Canvas & Projection Constants
# Calibrated for Philippine archipelago bounding box (116.5°E to 127.0°E, 4.5°N to 21.5°N)
MAP_CONFIG = {
    "width": 650,
    "height": 820,
    "pad_x": 35,
    "pad_y": 35,
    "lon_min": 116.5,
    "lon_max": 127.0,
    "lat_min": 4.5,
    "lat_max": 21.5
}

def project_ph_coords(lon: float, lat: float, cfg=MAP_CONFIG):
    """Projects geographic lon/lat into SVG canvas coordinates."""
    inner_w = cfg["width"] - 2 * cfg["pad_x"]
    inner_h = cfg["height"] - 2 * cfg["pad_y"]
    x = cfg["pad_x"] + ((lon - cfg["lon_min"]) / (cfg["lon_max"] - cfg["lon_min"])) * inner_w
    y = cfg["height"] - cfg["pad_y"] - ((lat - cfg["lat_min"]) / (cfg["lat_max"] - cfg["lat_min"])) * inner_h
    return round(x, 1), round(y, 1)

# Climatological Baseline & Calculation Parameters
# Source: Open-Meteo ERA5 Reanalysis Archive
CLIMATOLOGY_START_YEAR = 2005
CLIMATOLOGY_END_YEAR = 2025
RECENT_WINDOW_DAYS = 60

# WMO standard precipitation day threshold: >= 1.0 mm
RAIN_DAY_THRESHOLD_MM = 1.0

# Calendar day window: day-of-year +/- 15 days (31-day seasonal evaluation window)
CALENDAR_WINDOW_DAYS = 15

# Extreme heat threshold: 90th percentile of historical Tmax for that calendar day
HEAT_EXTREME_PERCENTILE = 90.0

# SEDI Component Weights (0 to 1.0)
# NOTE: Expert-judgement heuristic weights, not empirically validated against crop yields
SEDI_WEIGHTS = {
    "rain": 0.35,        # 35% weight: 30-day precipitation percentile deficit
    "soil": 0.30,        # 30% weight: 30-day rootzone (7-28cm) soil moisture depletion percentile
    "dry_spell": 0.20,   # 20% weight: Consecutive dry days (CDD) percentile
    "heat": 0.15         # 15% weight: Heat stress days count percentile
}

# Drought Tiers based on Historical SEDI Percentile Distribution (USDM-style)
# Source: Adapted from US Drought Monitor percentile ranking criteria
TIER_DEFINITIONS = [
    {
        "tier": "EXTREME DROUGHT",
        "min_percentile": 95.0,
        "code": "EXTREME",
        "color": "#ef4444",       # Coral Red
        "border_color": "#b91c1c",
        "bg_color": "rgba(239, 68, 68, 0.2)",
        "pulse_class": "pulse-crisis"
    },
    {
        "tier": "SEVERE DROUGHT",
        "min_percentile": 90.0,
        "code": "SEVERE",
        "color": "#f97316",       # Vibrant Orange
        "border_color": "#c2410c",
        "bg_color": "rgba(249, 115, 22, 0.2)",
        "pulse_class": "pulse-severe"
    },
    {
        "tier": "MODERATE DROUGHT",
        "min_percentile": 80.0,
        "code": "MODERATE",
        "color": "#eab308",       # Yellow / Gold
        "border_color": "#a16207",
        "bg_color": "rgba(234, 179, 8, 0.2)",
        "pulse_class": "pulse-moderate"
    },
    {
        "tier": "DRY SPELL WATCH",
        "min_percentile": 70.0,
        "code": "WATCH",
        "color": "#38bdf8",       # Electric Sky Blue
        "border_color": "#0284c7",
        "bg_color": "rgba(56, 189, 248, 0.2)",
        "pulse_class": "pulse-watch"
    },
    {
        "tier": "NORMAL",
        "min_percentile": 0.0,
        "code": "NORMAL",
        "color": "#10b981",       # Emerald Green
        "border_color": "#047857",
        "bg_color": "rgba(16, 185, 129, 0.2)",
        "pulse_class": "pulse-normal"
    }
]

def get_tier_for_percentile(pct: float):
    """Maps a percentile rank [0, 100] to its corresponding drought tier definition."""
    for t in TIER_DEFINITIONS:
        if pct >= t["min_percentile"]:
            return t
    return TIER_DEFINITIONS[-1]

# NOAA CPC ONI Classification Constants
# Source: NOAA Climate Prediction Center Operational Definitions
ONI_ANOMALY_THRESHOLD = 0.5
ONI_MIN_CONSECUTIVE_SEASONS = 5

# Data Quality Thresholds
MAX_PRECIPITATION_NULL_PCT = 2.0
MAX_SOIL_NULL_PCT = 5.0
MAX_DATA_LATENCY_DAYS = 7
