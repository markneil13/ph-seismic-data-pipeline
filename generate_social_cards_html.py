import os
import json
import duckdb
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "crypto_warehouse.duckdb")
HTML_OUT_PATH = os.path.join(BASE_DIR, "crypto_social_cards.html")

def generate_social_cards_page():
    print("[SOCIAL CARDS BUILDER] Generating Tailwind CSS Social Media Cards with Download Button...")
    con = duckdb.connect(DB_PATH)
    df_signals = con.execute("SELECT * FROM gold.mart_trading_signals ORDER BY ml_bullish_prob_pct DESC").fetchdf()
    con.close()
    
    cards_html = ""
    for idx, row in df_signals.iterrows():
        symbol = row['symbol']
        ticker = symbol.replace("USDT", "")
        coin_name = row['coin_name']
        price = row['latest_close_price']
        rsi = row['rsi_14']
        vol = row['volatility_annualized'] * 100
        prob = row['ml_bullish_prob_pct']
        signal = row['signal']
        risk = row['volatility_risk']
        ret_7d = row['return_7d_pct']
        
        # Signal Theme
        if "STRONG BUY" in signal:
            badge_class = "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
            border_accent = "border-emerald-500/50"
            sig_icon = "fa-arrow-trend-up"
            glow_color = "rgba(16, 185, 129, 0.15)"
        elif "BUY" in signal:
            badge_class = "bg-green-500/20 text-green-400 border-green-500/40"
            border_accent = "border-green-500/40"
            sig_icon = "fa-arrow-up"
            glow_color = "rgba(34, 197, 94, 0.12)"
        elif "STRONG SELL" in signal:
            badge_class = "bg-rose-500/20 text-rose-400 border-rose-500/40"
            border_accent = "border-rose-500/50"
            sig_icon = "fa-arrow-trend-down"
            glow_color = "rgba(244, 63, 94, 0.15)"
        elif "SELL" in signal:
            badge_class = "bg-red-500/20 text-red-400 border-red-500/40"
            border_accent = "border-red-500/40"
            sig_icon = "fa-arrow-down"
            glow_color = "rgba(239, 68, 68, 0.12)"
        else:
            badge_class = "bg-amber-500/20 text-amber-400 border-amber-500/40"
            border_accent = "border-amber-500/40"
            sig_icon = "fa-minus"
            glow_color = "rgba(245, 158, 11, 0.12)"
            
        card_id = f"card_{ticker.lower()}"
        
        cards_html += f"""
        <!-- Card Container -->
        <div class="flex flex-col items-center gap-3">
            <!-- Render Target for PNG Export -->
            <div id="{card_id}" class="w-[600px] h-[340px] bg-slate-900 border {border_accent} rounded-2xl p-6 relative overflow-hidden flex flex-col justify-between shadow-2xl font-sans" style="box-shadow: 0 0 40px {glow_color};">
                
                <!-- Background Subtle Grid Pattern -->
                <div class="absolute inset-0 opacity-10 bg-[radial-gradient(#3b82f6_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none"></div>

                <!-- Card Header -->
                <div class="flex justify-between items-start z-10">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-xl font-black text-blue-400">
                            {ticker[:3]}
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                <h3 class="text-2xl font-black tracking-tight text-white">{ticker} <span class="text-sm font-normal text-slate-400">/ USD</span></h3>
                            </div>
                            <p class="text-xs text-slate-400 font-medium">{coin_name} • Market Intelligence</p>
                        </div>
                    </div>
                    
                    <!-- Signal Pill -->
                    <div class="px-3.5 py-1.5 rounded-full border text-xs font-bold flex items-center gap-1.5 uppercase tracking-wider {badge_class}">
                        <i class="fa-solid {sig_icon}"></i> {signal}
                    </div>
                </div>

                <!-- Main Metrics Grid -->
                <div class="grid grid-cols-3 gap-3 my-2 z-10">
                    <div class="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Current Price</span>
                        <div class="text-xl font-extrabold text-white mt-0.5">${price:,.2f}</div>
                        <div class="text-[11px] font-semibold {'text-emerald-400' if ret_7d > 0 else 'text-rose-400'} mt-0.5">
                            {'+' if ret_7d > 0 else ''}{ret_7d:.1f}% (7D)
                        </div>
                    </div>

                    <div class="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">24H ML Forecast</span>
                        <div class="text-xl font-extrabold text-blue-400 mt-0.5">{prob:.1f}% <span class="text-xs font-normal text-slate-400">Bullish</span></div>
                        <div class="w-full bg-slate-700 h-1.5 rounded-full mt-2 overflow-hidden">
                            <div class="bg-blue-500 h-full rounded-full" style="width: {prob}%"></div>
                        </div>
                    </div>

                    <div class="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">RSI (14) Momentum</span>
                        <div class="text-xl font-extrabold text-slate-200 mt-0.5">{rsi:.1f}</div>
                        <div class="text-[11px] font-medium text-slate-400 mt-0.5">
                            Vol: <span class="text-amber-300 font-semibold">{vol:.1f}%</span>
                        </div>
                    </div>
                </div>

                <!-- Card Footer / Branding -->
                <div class="flex justify-between items-center pt-3 border-t border-slate-800 text-[11px] text-slate-400 z-10">
                    <div class="flex items-center gap-1.5 text-blue-400 font-semibold">
                        <i class="fa-solid fa-brain text-xs"></i> Random Forest ML Model
                    </div>
                    <div class="text-slate-500 font-mono text-[10px]">
                        Risk: <span class="text-slate-300 font-sans">{risk}</span>
                    </div>
                    <div class="flex items-center gap-1 font-bold text-slate-300">
                        <i class="fa-brands fa-x-twitter"></i> @MarketAI
                    </div>
                </div>
            </div>

            <!-- Download PNG Action Button -->
            <button onclick="downloadCard('{card_id}', '{ticker}_Social_Card.png')" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 active:scale-95 transition-all text-white font-semibold text-sm rounded-lg shadow-lg flex items-center gap-2">
                <i class="fa-solid fa-download"></i> Save {ticker} PNG Graphic
            </button>
        </div>
        """

    full_page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Social Media Graphic Cards — Ready to Export</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- html2canvas for High Resolution PNG Download -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        body {{ background-color: #0b0f19; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }}
    </style>
</head>
<body class="p-8 min-h-screen text-slate-100">
    <div class="max-w-6xl mx-auto space-y-8">
        
        <!-- Header -->
        <div class="text-center space-y-2">
            <h1 class="text-4xl font-extrabold text-white flex items-center justify-center gap-3">
                <i class="fa-brands fa-x-twitter text-blue-400"></i> Crypto Social Media Graphic Cards
            </h1>
            <p class="text-slate-400 text-sm max-w-xl mx-auto">
                Clean, human-designed fintech cards built with Tailwind CSS. Click <span class="text-blue-400 font-semibold">"Save PNG Graphic"</span> below any card to instantly export high-res images for X / Twitter!
            </p>
        </div>

        <!-- Cards Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-10 justify-items-center">
            {cards_html}
        </div>

    </div>

    <script>
        function downloadCard(elementId, filename) {{
            const cardElement = document.getElementById(elementId);
            
            // Render at 2x scale for ultra-crisp Retina PNG output
            html2canvas(cardElement, {{
                scale: 2.5,
                useCORS: true,
                backgroundColor: null,
                logging: false
            }}).then(canvas => {{
                const link = document.createElement('a');
                link.download = filename;
                link.href = canvas.toDataURL('image/png');
                link.click();
            }});
        }}
    </script>
</body>
</html>
"""

    with open(HTML_OUT_PATH, "w", encoding="utf-8") as f:
        f.write(full_page_html)
    print(f"  -> Successfully generated Tailwind social cards page at {HTML_OUT_PATH}")

if __name__ == "__main__":
    generate_social_cards_page()
