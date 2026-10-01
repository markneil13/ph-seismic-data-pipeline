import os
import json
import time
import urllib.request
import ssl
from datetime import datetime, timezone
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze")

# Bounding box for the Philippines archipelago region
PH_BOUNDS = {
    "minlatitude": 4.5,
    "maxlatitude": 21.5,
    "minlongitude": 116.0,
    "maxlongitude": 127.0
}

def fetch_live_ph_earthquakes(retries=3):
    """Fetches real-time seismic event data from USGS API for the Philippines region using standard SSL."""
    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
        f"&minlatitude={PH_BOUNDS['minlatitude']}&maxlatitude={PH_BOUNDS['maxlatitude']}"
        f"&minlongitude={PH_BOUNDS['minlongitude']}&maxlongitude={PH_BOUNDS['maxlongitude']}"
        "&minmagnitude=2.0"
    )
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AntigravityDataEngine/1.0"}
    # Standard default SSL context (removed ssl.CERT_NONE)
    ctx = ssl.create_default_context()
    
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                raw_json = json.loads(response.read().decode('utf-8'))
                
            features = raw_json.get("features", [])
            events = []
            
            for f in features:
                props = f.get("properties", {})
                geometry = f.get("geometry", {})
                coords = geometry.get("coordinates", [None, None, None])
                
                events.append({
                    "usgs_event_id": f.get("id"),
                    "magnitude": props.get("mag"),
                    "place": props.get("place"),
                    "time_epoch_ms": props.get("time"),
                    "updated_epoch_ms": props.get("updated"),
                    "url": props.get("url"),
                    "oceanic_event": props.get("tsunami"), # Renamed from tsunami_alert
                    "sig_score": props.get("sig"),
                    "alert_level": props.get("alert"),
                    "status": props.get("status"),
                    "longitude": coords[0],
                    "latitude": coords[1],
                    "depth_km": coords[2],
                    "ingested_at": datetime.now(timezone.utc).isoformat()
                })
                
            return pd.DataFrame(events)
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                raise e

def run_ingestion():
    """Saves live raw earthquake events to Bronze Parquet storage."""
    print("[BRONZE] Starting Real-Time Ingestion (USGS Philippines Feed)...")
    
    df = fetch_live_ph_earthquakes()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    output_dir = os.path.join(BRONZE_DIR, "earthquakes", f"date={today_str}")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "raw_ph_earthquakes.parquet")
    df.to_parquet(output_file, index=False)
    
    print(f"  + Fetched {len(df)} live seismic events across the Philippines.")
    print(f"  + Written Bronze Parquet file to {output_file}")
    print("[OK] Bronze Ingestion Complete.\n")
    return df

if __name__ == "__main__":
    run_ingestion()
