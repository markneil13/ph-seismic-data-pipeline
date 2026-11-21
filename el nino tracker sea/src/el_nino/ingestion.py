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

from src.el_nino.regions import SEA_REGIONS
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze", "el_nino")

NOAA_SSTOI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices"
NOAA_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

def fetch_noaa_enso_data():
    """Fetches and parses NOAA CPC Niño 3.4 SST index and ONI records."""
    headers = {"User-Agent": "AntigravityElNinoTracker/1.0 (Climate Research; contact@local)"}
    ctx = ssl.create_default_context()
    
    req = urllib.request.Request(NOAA_SSTOI_URL, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        sstoi_lines = resp.read().decode('utf-8').strip().split('\n')
        
    records = []
    # Skip header
    for line in sstoi_lines[1:]:
        parts = line.split()
        if len(parts) >= 10:
            try:
                yr = int(parts[0])
                mon = int(parts[1])
                # Only take recent years (2020 onward) for the pipeline
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

    # Also fetch ONI for rolling anomaly confirmation
    oni_dict = {}
    try:
        req_oni = urllib.request.Request(NOAA_ONI_URL, headers=headers)
        with urllib.request.urlopen(req_oni, context=ctx, timeout=15) as resp_oni:
            oni_lines = resp_oni.read().decode('utf-8').strip().split('\n')
        for line in oni_lines[1:]:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    seas, yr, total, anom = parts[0], int(parts[1]), float(parts[2]), float(parts[3])
                    if yr >= 2020:
                        oni_dict[f"{yr}_{seas}"] = {"oni_total": total, "oni_anom": anom}
                except ValueError:
                    continue
    except Exception as e:
        print(f"  [WARN] Could not fetch ONI secondary feed: {e}")

    df_enso = pd.DataFrame(records)
    if not df_enso.empty:
        df_enso = df_enso.sort_values(by="year_month").reset_index(drop=True)
    return df_enso

def fetch_sea_climate_data(past_days=60):
    """Fetches daily climate and soil moisture data for all 12 Southeast Asian regions from Open-Meteo."""
    headers = {"User-Agent": "AntigravityElNinoTracker/1.0"}
    ctx = ssl.create_default_context()
    
    all_climate_records = []
    
    for region in SEA_REGIONS:
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
            with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
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
        except Exception as e:
            print(f"  [ERROR] Failed to fetch climate data for {reg_id}: {e}")
            
    df_climate = pd.DataFrame(all_climate_records)
    return df_climate

def run_el_nino_ingestion():
    """Runs ingestion for both NOAA ENSO and Open-Meteo SEA regional climate."""
    print("[BRONZE] Starting Super El Niño Data Ingestion...")
    
    enso_dir = os.path.join(BRONZE_DIR, "enso")
    climate_dir = os.path.join(BRONZE_DIR, "climate")
    os.makedirs(enso_dir, exist_ok=True)
    os.makedirs(climate_dir, exist_ok=True)
    
    # 1. Ingest NOAA ENSO
    df_enso = fetch_noaa_enso_data()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    enso_file = os.path.join(enso_dir, f"enso_indices_{today_str}.parquet")
    df_enso.to_parquet(enso_file, index=False)
    print(f"  + Ingested {len(df_enso)} monthly NOAA Niño 3.4 SST records -> {enso_file}")
    
    # 2. Ingest SEA Climate
    df_climate = fetch_sea_climate_data(past_days=60)
    climate_file = os.path.join(climate_dir, f"sea_climate_{today_str}.parquet")
    df_climate.to_parquet(climate_file, index=False)
    print(f"  + Ingested {len(df_climate)} daily regional climate observations across 12 SEA hubs -> {climate_file}")
    print("[OK] Bronze Ingestion Complete.\n")
    
    return df_enso, df_climate

if __name__ == "__main__":
    run_el_nino_ingestion()
