import os
import duckdb
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "crypto_warehouse.duckdb")
CARDS_DIR = os.path.join(BASE_DIR, "cards")

def generate_individual_cards():
    """Generates standalone HTML files for each cryptocurrency tracked in the pipeline."""
    print("[INDIVIDUAL CARDS BUILDER] Generating separate HTML card files per crypto...")
    os.makedirs(CARDS_DIR, exist_ok=True)
    
    con = duckdb.connect(DB_PATH)
    df_signals = con.execute("SELECT * FROM gold.mart_trading_signals ORDER BY ml_bullish_prob_pct DESC").fetchdf()
    con.close()
    
    index_links = []
    
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
        
        # Color styling
        if "STRONG BUY" in signal:
            badge_class = "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
            border_accent = "border-emerald-500/50"
            sig_icon = "fa-arrow-trend-up"
            glow_color = "rgba(16, 185, 129, 0.2)"
        elif "BUY" in signal:
            badge_class = "bg-green-500/20 text-green-400 border-green-500/40"
            border_accent = "border-green-500/40"
            sig_icon = "fa-arrow-up"
            glow_color = "rgba(34, 197, 94, 0.15)"
        elif "STRONG SELL" in signal:
            badge_class = "bg-rose-500/20 text-rose-400 border-rose-500/40"
            border_accent = "border-rose-500/50"
            sig_icon = "fa-arrow-trend-down"
            glow_color = "rgba(244, 63, 94, 0.2)"
        elif "SELL" in signal:
            badge_class = "bg-red-500/20 text-red-400 border-red-500/40"
            border_accent = "border-red-500/40"
            sig_icon = "fa-arrow-down"
            glow_color = "rgba(239, 68, 68, 0.15)"
        else:
            badge_class = "bg-amber-500/20 text-amber-400 border-amber-500/40"
            border_accent = "border-amber-500/40"
            sig_icon = "fa-minus"
            glow_color = "rgba(245, 158, 11, 0.15)"
            
        file_name = f"{ticker.lower()}_card.html"
        file_path = os.path.join(CARDS_DIR, file_name)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{coin_name} ({ticker}) — Social Media Graphic Card</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- html2canvas -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        body {{ background-color: #090d16; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }}
    </style>
</head>
<body class="min-h-screen flex flex-col items-center justify-center p-6 text-slate-100">
    
    <!-- Top Action Nav -->
    <div class="mb-6 flex items-center gap-4">
        <a href="index.html" class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition-all">
            <i class="fa-solid fa-arrow-left"></i> All Crypto Cards
        </a>
        <button onclick="downloadPNG()" class="px-5 py-2 bg-blue-600 hover:bg-blue-500 active:scale-95 transition-all text-white font-bold text-sm rounded-lg shadow-lg flex items-center gap-2">
            <i class="fa-solid fa-download"></i> Download {ticker} High-Res PNG
        </button>
    </div>

    <!-- Render Container Target for High-Res PNG Export -->
    <div id="card_target" class="w-[600px] h-[340px] bg-slate-900 border {border_accent} rounded-2xl p-6 relative overflow-hidden flex flex-col justify-between shadow-2xl" style="box-shadow: 0 0 50px {glow_color};">
        
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

    <!-- Ready to Post X Copy Box -->
    <div class="mt-8 w-[600px] bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-300">
        <div class="flex justify-between items-center text-slate-400 mb-2 font-sans font-bold">
            <span><i class="fa-brands fa-x-twitter text-blue-400"></i> Post Copy for X:</span>
            <button onclick="copyTweetText()" class="text-blue-400 hover:text-blue-300 text-xs">Copy Text</button>
        </div>
        <textarea id="tweet_text" readonly class="w-full bg-slate-950 border border-slate-800 rounded p-2.5 text-slate-300 h-28 focus:outline-none">🤖 AI MARKET UPDATE: {coin_name} (${ticker})

📊 24h ML Forecast: {prob:.1f}% Bullish Probability
💰 Current Price: ${price:,.2f}
📈 7D Performance: {'+' if ret_7d > 0 else ''}{ret_7d:.1f}%
⚡ RSI (14): {rsi:.1f} | Volatility: {vol:.1f}%
🎯 Consensus Signal: {signal}
⚠️ Risk Level: {risk}

Powered by DuckDB Medallion Pipeline & Random Forest ML 🧠

#Crypto #{ticker} #{coin_name.replace(' ','')} #DataScience #AI #TradingSignals</textarea>
    </div>

    <script>
        function downloadPNG() {{
            const cardElement = document.getElementById('card_target');
            html2canvas(cardElement, {{
                scale: 3,
                useCORS: true,
                backgroundColor: null,
                logging: false
            }}).then(canvas => {{
                const link = document.createElement('a');
                link.download = '{ticker}_Social_Graphic.png';
                link.href = canvas.toDataURL('image/png');
                link.click();
            }});
        }}

        function copyTweetText() {{
            const copyText = document.getElementById("tweet_text");
            copyText.select();
            navigator.clipboard.writeText(copyText.value);
            alert("Copied tweet text to clipboard!");
        }}
    </script>
</body>
</html>
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print(f"  -> Generated standalone card: {file_path}")
        index_links.append((ticker, coin_name, signal, file_name))
        
    # Generate cards/index.html
    index_html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Social Media Graphic Cards Directory</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-slate-950 min-h-screen text-slate-100 p-8">
    <div class="max-w-4xl mx-auto space-y-8">
        <div class="text-center space-y-2">
            <h1 class="text-3xl font-extrabold text-white flex items-center justify-center gap-3">
                <i class="fa-brands fa-x-twitter text-blue-400"></i> Individual Crypto Social Media Cards
            </h1>
            <p class="text-slate-400 text-sm">Select any cryptocurrency below to open its dedicated full-screen graphic card & download high-res PNG assets.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            {"".join([f'''
            <a href="{link[3]}" class="block p-5 bg-slate-900 border border-slate-800 hover:border-blue-500/50 rounded-xl transition-all hover:scale-[1.02] shadow-lg">
                <div class="flex justify-between items-center">
                    <div>
                        <h3 class="text-xl font-bold text-white">{link[0]} <span class="text-xs text-slate-400 font-normal">({link[1]})</span></h3>
                        <p class="text-xs text-slate-400 mt-1">Standalone HTML Graphic Card</p>
                    </div>
                    <span class="px-3 py-1 text-xs rounded-full font-bold bg-slate-800 text-blue-400 border border-slate-700">
                        {link[2]}
                    </span>
                </div>
            </a>
            ''' for link in index_links])}
        </div>
    </div>
</body>
</html>
"""
    index_path = os.path.join(CARDS_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html_content)
        
    print(f"  -> Generated Index Page at {index_path}")
    print("[INDIVIDUAL CARDS BUILDER] Completed successfully.\n")

if __name__ == "__main__":
    generate_individual_cards()
