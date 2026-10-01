# 🇵🇭 Real-Time Philippine Seismic & Earthquake Data Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Spatial%20SQL-yellow.svg)](https://duckdb.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Medallion%20(Bronze%2FSilver%2FGold)-emerald.svg)](#architecture)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An end-to-end, production-grade **Medallion Architecture Data Pipeline** tracking real-time seismic events and earthquake activity across the **Philippine Archipelago** ($4.0^\circ\text{N} - 21.5^\circ\text{N}, 116.0^\circ\text{E} - 127.0^\circ\text{E}$).

Powered by **Python, DuckDB Spatial SQL, Parquet, Scikit-Learn Machine Learning, and Tailwind CSS**.

---

## 🏗️ Architecture Overview

```
[ USGS Live GeoJSON API (PH Bounding Box) ]
                    │
                    ▼  (Raw GeoJSON -> Partitioned Parquet)
      [ BRONZE LAYER: Raw Event Storage ]
                    │
                    ▼  (Bronze Data Quality Checks: Non-empty, Bounds, Non-Null, Future Time)
      [ SILVER LAYER: DuckDB Spatial SQL & PHT Timezone ]
                    │
                    ▼  (Nearest Reference City Distance, Richter & Depth Categorization)
      [ GOLD LAYER: Analytical Star Schema & Risk Marts ]
                    │
                    ▼  (DBSCAN Fault Line Clustering & Random Forest Risk Prediction)
      [ DATA SCIENCE ENGINE & DYNAMIC VISUAL DASHBOARD ]
```

---

## ✨ Key Features

* **Live Ingestion (Bronze Layer)**: Ingests real-time seismic events from USGS bounded to the Philippine coordinate region ($4.0^\circ\text{N} - 21.5^\circ\text{N}, 116.0^\circ\text{E} - 127.0^\circ\text{E}$).
* **Spatial & Time Transformations (Silver Layer)**:
  * Converts UTC timestamps to **Philippine Standard Time (PHT)** using `timezone('Asia/Manila', ...)`.
  * Calculates exact **Haversine spatial distances (km)** to 14 Philippine reference cities (Manila, Cebu City, Davao City, Baguio, Cagayan de Oro, Zamboanga City, Tacloban, General Santos, Legazpi, Naga, Puerto Princesa, Laoag, Calapan, Catbalogan).
  * Categorizes Richter scale magnitude severity and focal depth ranges without gap logic.
* **Analytical Data Warehouse (Gold Layer)**: Models `gold.fact_earthquakes`, `gold.dim_ph_cities`, and `gold.seismic_high_risk_alerts`.
* **Data Science & ML Module**:
  * Unsupervised spatial clustering (**DBSCAN**) mapping 4 active Philippine Fault Belts.
  * Supervised machine learning risk predictor (**Random Forest Classifier**).
  * Outlier detection via **Isolation Forest**.
* **Non-Tautological Quality & Unit Testing**: Bronze-layer assertions verified via automated unit test proofs in `tests/test_quality.py`.
* **Dynamic Visual Dashboard**: Self-contained HTML dashboard with SVG map plotting epicenters across Luzon, Visayas, Palawan, Mindoro, and Mindanao.

---

## 🛠️ Project Structure

```text
├── main.py                     # Main pipeline orchestrator & terminal bulletin reporter
├── generate_dashboard_html.py  # Dynamically exports dashboard_data.json & HTML dashboard
├── requirements.txt            # Python dependencies
├── src/
│   ├── ingestion.py            # Bronze Layer: USGS API fetcher & Parquet writer
│   ├── transformation.py       # Silver Layer: DuckDB Spatial SQL & PHT conversion
│   ├── analytics.py            # Gold Layer: Star Schema facts & alert data marts
│   ├── data_science.py         # Data Science Module: EDA, DBSCAN, Random Forest
│   └── quality.py              # Non-tautological Bronze Data Quality Suite
├── tests/
│   ├── test_quality.py         # Failure-proof unit test suite
│   └── test_timezone.py        # Timezone session consistency test
└── data/                       # Local data storage (Git ignored)
    ├── bronze/                 # Raw Parquet files partitioned by date
    └── warehouse.duckdb        # Embedded DuckDB Analytical Database
```

---

## 🚀 Quickstart Guide

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Unit Tests & Prove Quality Assertions

```bash
python tests/test_quality.py
python tests/test_timezone.py
```

### 3. Execute Full Pipeline & Update Dashboard

```bash
python main.py
```

Open `seismic_dashboard.html` in any browser to inspect the dynamic visual interface.

---

## 📜 License
This project is open-source under the MIT License.
