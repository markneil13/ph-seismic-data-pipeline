import os
import sys
import json
import duckdb
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino.sea_map_paths import SEA_COUNTRY_PATHS, SEA_MAP_CONFIG

DB_PATH = os.path.join(BASE_DIR, "data", "el_nino_warehouse.duckdb")
JSON_PATH = os.path.join(BASE_DIR, "el_nino_dashboard_data.json")
OUTPUT_HTML = os.path.join(BASE_DIR, "el_nino_dashboard.html")
ARTIFACT_DIR = r"C:\Users\marki\.gemini\antigravity\brain\3f02062b-df98-4788-a2f8-8ca1213a27ef"
ARTIFACT_HTML = os.path.join(ARTIFACT_DIR, "el_nino_dashboard.html")

def build_el_nino_dashboard():
    """Generates the interactive Super El Niño & Drought Tracker Dashboard with real geographical SVG coastlines."""
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

    # Generate Country SVG Paths HTML
    landmass_svg_elements = []
    for item in SEA_COUNTRY_PATHS:
        country = item['country']
        path_d = item['path_d']
        landmass_svg_elements.append(
            f'<path d="{path_d}" data-country="{country}" class="sea-landmass" '
            f'fill="rgba(51, 65, 85, 0.55)" stroke="rgba(148, 163, 184, 0.65)" stroke-width="1.1" '
            f'stroke-linejoin="round" />'
        )
    landmass_svg_str = "\n            ".join(landmass_svg_elements)

    # Graticules (lat/lon lines)
    cfg = SEA_MAP_CONFIG
    w, h = cfg['width'], cfg['height']
    pad_x, pad_y = cfg['pad_x'], cfg['pad_y']
    lon_min, lon_max = cfg['lon_min'], cfg['lon_max']
    lat_min, lat_max = cfg['lat_min'], cfg['lat_max']

    def proj_x(lon):
        return pad_x + ((lon - lon_min) / (lon_max - lon_min)) * (w - 2 * pad_x)

    def proj_y(lat):
        return (h - pad_y) - ((lat - lat_min) / (lat_max - lat_min)) * (h - 2 * pad_y)

    graticule_svg = []
    # Latitude parallels
    for lat_val in [20, 15, 10, 5, 0, -5, -10]:
        y_pos = round(proj_y(lat_val), 1)
        line_color = "rgba(239, 68, 68, 0.4)" if lat_val == 0 else "rgba(100, 116, 139, 0.2)"
        dash = "none" if lat_val == 0 else "3 3"
        graticule_svg.append(f'<line x1="{pad_x}" y1="{y_pos}" x2="{w - pad_x}" y2="{y_pos}" stroke="{line_color}" stroke-dasharray="{dash}" stroke-width="0.8" />')
        label = "0° (Equator)" if lat_val == 0 else (f"{lat_val}°N" if lat_val > 0 else f"{abs(lat_val)}°S")
        graticule_svg.append(f'<text x="{pad_x + 6}" y="{y_pos - 3}" fill="rgba(148, 163, 184, 0.5)" font-size="8.5" font-family="monospace">{label}</text>')

    # Longitude meridians
    for lon_val in [95, 100, 105, 110, 115, 120, 125]:
        x_pos = round(proj_x(lon_val), 1)
        graticule_svg.append(f'<line x1="{x_pos}" y1="{pad_y}" x2="{x_pos}" y2="{h - pad_y}" stroke="rgba(100, 116, 139, 0.2)" stroke-dasharray="3 3" stroke-width="0.8" />')
        graticule_svg.append(f'<text x="{x_pos + 3}" y="{h - pad_y - 4}" fill="rgba(148, 163, 184, 0.5)" font-size="8.5" font-family="monospace">{lon_val}°E</text>')

    graticules_svg_str = "\n            ".join(graticule_svg)

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
      background: radial-gradient(circle at 50% 45%, #0f172a 0%, #090d16 85%, #020617 100%);
    }}
    .sea-landmass {{
      transition: fill 0.2s ease, stroke 0.2s ease;
    }}
    .sea-landmass:hover {{
      fill: rgba(71, 85, 105, 0.75);
      stroke: rgba(226, 232, 240, 0.85);
    }}
    @keyframes pulse-ring {{
      0% {{ transform: scale(0.95); opacity: 0.8; }}
      50% {{ transform: scale(1.35); opacity: 0.2; }}
      100% {{ transform: scale(0.95); opacity: 0.8; }}
    }}
    .pulse-alert {{
      animation: pulse-ring 2.5s infinite ease-in-out;
      transform-origin: center;
    }}
    @media print {{
      body {{ background: white !important; color: black !important; }}
      .no-print {{ display: none !important; }}
    }}
  </style>
</head>
<body class="bg-transparent text-[var(--foreground)] antialiased p-4">
  <div class="max-w-7xl mx-auto space-y-6">
    
    <!-- Header -->
    <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-2xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <div class="flex items-center gap-2">
          <span class="inline-block w-3.5 h-3.5 rounded-full bg-red-500 animate-pulse"></span>
          <h1 class="text-2xl font-bold tracking-tight">Southeast Asia Super El Niño & Drought Tracker</h1>
        </div>
        <p class="text-sm text-[var(--muted-foreground)] mt-1">NOAA ERSST Niño 3.4 Oceanic Index • Open-Meteo Regional Climate Feed • DuckDB Analytical Engine</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span class="px-3 py-1 bg-red-500/20 border border-red-500/40 text-red-400 rounded-full text-xs font-bold tracking-wide">
          {enso_data['phase'].upper()} (+{enso_data['nino34_anom']:.2f}°C)
        </span>
        <button onclick="window.print()" class="no-print px-3 py-1 bg-slate-700/50 hover:bg-slate-700 border border-slate-600 text-slate-200 rounded-full text-xs font-semibold cursor-pointer transition-colors flex items-center gap-1.5">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
          Export / Print PDF
        </button>
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
        <div class="text-[10px] text-[var(--muted-foreground)] mt-0.5">PH, ID, VN, TH, MY (12 Basins)</div>
      </div>
    </div>

    <!-- Main Grid: Real Coastline SEA Drought Map & Regional Vulnerability Ranking -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Interactive Real SVG Map of Southeast Asia -->
      <div class="lg:col-span-2 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm flex flex-col">
        <div class="flex justify-between items-center mb-3">
          <div>
            <h2 class="font-semibold text-base flex items-center gap-2">
              <span>Southeast Asian Real Coastline Drought Map</span>
              <span class="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">Real GeoJSON Topology</span>
            </h2>
            <p class="text-xs text-[var(--muted-foreground)]">Geographic Bounds: 11.5°S–21.5°N, 94.0°E–130.0°E • Stations scaled by Drought Severity Index (SEDI)</p>
          </div>
          <div class="flex gap-2 text-[11px]">
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-red-500"></span> Crisis/Severe (≥65)</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span> Moderate (45-64)</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span> Normal (&lt;45)</span>
          </div>
        </div>

        <div class="sea-map-container relative w-full h-[450px] rounded-xl border border-[var(--border)] overflow-hidden flex items-center justify-center p-1">
          <svg id="sea-map-svg" viewBox="0 0 {w} {h}" class="w-full h-full max-h-[440px]">
            <!-- Graticules (Lat/Lon Grid) -->
            <g id="graticules-group">
            {graticules_svg_str}
            </g>

            <!-- Real Country Coastline Landmasses -->
            <g id="landmass-group">
            {landmass_svg_str}
            </g>

            <!-- Geographic Water Body Watermarks -->
            <text x="320" y="160" fill="rgba(100, 116, 139, 0.25)" font-size="11" font-weight="700" letter-spacing="3" font-family="sans-serif">SOUTH CHINA SEA</text>
            <text x="630" y="140" fill="rgba(100, 116, 139, 0.22)" font-size="10" font-weight="700" letter-spacing="3" font-family="sans-serif">PHILIPPINE SEA</text>
            <text x="80" y="440" fill="rgba(100, 116, 139, 0.22)" font-size="10" font-weight="700" letter-spacing="3" font-family="sans-serif">INDIAN OCEAN</text>
            <text x="360" y="445" fill="rgba(100, 116, 139, 0.22)" font-size="9" font-weight="700" letter-spacing="2" font-family="sans-serif">JAVA SEA</text>

            <!-- Geographic Country Name Labels -->
            <text x="565" y="150" fill="rgba(226, 232, 240, 0.65)" font-size="9" font-weight="800" letter-spacing="1.5">PHILIPPINES</text>
            <text x="280" y="490" fill="rgba(226, 232, 240, 0.65)" font-size="9" font-weight="800" letter-spacing="1.5">INDONESIA</text>
            <text x="210" y="130" fill="rgba(226, 232, 240, 0.65)" font-size="9" font-weight="800" letter-spacing="1.5">VIETNAM</text>
            <text x="140" y="110" fill="rgba(226, 232, 240, 0.65)" font-size="9" font-weight="800" letter-spacing="1.5">THAILAND</text>
            <text x="180" y="295" fill="rgba(226, 232, 240, 0.65)" font-size="8.5" font-weight="800" letter-spacing="1.5">MALAYSIA</text>

            <!-- Station Nodes Layer -->
            <g id="map-nodes-group"></g>
          </svg>
          <div id="map-tooltip" class="absolute pointer-events-none bg-slate-900/95 text-white border border-slate-700 text-xs rounded-xl p-3 shadow-2xl hidden z-20 max-w-xs"></div>
        </div>
      </div>

      <!-- Regional Vulnerability Ranking -->
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm flex flex-col justify-between">
        <div>
          <h2 class="font-semibold text-base mb-1">Drought Vulnerability Index</h2>
          <p class="text-xs text-[var(--muted-foreground)] mb-3">Ranked by Composite SEDI Score (0 to 100)</p>
          
          <div class="space-y-2.5 overflow-y-auto max-h-[370px] pr-1" id="ranking-list">
          </div>
        </div>
        <div class="pt-3 border-t border-[var(--border)] mt-3 text-[11px] text-[var(--muted-foreground)] flex justify-between">
          <span>Engine: DuckDB Rolling Window</span>
          <span>Coverage: 12 Core Basins</span>
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
    const cfg = {json.dumps(cfg)};

    function lonToX(lon) {{
      return cfg.pad_x + ((lon - cfg.lon_min) / (cfg.lon_max - cfg.lon_min)) * (cfg.width - 2 * cfg.pad_x);
    }}
    function latToY(lat) {{
      return (cfg.height - cfg.pad_y) - ((lat - cfg.lat_min) / (cfg.lat_max - cfg.lat_min)) * (cfg.height - 2 * cfg.pad_y);
    }}

    const nodesGroup = document.getElementById("map-nodes-group");
    const tooltip = document.getElementById("map-tooltip");

    bulletin.forEach(b => {{
      const cx = lonToX(b.longitude);
      const cy = latToY(b.latitude);
      const radius = Math.max(7, (b.drought_severity_index / 100) * 16);

      let color = "#10b981"; // Emerald
      if (b.drought_severity_index >= 65) color = "#ef4444"; // Red
      else if (b.drought_severity_index >= 45) color = "#f59e0b"; // Amber
      else if (b.drought_severity_index >= 25) color = "#3b82f6"; // Blue

      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");

      // Outer pulse ring if under moderate or severe drought
      if (b.drought_severity_index >= 45) {{
        const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        ring.setAttribute("cx", cx);
        ring.setAttribute("cy", cy);
        ring.setAttribute("r", radius + 6);
        ring.setAttribute("fill", "none");
        ring.setAttribute("stroke", color);
        ring.setAttribute("stroke-width", "1.5");
        ring.setAttribute("class", "pulse-alert");
        g.appendChild(ring);
      }}

      // Station node circle
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", cx);
      circle.setAttribute("cy", cy);
      circle.setAttribute("r", radius);
      circle.setAttribute("fill", color + "dd");
      circle.setAttribute("stroke", "#ffffff");
      circle.setAttribute("stroke-width", "1.5");
      circle.setAttribute("class", "cursor-pointer transition-transform hover:scale-125");

      // Hover Tooltip Interactions
      circle.addEventListener("mouseenter", (e) => {{
        tooltip.style.display = "block";
        tooltip.innerHTML = `
          <div class="font-bold text-sm text-white">${{b.region_name}} (${{b.country}})</div>
          <div class="text-[11px] text-slate-300 mt-1">${{b.economic_role}}</div>
          <div class="mt-2 pt-2 border-t border-slate-700 space-y-1 text-[11px]">
            <div>Drought Index (SEDI): <strong class="text-amber-400 font-bold">${{b.drought_severity_index}}/100</strong> (${{b.drought_tier}})</div>
            <div>Rain Deficit: <strong>${{b.precip_deficit_pct}}%</strong> (${{b.rolling_30d_precip_mm}}mm vs ${{b.baseline_monthly_rain_mm}}mm)</div>
            <div>Consecutive Dry Days: <strong>${{b.consecutive_dry_days}} days</strong></div>
            <div>Rootzone Soil Moisture: <strong>${{b.current_rootzone_moisture}} m³/m³</strong> (Depleted: ${{b.soil_moisture_depletion_pct}}%)</div>
            <div class="text-[10px] text-slate-400">Infra: ${{b.critical_infrastructure}}</div>
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

      g.appendChild(circle);

      // Station label text
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", cx + radius + 4);
      text.setAttribute("y", cy + 3);
      text.setAttribute("fill", "#f1f5f9");
      text.setAttribute("font-size", "9.5px");
      text.setAttribute("font-weight", "700");
      text.setAttribute("style", "text-shadow: 0 1px 3px rgba(0,0,0,0.9);");
      text.textContent = b.region_name.split(" ")[0];
      g.appendChild(text);

      nodesGroup.appendChild(g);
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

    print(f"  + Generated Super El Niño Dashboard with REAL MAP at {OUTPUT_HTML}")
    print(f"  + Synced to conversation artifact at {ARTIFACT_HTML}")

if __name__ == "__main__":
    build_el_nino_dashboard()
