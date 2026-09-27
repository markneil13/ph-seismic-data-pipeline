# 🇵🇭 Real-Time Philippine Seismic & Earthquake Data Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Spatial%20SQL-yellow.svg)](https://duckdb.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Medallion%20(Bronze%2FSilver%2FGold)-emerald.svg)](#architecture)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An end-to-end, production-grade **Medallion Architecture Data Pipeline** tracking real-time seismic events and earthquake activity across the **Philippine Archipelago** ($4.5^\circ\text{N} - 21.5^\circ\text{N}, 116^\circ\text{E} - 127^\circ\text{E}$).

Powered by **Python, DuckDB Spatial SQL, Parquet, and Tailwind CSS**.

---

## 🏗️ Architecture Overview

```
[ USGS Live GeoJSON API (PH Bounding Box) ]
                    │
                    ▼  (Raw JSON -> Partitioned Parquet)
      [ BRONZE LAYER: Raw Event Storage ]
                    │
                    ▼  (DuckDB Spatial Haversine Distance, PHT Timezone, Richter Scale)
      [ SILVER LAYER: Cleaned & Enriched Seismic Events ]
                    │
                    ▼  (Star Schema Dimensions & High-Risk Alert Data Marts)
      [ GOLD LAYER: Analytical Warehouse ]
                    │
                    ▼  (8 Automated Quality Assertions)
      [ DATA QUALITY ENGINE & INTERACTIVE DASHBOARD ]
```

---

## ✨ Features

* **Live Ingestion (Bronze Layer)**: Ingests real-time seismic events from USGS bounded strictly to the Philippine coordinate bounding box ($4.5^\circ\text{N} - 21.5^\circ\text{N}, 116^\circ\text{E} - 127^\circ\text{E}$).
* **Spatial & Time Transformations (Silver Layer)**:
  * Converts UTC timestamps to **Philippine Standard Time (PHT)**.
  * Calculates exact **Haversine spatial distances (km)** from event epicenters to major Philippine metropolitan cities (Manila, Cebu, Davao, Baguio, General Santos, Tacloban, etc.).
  * Categorizes Richter scale magnitude severity and focal depth ranges.
* **Analytical Data Warehouse (Gold Layer)**: Models `gold.fact_earthquakes`, `gold.dim_ph_cities` (regional exposure), and `gold.seismic_high_risk_alerts`.
* **Automated Data Quality Suite**: Runs 8 SQL assertions enforcing coordinate bounds, magnitude ranges, non-null values, and primary key uniqueness.
* **Interactive Visual Dashboard**: Self-contained HTML dashboard with SVG map plotting epicenters across Luzon, Visayas, and Mindanao.

---

## 🛠️ Project Structure

```text
├── main.py                     # Main pipeline orchestrator & terminal bulletin reporter
├── generate_dashboard_html.py  # Generates interactive HTML dashboard
├── requirements.txt            # Python dependencies
├── src/
│   ├── ingestion.py            # Bronze Layer: USGS API fetcher & Parquet writer
│   ├── transformation.py       # Silver Layer: DuckDB Spatial SQL & PHT conversion
│   ├── analytics.py            # Gold Layer: Star Schema facts & alert data marts
│   └── quality.py              # Data Quality Test Suite (8 assertions)
└── data/                       # Local data storage (Git ignored)
    ├── bronze/                 # Raw Parquet files partitioned by date
    └── warehouse.duckdb        # Embedded DuckDB Analytical Database
```

---

## 🚀 Quickstart Guide

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/<your-username>/ph-seismic-data-pipeline.git
cd ph-seismic-data-pipeline
pip install -r requirements.txt
```

### 2. Run the Data Pipeline

Execute the pipeline end-to-end to fetch live seismic events, perform spatial transformations, run data quality assertions, and output the terminal bulletin:

```bash
python main.py
```

### 3. Generate Visual Dashboard

Generate the interactive visual dashboard:

```bash
python generate_dashboard_html.py
```

Open `C:\Users\marki\.gemini\antigravity\brain\3f02062b-df98-4788-a2f8-8ca1213a27ef\seismic_dashboard.html` in any browser to inspect the interactive map and metrics.

---

## 🧪 Data Quality Assertion Suite

The pipeline runs 8 automated assertions before updating the warehouse:
1. `[PASS]` Uniqueness check on `silver.earthquakes_with_nearest_city.usgs_event_id`
2. `[PASS]` Non-NULL check on `usgs_event_id`
3. `[PASS]` Non-NULL check on `nearest_ph_city`
4. `[PASS]` Philippine Geospatial Bounding Box check ($4.0^\circ\text{N} \le \text{lat} \le 22.0^\circ\text{N}, 115.0^\circ\text{E} \le \text{lon} \le 128.0^\circ\text{E}$)
5. `[PASS]` Richter Magnitude sanity check ($0.0 \le M \le 10.0$)
6. `[PASS]` Uniqueness check on `gold.fact_earthquakes.usgs_event_id`
7. `[PASS]` Uniqueness check on `gold.dim_ph_cities.city_name`
8. `[PASS]` Non-NULL check on `gold.fact_earthquakes.event_time_pht`

---

## 📜 License
This project is open-source under the MIT License.
