import os
import sys
import json
import duckdb
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.el_nino_ph.config_ph import MAP_CONFIG, TIER_DEFINITIONS, SEDI_WEIGHTS
from src.el_nino_ph.ph_map_paths import PH_ISLAND_PATHS
from src.el_nino_ph.regions_ph import PH_REGIONS

DB_PATH = os.path.join(BASE_DIR, "data", "ph_el_nino_warehouse.duckdb")
OUTPUT_HTML = os.path.join(BASE_DIR, "ph_el_nino_dashboard.html")

def build_ph_el_nino_dashboard():
    """Generates the interactive Philippine Super El Niño & Drought Tracker Dashboard with empirical percentile telemetry."""
    total_regions = len(PH_REGIONS)
    print(f"[DASHBOARD] Compiling Philippine Super El Niño & Drought Dashboard ({total_regions} Basins)...")
    con = duckdb.connect(DB_PATH)
    
    # 1. Fetch Latest Global ENSO Status from fact_enso_monthly
    latest_enso_row = con.execute("""
        SELECT year_month, nino34_sst_c, nino34_anomaly_c, oni_anomaly, oni_season, enso_state, intensity
        FROM gold.fact_enso_monthly
        WHERE oni_anomaly IS NOT NULL
        ORDER BY year_month DESC
        LIMIT 1
    """).fetchone()
    
    if not latest_enso_row:
        raise RuntimeError("No ENSO records found in gold.fact_enso_monthly!")
        
    enso_data = {
        "year_month": latest_enso_row[0],
        "nino34_sst": float(latest_enso_row[1]),
        "nino34_anom": float(latest_enso_row[2]),
        "oni_anom": float(latest_enso_row[3]),
        "oni_season": str(latest_enso_row[4]),
        "enso_state": str(latest_enso_row[5]),
        "intensity": str(latest_enso_row[6])
    }
    
    # 2. Fetch Regional Bulletin Data
    bulletin_rows = con.execute("""
        SELECT 
            region_id,
            region_name,
            island_group,
            latitude,
            longitude,
            svg_x,
            svg_y,
            economic_role,
            critical_infrastructure,
            strftime(as_of_date, '%Y-%m-%d') AS as_of_date,
            data_latency_days,
            current_tmax_c,
            consecutive_dry_days,
            rolling_30d_precip_mm,
            current_rootzone_moisture,
            rolling_30d_extreme_heat_days,
            rain_severity,
            soil_severity,
            dry_spell_severity,
            heat_severity,
            drought_severity_index,
            sedi_historical_percentile,
            drought_tier
        FROM gold.dm_ph_el_nino_bulletin
        ORDER BY drought_severity_index DESC
    """).fetchall()
    
    con.close()
    
    if not bulletin_rows:
        raise RuntimeError("No records found in gold.dm_ph_el_nino_bulletin!")
        
    regions = []
    for r in bulletin_rows:
        regions.append({
            "region_id": str(r[0]),
            "region_name": str(r[1]),
            "island_group": str(r[2]),
            "latitude": float(r[3]),
            "longitude": float(r[4]),
            "svg_x": float(r[5]),
            "svg_y": float(r[6]),
            "economic_role": str(r[7]),
            "critical_infrastructure": str(r[8]),
            "as_of_date": str(r[9]),
            "data_latency_days": int(r[10]) if r[10] is not None else 0,
            "current_tmax_c": float(r[11]) if r[11] is not None else None,
            "consecutive_dry_days": int(r[12]) if r[12] is not None else 0,
            "rolling_30d_precip_mm": float(r[13]) if r[13] is not None else 0.0,
            "current_rootzone_moisture": float(r[14]) if r[14] is not None else 0.0,
            "rolling_30d_extreme_heat_days": int(r[15]) if r[15] is not None else 0,
            "rain_severity": float(r[16]) if r[16] is not None else 0.0,
            "soil_severity": float(r[17]) if r[17] is not None else 0.0,
            "dry_spell_severity": float(r[18]) if r[18] is not None else 0.0,
            "heat_severity": float(r[19]) if r[19] is not None else 0.0,
            "drought_severity_index": float(r[20]) if r[20] is not None else 0.0,
            "sedi_historical_percentile": float(r[21]) if r[21] is not None else 0.0,
            "drought_tier": str(r[22])
        })
        
    cfg = MAP_CONFIG
    w, h = cfg['width'], cfg['height']
    pad_x, pad_y = cfg['pad_x'], cfg['pad_y']
    lon_min, lon_max = cfg['lon_min'], cfg['lon_max']
    lat_min, lat_max = cfg['lat_min'], cfg['lat_max']
    
    def proj_x(lon):
        return pad_x + ((lon - lon_min) / (lon_max - lon_min)) * (w - 2 * pad_x)

    def proj_y(lat):
        return (h - pad_y) - ((lat - lat_min) / (lat_max - lat_min)) * (h - 2 * pad_y)
    
    # 3. Generate SVG Island Polygons with vibrant regional colors
    island_svg_elements = []
    for island in PH_ISLAND_PATHS:
        group = island.get("group", "Other")
        color = island.get("color", "#15803d")
        stroke = island.get("stroke", "#4ade80")
        island_svg_elements.append(
            f'<path d="{island["d"]}" fill="{color}" stroke="{stroke}" stroke-width="1.2" '
            f'class="ph-island island-{group.lower()} transition-all duration-200 hover:brightness-125" '
            f'data-group="{group}" />'
        )
    islands_svg_str = "\n            ".join(island_svg_elements)
    
    # 4. Generate Graticules
    graticule_svg = []
    for lat_val in [20, 18, 16, 14, 12, 10, 8, 6]:
        y_pos = round(proj_y(lat_val), 1)
        graticule_svg.append(f'<line x1="{pad_x}" y1="{y_pos}" x2="{w - pad_x}" y2="{y_pos}" stroke="rgba(56, 189, 248, 0.15)" stroke-dasharray="3 3" stroke-width="0.8" />')
        graticule_svg.append(f'<text x="{pad_x + 4}" y="{y_pos - 3}" fill="rgba(148, 163, 184, 0.45)" font-size="8.5" font-family="monospace">{lat_val}°N</text>')
    
    for lon_val in [118, 120, 122, 124, 126]:
        x_pos = round(proj_x(lon_val), 1)
        graticule_svg.append(f'<line x1="{x_pos}" y1="{pad_y}" x2="{x_pos}" y2="{h - pad_y}" stroke="rgba(56, 189, 248, 0.15)" stroke-dasharray="3 3" stroke-width="0.8" />')
        graticule_svg.append(f'<text x="{x_pos + 3}" y="{h - pad_y - 4}" fill="rgba(148, 163, 184, 0.45)" font-size="8.5" font-family="monospace">{lon_val}°E</text>')
    graticules_svg_str = "\n            ".join(graticule_svg)
    
    # Tier mapping lookup
    tier_map = {t["tier"]: t for t in TIER_DEFINITIONS}
    
    # 5. Generate Regional Hotspot Radar Markers
    pin_svg_elements = []
    for reg in regions:
        tier_info = tier_map.get(reg["drought_tier"], TIER_DEFINITIONS[-1])
        color = tier_info["color"]
        pulse_cls = tier_info["pulse_class"]
        short_name = reg["region_name"].split(" (")[0]
        
        pin_svg_elements.append(f"""
            <g class="region-pin group cursor-pointer" data-region-id="{reg['region_id']}" data-group="{reg['island_group']}" onclick="selectRegion('{reg['region_id']}')">
              <!-- Animated Pulse Ripple -->
              <circle cx="{reg['svg_x']}" cy="{reg['svg_y']}" r="14" fill="{color}" opacity="0.25" class="{pulse_cls}" />
              <!-- Radar Core -->
              <circle cx="{reg['svg_x']}" cy="{reg['svg_y']}" r="5.5" fill="{color}" stroke="#ffffff" stroke-width="1.8" filter="url(#pinGlow)" />
              <!-- Label -->
              <text x="{reg['svg_x'] + 9}" y="{reg['svg_y'] + 3}" fill="#f8fafc" font-size="9" font-weight="600" class="pointer-events-none drop-shadow-[0_1px_2px_rgba(0,0,0,0.9)]">{short_name}</text>
            </g>
        """)
    pins_svg_str = "\n".join(pin_svg_elements)
    
    # Tier counts for KPI 4
    tier_counts = {t["tier"]: 0 for t in TIER_DEFINITIONS}
    for r in regions:
        t = r["drought_tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1
        
    top_reg = regions[0]
    top_tier_info = tier_map.get(top_reg["drought_tier"], TIER_DEFINITIONS[-1])
    
    # Specific regions for KPI cards
    angat_reg = next((r for r in regions if r['region_id'] == 'PH_ANGAT_BASIN'), None)
    cluzon_reg = next((r for r in regions if r['region_id'] == 'PH_CENTRAL_LUZON'), None)
    
    # ENSO badge coloring
    enso_state = enso_data["enso_state"]
    if "El Niño" in enso_state:
        enso_bg = "bg-red-500/20 text-red-400 border-red-500/40"
        enso_pill_class = "text-red-400"
    elif "La Niña" in enso_state:
        enso_bg = "bg-blue-500/20 text-blue-400 border-blue-500/40"
        enso_pill_class = "text-blue-400"
    else:
        enso_bg = "bg-slate-800 text-slate-300 border-slate-700"
        enso_pill_class = "text-slate-300"
        
    regions_json_str = json.dumps(regions, default=str)
    enso_json_str = json.dumps(enso_data, default=str)
    tier_json_str = json.dumps(TIER_DEFINITIONS, default=str)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Philippines Super El Niño & Basin Drought Tracker</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    .ph-map-bg {{
      background: radial-gradient(circle at 45% 40%, #0d2c4d 0%, #081d33 60%, #030d17 100%);
    }}
    @keyframes pulseCrisis {{
      0% {{ r: 6px; opacity: 0.8; stroke-width: 2px; }}
      50% {{ r: 20px; opacity: 0.2; stroke-width: 1px; }}
      100% {{ r: 24px; opacity: 0; stroke-width: 0.5px; }}
    }}
    .pulse-crisis {{
      animation: pulseCrisis 1.6s infinite cubic-bezier(0.2, 0, 0, 1);
      transform-origin: center;
    }}
    @keyframes pulseSevere {{
      0% {{ r: 6px; opacity: 0.7; }}
      50% {{ r: 18px; opacity: 0.15; }}
      100% {{ r: 22px; opacity: 0; }}
    }}
    .pulse-severe {{
      animation: pulseSevere 2.0s infinite cubic-bezier(0.2, 0, 0, 1);
      transform-origin: center;
    }}
    @keyframes pulseModerate {{
      0% {{ r: 6px; opacity: 0.6; }}
      50% {{ r: 16px; opacity: 0.12; }}
      100% {{ r: 20px; opacity: 0; }}
    }}
    .pulse-moderate {{
      animation: pulseModerate 2.6s infinite ease-out;
      transform-origin: center;
    }}
    @keyframes pulseWatch {{
      0% {{ r: 6px; opacity: 0.5; }}
      50% {{ r: 14px; opacity: 0.1; }}
      100% {{ r: 18px; opacity: 0; }}
    }}
    .pulse-watch {{
      animation: pulseWatch 3.2s infinite ease-out;
      transform-origin: center;
    }}
    .pulse-normal {{
      /* Normal status: steady green indicator without pulsing */
      display: none;
    }}
    .custom-scrollbar::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    .custom-scrollbar::-webkit-scrollbar-track {{
      background: #0f172a;
    }}
    .custom-scrollbar::-webkit-scrollbar-thumb {{
      background: #334155;
      border-radius: 4px;
    }}
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {{
      background: #475569;
    }}
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col antialiased">

  <!-- TOP HEADER -->
  <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 font-black text-sm border border-emerald-500/40">🇵🇭</span>
          <h1 class="text-xl md:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            PHILIPPINES SUPER EL NIÑO & DROUGHT INTELLIGENCE
          </h1>
          <span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            PERCENTILE ENGINE
          </span>
        </div>
        <p class="text-xs text-slate-400 mt-1">
          Historical Climatology Benchmark (2005–2025) across {total_regions} Key Agricultural Basins, Hydro Dams & Watersheds
        </p>
      </div>

      <!-- Live Global ENSO Metric Pill -->
      <div class="flex items-center gap-4 bg-slate-800/80 px-4 py-2.5 rounded-xl border border-slate-700/60 shadow-inner">
        <div>
          <div class="text-[10px] uppercase tracking-wider font-semibold text-slate-400">NOAA ONI Season ({enso_data['oni_season']})</div>
          <div class="text-lg font-bold {enso_pill_class} flex items-center gap-1.5">
            <span>{enso_data['oni_anom']:+.2f}°C</span>
            <span class="text-xs font-medium text-amber-300">({enso_data['enso_state']})</span>
          </div>
        </div>
        <div class="h-8 w-px bg-slate-700"></div>
        <div>
          <div class="text-[10px] uppercase tracking-wider font-semibold text-slate-400">Niño 3.4 Anomaly</div>
          <div class="text-lg font-bold text-white">{enso_data['nino34_anom']:+.2f}°C</div>
        </div>
        <div class="h-8 w-px bg-slate-700"></div>
        <div>
          <div class="text-[10px] uppercase tracking-wider font-semibold text-slate-400">Intensity Status</div>
          <div class="text-xs font-medium text-slate-300 mt-0.5">{enso_data['intensity']}</div>
        </div>
      </div>
    </div>
  </header>

  <!-- MAIN DASHBOARD CONTENT -->
  <main class="max-w-7xl mx-auto px-4 md:px-6 py-6 flex-1 w-full space-y-6">

    <!-- KPI STATS CARDS -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- KPI 1: Highest Drought Severity -->
      <div class="bg-slate-900/80 border rounded-xl p-4 shadow-lg relative overflow-hidden" style="border-color: {top_tier_info['border_color']}">
        <div class="absolute -right-4 -bottom-4 w-20 h-20 rounded-full blur-xl pointer-events-none" style="background-color: {top_tier_info['color']}22"></div>
        <div class="text-xs font-medium uppercase tracking-wider flex items-center justify-between" style="color: {top_tier_info['color']}">
          <span>Highest Drought Severity</span>
          <span class="w-2 h-2 rounded-full" style="background-color: {top_tier_info['color']}"></span>
        </div>
        <div class="mt-2 text-xl font-bold text-white truncate" id="kpi-top-region">{top_reg['region_name'].split(' (')[0]}</div>
        <div class="mt-1 text-xs text-slate-400 flex items-center justify-between">
          <span>Climatological SEDI</span>
          <span class="text-base font-extrabold" style="color: {top_tier_info['color']}" id="kpi-top-sedi">{top_reg['drought_severity_index']} / 100</span>
        </div>
        <div class="mt-2 text-[11px] px-2 py-1 rounded border flex justify-between items-center" style="background-color: {top_tier_info['bg_color']}; border-color: {top_tier_info['border_color']}">
          <span class="font-bold text-white">{top_reg['drought_tier']}</span>
          <span class="text-slate-300">Lag: {top_reg['data_latency_days']}d</span>
        </div>
      </div>

      <!-- KPI 2: Angat Dam Status -->
      <div class="bg-slate-900/80 border border-slate-700/60 rounded-xl p-4 shadow-lg relative overflow-hidden">
        <div class="text-xs font-medium uppercase tracking-wider text-slate-400 flex items-center justify-between">
          <span>Metro Manila Water Lifeline</span>
          <span class="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">Angat Dam</span>
        </div>
        <div class="mt-2 text-xl font-bold text-white">Angat Dam Catchment</div>
        <div class="mt-1 text-xs text-slate-400 flex items-center justify-between">
          <span>Rain Severity Percentile</span>
          <span class="text-base font-extrabold text-amber-400">
            {angat_reg['rain_severity'] if angat_reg else 'N/A'}/100
          </span>
        </div>
        <div class="mt-2 text-[11px] text-slate-300 bg-slate-950/60 px-2 py-1 rounded border border-slate-800 flex justify-between items-center">
          <span>30d Rain: {angat_reg['rolling_30d_precip_mm'] if angat_reg else 'N/A'} mm</span>
          <span class="font-semibold text-emerald-400">{angat_reg['drought_tier'] if angat_reg else 'N/A'}</span>
        </div>
      </div>

      <!-- KPI 3: Central Luzon Granary -->
      <div class="bg-slate-900/80 border border-slate-700/60 rounded-xl p-4 shadow-lg relative overflow-hidden">
        <div class="text-xs font-medium uppercase tracking-wider text-slate-400 flex items-center justify-between">
          <span>National Rice Granary</span>
          <span class="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">Central Luzon</span>
        </div>
        <div class="mt-2 text-xl font-bold text-white">Nueva Ecija / Pampanga</div>
        <div class="mt-1 text-xs text-slate-400 flex items-center justify-between">
          <span>Dry Streak (CDD)</span>
          <span class="text-base font-extrabold text-amber-400">
            {cluzon_reg['consecutive_dry_days'] if cluzon_reg else 'N/A'} Days Dry
          </span>
        </div>
        <div class="mt-2 text-[11px] text-slate-300 bg-slate-950/60 px-2 py-1 rounded border border-slate-800 flex justify-between items-center">
          <span>Soil Severity: {cluzon_reg['soil_severity'] if cluzon_reg else 'N/A'}/100</span>
          <span class="font-semibold text-emerald-400">{cluzon_reg['drought_tier'] if cluzon_reg else 'N/A'}</span>
        </div>
      </div>

      <!-- KPI 4: National Basin Summary -->
      <div class="bg-slate-900/80 border border-slate-700/60 rounded-xl p-4 shadow-lg relative overflow-hidden">
        <div class="text-xs font-medium uppercase tracking-wider text-slate-400 flex items-center justify-between">
          <span>Archipelago Monitored Basins</span>
          <span class="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded font-mono">{total_regions} Hubs</span>
        </div>
        <div class="mt-2 text-xl font-bold text-white">Luzon · Visayas · Mindanao</div>
        <div class="mt-1 text-xs text-slate-400 flex items-center justify-between">
          <span>Archipelago Average SEDI</span>
          <span class="text-base font-extrabold text-emerald-400">
            {round(sum(r['drought_severity_index'] for r in regions)/len(regions), 1)} / 100
          </span>
        </div>
        <div class="mt-2 text-[10px] text-slate-300 bg-slate-950/60 px-2 py-1 rounded border border-slate-800 flex justify-between">
          <span class="text-red-400 font-bold">Ext: {tier_counts.get('EXTREME DROUGHT', 0)}</span>
          <span class="text-orange-400 font-bold">Sev: {tier_counts.get('SEVERE DROUGHT', 0)}</span>
          <span class="text-yellow-400 font-bold">Mod: {tier_counts.get('MODERATE DROUGHT', 0)}</span>
          <span class="text-cyan-400 font-bold">Wat: {tier_counts.get('DRY SPELL WATCH', 0)}</span>
          <span class="text-emerald-400 font-bold">Norm: {tier_counts.get('NORMAL', 0)}</span>
        </div>
      </div>
    </div>

    <!-- MAIN TWO-COLUMN LAYOUT: MAP + TELEMETRY PANEL -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      
      <!-- LEFT: VIBRANT COLORFUL PHILIPPINES SVG MAP (7 Cols) -->
      <div class="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl flex flex-col">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
              PHILIPPINE ARCHIPELAGO DROUGHT RADAR
            </h2>
            <p class="text-xs text-slate-400">Natural Earth 50m Coastlines with Empirical Climatology Percentile Coding</p>
          </div>
          
          <!-- Filter Buttons -->
          <div class="flex flex-wrap items-center gap-1.5 text-xs">
            <button onclick="filterMap('all')" class="filter-btn active px-2.5 py-1 rounded-md bg-emerald-500 text-slate-950 font-bold border border-emerald-400 transition" id="btn-all">All ({total_regions})</button>
            <button onclick="filterMap('Luzon')" class="filter-btn px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 transition" id="btn-luzon">Luzon</button>
            <button onclick="filterMap('Visayas')" class="filter-btn px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 transition" id="btn-visayas">Visayas</button>
            <button onclick="filterMap('Mindanao')" class="filter-btn px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 transition" id="btn-mindanao">Mindanao</button>
            <button onclick="filterMap('Palawan')" class="filter-btn px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 transition" id="btn-palawan">Palawan</button>
          </div>
        </div>

        <!-- Legend Ribbon -->
        <div class="flex flex-wrap items-center justify-between gap-2 py-2.5 px-3 bg-slate-950/60 rounded-lg border border-slate-800/80 my-3 text-[11px]">
          <!-- Regional Landmass Colors -->
          <div class="flex items-center gap-2.5">
            <span class="text-slate-400 font-semibold uppercase text-[10px]">Islands:</span>
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-[#15803d] border border-[#4ade80]"></span> Luzon</span>
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-[#0d9488] border border-[#5eead4]"></span> Visayas</span>
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-[#047857] border border-[#34d399]"></span> Mindanao</span>
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-[#0284c7] border border-[#38bdf8]"></span> Palawan</span>
          </div>

          <!-- Alert Radar Severity -->
          <div class="flex items-center gap-2">
            <span class="text-slate-400 font-semibold uppercase text-[10px]">Severity Tiers:</span>
            <span class="inline-flex items-center gap-1 text-red-400"><span class="w-2 h-2 rounded-full bg-red-500"></span> Extreme (95+)</span>
            <span class="inline-flex items-center gap-1 text-orange-400"><span class="w-2 h-2 rounded-full bg-orange-500"></span> Severe (90+)</span>
            <span class="inline-flex items-center gap-1 text-yellow-400"><span class="w-2 h-2 rounded-full bg-yellow-500"></span> Mod (80+)</span>
            <span class="inline-flex items-center gap-1 text-cyan-400"><span class="w-2 h-2 rounded-full bg-cyan-400"></span> Watch (70+)</span>
            <span class="inline-flex items-center gap-1 text-emerald-400"><span class="w-2 h-2 rounded-full bg-emerald-500"></span> Normal</span>
          </div>
        </div>

        <!-- SVG MAP CONTAINER -->
        <div class="relative w-full rounded-xl overflow-hidden border border-slate-800 shadow-inner ph-map-bg flex items-center justify-center">
          <svg viewBox="0 0 {w} {h}" class="w-full h-auto max-h-[750px] select-none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <!-- Pin Glow Filter -->
              <filter id="pinGlow" x="-30%" y="-30%" width="160%" height="160%">
                <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#000" flood-opacity="0.8" />
              </filter>
              <!-- Coastal Halo Filter -->
              <filter id="coastalAura" x="-20%" y="-20%" width="140%" height="140%">
                <feMorphology operator="dilate" radius="2" result="dilated" />
                <feGaussianBlur in="dilated" stdDeviation="2.5" result="blurred" />
                <feFlood flood-color="#38bdf8" flood-opacity="0.25" result="glow" />
                <feComposite in="glow" in2="blurred" operator="in" result="coastalGlow" />
                <feMerge>
                  <feMergeNode in="coastalGlow" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <!-- Geographic Graticules & Lat/Lon Lines -->
            <g id="graticules" opacity="0.6">
              {graticules_svg_str}
            </g>

            <!-- Oceanic Water Body Typography -->
            <g id="water-labels" class="select-none pointer-events-none" fill="rgba(56, 189, 248, 0.28)" font-family="system-ui, sans-serif" font-weight="700" letter-spacing="3.5">
              <text x="75" y="290" font-size="11" transform="rotate(-65 75 290)">WEST PHILIPPINE SEA</text>
              <text x="475" y="240" font-size="11" transform="rotate(70 475 240)">PHILIPPINE SEA (PACIFIC OCEAN)</text>
              <text x="175" y="650" font-size="10">S U L U   S E A</text>
              <text x="400" y="605" font-size="8.5">B O H O L   S E A</text>
              <text x="350" y="795" font-size="9">C E L E B E S   S E A</text>
              <text x="250" y="65" font-size="8.5">L U Z O N   S T R A I T</text>
            </g>

            <!-- 48 Realistic Natural Earth Island Coastlines with Rich Color Topography -->
            <g id="ph-islands" filter="url(#coastalAura)">
              {islands_svg_str}
            </g>

            <!-- 18 Agricultural & Dam Basin Hotspot Pins -->
            <g id="ph-pins">
              {pins_svg_str}
            </g>
          </svg>
        </div>
      </div>

      <!-- RIGHT: BASIN TELEMETRY INSPECTOR & RANKING (5 Cols) -->
      <div class="lg:col-span-5 space-y-5">
        
        <!-- SELECTED BASIN INSPECTOR CARD -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl relative overflow-hidden" id="basin-inspector">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">TELEMETRY INSPECTOR</span>
                <span class="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono" id="inspector-latency">As of: {regions[0]['as_of_date']} (lag {regions[0]['data_latency_days']}d)</span>
              </div>
              <h3 class="text-lg font-bold text-white flex items-center gap-2 mt-0.5" id="inspector-name">
                {regions[0]['region_name']}
              </h3>
            </div>
            <div class="flex flex-col items-end gap-1">
              <span class="px-2.5 py-1 text-xs font-extrabold rounded-full" id="inspector-tier-badge">
                {regions[0]['drought_tier']}
              </span>
              <span class="text-[10px] px-2 py-0.5 rounded border {enso_bg} font-semibold">
                ENSO: {enso_data['enso_state']} ({enso_data['intensity']})
              </span>
            </div>
          </div>

          <div class="mt-4 space-y-4">
            <!-- SEDI Gauge Bar -->
            <div>
              <div class="flex justify-between text-xs mb-1">
                <span class="text-slate-400">Standardized Drought Index (SEDI)</span>
                <span class="font-bold text-white" id="inspector-sedi">{regions[0]['drought_severity_index']} / 100</span>
              </div>
              <div class="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-emerald-500 via-yellow-500 via-orange-500 to-red-500 rounded-full" id="inspector-sedi-bar" style="width: {regions[0]['drought_severity_index']}%"></div>
              </div>
            </div>

            <!-- 4 Component Severities Grid (0-100) -->
            <div>
              <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2 flex justify-between">
                <span>SEDI Component Severity Breakdown</span>
                <span class="text-slate-500 font-normal">Expert-judgement weights</span>
              </div>
              <div class="grid grid-cols-2 gap-2 text-xs">
                <div class="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  <div class="flex justify-between text-[10px] text-slate-400">
                    <span>Rain Deficit (35%)</span>
                    <span class="font-mono text-cyan-300" id="inspector-rain-vol">{regions[0]['rolling_30d_precip_mm']}mm 30d</span>
                  </div>
                  <div class="text-base font-extrabold text-cyan-400 mt-0.5" id="inspector-rain-sev">{regions[0]['rain_severity']} / 100</div>
                  <div class="text-[9px] text-slate-500">Historical seasonal percentile deficit</div>
                </div>

                <div class="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  <div class="flex justify-between text-[10px] text-slate-400">
                    <span>Soil Depletion (30%)</span>
                    <span class="font-mono text-emerald-300" id="inspector-soil-vol">{regions[0]['current_rootzone_moisture']} m³/m³</span>
                  </div>
                  <div class="text-base font-extrabold text-emerald-400 mt-0.5" id="inspector-soil-sev">{regions[0]['soil_severity']} / 100</div>
                  <div class="text-[9px] text-slate-500">Rootzone (7-28cm) seasonal depletion</div>
                </div>

                <div class="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  <div class="flex justify-between text-[10px] text-slate-400">
                    <span>Dry Spell Streak (20%)</span>
                    <span class="font-mono text-amber-300" id="inspector-cdd">{regions[0]['consecutive_dry_days']} Days CDD</span>
                  </div>
                  <div class="text-base font-extrabold text-amber-400 mt-0.5" id="inspector-cdd-sev">{regions[0]['dry_spell_severity']} / 100</div>
                  <div class="text-[9px] text-slate-500">CDD vs historical distribution</div>
                </div>

                <div class="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  <div class="flex justify-between text-[10px] text-slate-400">
                    <span>Heat Stress (15%)</span>
                    <span class="font-mono text-orange-300" id="inspector-heat-days">{regions[0]['rolling_30d_extreme_heat_days']} Days</span>
                  </div>
                  <div class="text-base font-extrabold text-orange-400 mt-0.5" id="inspector-heat-sev">{regions[0]['heat_severity']} / 100</div>
                  <div class="text-[9px] text-slate-500">Days Tmax ≥ 90th percentile of date</div>
                </div>
              </div>
            </div>

            <!-- Strategic Impact Details -->
            <div class="bg-slate-950/70 p-3.5 rounded-xl border border-slate-800 space-y-2 text-xs">
              <div class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold min-w-[70px]">Agri-Role:</span>
                <span class="text-slate-300" id="inspector-role">{regions[0]['economic_role']}</span>
              </div>
              <div class="flex items-start gap-2">
                <span class="text-cyan-400 font-bold min-w-[70px]">Lifeline Infra:</span>
                <span class="text-slate-300" id="inspector-infra">{regions[0]['critical_infrastructure']}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- BASIN RANKING & COMPARISON LIST -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl flex flex-col">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 class="text-sm font-bold text-white flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              ALL {total_regions} PHILIPPINE BASINS BY STRESS
            </h3>
            <span class="text-xs text-slate-400 font-mono">Sorted by Climatological SEDI</span>
          </div>

          <div class="mt-3 space-y-2 max-h-[380px] overflow-y-auto custom-scrollbar pr-1" id="ranking-list">
            <!-- Dynamically populated via JavaScript -->
          </div>
        </div>

      </div>

    </div>

    <!-- FULL TELEMETRY TABLE -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl overflow-hidden">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-2">
        <div>
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <span>📋</span> FULL ARCHIPELAGO BASIN TELEMETRY SPECIFICATION
          </h3>
          <p class="text-xs text-slate-400">Real-time Open-Meteo ERA5 Reanalysis & NOAA CPC Ingested Telemetry</p>
        </div>
        <div class="text-xs text-slate-400 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
          Source: DuckDB Gold Mart (<code class="text-emerald-400 font-mono">gold.dm_ph_el_nino_bulletin</code>)
        </div>
      </div>

      <div class="mt-4 overflow-x-auto custom-scrollbar">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-slate-800 text-slate-400 font-semibold bg-slate-950/80">
              <th class="py-3 px-3">Basin / Region</th>
              <th class="py-3 px-2">Group</th>
              <th class="py-3 px-2">SEDI Index</th>
              <th class="py-3 px-2">Drought Tier</th>
              <th class="py-3 px-2">Rain Sev. (35%)</th>
              <th class="py-3 px-2">Soil Sev. (30%)</th>
              <th class="py-3 px-2">Dry Spell (20%)</th>
              <th class="py-3 px-2">Heat Sev. (15%)</th>
              <th class="py-3 px-2">As Of (Latency)</th>
              <th class="py-3 px-3">Lifeline Catchment / Role</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60" id="telemetry-table-body">
            <!-- Populated via JavaScript -->
          </tbody>
        </table>
      </div>
    </div>

  </main>

  <!-- FOOTER -->
  <footer class="border-t border-slate-800 bg-slate-950 py-4 px-6 text-xs text-slate-500 mt-6">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-2">
      <div>
        Philippine Super El Niño Intelligence Engine · Open Public Feeds: NOAA CPC & Open-Meteo ERA5 · Medallion Warehouse
      </div>
      <div class="font-mono text-[11px] text-slate-400">
        DuckDB v1.0+ · Parquet · Natural Earth 50m High-Precision Polygons ({total_regions} Basins)
      </div>
    </div>
  </footer>

  <!-- INTERACTIVE CLIENT-SIDE ENGINE -->
  <script>
    const REGIONS = {regions_json_str};
    const ENSO_DATA = {enso_json_str};
    const TIER_DEFS = {tier_json_str};

    const tierMap = {{}};
    TIER_DEFS.forEach(t => {{ tierMap[t.tier] = t; }});

    let selectedRegionId = REGIONS[0].region_id;

    function renderRankingList() {{
      const container = document.getElementById('ranking-list');
      container.innerHTML = '';

      REGIONS.forEach((reg, idx) => {{
        const tierInfo = tierMap[reg.drought_tier] || TIER_DEFS[TIER_DEFS.length - 1];

        const row = document.createElement('div');
        row.className = `p-2.5 rounded-lg border transition cursor-pointer flex items-center justify-between text-xs ${{
          reg.region_id === selectedRegionId 
            ? 'bg-slate-800/90 border-emerald-500 shadow-md ring-1 ring-emerald-500/40' 
            : 'bg-slate-950/50 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700'
        }}`;
        row.onclick = () => selectRegion(reg.region_id);

        row.innerHTML = `
          <div class="flex items-center gap-2.5">
            <span class="w-5 text-center font-mono font-bold text-slate-500">#${{idx + 1}}</span>
            <div>
              <div class="font-bold text-white flex items-center gap-1.5">
                ${{reg.region_name.split(' (')[0]}}
                <span class="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-400 font-normal">${{reg.island_group}}</span>
              </div>
              <div class="text-[10px] text-slate-400">${{reg.consecutive_dry_days}} CDD · ${{reg.rolling_30d_precip_mm}}mm 30d rain</div>
            </div>
          </div>
          <div class="text-right">
            <div class="font-extrabold text-sm" style="color: ${{tierInfo.color}}">
              ${{reg.drought_severity_index}}
            </div>
            <div class="text-[9px] px-1.5 py-0.5 rounded border font-semibold mt-0.5" style="color: ${{tierInfo.color}}; background-color: ${{tierInfo.bg_color}}; border-color: ${{tierInfo.border_color}}">
              ${{reg.drought_tier}}
            </div>
          </div>
        `;
        container.appendChild(row);
      }});
    }}

    function renderTable() {{
      const tbody = document.getElementById('telemetry-table-body');
      tbody.innerHTML = '';

      REGIONS.forEach(reg => {{
        const tierInfo = tierMap[reg.drought_tier] || TIER_DEFS[TIER_DEFS.length - 1];

        const tr = document.createElement('tr');
        tr.className = `hover:bg-slate-800/40 transition cursor-pointer ${{reg.region_id === selectedRegionId ? 'bg-slate-800/30' : ''}}`;
        tr.onclick = () => selectRegion(reg.region_id);

        tr.innerHTML = `
          <td class="py-2.5 px-3 font-bold text-white">${{reg.region_name}}</td>
          <td class="py-2.5 px-2 text-slate-300"><span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">${{reg.island_group}}</span></td>
          <td class="py-2.5 px-2 font-mono font-bold text-sm" style="color: ${{tierInfo.color}}">${{reg.drought_severity_index}}</td>
          <td class="py-2.5 px-2"><span class="px-2 py-0.5 rounded border text-[10px] font-semibold" style="color: ${{tierInfo.color}}; background-color: ${{tierInfo.bg_color}}; border-color: ${{tierInfo.border_color}}">${{reg.drought_tier}}</span></td>
          <td class="py-2.5 px-2 text-cyan-300 font-mono font-semibold">${{reg.rain_severity}}</td>
          <td class="py-2.5 px-2 text-emerald-300 font-mono font-semibold">${{reg.soil_severity}}</td>
          <td class="py-2.5 px-2 text-amber-300 font-mono font-semibold">${{reg.dry_spell_severity}} (${{reg.consecutive_dry_days}}d)</td>
          <td class="py-2.5 px-2 text-orange-300 font-mono font-semibold">${{reg.heat_severity}}</td>
          <td class="py-2.5 px-2 text-slate-400 font-mono">${{reg.as_of_date}} (${{reg.data_latency_days}}d lag)</td>
          <td class="py-2.5 px-3 text-slate-400 truncate max-w-xs">${{reg.critical_infrastructure}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function selectRegion(regionId) {{
      selectedRegionId = regionId;
      const reg = REGIONS.find(r => r.region_id === regionId);
      if (!reg) return;

      const tierInfo = tierMap[reg.drought_tier] || TIER_DEFS[TIER_DEFS.length - 1];

      document.getElementById('inspector-name').innerText = reg.region_name;
      document.getElementById('inspector-latency').innerText = `As of: ${{reg.as_of_date}} (lag ${{reg.data_latency_days}}d)`;
      
      const tierBadge = document.getElementById('inspector-tier-badge');
      tierBadge.innerText = reg.drought_tier;
      tierBadge.style.color = tierInfo.color;
      tierBadge.style.backgroundColor = tierInfo.bg_color;
      tierBadge.style.borderColor = tierInfo.border_color;
      tierBadge.className = "px-2.5 py-1 text-xs font-extrabold rounded-full border";

      document.getElementById('inspector-sedi').innerText = `${{reg.drought_severity_index}} / 100`;
      document.getElementById('inspector-sedi-bar').style.width = `${{reg.drought_severity_index}}%`;
      
      document.getElementById('inspector-rain-vol').innerText = `${{reg.rolling_30d_precip_mm}}mm 30d`;
      document.getElementById('inspector-rain-sev').innerText = `${{reg.rain_severity}} / 100`;
      
      document.getElementById('inspector-soil-vol').innerText = `${{reg.current_rootzone_moisture}} m³/m³`;
      document.getElementById('inspector-soil-sev').innerText = `${{reg.soil_severity}} / 100`;
      
      document.getElementById('inspector-cdd').innerText = `${{reg.consecutive_dry_days}} Days CDD`;
      document.getElementById('inspector-cdd-sev').innerText = `${{reg.dry_spell_severity}} / 100`;
      
      document.getElementById('inspector-heat-days').innerText = `${{reg.rolling_30d_extreme_heat_days}} Days`;
      document.getElementById('inspector-heat-sev').innerText = `${{reg.heat_severity}} / 100`;

      document.getElementById('inspector-role').innerText = reg.economic_role;
      document.getElementById('inspector-infra').innerText = reg.critical_infrastructure;

      // Update Pin Highlight on Map
      document.querySelectorAll('.region-pin').forEach(el => {{
        const isMatch = el.getAttribute('data-region-id') === regionId;
        const circle = el.querySelector('circle:nth-child(2)');
        if (circle) {{
          if (isMatch) {{
            circle.setAttribute('r', '8.5');
            circle.setAttribute('stroke-width', '2.5');
          }} else {{
            circle.setAttribute('r', '5.5');
            circle.setAttribute('stroke-width', '1.8');
          }}
        }}
      }});

      renderRankingList();
      renderTable();
    }}

    function filterMap(group) {{
      document.querySelectorAll('.filter-btn').forEach(btn => {{
        btn.classList.remove('bg-emerald-500', 'text-slate-950', 'font-bold', 'border-emerald-400');
        btn.classList.add('bg-slate-800', 'text-slate-300', 'border-slate-700');
      }});

      const activeBtn = document.getElementById(`btn-${{group.toLowerCase()}}`);
      if (activeBtn) {{
        activeBtn.classList.remove('bg-slate-800', 'text-slate-300', 'border-slate-700');
        activeBtn.classList.add('bg-emerald-500', 'text-slate-950', 'font-bold', 'border-emerald-400');
      }}

      // Show/hide island polygons and pins
      document.querySelectorAll('.ph-island').forEach(island => {{
        const islandGroup = island.getAttribute('data-group');
        if (group === 'all' || islandGroup === group) {{
          island.style.opacity = '1';
        }} else {{
          island.style.opacity = '0.25';
        }}
      }});

      document.querySelectorAll('.region-pin').forEach(pin => {{
        const pinGroup = pin.getAttribute('data-group');
        if (group === 'all' || pinGroup === group) {{
          pin.style.display = 'block';
        }} else {{
          pin.style.display = 'none';
        }}
      }});
    }}

    // Single initial render on load
    window.onload = () => {{
      selectRegion(selectedRegionId);
    }};
  </script>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  [SAVED] Philippine El Niño Dashboard -> {OUTPUT_HTML}")
    
    # Read optional ARTIFACT_DIR environment variable
    artifact_dir = os.environ.get("ARTIFACT_DIR")
    if artifact_dir and os.path.isdir(artifact_dir):
        artifact_html = os.path.join(artifact_dir, "ph_el_nino_dashboard.html")
        shutil.copyfile(OUTPUT_HTML, artifact_html)
        print(f"  [COPIED] Copied to ARTIFACT_DIR -> {artifact_html}")
        return artifact_html
        
    return OUTPUT_HTML

if __name__ == "__main__":
    build_ph_el_nino_dashboard()
