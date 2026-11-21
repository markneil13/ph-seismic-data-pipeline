import os
import sys
import json
import time
import urllib.request
import urllib.error
import ssl
from datetime import datetime, date, timedelta, timezone
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.config_ph import (
    CLIMATOLOGY_START_YEAR,
    CLIMATOLOGY_END_YEAR,
    RECENT_WINDOW_DAYS
)
from src.el_nino_ph.regions_ph import PH_REGIONS

BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze", "el_nino_ph")
CLIMATOLOGY_DIR = os.path.join(BRONZE_DIR, "climatology")

NOAA_SSTOI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices"
NOAA_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
ARCHIVE_API_URL = "https://archive-api.open-meteo.com/v1/archive"

def fetch_with_retry(url: str, retries: int = 5, base_backoff: float = 12.0, timeout: int = 35):
    """Fetches a URL with exponential backoff on HTTP 429/5xx and network errors."""
    headers = {"User-Agent": "AntigravityPHElNinoTracker/2.0 (Climate Research; contact@local)"}
    ctx = ssl.create_default_context()
    last_err = None
    
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                return resp.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            last_err = e
            # Retry on 429 (rate limit) or 5xx (server error)
            if e.code == 429 or 500 <= e.code < 600:
                sleep_sec = base_backoff * (attempt + 1)
                print(f"    [RETRY] HTTP {e.code} on attempt {attempt+1}/{retries}. Cooling down {sleep_sec:.1f}s...")
                time.sleep(sleep_sec)
            else:
                raise
        except Exception as e:
            last_err = e
            sleep_sec = base_backoff * (attempt + 1)
            print(f"    [RETRY] Error on attempt {attempt+1}/{retries}: {e}. Backing off {sleep_sec:.1f}s...")
            time.sleep(sleep_sec)
            
    raise RuntimeError(f"Failed to fetch {url} after {retries} retries: {last_err}")

def fetch_noaa_nino34_data():
    """Fetches and parses NOAA CPC Niño 3.4 SST index (sstoi.indices)."""
    raw_text = fetch_with_retry(NOAA_SSTOI_URL)
    sstoi_lines = raw_text.strip().split('\n')
    records = []
    
    for line in sstoi_lines[1:]:
        parts = line.split()
        if len(parts) >= 10:
            try:
                yr = int(parts[0])
                mon = int(parts[1])
                if yr >= 1950:
                    nino34_sst = float(parts[8])
                    nino34_anom = float(parts[9])
                    records.append({
                        "year_month": f"{yr:04d}-{mon:02d}",
                        "year": yr,
                        "month": mon,
                        "nino34_sst": nino34_sst,
                        "nino34_anom": nino34_anom,
                        "ingested_at": datetime.now(timezone.utc).isoformat()
                    })
            except ValueError:
                continue

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values(by="year_month").reset_index(drop=True)
    return df

def fetch_noaa_oni_data():
    """Fetches and parses NOAA CPC Oceanic Niño Index (oni.ascii.txt)."""
    raw_text = fetch_with_retry(NOAA_ONI_URL)
    oni_lines = raw_text.strip().split('\n')
    records = []
    
    for line in oni_lines[1:]:
        parts = line.split()
        if len(parts) >= 4:
            try:
                seas = parts[0].strip()
                yr = int(parts[1])
                total = float(parts[2])
                anom = float(parts[3])
                records.append({
                    "season": seas,
                    "year": yr,
                    "season_year": f"{yr}_{seas}",
                    "oni_total": total,
                    "oni_anomaly": anom,
                    "ingested_at": datetime.now(timezone.utc).isoformat()
                })
            except ValueError:
                continue

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values(by=["year", "season"]).reset_index(drop=True)
    return df

def fetch_region_climate_range(lat: float, lon: float, start_year: int, end_year: int):
    """Fetches daily climate observations for a region from Open-Meteo ERA5 archive across a year range."""
    start_d = f"{start_year}-01-01"
    end_d = f"{end_year}-12-31"
    url = (
        f"{ARCHIVE_API_URL}?latitude={lat}&longitude={lon}"
        f"&start_date={start_d}&end_date={end_d}"
        "&daily=temperature_2m_max,temperature_2m_mean,precipitation_sum,soil_moisture_7_to_28cm_mean"
        "&timezone=auto"
    )
    raw_json = fetch_with_retry(url, retries=4, timeout=35)
    data = json.loads(raw_json)
    daily = data.get("daily", {})
    times = daily.get("time", [])
    tmax = daily.get("temperature_2m_max", [])
    tmean = daily.get("temperature_2m_mean", [])
    precip = daily.get("precipitation_sum", [])
    soil = daily.get("soil_moisture_7_to_28cm_mean", [])
    
    records = []
    for i, d_str in enumerate(times):
        d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
        records.append({
            "date": d_str,
            "year": d_obj.year,
            "day_of_year": d_obj.timetuple().tm_yday,
            "temp_max_c": float(tmax[i]) if i < len(tmax) and tmax[i] is not None else None,
            "temp_mean_c": float(tmean[i]) if i < len(tmean) and tmean[i] is not None else None,
            "precipitation_mm": float(precip[i]) if i < len(precip) and precip[i] is not None else None,
            "soil_moisture_rootzone": float(soil[i]) if i < len(soil) and soil[i] is not None else None
        })
    return records

def ingest_climatology_cache():
    """Ingests and caches historical ERA5 climatology per region (2005-2025)."""
    os.makedirs(CLIMATOLOGY_DIR, exist_ok=True)
    target_years = set(range(CLIMATOLOGY_START_YEAR, CLIMATOLOGY_END_YEAR + 1))
    total_regions = len(PH_REGIONS)
    
    print(f"\n-> Checking historical ERA5 climatology cache ({CLIMATOLOGY_START_YEAR}-{CLIMATOLOGY_END_YEAR}) for {total_regions} basins...")
    
    for idx, reg in enumerate(PH_REGIONS, start=1):
        reg_id = reg["region_id"]
        cache_path = os.path.join(CLIMATOLOGY_DIR, f"{reg_id}.parquet")
        existing_df = None
        missing_years = sorted(list(target_years))
        
        if os.path.exists(cache_path):
            try:
                existing_df = pd.read_parquet(cache_path)
                cached_years = set(existing_df["year"].unique())
                missing_years = sorted(list(target_years - cached_years))
            except Exception as e:
                print(f"  [WARN] Corrupt cache for {reg_id}, refetching: {e}")
                existing_df = None
                missing_years = sorted(list(target_years))
                
        if not missing_years:
            print(f"  [{idx}/{total_regions}] {reg_id}: Cache valid ({len(existing_df)} historical days)")
            continue
            
        print(f"  [{idx}/{total_regions}] {reg_id}: Fetching {len(missing_years)} missing years ({min(missing_years)}-{max(missing_years)})...")
        new_records = fetch_region_climate_range(reg["latitude"], reg["longitude"], min(missing_years), max(missing_years))
        for r in new_records:
            r["region_id"] = reg_id
        time.sleep(2.5) # respect rate limit between multi-year queries
            
        new_df = pd.DataFrame(new_records)
        if existing_df is not None and not existing_df.empty:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
            
        combined_df = combined_df.sort_values(by="date").drop_duplicates(subset=["region_id", "date"]).reset_index(drop=True)
        combined_df.to_parquet(cache_path, index=False)
        print(f"  [{idx}/{total_regions}] {reg_id}: Saved {len(combined_df)} climatology days -> {os.path.basename(cache_path)}")

def fetch_recent_completed_climate(window_days: int = RECENT_WINDOW_DAYS):
    """
    Fetches recent daily climate observations using Open-Meteo ERA5 archive.
    Filters exclusively for completed days (lagging by 1-2 days) up to yesterday.
    No forecast or partial day is ever included.
    """
    yesterday = date.today() - timedelta(days=1)
    start_date = yesterday - timedelta(days=window_days)
    
    all_records = []
    total_regions = len(PH_REGIONS)
    
    for idx, reg in enumerate(PH_REGIONS, start=1):
        reg_id = reg["region_id"]
        lat = reg["latitude"]
        lon = reg["longitude"]
        
        url = (
            f"{ARCHIVE_API_URL}?latitude={lat}&longitude={lon}"
            f"&start_date={start_date.isoformat()}&end_date={yesterday.isoformat()}"
            "&daily=temperature_2m_max,temperature_2m_mean,precipitation_sum,soil_moisture_7_to_28cm_mean"
            "&timezone=auto"
        )
        
        raw_json = fetch_with_retry(url)
        data = json.loads(raw_json)
        daily = data.get("daily", {})
        times = daily.get("time", [])
        tmax = daily.get("temperature_2m_max", [])
        tmean = daily.get("temperature_2m_mean", [])
        precip = daily.get("precipitation_sum", [])
        soil = daily.get("soil_moisture_7_to_28cm_mean", [])
        
        valid_days = 0
        for i, d_str in enumerate(times):
            # Verify completed day (not null)
            p_val = float(precip[i]) if i < len(precip) and precip[i] is not None else None
            t_val = float(tmax[i]) if i < len(tmax) and tmax[i] is not None else None
            
            # Open-Meteo archive returns null for unfinished days
            if p_val is None and t_val is None:
                continue
                
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
            all_records.append({
                "record_id": f"{reg_id}_{d_str}",
                "region_id": reg_id,
                "date": d_str,
                "temp_max_c": t_val,
                "temp_mean_c": float(tmean[i]) if i < len(tmean) and tmean[i] is not None else None,
                "precipitation_mm": p_val,
                "soil_moisture_rootzone": float(soil[i]) if i < len(soil) and soil[i] is not None else None,
                "ingested_at": datetime.now(timezone.utc).isoformat()
            })
            valid_days += 1
            
        print(f"  [OK] [{idx}/{total_regions}] Ingested {valid_days} completed daily records for {reg['region_name']}")
        time.sleep(0.08)
        
    df = pd.DataFrame(all_records)
    return df

def ingest_ph_bronze_layer():
    """Runs ingestion and saves Bronze parquet files with robust retries and validation."""
    os.makedirs(BRONZE_DIR, exist_ok=True)
    total_regions = len(PH_REGIONS)
    print("\n" + "="*70)
    print(f"=== [BRONZE] Ingesting Feeds for {total_regions} Philippine Agricultural Basins ===")
    print("="*70)
    
    # 1. Ingest NOAA Niño 3.4 SST
    print("-> Pulling NOAA CPC Niño 3.4 SST & Anomaly indices...")
    df_nino = fetch_noaa_nino34_data()
    nino_path = os.path.join(BRONZE_DIR, "raw_noaa_nino34.parquet")
    df_nino.to_parquet(nino_path, index=False)
    print(f"  [SAVED] {len(df_nino)} NOAA Niño 3.4 monthly records -> {os.path.basename(nino_path)}")
    
    # 2. Ingest NOAA ONI
    print("-> Pulling NOAA CPC Oceanic Niño Index (oni.ascii.txt)...")
    df_oni = fetch_noaa_oni_data()
    oni_path = os.path.join(BRONZE_DIR, "raw_noaa_oni.parquet")
    df_oni.to_parquet(oni_path, index=False)
    print(f"  [SAVED] {len(df_oni)} NOAA ONI seasonal records -> {os.path.basename(oni_path)}")
    
    # 3. Ingest Historical ERA5 Climatology Cache (2005-2025)
    ingest_climatology_cache()
    
    # 4. Ingest Recent Completed Window (Open-Meteo ERA5 Archive, completed days only)
    print(f"\n-> Pulling completed observed ERA5 daily series for {total_regions} basins...")
    df_climate = fetch_recent_completed_climate(window_days=RECENT_WINDOW_DAYS)
    climate_path = os.path.join(BRONZE_DIR, "raw_ph_climate_daily.parquet")
    df_climate.to_parquet(climate_path, index=False)
    print(f"  [SAVED] {len(df_climate)} Recent Daily Climate records -> {os.path.basename(climate_path)}")
    
    # 5. Save Region Metadata
    regions_path = os.path.join(BRONZE_DIR, "dim_ph_regions_raw.parquet")
    pd.DataFrame(PH_REGIONS).to_parquet(regions_path, index=False)
    print(f"  [SAVED] {total_regions} Philippine Basins Metadata -> {os.path.basename(regions_path)}\n")
    
    return nino_path, oni_path, climate_path, regions_path

if __name__ == "__main__":
    ingest_ph_bronze_layer()
