import os
import json
import duckdb
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "crypto_warehouse.duckdb")
JSON_OUT_PATH = os.path.join(BASE_DIR, "crypto_dashboard_data.json")
HTML_OUT_PATH = os.path.join(BASE_DIR, "crypto_analytics_dashboard.html")

def generate_dashboard():
    """Extracts Gold data marts into JSON and builds an interactive standalone HTML Analytics Dashboard."""
    print("[DASHBOARD BUILDER] Generating Interactive Crypto Analytics Dashboard...")
    con = duckdb.connect(DB_PATH)
    
    # 1. Fetch Trading Signals & ML Forecasts
    df_signals = con.execute("SELECT * FROM gold.mart_trading_signals").fetchdf()
    
    # 2. Fetch Candle Price History for Charts
    df_candles = con.execute("""
        SELECT 
            symbol,
            coin_name,
            strftime(timestamp, '%Y-%m-%d') AS date_str,
            close_price,
            rsi_14,
            macd,
            macd_signal,
            bb_upper,
            bb_lower,
            volatility_14d
        FROM silver.fact_crypto_daily
        ORDER BY symbol, timestamp ASC
    """).fetchdf()
    
    # 3. Fetch Feature Importance
    df_feat_imp = con.execute("""
        SELECT feature, AVG(importance) AS avg_importance
        FROM gold.ml_feature_importance
        GROUP BY feature
        ORDER BY avg_importance DESC
    """).fetchdf()
    
    con.close()
    
    # Structure JSON data
    dashboard_data = {
        "generated_at": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "trading_signals": df_signals.to_dict(orient="records"),
        "price_history": df_candles.to_dict(orient="records"),
        "feature_importance": df_feat_imp.to_dict(orient="records")
    }
    
    with open(JSON_OUT_PATH, "w") as f:
        json.dump(dashboard_data, f, indent=2)
    print(f"  -> Exported dashboard dataset to {JSON_OUT_PATH}")
    
    # Build HTML Page
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial & Crypto Market Analytics Engine</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Plotly.js CDN -->
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <!-- FontAwesome icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {{ background-color: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; }}
        .card {{ background-color: #1e293b; border: 1px solid #334155; border-radius: 0.75rem; }}
        .badge-buy {{ background-color: #166534; color: #4ade80; border: 1px solid #22c55e; }}
        .badge-strong-buy {{ background-color: #14532d; color: #86efac; border: 1px solid #4ade80; font-weight: bold; }}
        .badge-sell {{ background-color: #991b1b; color: #fca5a5; border: 1px solid #ef4444; }}
        .badge-strong-sell {{ background-color: #7f1d1d; color: #fecaca; border: 1px solid #f87171; font-weight: bold; }}
        .badge-hold {{ background-color: #854d0e; color: #fef08a; border: 1px solid #eab308; }}
    </style>
</head>
<body class="p-6">
    <div class="max-w-7xl mx-auto space-y-6">
        
        <!-- Header -->
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center card p-6">
            <div>
                <h1 class="text-3xl font-extrabold text-blue-400 flex items-center gap-3">
                    <i class="fa-solid fa-chart-line text-emerald-400"></i> Crypto Market Analytics & ML Forecast Engine
                </h1>
                <p class="text-slate-400 text-sm mt-1">Live Ingestion • DuckDB Medallion Pipeline • Random Forest 24h Volatility & Direction ML Model</p>
            </div>
            <div class="mt-4 md:mt-0 text-right">
                <span class="text-xs px-3 py-1.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800">
                    <i class="fa-solid fa-clock"></i> Generated: {dashboard_data['generated_at']}
                </span>
            </div>
        </div>

        <!-- Metric KPI Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="card p-5">
                <div class="text-slate-400 text-xs font-semibold uppercase">Assets Tracked</div>
                <div class="text-3xl font-bold mt-2 text-white">{len(df_signals)}</div>
                <div class="text-slate-500 text-xs mt-1">BTC, ETH, SOL, BNB, XRP, ADA</div>
            </div>
            <div class="card p-5">
                <div class="text-slate-400 text-xs font-semibold uppercase">Top ML Bullish Signal</div>
                <div class="text-2xl font-bold mt-2 text-emerald-400">
                    {df_signals.iloc[0]['symbol']} ({df_signals.iloc[0]['ml_bullish_prob_pct']}%)
                </div>
                <div class="text-emerald-500 text-xs mt-1">{df_signals.iloc[0]['signal']}</div>
            </div>
            <div class="card p-5">
                <div class="text-slate-400 text-xs font-semibold uppercase">Average 14D Volatility</div>
                <div class="text-3xl font-bold mt-2 text-amber-400">
                    {df_signals['volatility_annualized'].mean()*100:.1f}%
                </div>
                <div class="text-slate-400 text-xs mt-1">Annualized Standard Deviation</div>
            </div>
            <div class="card p-5">
                <div class="text-slate-400 text-xs font-semibold uppercase">Highest 7D Gain</div>
                <div class="text-3xl font-bold mt-2 text-emerald-400">
                    +{df_signals['return_7d_pct'].max():.1f}%
                </div>
                <div class="text-slate-400 text-xs mt-1">7-Day Top Performer</div>
            </div>
        </div>

        <!-- ML Trading Signals Table -->
        <div class="card p-6">
            <h2 class="text-xl font-bold text-slate-100 mb-4 flex items-center gap-2">
                <i class="fa-solid fa-robot text-purple-400"></i> Machine Learning 24-Hour Forecast & Trading Consensus
            </h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-slate-300">
                    <thead class="text-xs uppercase bg-slate-800 text-slate-400">
                        <tr>
                            <th class="py-3 px-4">Asset</th>
                            <th class="py-3 px-4">Price (USD)</th>
                            <th class="py-3 px-4">7D Return</th>
                            <th class="py-3 px-4">RSI (14)</th>
                            <th class="py-3 px-4">Volatility</th>
                            <th class="py-3 px-4">ML Bullish %</th>
                            <th class="py-3 px-4">Signal</th>
                            <th class="py-3 px-4">Risk Level</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
                        {"".join([f'''
                        <tr class="hover:bg-slate-800/50 transition-colors">
                            <td class="py-3 px-4 font-bold text-white">{row['symbol']} <span class="text-xs text-slate-500 font-normal">({row['coin_name']})</span></td>
                            <td class="py-3 px-4">${row['latest_close_price']:,.2f}</td>
                            <td class="py-3 px-4 {'text-emerald-400' if row['return_7d_pct'] > 0 else 'text-rose-400'} font-semibold">{'+' if row['return_7d_pct'] > 0 else ''}{row['return_7d_pct']:.2f}%</td>
                            <td class="py-3 px-4">{row['rsi_14']} <span class="text-xs text-slate-500">({row['rsi_status']})</span></td>
                            <td class="py-3 px-4">{(row['volatility_annualized']*100):.1f}%</td>
                            <td class="py-3 px-4">
                                <div class="flex items-center gap-2">
                                    <div class="w-16 bg-slate-700 h-2 rounded-full overflow-hidden">
                                        <div class="bg-blue-500 h-full" style="width: {row['ml_bullish_prob_pct']}%"></div>
                                    </div>
                                    <span class="font-bold text-blue-300">{row['ml_bullish_prob_pct']}%</span>
                                </div>
                            </td>
                            <td class="py-3 px-4">
                                <span class="px-2.5 py-1 text-xs rounded-md {'badge-strong-buy' if 'STRONG BUY' in row['signal'] else ('badge-buy' if 'BUY' in row['signal'] else ('badge-strong-sell' if 'STRONG SELL' in row['signal'] else ('badge-sell' if 'SELL' in row['signal'] else 'badge-hold')))}">
                                    {row['signal']}
                                </span>
                            </td>
                            <td class="py-3 px-4 text-xs font-medium text-amber-300">{row['volatility_risk']}</td>
                        </tr>
                        ''' for _, row in df_signals.iterrows()])}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Interactive Plotly Charts Section -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Price History Chart -->
            <div class="card p-6">
                <h3 class="text-lg font-bold text-slate-200 mb-2">Price Trend History</h3>
                <div id="priceChart" class="h-80 w-full"></div>
            </div>
            
            <!-- RSI Indicator Chart -->
            <div class="card p-6">
                <h3 class="text-lg font-bold text-slate-200 mb-2">RSI (14) Momentum Indicator</h3>
                <div id="rsiChart" class="h-80 w-full"></div>
            </div>
        </div>

        <!-- ML Feature Importance -->
        <div class="card p-6">
            <h3 class="text-lg font-bold text-slate-200 mb-2">Random Forest Feature Importance Drivers</h3>
            <p class="text-xs text-slate-400 mb-4">Relative weight of indicators influencing model direction prediction.</p>
            <div id="featureImpChart" class="h-64 w-full"></div>
        </div>

    </div>

    <script>
        const dashboardData = {json.dumps(dashboard_data)};
        
        // Group price history by symbol
        const priceBySymbol = {{}};
        dashboardData.price_history.forEach(row => {{
            if (!priceBySymbol[row.symbol]) priceBySymbol[row.symbol] = {{ x: [], y: [], rsi: [] }};
            priceBySymbol[row.symbol].x.push(row.date_str);
            priceBySymbol[row.symbol].y.push(row.close_price);
            priceBySymbol[row.symbol].rsi.push(row.rsi_14);
        }});

        // Render Price Chart
        const priceTraces = Object.keys(priceBySymbol).map(sym => ({{
            x: priceBySymbol[sym].x,
            y: priceBySymbol[sym].y,
            mode: 'lines',
            name: sym
        }}));

        Plotly.newPlot('priceChart', priceTraces, {{
            margin: {{ t: 10, b: 30, l: 40, r: 10 }},
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#94a3b8' }},
            xaxis: {{ gridcolor: '#334155' }},
            yaxis: {{ gridcolor: '#334155', title: 'Price (USD)' }}
        }});

        // Render RSI Chart
        const rsiTraces = Object.keys(priceBySymbol).map(sym => ({{
            x: priceBySymbol[sym].x,
            y: priceBySymbol[sym].rsi,
            mode: 'lines',
            name: sym
        }}));

        Plotly.newPlot('rsiChart', rsiTraces, {{
            margin: {{ t: 10, b: 30, l: 40, r: 10 }},
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#94a3b8' }},
            xaxis: {{ gridcolor: '#334155' }},
            yaxis: {{ gridcolor: '#334155', range: [0, 100], title: 'RSI' }},
            shapes: [
                {{ type: 'line', y0: 70, y1: 70, x0: rsiTraces[0].x[0], x1: rsiTraces[0].x[rsiTraces[0].x.length-1], line: {{ color: '#ef4444', dash: 'dash' }} }},
                {{ type: 'line', y0: 30, y1: 30, x0: rsiTraces[0].x[0], x1: rsiTraces[0].x[rsiTraces[0].x.length-1], line: {{ color: '#22c55e', dash: 'dash' }} }}
            ]
        }});

        // Render Feature Importance Chart
        const featData = dashboardData.feature_importance;
        Plotly.newPlot('featureImpChart', [{{
            x: featData.map(f => f.feature),
            y: featData.map(f => f.avg_importance),
            type: 'bar',
            marker: {{ color: '#818cf8' }}
        }}], {{
            margin: {{ t: 10, b: 40, l: 40, r: 10 }},
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#94a3b8' }},
            xaxis: {{ gridcolor: '#334155' }},
            yaxis: {{ gridcolor: '#334155', title: 'Importance Weight' }}
        }});
    </script>
</body>
</html>
"""
    with open(HTML_OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  -> Successfully generated standalone HTML dashboard at {HTML_OUT_PATH}")
    print("[DASHBOARD BUILDER] Completed successfully.\n")

if __name__ == "__main__":
    generate_dashboard()
