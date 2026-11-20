import os
import sys
import json
import duckdb
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DB_PATH = os.path.join(BASE_DIR, "data", "el_nino_warehouse.duckdb")
JSON_PATH = os.path.join(BASE_DIR, "el_nino_dashboard_data.json")
OUTPUT_HTML = os.path.join(BASE_DIR, "el_nino_dashboard.html")
ARTIFACT_DIR = r"C:\Users\marki\.gemini\antigravity\brain\3f02062b-df98-4788-a2f8-8ca1213a27ef"
ARTIFACT_HTML = os.path.join(ARTIFACT_DIR, "el_nino_dashboard.html")

def build_el_nino_dashboard():
    """Generates the interactive Super El Niño & Drought Tracker Dashboard HTML."""
    con = duckdb.connect(DB_PATH)
    
    # 1. Fetch Latest Global ENSO Status
    latest_enso = con.execute("""
        SELECT year_month, nino34_sst_c, nino34_anomaly_c, enso_phase
        FROM gold.fact_enso_monthly
        ORDER BY year_month DESC
        LIMIT 1
    """).fetchone()
    
    enso_data = {
        "year_month": latest_enso[0],
        "nino34_sst": latest_enso[1],
        "nino34_anom": latest_enso[2],
        "phase": latest_enso[3]
    }
    
    # 2. Fetch Regional Bulletin Data
    bulletin_rows = con.execute("""
        SELECT 
            region_id,
            region_name,
            country,
            latitude,
            longitude,
            economic_role,
            critical_infrastructure,
            strftime(as_of_date, '%Y-%m-%d') AS as_of_date,
            current_tmax_c,
            consecutive_dry_days,
            rolling_30d_precip_mm,
            baseline_monthly_rain_mm,
            precip_deficit_pct,
            current_rootzone_moisture,
            soil_moisture_depletion_pct,
            rolling_30d_extreme_heat_days,
            drought_severity_index,
            drought_tier
        FROM gold.dm_super_el_nino_bulletin
        ORDER BY drought_severity_index DESC
    """).fetchdf().to_dict(orient='records')
    
    con.close()
    
    payload = {
        "enso": enso_data,
        "bulletin": bulletin_rows
    }
    
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        
    bulletin_json = json.dumps(bulletin_rows)
    
    # Summary KPIs
    total_regions = len(bulletin_rows)
    avg_sedi = round(sum(r['drought_severity_index'] for r in bulletin_rows) / total_regions, 1) if total_regions > 0 else 0
    max_cdd = max(r['consecutive_dry_days'] for r in bulletin_rows) if total_regions > 0 else 0
    top_stressed = bulletin_rows[0] if bulletin_rows else {"region_name": "N/A", "country": "N/A", "drought_severity_index": 0}
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Southeast Asia Super El Niño & Drought Tracker</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    body {{
      font-family: system-ui, -apple-system, sans-serif;
    }}
    .sea-map-container {{
      background: radial-gradient(circle at 50% 50%, rgba(15, 23, 42, 0.8), rgba(2, 6, 23, 0.98));
    }}
  </style>
</head>
<body class="bg-transparent text-[var(--foreground)] antialiased p-4">
  <div class="max-w-7xl mx-auto space-y-6">
    
    <!-- Header -->
    <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-2xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <div class="flex items-center gap-2">
          <span class="inline-block w-3.5 h-3.5 rounded-full bg-amber-500 animate-pulse"></span>
          <h1 class="text-2xl font-bold tracking-tight">Southeast Asia Super El Niño & Drought Tracker</h1>
        </div>
        <p class="text-sm text-[var(--muted-foreground)] mt-1">NOAA ERSST Niño 3.4 Oceanic Index • Open-Meteo Regional Soil & Climate Feed • DuckDB Analytical Engine</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span class="px-3 py-1 bg-red-500/20 border border-red-500/40 text-red-400 rounded-full text-xs font-bold tracking-wide">
          {enso_data['phase'].upper()} (+{enso_data['nino34_anom']:.2f}°C)
        </span>
        <span class="px-3 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded-full text-xs font-semibold">
          12 Core SEA Basins
        </span>
      </div>
    </div>

    <!-- ENSO Oceanic Gauge & Ground Drought Metrics -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <!-- Thermometer Card -->
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm flex flex-col justify-between">
        <div>
          <div class="text-xs font-medium text-[var(--muted-foreground)]">Niño 3.4 SST Anomaly</div>
          <div class="text-2xl font-bold mt-1 text-red-400">+{enso_data['nino34_anom']:.2f}°C</div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">Threshold: ≥ +2.0°C (Super El Niño)</div>
        </div>
        <div class="w-full bg-slate-800 rounded-full h-2 mt-3 overflow-hidden">
          <div class="bg-gradient-to-r from-blue-500 via-amber-500 to-red-500 h-2 rounded-full" style="width: {min(100, int((enso_data['nino34_anom'] / 3.5) * 100))}%"></div>
        </div>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
        <div class="text-xs font-medium text-[var(--muted-foreground)]">Average SEA Drought Index</div>
        <div class="text-2xl font-bold mt-1 text-amber-400">{avg_sedi} <span class="text-sm font-normal text-[var(--muted-foreground)]">/ 100</span></div>
        <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">Composite SEDI (Soil + Rain + Dry Days)</div>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
        <div class="text-xs font-medium text-[var(--muted-foreground)]">Highest Stress Basin</div>
        <div class="text-lg font-bold mt-1 text-rose-400 truncate" title="{top_stressed['region_name']}">{top_stressed['region_name']}</div>
        <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">{top_stressed['country']} • Score: {top_stressed['drought_severity_index']}/100</div>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
        <div class="text-xs font-medium text-[var(--muted-foreground)]">Max Consecutive Dry Days</div>
        <div class="text-2xl font-bold mt-1 text-indigo-400">{max_cdd} days</div>
        <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">Continuous days with rain &lt; 1mm</div>
      </div>

      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
        <div class="text-xs font-medium text-[var(--muted-foreground)]">Monitored Nations</div>
        <div class="text-2xl font-bold mt-1 text-emerald-400">5 Countries</div>
        <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">PH, ID, VN, TH, MY</div>
      </div>
    </div>

    <!-- Main Grid: SEA Drought Map & Regional Vulnerability Ranking -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Interactive SVG Map of Southeast Asia -->
      <div class="lg:col-span-2 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm flex flex-col">
        <div class="flex justify-between items-center mb-3">
          <div>
            <h2 class="font-semibold text-base">Southeast Asian Drought & Soil Moisture Map</h2>
            <p class="text-xs text-[var(--muted-foreground)]">Coordinates: 10°S–22°N, 95°E–130°E • Circles scaled by Drought Severity Index (SEDI)</p>
          </div>
          <div class="flex gap-2 text-[11px]">
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-red-500"></span> Crisis (≥80)</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span> Mod/Severe (45-79)</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span> Normal (&lt;45)</span>
          </div>
        </div>

        <div class="sea-map-container relative w-full h-[430px] rounded-xl border border-[var(--border)] overflow-hidden flex items-center justify-center p-2">
          <svg id="sea-map-svg" viewBox="0 0 800 500" class="w-full h-full max-h-[410px]">
            <!-- Rough Landmass outlines for SEA region -->
            <!-- Indochina / Thailand / Vietnam -->
            <path d="M 120,40 L 220,50 L 250,150 L 240,240 L 190,260 L 160,200 L 130,120 Z" fill="rgba(71, 85, 105, 0.25)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.2"/>
            <!-- Malay Peninsula -->
            <path d="M 190,260 L 220,330 L 210,360 L 180,310 Z" fill="rgba(71, 85, 105, 0.25)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.2"/>
            <!-- Sumatra -->
            <path d="M 170,330 L 290,430 L 260,450 L 150,360 Z" fill="rgba(71, 85, 105, 0.25)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.2"/>
            <!-- Borneo / Kalimantan -->
            <path d="M 330,260 L 440,270 L 460,360 L 360,370 L 320,310 Z" fill="rgba(71, 85, 105, 0.25)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.2"/>
            <!-- Java -->
            <path d="M 270,450 L 450,470 L 440,490 L 260,470 Z" fill="rgba(71, 85, 105, 0.25)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.2"/>
            <!-- Philippines -->
            <path d="M 520,100 L 580,120 L 610,210 L 590,260 L 530,230 Z" fill="rgba(71, 85, 105, 0.25)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.2"/>
            <path d="M 560,260 L 640,320 L 590,370 L 530,320 Z" fill="rgba(71, 85, 105, 0.25)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.2"/>
            
            <g id="map-nodes-group"></g>
          </svg>
          <div id="map-tooltip" class="absolute pointer-events-none bg-slate-900/95 text-white border border-slate-700 text-xs rounded-xl p-3 shadow-xl hidden z-20 max-w-xs"></div>
        </div>
      </div>

      <!-- Regional Vulnerability Ranking -->
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm flex flex-col justify-between">
        <div>
          <h2 class="font-semibold text-base mb-1">Drought Vulnerability Index</h2>
          <p class="text-xs text-[var(--muted-foreground)] mb-3">Ranked by Composite SEDI Score (0 to 100)</p>
          
          <div class="space-y-2.5 overflow-y-auto max-h-[350px] pr-1" id="ranking-list">
          </div>
        </div>
        <div class="pt-3 border-t border-[var(--border)] mt-3 text-[11px] text-[var(--muted-foreground)] flex justify-between">
          <span>Engine: DuckDB Rolling Window</span>
          <span>Baseline: 30-Day Monthly Norm</span>
        </div>
      </div>
    </div>

    <!-- Live Regional Drought Bulletin Table -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
        <div>
          <h2 class="font-semibold text-base">Regional Hydrological & Agricultural Bulletin (Gold Layer)</h2>
          <p class="text-xs text-[var(--muted-foreground)]">30-Day Cumulative Precipitation, Deficits %, Soil Moisture, and Alert Levels</p>
        </div>
        
        <div class="flex gap-2">
          <input type="text" id="search-input" placeholder="Search region or country..." class="bg-[var(--background)] border border-[var(--border)] text-xs rounded-lg px-3 py-2 text-[var(--foreground)] outline-none focus:border-blue-500 w-48">
          <select id="filter-tier" class="bg-[var(--background)] border border-[var(--border)] text-xs rounded-lg px-3 py-2 text-[var(--foreground)] outline-none">
            <option value="ALL">All Drought Tiers</option>
            <option value="DROUGHT">Drought / Watch</option>
            <option value="NORMAL">Normal</option>
          </select>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs text-[var(--foreground)] border-collapse">
          <thead>
            <tr class="border-b border-[var(--border)] text-[var(--muted-foreground)] font-semibold">
              <th class="p-3">Region & Country</th>
              <th class="p-3">Economic Role & Infrastructure</th>
              <th class="p-3">30d Rain (Obs / Base)</th>
              <th class="p-3">Rain Deficit %</th>
              <th class="p-3">Dry Days (CDD)</th>
              <th class="p-3">Rootzone Moisture</th>
              <th class="p-3">SEDI Score</th>
              <th class="p-3">Drought Alert Status</th>
            </tr>
          </thead>
          <tbody id="bulletin-table-body" class="divide-y divide-[var(--border)]">
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const bulletin = {bulletin_json};

    // Geospatial Mapping:
    // Longitude: 95°E to 130°E -> SVG X: 60 to 740
    // Latitude: -10°S to 22°N -> SVG Y: 460 to 40
    function lonToX(lon) {{
      return 60 + ((lon - 95.0) / (130.0 - 95.0)) * 680;
    }}
    function latToY(lat) {{
      return 460 - ((lat - (-10.0)) / (22.0 - (-10.0))) * 420;
    }}

    const nodesGroup = document.getElementById("map-nodes-group");
    const tooltip = document.getElementById("map-tooltip");

    bulletin.forEach(b => {{
      const cx = lonToX(b.longitude);
      const cy = latToY(b.latitude);
      const radius = Math.max(7, (b.drought_severity_index / 100) * 18);

      let color = "#10b981"; // Emerald
      if (b.drought_severity_index >= 65) color = "#ef4444"; // Red
      else if (b.drought_severity_index >= 45) color = "#f59e0b"; // Amber
      else if (b.drought_severity_index >= 25) color = "#3b82f6"; // Blue

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", cx);
      circle.setAttribute("cy", cy);
      circle.setAttribute("r", radius);
      circle.setAttribute("fill", color + "cc");
      circle.setAttribute("stroke", color);
      circle.setAttribute("stroke-width", "2");
      circle.setAttribute("class", "cursor-pointer hover:scale-125 transition-transform");

      circle.addEventListener("mouseenter", (e) => {{
        tooltip.style.display = "block";
        tooltip.innerHTML = `
          <div class="font-bold text-sm text-white">${{b.region_name}} (${{b.country}})</div>
          <div class="text-[11px] text-slate-300 mt-1">${{b.economic_role}}</div>
          <div class="mt-2 pt-2 border-t border-slate-700 space-y-1 text-[11px]">
            <div>Drought Index (SEDI): <strong class="text-amber-400">${{b.drought_severity_index}}/100</strong> (${{b.drought_tier}})</div>
            <div>Rain Deficit: <strong>${{b.precip_deficit_pct}}%</strong> (${{b.rolling_30d_precip_mm}}mm vs ${{b.baseline_monthly_rain_mm}}mm)</div>
            <div>Consecutive Dry Days: <strong>${{b.consecutive_dry_days}} days</strong></div>
            <div>Rootzone Soil Moisture: <strong>${{b.current_rootzone_moisture}} m³/m³</strong> (Depleted: ${{b.soil_moisture_depletion_pct}}%)</div>
          </div>
        `;
      }});
      circle.addEventListener("mousemove", (e) => {{
        tooltip.style.left = (e.clientX + 15) + "px";
        tooltip.style.top = (e.clientY + 15) + "px";
      }});
      circle.addEventListener("mouseleave", () => {{
        tooltip.style.display = "none";
      }});

      nodesGroup.appendChild(circle);

      // Node label
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", cx + radius + 4);
      text.setAttribute("y", cy + 4);
      text.setAttribute("fill", "#cbd5e1");
      text.setAttribute("font-size", "10px");
      text.setAttribute("font-weight", "600");
      text.textContent = b.region_name.split(" ")[0];
      nodesGroup.appendChild(text);
    }});

    // Populate Ranking List
    const rankingListEl = document.getElementById("ranking-list");
    bulletin.forEach((b, idx) => {{
      const div = document.createElement("div");
      div.className = "p-2.5 rounded-xl bg-[var(--background)] border border-[var(--border)] flex justify-between items-center";
      
      let badgeColor = "text-emerald-400";
      if (b.drought_severity_index >= 65) badgeColor = "text-red-400";
      else if (b.drought_severity_index >= 45) badgeColor = "text-amber-400";

      div.innerHTML = `
        <div class="truncate pr-2">
          <div class="font-semibold text-xs text-[var(--foreground)] truncate">${{idx + 1}}. ${{b.region_name}} <span class="text-[10px] text-[var(--muted-foreground)]">(${{b.country}})</span></div>
          <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">Deficit: <span class="font-medium text-slate-300">${{b.precip_deficit_pct}}%</span> • Dry Days: <span class="font-medium text-slate-300">${{b.consecutive_dry_days}}d</span></div>
        </div>
        <div class="text-right flex-shrink-0">
          <div class="text-xs font-bold ${{badgeColor}}">${{b.drought_severity_index}}</div>
          <div class="text-[9px] text-[var(--muted-foreground)]">${{b.drought_tier.split(" ")[0]}}</div>
        </div>
      `;
      rankingListEl.appendChild(div);
    }});

    // Populate Table
    const tableBody = document.getElementById("bulletin-table-body");
    function renderTable(filterTier = "ALL", search = "") {{
      tableBody.innerHTML = "";
      const filtered = bulletin.filter(b => {{
        const matchTier = filterTier === "ALL" || 
          (filterTier === "DROUGHT" && !b.drought_tier.includes("NORMAL")) ||
          (filterTier === "NORMAL" && b.drought_tier.includes("NORMAL"));
        const matchSearch = search === "" || 
          b.region_name.toLowerCase().includes(search.toLowerCase()) || 
          b.country.toLowerCase().includes(search.toLowerCase()) ||
          b.economic_role.toLowerCase().includes(search.toLowerCase());
        return matchTier && matchSearch;
      }});

      filtered.forEach(b => {{
        const tr = document.createElement("tr");
        tr.className = "hover:bg-white/5 transition-colors";
        
        let statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-300 font-semibold border border-emerald-500/20">NORMAL</span>';
        if (b.drought_tier.includes("CRISIS") || b.drought_tier.includes("SEVERE")) {{
          statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-red-500/20 text-red-300 font-bold border border-red-500/30">${{b.drought_tier}}</span>`;
        }} else if (b.drought_tier.includes("MODERATE") || b.drought_tier.includes("WATCH")) {{
          statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30">${{b.drought_tier}}</span>`;
        }}

        tr.innerHTML = `
          <td class="p-3 whitespace-nowrap">
            <div class="font-bold text-xs text-[var(--foreground)]">${{b.region_name}}</div>
            <div class="text-[10px] text-[var(--muted-foreground)]">${{b.country}}</div>
          </td>
          <td class="p-3 max-w-xs">
            <div class="text-xs text-slate-300 truncate" title="${{b.economic_role}}">${{b.economic_role}}</div>
            <div class="text-[10px] text-[var(--muted-foreground)] truncate" title="${{b.critical_infrastructure}}">Infra: ${{b.critical_infrastructure}}</div>
          </td>
          <td class="p-3 text-slate-300 font-mono">${{b.rolling_30d_precip_mm}} / ${{b.baseline_monthly_rain_mm}} mm</td>
          <td class="p-3 font-bold ${{b.precip_deficit_pct > 50 ? 'text-rose-400' : 'text-slate-300'}}">${{b.precip_deficit_pct}}%</td>
          <td class="p-3 font-semibold text-slate-300">${{b.consecutive_dry_days}} days</td>
          <td class="p-3 font-mono text-[var(--muted-foreground)]">${{b.current_rootzone_moisture}} m³/m³</td>
          <td class="p-3 font-bold text-amber-400 text-sm">${{b.drought_severity_index}}</td>
          <td class="p-3">${{statusBadge}}</td>
        `;
        tableBody.appendChild(tr);
      }});
    }}

    renderTable();

    document.getElementById("filter-tier").addEventListener("change", (e) => {{
      renderTable(e.target.value, document.getElementById("search-input").value);
    }});
    document.getElementById("search-input").addEventListener("input", (e) => {{
      renderTable(document.getElementById("filter-tier").value, e.target.value);
    }});
  </script>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    shutil.copyfile(OUTPUT_HTML, ARTIFACT_HTML)

    print(f"  + Generated Super El Niño Dashboard at {OUTPUT_HTML}")
    print(f"  + Synced to conversation artifact at {ARTIFACT_HTML}")

if __name__ == "__main__":
    build_el_nino_dashboard()
