import os
import duckdb
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import accuracy_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "warehouse.duckdb")

def run_data_science():
    """Performs Exploratory Data Analysis, Spatial Fault Line Clustering, and ML Risk Prediction."""
    print("[DATA SCIENCE] Starting Exploratory Analysis & Machine Learning Engine...")
    
    con = duckdb.connect(DB_PATH)
    
    # Load Fact Data
    df = con.execute("""
        SELECT usgs_event_id, event_time_pht, place, magnitude, depth_km, latitude, longitude, nearest_reference_city, island_group, distance_to_reference_city_km, oceanic_event
        FROM gold.fact_earthquakes
    """).fetchdf()
    
    if len(df) == 0:
        print("  [WARN] No data available for Data Science module.")
        con.close()
        return
        
    # ---------------------------------------------------------
    # 1. EXPLORATORY DATA ANALYSIS (EDA) & STATISTICAL PROFILING
    # ---------------------------------------------------------
    corr_depth_mag = df['depth_km'].corr(df['magnitude']) if 'depth_km' in df and len(df) > 1 else 0.0
    avg_mag = df['magnitude'].mean()
    max_mag = df['magnitude'].max()
    
    print("  + Statistical EDA Profile:")
    print(f"    - Pearson Correlation (Depth vs Magnitude): {corr_depth_mag:.3f}")
    print(f"    - Average Richter Magnitude across PH: M {avg_mag:.2f} (Max: M {max_mag:.1f})")
    
    # Regional Group Breakdown
    regional_summary = df.groupby('island_group').agg(
        total_events=('usgs_event_id', 'count'),
        avg_magnitude=('magnitude', 'mean'),
        max_magnitude=('magnitude', 'max')
    ).reset_index()
    
    con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    con.execute("""
    CREATE OR REPLACE TABLE gold.ds_regional_eda AS
    SELECT * FROM regional_summary;
    """)
    
    # ---------------------------------------------------------
    # 2. SPATIAL FAULT LINE CLUSTERING (DBSCAN)
    # ---------------------------------------------------------
    coords = df[['latitude', 'longitude']].values
    db = DBSCAN(eps=1.2, min_samples=2).fit(coords)
    df['fault_cluster_id'] = db.labels_
    
    con.execute("""
    CREATE OR REPLACE TABLE gold.ds_seismic_clusters AS
    SELECT 
        usgs_event_id,
        latitude,
        longitude,
        magnitude,
        fault_cluster_id,
        CASE 
            WHEN fault_cluster_id = -1 THEN 'Isolated Seismic Event'
            ELSE 'PH Active Fault Zone #' || CAST(fault_cluster_id + 1 AS VARCHAR)
        END AS fault_zone_label
    FROM df;
    """)
    num_clusters = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
    print(f"  + Spatial Clustering (DBSCAN): Identified {num_clusters} active seismic fault clusters in PH.")
    
    # ---------------------------------------------------------
    # 3. PREDICTIVE MACHINE LEARNING (Random Forest Risk Classifier)
    # ---------------------------------------------------------
    df['is_high_risk'] = (df['magnitude'] >= 4.5).astype(int)
    X = df[['latitude', 'longitude', 'depth_km', 'distance_to_reference_city_km']].fillna(0)
    y = df['is_high_risk']
    
    if len(df) >= 5 and len(y.unique()) > 1:
        rf_model = RandomForestClassifier(n_estimators=50, random_state=42)
        rf_model.fit(X, y)
        
        preds = rf_model.predict(X)
        probs = rf_model.predict_proba(X)[:, 1]
        acc = accuracy_score(y, preds)
        
        df['ml_predicted_high_risk'] = preds
        df['ml_risk_probability'] = np.round(probs * 100.0, 1)
        
        importances = dict(zip(X.columns, np.round(rf_model.feature_importances_, 3)))
        print(f"  + Predictive ML Model (Random Forest Classifier):")
        print(f"    - Training Accuracy: {acc * 100.0:.1f}%")
        print(f"    - Feature Importances: {importances}")
    else:
        df['ml_predicted_high_risk'] = df['is_high_risk']
        df['ml_risk_probability'] = np.where(df['is_high_risk'] == 1, 90.0, 10.0)
        acc = 1.0

    # 4. ANOMALY DETECTION (Isolation Forest)
    iso_forest = IsolationForest(contamination=0.1, random_state=42)
    df['is_seismic_anomaly'] = iso_forest.fit_predict(X[['depth_km', 'latitude', 'longitude']])
    df['anomaly_flag'] = np.where(df['is_seismic_anomaly'] == -1, 'SEISMIC OUTLIER', 'NORMAL')
    
    con.execute("""
    CREATE OR REPLACE TABLE gold.ds_ml_predictions AS
    SELECT 
        usgs_event_id,
        magnitude,
        is_high_risk AS actual_high_risk,
        ml_predicted_high_risk,
        ml_risk_probability,
        anomaly_flag,
        fault_cluster_id
    FROM df;
    """)
    
    con.close()
    print("[OK] Data Science & Machine Learning Pipeline Complete.\n")

if __name__ == "__main__":
    run_data_science()
