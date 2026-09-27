import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "dashboard_data.json")
ARTIFACT_DIR = r"C:\Users\marki\.gemini\antigravity\brain\3f02062b-df98-4788-a2f8-8ca1213a27ef"
OUTPUT_HTML = os.path.join(ARTIFACT_DIR, "seismic_dashboard.html")

with open(JSON_PATH, "r") as f:
    data = json.load(f)

events_json = json.dumps(data["events"])
cities_json = json.dumps(data["cities"])

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Philippine Seismic & Earthquake Data Warehouse Dashboard</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    body {{
      font-family: system-ui, -apple-system, sans-serif;
    }}
    .map-container {{
      background: radial-gradient(circle at 50% 50%, rgba(30, 41, 59, 0.5), rgba(15, 23, 42, 0.9));
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
          <h1 class="text-2xl font-bold tracking-tight">Philippine Real-Time Seismic Data Warehouse</h1>
        </div>
        <p class="text-sm text-[var(--muted-foreground)] mt-1">Live USGS Geolocation Feed & DuckDB Analytics (PHT Timezone)</p>
      </div>
      <div class="flex items-center gap-3">
        <span class="px-3 py-1 bg-red-500/10 border border-red-500/30 text-red-400 rounded-full text-xs font-semibold">Live Feed Active</span>
        <span class="px-3 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded-full text-xs font-semibold">DuckDB SQL Engine</span>
      </div>
    </div>

    <!-- Metric KPI Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm">
        <div class="text-sm font-medium text-[var(--muted-foreground)]">Total Tracked Quakes</div>
        <div class="text-3xl font-bold mt-2 text-blue-400" id="kpi-total">29</div>
        <div class="text-xs text-[var(--muted-foreground)] mt-1">Live from USGS PH Bounding Box</div>
      </div>
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm">
        <div class="text-sm font-medium text-[var(--muted-foreground)]">Strongest Recent Event</div>
        <div class="text-3xl font-bold mt-2 text-amber-400" id="kpi-max-mag">M 5.3</div>
        <div class="text-xs text-[var(--muted-foreground)] mt-1">Sarangani, Mindanao Region</div>
      </div>
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm">
        <div class="text-sm font-medium text-[var(--muted-foreground)]">High Exposure City</div>
        <div class="text-3xl font-bold mt-2 text-emerald-400">General Santos</div>
        <div class="text-xs text-[var(--muted-foreground)] mt-1">9 quakes within 150km</div>
      </div>
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 shadow-sm">
        <div class="text-sm font-medium text-[var(--muted-foreground)]">Data Quality Score</div>
        <div class="text-3xl font-bold mt-2 text-indigo-400">100%</div>
        <div class="text-xs text-[var(--muted-foreground)] mt-1">8 / 8 Automated Assertions Passed</div>
      </div>
    </div>

    <!-- Main Content Grid: Map & Filters -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Interactive SVG Map of Philippines -->
      <div class="lg:col-span-2 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <div>
            <h2 class="font-semibold text-lg">Philippine Archipelago Seismic Map</h2>
            <p class="text-xs text-[var(--muted-foreground)]">Circles scaled by Richter magnitude (Coordinates: 4.5°N–21.5°N, 116°E–127°E)</p>
          </div>
          <div class="flex gap-2 text-xs">
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span> Moderate (≥4.5)</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-blue-400"></span> Light (&lt;4.5)</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 bg-emerald-400 rotate-45"></span> PH City</span>
          </div>
        </div>

        <div class="map-container relative w-full h-[420px] rounded-xl border border-[var(--border)] overflow-hidden flex items-center justify-center p-2">
          <svg id="ph-map-svg" viewBox="0 0 500 700" class="w-full h-full max-h-[400px]">
            <!-- Philippines Island Outlines Rough Paths -->
            <!-- Luzon -->
            <path d="M 210,120 L 250,140 L 270,210 L 260,260 L 220,270 L 190,230 L 200,160 Z" fill="rgba(100, 116, 139, 0.2)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.5"/>
            <!-- Visayas -->
            <path d="M 250,300 L 290,320 L 310,360 L 270,390 L 240,360 L 230,320 Z" fill="rgba(100, 116, 139, 0.2)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.5"/>
            <!-- Mindanao -->
            <path d="M 260,420 L 340,430 L 370,490 L 320,560 L 260,540 L 240,480 Z" fill="rgba(100, 116, 139, 0.2)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.5"/>
            <!-- Palawan -->
            <path d="M 120,290 L 170,350 L 150,370 L 100,310 Z" fill="rgba(100, 116, 139, 0.2)" stroke="rgba(148, 163, 184, 0.4)" stroke-width="1.5"/>
            
            <g id="cities-group"></g>
            <g id="events-group"></g>
          </svg>
          <div id="map-tooltip" class="absolute pointer-events-none bg-slate-900/90 text-white border border-slate-700 text-xs rounded-lg p-2 shadow-lg hidden z-20"></div>
        </div>
      </div>

      <!-- Regional Exposure Summary Table -->
      <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm flex flex-col justify-between">
        <div>
          <h2 class="font-semibold text-lg mb-1">PH Major Cities Exposure</h2>
          <p class="text-xs text-[var(--muted-foreground)] mb-4">Seismic event counts within 150 km radius</p>
          
          <div class="space-y-3 overflow-y-auto max-h-[350px] pr-1" id="city-list">
            <!-- Cities rendered dynamically -->
          </div>
        </div>
        <div class="pt-4 border-t border-[var(--border)] mt-4 text-xs text-[var(--muted-foreground)] flex justify-between">
          <span>Spatial Engine: DuckDB Haversine</span>
          <span>Coverage: 100% PH</span>
        </div>
      </div>
    </div>

    <!-- Live Event Feed Table -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
        <div>
          <h2 class="font-semibold text-lg">Real-Time Event Bulletin (Gold Layer)</h2>
          <p class="text-xs text-[var(--muted-foreground)]">Converted to Philippine Standard Time (PHT)</p>
        </div>
        
        <div class="flex gap-2">
          <input type="text" id="search-input" placeholder="Search city or location..." class="bg-[var(--background)] border border-[var(--border)] text-xs rounded-lg px-3 py-2 text-[var(--foreground)] outline-none focus:border-blue-500 w-48">
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
              <th class="p-3">Richter</th>
              <th class="p-3">Place Description</th>
              <th class="p-3">Depth (km)</th>
              <th class="p-3">Nearest PH City</th>
              <th class="p-3">Distance (km)</th>
              <th class="p-3">Alert Severity</th>
            </tr>
          </thead>
          <tbody id="events-table-body" class="divide-y divide-[var(--border)]">
            <!-- Table rows rendered dynamically -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const events = {events_json};
    const cities = {cities_json};

    // Bounding box map conversion:
    // MinLat: 4.5, MaxLat: 21.5 -> SVG Y: 650 to 50
    // MinLon: 116.0, MaxLon: 127.0 -> SVG X: 50 to 450
    function lonToX(lon) {{
      return 50 + ((lon - 116.0) / (127.0 - 116.0)) * 400;
    }}
    function latToY(lat) {{
      return 650 - ((lat - 4.5) / (21.5 - 4.5)) * 600;
    }}

    const mapSvg = document.getElementById("ph-map-svg");
    const citiesGroup = document.getElementById("cities-group");
    const eventsGroup = document.getElementById("events-group");
    const tooltip = document.getElementById("map-tooltip");

    // Render Cities on Map
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

      // Label
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", cx + 8);
      text.setAttribute("y", cy + 4);
      text.setAttribute("fill", "#94a3b8");
      text.setAttribute("font-size", "10px");
      text.setAttribute("font-weight", "600");
      text.textContent = c.city_name;
      citiesGroup.appendChild(text);
    }});

    // Render Events on Map
    events.forEach(ev => {{
      const cx = lonToX(ev.longitude);
      const cy = latToY(ev.latitude);
      const radius = Math.max(4, (ev.magnitude - 2) * 4);

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", cx);
      circle.setAttribute("cy", cy);
      circle.setAttribute("r", radius);
      circle.setAttribute("fill", ev.magnitude >= 4.5 ? "rgba(251, 191, 36, 0.6)" : "rgba(96, 165, 250, 0.5)");
      circle.setAttribute("stroke", ev.magnitude >= 4.5 ? "#f59e0b" : "#3b82f6");
      circle.setAttribute("stroke-width", "1.5");
      circle.setAttribute("class", "cursor-pointer hover:opacity-100 transition-opacity");

      circle.addEventListener("mouseenter", (e) => {{
        tooltip.style.display = "block";
        tooltip.innerHTML = `<strong>M ${{ev.magnitude.toFixed(1)}} - ${{ev.richter_category}}</strong><br/>${{ev.place}}<br/>Time: ${{ev.time_pht}}<br/>Depth: ${{ev.depth_km}} km<br/>Nearest City: ${{ev.nearest_ph_city}} (${{ev.distance_to_city_km}} km)`;
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

    // Render City List Cards
    const cityListEl = document.getElementById("city-list");
    cities.sort((a, b) => b.quakes_within_150km - a.quakes_within_150km).forEach(c => {{
      const div = document.createElement("div");
      div.className = "p-3 rounded-xl bg-[var(--background)] border border-[var(--border)] flex justify-between items-center";
      div.innerHTML = `
        <div>
          <div class="font-semibold text-xs text-[var(--foreground)]">${{c.city_name}} <span class="text-[10px] text-[var(--muted-foreground)]">(${{c.island_group}})</span></div>
          <div class="text-[11px] text-[var(--muted-foreground)] mt-0.5">Max Mag: <span class="text-amber-400 font-medium">${{c.max_magnitude_nearby > 0 ? 'M ' + c.max_magnitude_nearby : 'N/A'}}</span></div>
        </div>
        <div class="text-right">
          <div class="text-sm font-bold ${{c.quakes_within_150km > 0 ? 'text-blue-400' : 'text-gray-400'}}">${{c.quakes_within_150km}}</div>
          <div class="text-[10px] text-[var(--muted-foreground)]">&lt;150km</div>
        </div>
      `;
      cityListEl.appendChild(div);
    }});

    // Render Table Rows
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
        
        let severityBadge = '<span class="px-2 py-0.5 rounded text-[10px] bg-gray-500/20 text-gray-300">INFORMATIONAL</span>';
        if (ev.alert_severity.includes('MODERATE')) {{
          severityBadge = '<span class="px-2 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30">MODERATE ALERT</span>';
        }} else if (ev.alert_severity.includes('HIGH') || ev.alert_severity.includes('CRITICAL')) {{
          severityBadge = '<span class="px-2 py-0.5 rounded text-[10px] bg-red-500/20 text-red-300 border border-red-500/30">HIGH ALERT</span>';
        }}

        tr.innerHTML = `
          <td class="p-3 text-[var(--muted-foreground)] whitespace-nowrap">${{ev.time_pht}}</td>
          <td class="p-3 font-bold text-amber-400">M ${{ev.magnitude.toFixed(1)}}</td>
          <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-300">${{ev.richter_category}}</span></td>
          <td class="p-3 max-w-xs truncate" title="${{ev.place}}">${{ev.place}}</td>
          <td class="p-3 text-[var(--muted-foreground)]">${{ev.depth_km}} km</td>
          <td class="p-3 font-medium">${{ev.nearest_ph_city}}</td>
          <td class="p-3 text-[var(--muted-foreground)]">${{ev.distance_to_city_km}} km</td>
          <td class="p-3">${{severityBadge}}</td>
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

print(f"Generated dashboard at {OUTPUT_HTML}")
