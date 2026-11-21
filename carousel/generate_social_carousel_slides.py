import os
import sys
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "social_carousel")
ARTIFACT_DIR = r"C:\Users\marki\.gemini\antigravity\brain\3f02062b-df98-4788-a2f8-8ca1213a27ef\social_carousel"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

# 1080 x 1350 (4:5 Aspect Ratio - Standard for IG & TikTok Carousels)
WIDTH = 1080
HEIGHT = 1350

# Colors (Modern Tech Dark Mode)
BG_COLOR = (11, 15, 25)         # Deep slate navy
CARD_BG = (19, 27, 44)          # Card container
TEXT_WHITE = (248, 250, 252)
TEXT_MUTED = (148, 163, 184)
ACCENT_RED = (239, 68, 68)      # El Nino / Seismic alert
ACCENT_AMBER = (245, 158, 11)   # Warning / Accent
ACCENT_BLUE = (59, 130, 246)    # Tech / Pipeline
ACCENT_EMERALD = (16, 185, 129) # Success
BORDER_COLOR = (51, 65, 85)

def get_font(size, bold=False):
    """Attempts to load clean system fonts on Windows, falling back to default."""
    font_names = [
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\tahomabd.ttf" if bold else "C:\\Windows\\Fonts\\tahoma.ttf",
    ]
    for fn in font_names:
        if os.path.exists(fn):
            try:
                return ImageFont.truetype(fn, size)
            except Exception:
                continue
    return ImageFont.load_default()

def draw_header_badge(draw, slide_num, total_slides, category="DATA ENGINEERING"):
    # Header badge
    draw.rounded_rectangle([70, 60, 340, 110], radius=15, fill=(30, 41, 59), outline=BORDER_COLOR, width=2)
    font_badge = get_font(22, bold=True)
    draw.text((95, 74), f"• {category}", fill=ACCENT_AMBER, font=font_badge)
    
    font_slide = get_font(24, bold=True)
    draw.text((WIDTH - 150, 72), f"{slide_num}/{total_slides}", fill=TEXT_MUTED, font=font_slide)

def draw_footer_branding(draw):
    draw.line([70, HEIGHT - 100, WIDTH - 70, HEIGHT - 100], fill=BORDER_COLOR, width=2)
    font_foot = get_font(22, bold=True)
    draw.text((70, HEIGHT - 80), "@data.engineering.ph", fill=TEXT_MUTED, font=font_foot)
    draw.text((WIDTH - 270, HEIGHT - 80), "Swipe to learn ➔", fill=ACCENT_BLUE, font=font_foot)

# -------------------------------------------------------------
# SLIDE 1: THE VIRAL HOOK
# -------------------------------------------------------------
def make_slide_1():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_header_badge(draw, 1, 7, "REAL-WORLD TECH")
    
    # Sub-tagline
    draw.text((70, 220), "FROM 'FAKING IT' TO BUILDING IT:", fill=ACCENT_RED, font=get_font(32, bold=True))
    
    # Big Hook Headline
    title_font = get_font(68, bold=True)
    draw.text((70, 280), "How I Built a Real-Time", fill=TEXT_WHITE, font=title_font)
    draw.text((70, 365), "Super El Niño &", fill=ACCENT_AMBER, font=title_font)
    draw.text((70, 450), "Seismic Engine", fill=ACCENT_AMBER, font=title_font)
    draw.text((70, 535), "with a $0 Budget.", fill=TEXT_WHITE, font=title_font)
    
    # Content Card
    draw.rounded_rectangle([70, 660, WIDTH - 70, 1080], radius=24, fill=CARD_BG, outline=BORDER_COLOR, width=2)
    
    draw.text((110, 700), "WHAT THIS COVERS:", fill=TEXT_WHITE, font=get_font(28, bold=True))
    
    points = [
        ("• Zero Cloud Bills:", " Built 100% locally on Python, DuckDB & Parquet."),
        ("• Free Real-Time APIs:", " Live NOAA Ocean SST + USGS Earthquakes."),
        ("• Medallion Architecture:", " Bronze -> Silver -> Gold Star Schema."),
        ("• Visual Deliverables:", " Real Coastline Map + 4-Page Executive PDF Report.")
    ]
    
    y = 760
    for title, desc in points:
        draw.text((110, y), title, fill=ACCENT_BLUE, font=get_font(26, bold=True))
        draw.text((380, y), desc, fill=TEXT_WHITE, font=get_font(24))
        y += 75
        
    draw.text((70, 1140), "No fancy subscriptions. No paid APIs. Just real engineering.", fill=TEXT_MUTED, font=get_font(28, bold=True))
    draw_footer_branding(draw)
    return img

# -------------------------------------------------------------
# SLIDE 2: THE ZERO-DOLLAR STACK
# -------------------------------------------------------------
def make_slide_2():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_header_badge(draw, 2, 7, "THE $0 TECH STACK")
    
    draw.text((70, 180), "THE BIGGEST MYTH IN TECH:", fill=ACCENT_RED, font=get_font(30, bold=True))
    draw.text((70, 235), "You don't need AWS or", fill=TEXT_WHITE, font=get_font(60, bold=True))
    draw.text((70, 310), "$1,000 Snowflake bills.", fill=TEXT_WHITE, font=get_font(60, bold=True))
    
    # 4 Tech Cards
    techs = [
        ("DuckDB", "Fast Embedded Analytical SQL Warehouse. Runs inside Python on local memory with zero infrastructure setup.", ACCENT_AMBER),
        ("Apache Parquet", "Industry-standard compressed columnar storage. Blazing fast reads and partitioned by date.", ACCENT_BLUE),
        ("NOAA & USGS APIs", "100% Free Public Government Data. No rate limits, no API keys, no credit card required.", ACCENT_EMERALD),
        ("Scikit-Learn & ReportLab", "Unsupervised spatial clustering (DBSCAN) + automated publication-grade PDF report engine.", ACCENT_RED)
    ]
    
    y = 420
    for name, desc, col in techs:
        draw.rounded_rectangle([70, y, WIDTH - 70, y + 150], radius=20, fill=CARD_BG, outline=BORDER_COLOR, width=2)
        draw.rectangle([70, y + 25, 82, y + 125], fill=col)
        draw.text((110, y + 25), name, fill=TEXT_WHITE, font=get_font(32, bold=True))
        
        # Word wrap description
        words = desc.split()
        line1 = " ".join(words[:11])
        line2 = " ".join(words[11:])
        draw.text((110, y + 70), line1, fill=TEXT_MUTED, font=get_font(23))
        if line2:
            draw.text((110, y + 102), line2, fill=TEXT_MUTED, font=get_font(23))
        y += 180
        
    draw_footer_branding(draw)
    return img

# -------------------------------------------------------------
# SLIDE 3: THE CLIMATE CRISIS (Super El Niño +3.25°C)
# -------------------------------------------------------------
def make_slide_3():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_header_badge(draw, 3, 7, "THE PROBLEM & SCIENCE")
    
    draw.text((70, 180), "WHY THIS MATTERS IN SOUTHEAST ASIA:", fill=ACCENT_AMBER, font=get_font(28, bold=True))
    draw.text((70, 235), "Tracking the 2026", fill=TEXT_WHITE, font=get_font(60, bold=True))
    draw.text((70, 310), "'Super El Niño' Crisis.", fill=ACCENT_RED, font=get_font(60, bold=True))
    
    # Large Stat Card
    draw.rounded_rectangle([70, 410, WIDTH - 70, 650], radius=24, fill=(35, 15, 20), outline=ACCENT_RED, width=3)
    draw.text((110, 440), "PACIFIC OCEAN NIÑO 3.4 ANOMALY:", fill=TEXT_MUTED, font=get_font(24, bold=True))
    draw.text((110, 480), "+3.25°C", fill=ACCENT_RED, font=get_font(95, bold=True))
    draw.text((540, 520), "OFFICIAL STATUS: SUPER EL NIÑO", fill=TEXT_WHITE, font=get_font(26, bold=True))
    draw.text((540, 560), "(Historic Threshold is ≥ +2.0°C)", fill=TEXT_MUTED, font=get_font(22))
    
    # What this means on the ground
    draw.text((70, 690), "GROUND IMPACT ACROSS 12 BASINS:", fill=TEXT_WHITE, font=get_font(32, bold=True))
    
    impacts = [
        ("🇵🇭 Central Luzon (Rice Granary):", "81.2% rainfall deficit! Only 33.9mm in 30 days."),
        ("🇵🇭 Angat Dam (Manila Potable Water):", "77.5% rain deficit; water watch active."),
        ("🇮🇩 East Java (Brantas Basin):", "49.5% deficit impacting sugar & second rice crop."),
        ("🇻🇳 Central Highlands (Coffee Hub):", "9 consecutive dry days; topsoil depleted.")
    ]
    
    y = 750
    for hub, desc in impacts:
        draw.rounded_rectangle([70, y, WIDTH - 70, y + 105], radius=16, fill=CARD_BG, outline=BORDER_COLOR, width=2)
        draw.text((100, y + 18), hub, fill=ACCENT_AMBER, font=get_font(25, bold=True))
        draw.text((100, y + 55), desc, fill=TEXT_WHITE, font=get_font(23))
        y += 125
        
    draw_footer_branding(draw)
    return img

# -------------------------------------------------------------
# SLIDE 4: THE MEDALLION PIPELINE
# -------------------------------------------------------------
def make_slide_4():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_header_badge(draw, 4, 7, "DATA PIPELINE ARCHITECTURE")
    
    draw.text((70, 180), "HOW SENIOR ENGINEERS BUILD IT:", fill=ACCENT_BLUE, font=get_font(28, bold=True))
    draw.text((70, 235), "The Medallion Pipeline", fill=TEXT_WHITE, font=get_font(60, bold=True))
    draw.text((70, 310), "(Bronze ➔ Silver ➔ Gold)", fill=TEXT_MUTED, font=get_font(50, bold=True))
    
    layers = [
        ("BRONZE LAYER (Raw Ingestion)", 
         "Pulls real-time NOAA SST anomalies & Open-Meteo daily weather/soil data. Saves raw partitioned Parquet files by date.", 
         (205, 127, 50)),
        ("SILVER LAYER (DuckDB SQL Transformations)", 
         "Calculates Consecutive Dry Days (CDD) with window functions, 30-day rolling rainfall sums, and deduplicates records.", 
         (148, 163, 184)),
        ("GOLD LAYER (Dimensional Analytics)", 
         "Builds Star Schema: dim_sea_regions, fact_climate_daily, and dm_drought_bulletin with a 0-100 Drought Index (SEDI).", 
         (234, 179, 8))
    ]
    
    y = 400
    for name, desc, col in layers:
        draw.rounded_rectangle([70, y, WIDTH - 70, y + 195], radius=20, fill=CARD_BG, outline=BORDER_COLOR, width=2)
        draw.rounded_rectangle([100, y + 25, 450, y + 68], radius=8, fill=col)
        draw.text((115, y + 32), name.split(" (")[0], fill=(15, 23, 42), font=get_font(24, bold=True))
        
        words = desc.split()
        line1 = " ".join(words[:11])
        line2 = " ".join(words[11:23])
        line3 = " ".join(words[23:])
        draw.text((105, y + 85), line1, fill=TEXT_WHITE, font=get_font(24))
        if line2:
            draw.text((105, y + 120), line2, fill=TEXT_WHITE, font=get_font(24))
        if line3:
            draw.text((105, y + 155), line3, fill=TEXT_WHITE, font=get_font(24))
        y += 225
        
    # Data Quality Callout
    draw.rounded_rectangle([70, 1090, WIDTH - 70, 1190], radius=16, fill=(15, 23, 42), outline=ACCENT_EMERALD, width=2)
    draw.text((100, 1115), "🛡️ 100% Quality Tested:", fill=ACCENT_EMERALD, font=get_font(26, bold=True))
    draw.text((100, 1150), "Unit tests with corrupted data prove every assertion catches bad data.", fill=TEXT_MUTED, font=get_font(22))
    
    draw_footer_branding(draw)
    return img

# -------------------------------------------------------------
# SLIDE 5: THE INTERACTIVE DASHBOARD
# -------------------------------------------------------------
def make_slide_5():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_header_badge(draw, 5, 7, "PRODUCT DELIVERABLE #1")
    
    draw.text((70, 180), "DON'T JUST WRITE SCRIPTS:", fill=ACCENT_EMERALD, font=get_font(28, bold=True))
    draw.text((70, 235), "Build Live Interactive", fill=TEXT_WHITE, font=get_font(60, bold=True))
    draw.text((70, 310), "Visual Dashboards.", fill=ACCENT_BLUE, font=get_font(60, bold=True))
    
    # Feature Showcase Card
    draw.rounded_rectangle([70, 400, WIDTH - 70, 1160], radius=24, fill=CARD_BG, outline=BORDER_COLOR, width=2)
    
    feats = [
        ("🗺️ Real Country Geography", "Accurate SVG landmass coastlines for Philippines, Indonesia, Malaysia, Thailand, Vietnam."),
        ("🌡️ Super El Niño Thermometer", "Dynamic oceanic SST gauge showing current Pacific anomaly status (+3.25°C)."),
        ("⚡ Pulsating Radar Alert Rings", "Active animations on stations experiencing acute drought (Central Luzon & East Java)."),
        ("🔍 Interactive Hover Tooltips", "Hover over any station for 30d rain deficits, consecutive dry days, and soil moisture."),
        ("🖨️ One-Click PDF Export", "Browser print styling allows exporting directly to a formatted PDF anytime.")
    ]
    
    y = 440
    for title, desc in feats:
        draw.text((110, y), title, fill=ACCENT_AMBER, font=get_font(30, bold=True))
        words = desc.split()
        line1 = " ".join(words[:10])
        line2 = " ".join(words[10:])
        draw.text((110, y + 42), line1, fill=TEXT_WHITE, font=get_font(23))
        if line2:
            draw.text((110, y + 74), line2, fill=TEXT_MUTED, font=get_font(23))
        y += 138
        
    draw_footer_branding(draw)
    return img

# -------------------------------------------------------------
# SLIDE 6: THE 4-PAGE PDF REPORT
# -------------------------------------------------------------
def make_slide_6():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_header_badge(draw, 6, 7, "PRODUCT DELIVERABLE #2")
    
    draw.text((70, 180), "WHAT EXECUTIVES ACTUALLY WANT:", fill=ACCENT_AMBER, font=get_font(28, bold=True))
    draw.text((70, 235), "Automated 4-Page", fill=TEXT_WHITE, font=get_font(60, bold=True))
    draw.text((70, 310), "Executive PDF Reports.", fill=ACCENT_RED, font=get_font(60, bold=True))
    
    pages = [
        ("PAGE 1: Executive Briefing & Oceanic Trigger", 
         "High-level callout summary + Matplotlib Niño 3.4 SST Anomaly Trajectory Chart (2020–2026)."),
        ("PAGE 2: Regional Drought Severity Index (SEDI)", 
         "Horizontal ranking bar chart benchmarking all 12 SEA agricultural basins on a 0–100 scale."),
        ("PAGE 3: 12-Basin Hydrological Matrix Table", 
         "Complete matrix with 30d rain (observed vs baseline), deficit %, dry days, and alert tiers."),
        ("PAGE 4: Country Assessments & Infrastructure Alerts", 
         "Disaster risk assessments for PH, ID, VN, TH, MY + Data Architecture integrity notes.")
    ]
    
    y = 410
    for title, desc in pages:
        draw.rounded_rectangle([70, y, WIDTH - 70, y + 160], radius=18, fill=CARD_BG, outline=BORDER_COLOR, width=2)
        draw.text((105, y + 25), title, fill=TEXT_WHITE, font=get_font(28, bold=True))
        words = desc.split()
        line1 = " ".join(words[:11])
        line2 = " ".join(words[11:])
        draw.text((105, y + 68), line1, fill=TEXT_MUTED, font=get_font(23))
        if line2:
            draw.text((105, y + 102), line2, fill=TEXT_MUTED, font=get_font(23))
        y += 185
        
    draw_footer_branding(draw)
    return img

# -------------------------------------------------------------
# SLIDE 7: HOW YOU CAN DO THIS (CTA)
# -------------------------------------------------------------
def make_slide_7():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_header_badge(draw, 7, 7, "HOW TO START")
    
    draw.text((70, 180), "THE BLUEPRINT TO LEVEL UP:", fill=ACCENT_EMERALD, font=get_font(28, bold=True))
    draw.text((70, 235), "Your Roadmap to", fill=TEXT_WHITE, font=get_font(60, bold=True))
    draw.text((70, 310), "Winning DE Roles.", fill=ACCENT_BLUE, font=get_font(60, bold=True))
    
    steps = [
        ("1. Pick a Real-World Problem", "Don't just analyze Titanic or Iris data. Choose natural disasters, climate, or finance."),
        ("2. Use DuckDB + Parquet", "Master modern columnar storage and analytical SQL without needing complex servers."),
        ("3. Write Automated Quality Tests", "Tautological tests are useless. Prove your assertions catch corrupted data."),
        ("4. Ship a Real Visual Product", "Dashboards + Executive PDF reports prove to US clients that you can deliver end-to-end.")
    ]
    
    y = 410
    for num, desc in steps:
        draw.rounded_rectangle([70, y, WIDTH - 70, y + 130], radius=18, fill=CARD_BG, outline=BORDER_COLOR, width=2)
        draw.text((105, y + 20), num, fill=ACCENT_AMBER, font=get_font(28, bold=True))
        draw.text((105, y + 65), desc, fill=TEXT_WHITE, font=get_font(22))
        y += 155
        
    # Big Call to Action Box
    draw.rounded_rectangle([70, 1050, WIDTH - 70, 1190], radius=22, fill=(30, 58, 138), outline=ACCENT_BLUE, width=3)
    draw.text((110, 1075), "Want the complete GitHub repo & code breakdown?", fill=TEXT_WHITE, font=get_font(28, bold=True))
    draw.text((110, 1120), "Comment 'SUPER EL NINO' & I'll send it over! 🚀", fill=ACCENT_AMBER, font=get_font(28, bold=True))
    
    draw_footer_branding(draw)
    return img

def main():
    print("[CAROUSEL] Generating 7 High-Definition Social Media Carousel Slides (1080x1350)...")
    
    slides = [
        ("slide_1_hook.png", make_slide_1()),
        ("slide_2_zero_dollar_stack.png", make_slide_2()),
        ("slide_3_climate_crisis.png", make_slide_3()),
        ("slide_4_medallion_pipeline.png", make_slide_4()),
        ("slide_5_interactive_dashboard.png", make_slide_5()),
        ("slide_6_executive_pdf_report.png", make_slide_6()),
        ("slide_7_roadmap_cta.png", make_slide_7()),
    ]
    
    import shutil
    for fname, slide_img in slides:
        local_path = os.path.join(OUTPUT_DIR, fname)
        artifact_path = os.path.join(ARTIFACT_DIR, fname)
        slide_img.save(local_path, quality=95)
        shutil.copyfile(local_path, artifact_path)
        print(f"  + Saved {fname} (1080x1350)")
        
    print(f"\n[SUCCESS] Generated all 7 slides in: {OUTPUT_DIR}")
    print(f"Synced to conversation artifacts in: {ARTIFACT_DIR}")

if __name__ == "__main__":
    main()
