import os
import duckdb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "crypto_warehouse.duckdb")
ARTIFACT_DIR = r"C:\Users\marki\.gemini\antigravity\brain\38ee009d-0bd1-485d-9ef1-275e90573680"
MARKDOWN_OUT = os.path.join(ARTIFACT_DIR, "x_social_content_strategy.md")

ETH_IMAGE = os.path.join(ARTIFACT_DIR, "eth_x_card_1790215833234.jpg").replace("\\", "/")
SOL_IMAGE = os.path.join(ARTIFACT_DIR, "sol_x_card_1790215850695.jpg").replace("\\", "/")

def generate_x_posts():
    con = duckdb.connect(DB_PATH)
    df_signals = con.execute("SELECT * FROM gold.mart_trading_signals ORDER BY ml_bullish_prob_pct DESC").fetchdf()
    con.close()

    md_content = """# 🚀 X (Twitter) Content & Graphic Strategy

This document contains ready-to-publish social media graphics and high-engagement post copy for each cryptocurrency tracked by your AI Market Engine.

---

"""
    for _, row in df_signals.iterrows():
        symbol = row['symbol']
        coin_name = row['coin_name']
        price = row['latest_close_price']
        rsi = row['rsi_14']
        vol = row['volatility_annualized'] * 100
        prob = row['ml_bullish_prob_pct']
        signal = row['signal']
        risk = row['volatility_risk']
        ret_7d = row['return_7d_pct']

        emoji_sig = "🚀" if "BUY" in signal else ("🚨" if "SELL" in signal else "⚖️")
        
        md_content += f"## {emoji_sig} {coin_name} ({symbol}) — Social Post Package\n\n"
        
        # Attach image if available
        if symbol == "ETHUSDT" and os.path.exists(ETH_IMAGE):
            md_content += f"![Ethereum X Graphic Card](file:///{ETH_IMAGE})\n\n"
        elif symbol == "SOLUSDT" and os.path.exists(SOL_IMAGE):
            md_content += f"![Solana X Graphic Card](file:///{SOL_IMAGE})\n\n"

        md_content += f"### 📝 Tweet Copy (Click to Copy):\n\n"
        md_content += "```text\n"
        md_content += f"🤖 AI MARKET UPDATE: {coin_name} (${symbol.replace('USDT','')})\n\n"
        md_content += f"📊 24h ML Forecast: {prob}% Bullish Probability\n"
        md_content += f"💰 Current Price: ${price:,.2f}\n"
        md_content += f"📈 7D Performance: {'+' if ret_7d > 0 else ''}{ret_7d:.1f}%\n"
        md_content += f"⚡ RSI (14): {rsi:.1f} | Volatility: {vol:.1f}%\n"
        md_content += f"🎯 Consensus Signal: {signal} {emoji_sig}\n"
        md_content += f"⚠️ Risk Level: {risk}\n\n"
        md_content += f"Powered by DuckDB Medallion Pipeline & Random Forest ML 🧠\n\n"
        md_content += f"#Crypto #{symbol.replace('USDT','')} #{coin_name.replace(' ','')} #DataScience #TradingSignals #Web3 #AI\n"
        md_content += "```\n\n"
        md_content += "---\n\n"

    with open(MARKDOWN_OUT, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Social content strategy written to {MARKDOWN_OUT}")

if __name__ == "__main__":
    generate_x_posts()
