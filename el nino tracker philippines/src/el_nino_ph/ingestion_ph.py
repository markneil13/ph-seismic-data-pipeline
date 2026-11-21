import os
import sys
import json
import time
import urllib.request
import ssl
from datetime import datetime, timezone
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.regions_ph import PH_REGIONS
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze", "el_nino_ph")

NOAA_SSTOI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices"
NOAA_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

def fetch_noaa_enso_data():
    """Fetches and parses NOAA CPC Niño 3.4 SST index and ONI records."""
    headers = {"User-Agent": "AntigravityPHElNinoTracker/1.0 (Climate Research; contact@local)"}
    ctx = ssl.create_default_context()
    
    req = urllib.request.Request(NOAA_SSTOI_URL, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        sstoi_lines = resp.read().decode('utf-8').strip().split('\n')
        
    records = []
    for line in sstoi_lines[1:]:
        parts = line.split()
        if len(parts) >= 10:
            try:
                yr = int(parts[0])
                mon = int(parts[1])
                if yr >= 2020:
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

    df_enso = pd.DataFrame(records)
    if not df_enso.empty:
        df_enso = df_enso.sort_values(by="year_month").reset_index(drop=True)
    return df_enso

def fetch_ph_climate_data(past_days=60):
    """Fetches daily climate and soil moisture data for all 16 Philippine agricultural regions and reservoirs."""
    headers = {"User-Agent": "AntigravityPHElNinoTracker/1.0"}
    ctx = ssl.create_default_context()
    
    all_climate_records = []
    
    for region in PH_REGIONS:
        lat = region["latitude"]
        lon = region["longitude"]
        reg_id = region["region_id"]
        
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&past_days={past_days}&forecast_days=1"
            "&daily=temperature_2m_max,temperature_2m_mean,precipitation_sum,et0_fao_evapotranspiration,"
            "soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean"
            "&timezone=auto"
        )
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
            daily = data.get("daily", {})
            times = daily.get("time", [])
            tmax = daily.get("temperature_2m_max", [])
            tmean = daily.get("temperature_2m_mean", [])
            precip = daily.get("precipitation_sum", [])
            et0 = daily.get("et0_fao_evapotranspiration", [])
            soil_surf = daily.get("soil_moisture_0_to_7cm_mean", [])
            soil_root = daily.get("soil_moisture_7_to_28cm_mean", [])
            
            for i, d_str in enumerate(times):
                all_climate_records.append({
                    "record_id": f"{reg_id}_{d_str}",
                    "region_id": reg_id,
                    "date": d_str,
                    "temp_max_c": tmax[i] if i < len(tmax) else None,
                    "temp_mean_c": tmean[i] if i < len(tmean) else None,
                    "precipitation_mm": precip[i] if i < len(precip) else None,
                    "et0_evapotranspiration_mm": et0[i] if i < len(et0) else None,
                    "soil_moisture_surface": soil_surf[i] if i < len(soil_surf) else None,
                    "soil_moisture_rootzone": soil_root[i] if i < len(soil_root) else None,
                    "ingested_at": datetime.now(timezone.utc).isoformat()
                })
            print(f"  [OK] Ingested {len(times)} daily records for {region['region_name']}")
            time.sleep(0.15) # respect rate limit
        except Exception as e:
            print(f"  [WARN] Failed to fetch climate for {reg_id}: {e}")
            
    df_climate = pd.DataFrame(all_climate_records)
    return df_climate

def ingest_ph_bronze_layer():
    """Runs ingestion and saves Bronze parquet files."""
    os.makedirs(BRONZE_DIR, exist_ok=True)
    print("\n=== [BRONZE] Starting Philippine Super El Nino Ingestion ===")
    
    # 1. Ingest NOAA ENSO
    print("-> Pulling NOAA CPC Nino 3.4 SST & Anomaly indices...")
    df_enso = fetch_noaa_enso_data()
    enso_path = os.path.join(BRONZE_DIR, "raw_noaa_nino34.parquet")
    df_enso.to_parquet(enso_path, index=False)
    print(f"  [SAVED] {len(df_enso)} NOAA ENSO records -> {enso_path}")
    
    # 2. Ingest Open-Meteo Philippine climate
    print("-> Pulling Open-Meteo 60-day climate feeds for 16 Philippine basins & reservoirs...")
    df_climate = fetch_ph_climate_data(past_days=60)
    climate_path = os.path.join(BRONZE_DIR, "raw_ph_climate_daily.parquet")
    df_climate.to_parquet(climate_path, index=False)
    print(f"  [SAVED] {len(df_climate)} Daily Climate records -> {climate_path}")
    
    # 3. Save Region Metadata
    regions_path = os.path.join(BRONZE_DIR, "dim_ph_regions_raw.parquet")
    pd.DataFrame(PH_REGIONS).to_parquet(regions_path, index=False)
    print(f"  [SAVED] {len(PH_REGIONS)} Philippine Basins Metadata -> {regions_path}")
    
    return enso_path, climate_path, regions_path

if __name__ == "__main__":
    ingest_ph_bronze_layer()
