# Philippine Regional Monitoring Grid for Super El Niño & Drought Tracking
# 18 Critical Agricultural Basins, Reservoirs, and Hydroelectric Catchments
from src.el_nino_ph.config_ph import MAP_CONFIG, project_ph_coords

PH_REGIONS = [
    {
        "region_id": "PH_CENTRAL_LUZON",
        "region_name": "Central Luzon (Nueva Ecija / Pampanga)",
        "island_group": "Luzon",
        "latitude": 15.4858,
        "longitude": 120.9673,
        "economic_role": "National Rice Granary (Palay Hub)",
        "critical_infrastructure": "Pantabangan Reservoir & Pampanga River"
    },
    {
        "region_id": "PH_ANGAT_BASIN",
        "region_name": "Angat Dam Catchment (Bulacan)",
        "island_group": "Luzon",
        "latitude": 14.9083,
        "longitude": 121.1444,
        "economic_role": "Metro Manila Primary Potable Water Supply",
        "critical_infrastructure": "Angat Hydro Reservoir (212m Spill Level)"
    },
    {
        "region_id": "PH_CAGAYAN_ISABELA",
        "region_name": "Cagayan Valley (Isabela / Ilagan)",
        "island_group": "Luzon",
        "latitude": 17.1485,
        "longitude": 121.8889,
        "economic_role": "Major Corn & Grain Production Valley",
        "critical_infrastructure": "Magat Dam & Cagayan River Basin"
    },
    {
        "region_id": "PH_PANGASINAN_AGNO",
        "region_name": "Pangasinan (Agno River Basin)",
        "island_group": "Luzon",
        "latitude": 15.9281,
        "longitude": 120.3347,
        "economic_role": "Agri-Fisheries & Lowland Rice Bowl",
        "critical_infrastructure": "San Roque Hydro Dam"
    },
    {
        "region_id": "PH_ILOCOS_NORTE",
        "region_name": "Ilocos Norte (Laoag Arid Corridor)",
        "island_group": "Luzon",
        "latitude": 18.1960,
        "longitude": 120.5927,
        "economic_role": "High-Value Cash Crops & Garlic/Onion Belt",
        "critical_infrastructure": "Padsan River Irrigation System"
    },
    {
        "region_id": "PH_BENGUET_HIGHLANDS",
        "region_name": "Benguet Highlands (La Trinidad)",
        "island_group": "Luzon",
        "latitude": 16.4550,
        "longitude": 120.5880,
        "economic_role": "Salad Bowl of the Philippines (Highland Veg)",
        "critical_infrastructure": "Ambuklao / Binga Dam Cascade"
    },
    {
        "region_id": "PH_BICOL_ALBAY",
        "region_name": "Bicol Basin (Albay / Legazpi)",
        "island_group": "Luzon",
        "latitude": 13.1391,
        "longitude": 123.7438,
        "economic_role": "Coconut & Abaca Agricultural Cluster",
        "critical_infrastructure": "Yawa & Quinale River Basin"
    },
    {
        "region_id": "PH_MINDORO_ORIENTAL",
        "region_name": "Oriental Mindoro (Calapan Plains)",
        "island_group": "Luzon",
        "latitude": 13.4115,
        "longitude": 121.1803,
        "economic_role": "MIMAROPA Food Gateway & Citrus Orchards",
        "critical_infrastructure": "Naujan Lake Basin & Bucayao River"
    },
    {
        "region_id": "PH_PALAWAN_CENTRAL",
        "region_name": "Palawan Mainland (Puerto Princesa)",
        "island_group": "Palawan",
        "latitude": 9.7392,
        "longitude": 118.7353,
        "economic_role": "Biosphere Frontier, Fisheries & Cashew Belt",
        "critical_infrastructure": "Iwahig Catchment & Montible River"
    },
    {
        "region_id": "PH_ILOILO_PANAY",
        "region_name": "Iloilo Plains (Western Visayas)",
        "island_group": "Visayas",
        "latitude": 10.7202,
        "longitude": 122.5621,
        "economic_role": "Western Visayas Rice & Sugar Center",
        "critical_infrastructure": "Jalaur River Multipurpose Dam"
    },
    {
        "region_id": "PH_NEGROS_OCCIDENTAL",
        "region_name": "Negros Occidental (Bacolod Sugarcane Belt)",
        "island_group": "Visayas",
        "latitude": 10.6765,
        "longitude": 122.9509,
        "economic_role": "Sugar Capital of the Philippines (>50% Output)",
        "critical_infrastructure": "Binalbagan-Isabela River Basin"
    },
    {
        "region_id": "PH_METRO_CEBU",
        "region_name": "Metro Cebu (Central Visayas)",
        "island_group": "Visayas",
        "latitude": 10.3157,
        "longitude": 123.8854,
        "economic_role": "Regional Industrial & Urban Hub",
        "critical_infrastructure": "Buhisan Dam & Mananga Aquifer (Severe Karst Stress)"
    },
    {
        "region_id": "PH_BOHOL_BASIN",
        "region_name": "Bohol Basin (Wahig-Inabanga)",
        "island_group": "Visayas",
        "latitude": 9.8800,
        "longitude": 124.2100,
        "economic_role": "Central Visayas Rice Reservoir Hub",
        "critical_infrastructure": "Malinao & Bayongan Reservoirs"
    },
    {
        "region_id": "PH_LEYTE_VALLEY",
        "region_name": "Leyte Valley (Tacloban Ag-Corridor)",
        "island_group": "Visayas",
        "latitude": 11.2444,
        "longitude": 124.9984,
        "economic_role": "Eastern Visayas Agri-Trading & Geothermal Hub",
        "critical_infrastructure": "Binahaan River Catchment"
    },
    {
        "region_id": "PH_MINDANAO_BUKIDNON",
        "region_name": "Bukidnon Highlands (Northern Mindanao)",
        "island_group": "Mindanao",
        "latitude": 8.1575,
        "longitude": 125.1278,
        "economic_role": "Mindanao Grain & Agro-Plantation Hub (Del Monte/Pineapple)",
        "critical_infrastructure": "Pulangi IV Hydro Reservoir"
    },
    {
        "region_id": "PH_DAVAO_NORTE",
        "region_name": "Davao del Norte (Tagum Banana Belt)",
        "island_group": "Mindanao",
        "latitude": 7.4478,
        "longitude": 125.8078,
        "economic_role": "Cavendish Banana & Cacao Export Epicenter",
        "critical_infrastructure": "Libuganon River Catchment"
    },
    {
        "region_id": "PH_SOUTH_COTABATO",
        "region_name": "South Cotabato / General Santos (SOCCSKSARGEN)",
        "island_group": "Mindanao",
        "latitude": 6.1164,
        "longitude": 125.1716,
        "economic_role": "Tuna Capital & DOLE Pineapple Export Basin",
        "critical_infrastructure": "Silway River & Lake Sebu Watershed"
    },
    {
        "region_id": "PH_NORTH_COTABATO",
        "region_name": "North Cotabato (Central Mindanao Rice & Rubber)",
        "island_group": "Mindanao",
        "latitude": 7.1895,
        "longitude": 124.8988,
        "economic_role": "Liguasan Marsh Agro-Ecological Catchment",
        "critical_infrastructure": "Rio Grande de Mindanao / Kabacan River"
    }
]

for r in PH_REGIONS:
    px, py = project_ph_coords(r["longitude"], r["latitude"])
    r["svg_x"] = px
    r["svg_y"] = py
