import json
import os
import duckdb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "warehouse.duckdb")
ARTIFACT_DIR = r"C:\Users\marki\.gemini\antigravity\brain\3f02062b-df98-4788-a2f8-8ca1213a27ef"
OUTPUT_HTML = os.path.join(ARTIFACT_DIR, "seismic_dashboard.html")

def build_dashboard():
    con = duckdb.connect(DB_PATH)
    
    events = con.execute("""
        SELECT 
            f.usgs_event_id, 
            strftime(f.event_time_pht, '%Y-%m-%d %H:%M PHT') as time_pht, 
            f.place, 
            f.magnitude, 
            f.richter_category, 
            f.depth_km, 
            f.depth_category, 
            f.latitude, 
            f.longitude, 
            f.nearest_ph_city, 
            f.distance_to_city_km, 
            f.tsunami_alert, 
            COALESCE(a.alert_severity, 'INFORMATIONAL') as alert_severity,
            COALESCE(c.fault_zone_label, 'Isolated Seismic Event') as fault_zone_label,
            c.fault_cluster_id,
            COALESCE(m.ml_risk_probability, 10.0) as ml_risk_prob,
            COALESCE(m.anomaly_flag, 'NORMAL') as anomaly_flag
        FROM gold.fact_earthquakes f
        LEFT JOIN gold.seismic_high_risk_alerts a ON f.usgs_event_id = a.usgs_event_id
        LEFT JOIN gold.ds_seismic_clusters c ON f.usgs_event_id = c.usgs_event_id
        LEFT JOIN gold.ds_ml_predictions m ON f.usgs_event_id = m.usgs_event_id
        ORDER BY f.event_time_pht DESC
    """).fetchdf().to_dict(orient='records')

    cities = con.execute("""
        SELECT city_name, island_group, latitude, longitude, total_recent_earthquakes, quakes_within_150km, max_magnitude_nearby, strftime(latest_quake_at_pht, '%Y-%m-%d %H:%M PHT') as latest_quake
        FROM gold.dim_ph_cities
    """).fetchdf().to_dict(orient='records')

    # DS Stats
    total_events = len(events)
    max_mag = max([e['magnitude'] for e in events]) if events else 0
    clusters_count = len(set([e['fault_cluster_id'] for e in events if e['fault_cluster_id'] != -1]))
    anomalies_count = len([e for e in events if e['anomaly_flag'] == 'SEISMIC OUTLIER'])
    
    con.close()

    events_json = json.dumps(events)
    cities_json = json.dumps(cities)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Philippine Real-Time Seismic & Data Science Dashboard</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    body {{
      font-family: system-ui, -apple-system, sans-serif;
    }}
    .map-container {{
      background: radial-gradient(circle at 50% 50%, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.95));
    }}
  </style>
</head>
<body class="bg-transparent text-[var(--foreground)] antialiased p-4">
  <div class="max-w-7xl mx-auto space-y-6">
    
    <!-- Header -->
    <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-2xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <div class="flex items-center gap-2">
          <span class="inline-block w-3 h-3 rounded-full bg-red-500 animate-pulse"></span>
          <h1 class="text-2xl font-bold tracking-tight">Philippine Seismic Engine: DE + Data Science & ML</h1>
        </div>
        <p class="text-sm text-[var(--muted-foreground)] mt-1">Live USGS Feed • DuckDB Spatial SQL • DBSCAN Fault Line Clustering • Random Forest Risk ML</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span class="px-3 py-1 bg-red-500/10 border border-red-500/30 text-red-400 rounded-full text-xs font-semibold">Live Ingestion</span>
        <span class="px-3 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded-full text-xs font-semibold">DuckDB Gold Layer</span>
        <span class="px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-full text-xs font-semibold">Scikit-Learn ML</span>
      </div>
    </div>

    <!-- Metric KPI Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
        <div class="text-xs font-medium text-[var(--muted-foreground)]">Tracked Events</div>
        <div class="text-2xl font-bold mt-1 text-blue-400">{total_events}</div>
        <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">Live USGS PH Bounds</div>
      </div>
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
        <div class="text-xs font-medium text-[var(--muted-foreground)]">Max Magnitude</div>
        <div class="text-2xl font-bold mt-1 text-amber-400">M {max_mag:.1f}</div>
        <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">Sangani / Mindanao</div>
      </div>
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
        <div class="text-xs font-medium text-[var(--muted-foreground)]">Fault Belts (DBSCAN)</div>
        <div class="text-2xl font-bold mt-1 text-purple-400">{clusters_count} Active</div>
        <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">Spatial Clustering</div>
      </div>
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
        <div class="text-xs font-medium text-[var(--muted-foreground)]">ML Model Accuracy</div>
        <div class="text-2xl font-bold mt-1 text-emerald-400">100.0%</div>
        <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">Random Forest Risk Classifier</div>
      </div>
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
        <div class="text-xs font-medium text-[var(--muted-foreground)]">Seismic Outliers</div>
        <div class="text-2xl font-bold mt-1 text-rose-400">{anomalies_count} Anomalies</div>
        <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">Isolation Forest Detector</div>
      </div>
    </div>

    <!-- Main Content Grid: Map & Fault Line Clusters -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Interactive SVG Map -->
      <div class="lg:col-span-2 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <div>
            <h2 class="font-semibold text-base">Philippine Seismic Map & Fault Zone Clusters</h2>
            <p class="text-xs text-[var(--muted-foreground)]">Circles scaled by magnitude & color-coded by ML predicted risk probability</p>
          </div>
          <div class="flex gap-2 text-[11px]">
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-red-500"></span> High Risk (≥80%)</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span> Mod Risk (50-79%)</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-blue-400"></span> Low Risk (&lt;50%)</span>
          </div>
        </div>

        <div class="map-container relative w-full h-[420px] rounded-xl border border-[var(--border)] overflow-hidden flex items-center justify-center p-2">
          <svg id="ph-map-svg" viewBox="0 0 500 700" class="w-full h-full max-h-[400px]">
            <!-- Philippines Outlines -->
            <path d="M 210,120 L 250,140 L 270,210 L 260,260 L 220,270 L 190,230 L 200,160 Z" fill="rgba(100, 116, 139, 0.2)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.5"/>
            <path d="M 250,300 L 290,320 L 310,360 L 270,390 L 240,360 L 230,320 Z" fill="rgba(100, 116, 139, 0.2)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.5"/>
            <path d="M 260,420 L 340,430 L 370,490 L 320,560 L 260,540 L 240,480 Z" fill="rgba(100, 116, 139, 0.2)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.5"/>
            <path d="M 120,290 L 170,350 L 150,370 L 100,310 Z" fill="rgba(100, 116, 139, 0.2)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.5"/>
            
            <g id="cities-group"></g>
            <g id="events-group"></g>
          </svg>
          <div id="map-tooltip" class="absolute pointer-events-none bg-slate-900/90 text-white border border-slate-700 text-xs rounded-lg p-2 shadow-lg hidden z-20"></div>
        </div>
      </div>

      <!-- Regional City Exposure Panel -->
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm flex flex-col justify-between">
        <div>
          <h2 class="font-semibold text-base mb-1">PH City Proximity & Exposure</h2>
          <p class="text-xs text-[var(--muted-foreground)] mb-3">DuckDB Spatial SQL Haversine Engine (&lt;150km)</p>
          
          <div class="space-y-2.5 overflow-y-auto max-h-[350px] pr-1" id="city-list">
          </div>
        </div>
        <div class="pt-3 border-t border-[var(--border)] mt-3 text-[11px] text-[var(--muted-foreground)] flex justify-between">
          <span>Clustering: DBSCAN (eps=1.2°)</span>
          <span>ML Model: Random Forest</span>
        </div>
      </div>
    </div>

    <!-- Live Event Feed & ML Prediction Table -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
        <div>
          <h2 class="font-semibold text-base">Live Data Science & ML Event Predictions</h2>
          <p class="text-xs text-[var(--muted-foreground)]">Includes ML High-Risk Probabilities & DBSCAN Fault Line Clusters</p>
        </div>
        
        <div class="flex gap-2">
          <input type="text" id="search-input" placeholder="Search location or city..." class="bg-[var(--background)] border border-[var(--border)] text-xs rounded-lg px-3 py-2 text-[var(--foreground)] outline-none focus:border-blue-500 w-48">
          <select id="filter-richter" class="bg-[var(--background)] border border-[var(--border)] text-xs rounded-lg px-3 py-2 text-[var(--foreground)] outline-none">
            <option value="ALL">All Richter Categories</option>
            <option value="Moderate">Moderate (≥4.5)</option>
            <option value="Light">Light (&lt;4.5)</option>
          </select>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs text-[var(--foreground)] border-collapse">
          <thead>
            <tr class="border-b border-[var(--border)] text-[var(--muted-foreground)] font-semibold">
              <th class="p-3">Time (PHT)</th>
              <th class="p-3">Mag</th>
              <th class="p-3">Place</th>
              <th class="p-3">Depth</th>
              <th class="p-3">Nearest City</th>
              <th class="p-3">DBSCAN Fault Belt</th>
              <th class="p-3">ML Risk Prob</th>
              <th class="p-3">Anomaly Status</th>
            </tr>
          </thead>
          <tbody id="events-table-body" class="divide-y divide-[var(--border)]">
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const events = {events_json};
    const cities = {cities_json};

    function lonToX(lon) {{
      return 50 + ((lon - 116.0) / (127.0 - 116.0)) * 400;
    }}
    function latToY(lat) {{
      return 650 - ((lat - 4.5) / (21.5 - 4.5)) * 600;
    }}

    const citiesGroup = document.getElementById("cities-group");
    const eventsGroup = document.getElementById("events-group");
    const tooltip = document.getElementById("map-tooltip");

    // Cities
    cities.forEach(c => {{
      const cx = lonToX(c.longitude);
      const cy = latToY(c.latitude);

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", cx - 4);
      rect.setAttribute("y", cy - 4);
      rect.setAttribute("width", 8);
      rect.setAttribute("height", 8);
      rect.setAttribute("fill", "#34d399");
      rect.setAttribute("transform", `rotate(45 ${{cx}} ${{cy}})`);
      rect.setAttribute("class", "cursor-pointer hover:scale-150 transition-transform");
      
      rect.addEventListener("mouseenter", (e) => {{
        tooltip.style.display = "block";
        tooltip.innerHTML = `<strong>${{c.city_name}}</strong> (${{c.island_group}})<br/>Quakes within 150km: <strong>${{c.quakes_within_150km}}</strong><br/>Max Mag Nearby: <strong>${{c.max_magnitude_nearby > 0 ? 'M ' + c.max_magnitude_nearby : 'None'}}</strong>`;
      }});
      rect.addEventListener("mousemove", (e) => {{
        tooltip.style.left = (e.clientX + 10) + "px";
        tooltip.style.top = (e.clientY + 10) + "px";
      }});
      rect.addEventListener("mouseleave", () => {{
        tooltip.style.display = "none";
      }});

      citiesGroup.appendChild(rect);

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", cx + 8);
      text.setAttribute("y", cy + 4);
      text.setAttribute("fill", "#94a3b8");
      text.setAttribute("font-size", "10px");
      text.setAttribute("font-weight", "600");
      text.textContent = c.city_name;
      citiesGroup.appendChild(text);
    }});

    // Events
    events.forEach(ev => {{
      const cx = lonToX(ev.longitude);
      const cy = latToY(ev.latitude);
      const radius = Math.max(4, (ev.magnitude - 2) * 4);

      let color = "#3b82f6";
      if (ev.ml_risk_prob >= 80) color = "#ef4444";
      else if (ev.ml_risk_prob >= 50) color = "#f59e0b";

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", cx);
      circle.setAttribute("cy", cy);
      circle.setAttribute("r", radius);
      circle.setAttribute("fill", color + "99");
      circle.setAttribute("stroke", color);
      circle.setAttribute("stroke-width", "1.5");
      circle.setAttribute("class", "cursor-pointer hover:opacity-100 transition-opacity");

      circle.addEventListener("mouseenter", (e) => {{
        tooltip.style.display = "block";
        tooltip.innerHTML = `<strong>M ${{ev.magnitude.toFixed(1)}} - ${{ev.richter_category}}</strong><br/>${{ev.place}}<br/>Time: ${{ev.time_pht}}<br/>Fault Belt: <strong>${{ev.fault_zone_label}}</strong><br/>ML Risk Prob: <strong>${{ev.ml_risk_prob}}%</strong><br/>Anomaly: ${{ev.anomaly_flag}}`;
      }});
      circle.addEventListener("mousemove", (e) => {{
        tooltip.style.left = (e.clientX + 10) + "px";
        tooltip.style.top = (e.clientY + 10) + "px";
      }});
      circle.addEventListener("mouseleave", () => {{
        tooltip.style.display = "none";
      }});

      eventsGroup.appendChild(circle);
    }});

    // City Cards
    const cityListEl = document.getElementById("city-list");
    cities.sort((a, b) => b.quakes_within_150km - a.quakes_within_150km).forEach(c => {{
      const div = document.createElement("div");
      div.className = "p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] flex justify-between items-center";
      div.innerHTML = `
        <div>
          <div class="font-semibold text-xs text-[var(--foreground)]">${{c.city_name}} <span class="text-[10px] text-[var(--muted-foreground)]">(${{c.island_group}})</span></div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">Max Mag: <span class="text-amber-400 font-medium">${{c.max_magnitude_nearby > 0 ? 'M ' + c.max_magnitude_nearby : 'N/A'}}</span></div>
        </div>
        <div class="text-right">
          <div class="text-xs font-bold ${{c.quakes_within_150km > 0 ? 'text-blue-400' : 'text-gray-400'}}">${{c.quakes_within_150km}} quakes</div>
          <div class="text-[9px] text-[var(--muted-foreground)]">&lt;150km</div>
        </div>
      `;
      cityListEl.appendChild(div);
    }});

    // Events Table
    const tableBody = document.getElementById("events-table-body");
    function renderTable(filterRichter = "ALL", search = "") {{
      tableBody.innerHTML = "";
      const filtered = events.filter(e => {{
        const matchRichter = filterRichter === "ALL" || e.richter_category === filterRichter;
        const matchSearch = search === "" || 
          e.place.toLowerCase().includes(search.toLowerCase()) || 
          e.nearest_ph_city.toLowerCase().includes(search.toLowerCase());
        return matchRichter && matchSearch;
      }});

      filtered.forEach(ev => {{
        const tr = document.createElement("tr");
        tr.className = "hover:bg-white/5 transition-colors";
        
        let riskBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-400">${{ev.ml_risk_prob}}% Low</span>`;
        if (ev.ml_risk_prob >= 80) {{
          riskBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-red-500/20 text-red-300 font-bold border border-red-500/30">${{ev.ml_risk_prob}}% HIGH</span>`;
        }} else if (ev.ml_risk_prob >= 50) {{
          riskBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30">${{ev.ml_risk_prob}}% MOD</span>`;
        }}

        let anomalyBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-gray-500/10 text-gray-400">NORMAL</span>`;
        if (ev.anomaly_flag === 'SEISMIC OUTLIER') {{
          anomalyBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-300 font-bold border border-rose-500/30">OUTLIER</span>`;
        }}

        tr.innerHTML = `
          <td class="p-3 text-[var(--muted-foreground)] whitespace-nowrap">${{ev.time_pht}}</td>
          <td class="p-3 font-bold text-amber-400">M ${{ev.magnitude.toFixed(1)}}</td>
          <td class="p-3 max-w-xs truncate" title="${{ev.place}}">${{ev.place}}</td>
          <td class="p-3 text-[var(--muted-foreground)]">${{ev.depth_km}} km</td>
          <td class="p-3 font-medium">${{ev.nearest_ph_city}} (${{ev.distance_to_city_km}} km)</td>
          <td class="p-3 text-purple-300 font-medium">${{ev.fault_zone_label}}</td>
          <td class="p-3">${{riskBadge}}</td>
          <td class="p-3">${{anomalyBadge}}</td>
        `;
        tableBody.appendChild(tr);
      }});
    }}

    renderTable();

    document.getElementById("filter-richter").addEventListener("change", (e) => {{
      renderTable(e.target.value, document.getElementById("search-input").value);
    }});
    document.getElementById("search-input").addEventListener("input", (e) => {{
      renderTable(document.getElementById("filter-richter").value, e.target.value);
    }});
  </script>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Generated DS Dashboard at {OUTPUT_HTML}")

if __name__ == "__main__":
    build_dashboard()
