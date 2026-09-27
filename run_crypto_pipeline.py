import os
import sys
import duckdb
from crypto_engine.ingestion import run_ingestion
from crypto_engine.transformation import run_transformation
from crypto_engine.ml_forecasting import train_and_forecast
from crypto_engine.analytics import run_analytics
from crypto_engine.quality import run_quality_checks
from crypto_engine.dashboard import generate_dashboard
from generate_pdf_report import create_pdf_report
from generate_social_cards_html import generate_social_cards_page
from generate_individual_crypto_cards import generate_individual_cards

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "crypto_warehouse.duckdb")

def print_executive_bulletin():
    """Prints a formatted Executive Financial & Crypto Intelligence Bulletin in the terminal."""
    print("=" * 100)
    print("      FINANCIAL & CRYPTO MARKET ANALYTICS ENGINE — EXECUTIVE BULLETIN")
    print("=" * 100)
    
    con = duckdb.connect(DB_PATH)
    
    df_signals = con.execute("""
        SELECT 
            symbol,
            coin_name,
            latest_close_price AS price_usd,
            rsi_14 AS rsi,
            volatility_annualized * 100 AS vol_pct,
            ml_bullish_prob_pct AS ml_bull_pct,
            signal,
            volatility_risk
        FROM gold.mart_trading_signals
        ORDER BY ml_bullish_prob_pct DESC
    """).fetchdf()
    
    print("\n[SIGNALS] Live Machine Learning Forecasts & Technical Consensus Signals:")
    print("-" * 100)
    print(df_signals.to_string(index=False))
    print("-" * 100)
    
    top_buy = df_signals.iloc[0]
    total_assets = len(df_signals)
    avg_vol = df_signals["vol_pct"].mean()
    
    print(f"\nTotal Crypto Assets Tracked: {total_assets}")
    print(f"Top Bullish ML Opportunity: {top_buy['symbol']} ({top_buy['coin_name']}) with {top_buy['ml_bull_pct']:.1f}% Bullish Probability")
    print(f"Archipelago Average Annualized Volatility: {avg_vol:.1f}%\n")
    con.close()

def main():
    print("==========================================================================")
    print("     FINANCIAL & CRYPTO MARKET ENGINE (END-TO-END PIPELINE)    ")
    print("==========================================================================\n")
    
    try:
        # Step 1: Ingest Live Data (Bronze)
        run_ingestion()
        
        # Step 2: Transform Technical Indicators (Silver)
        run_transformation()
        
        # Step 3: Train Machine Learning Models (Gold)
        train_and_forecast()
        
        # Step 4: Build Data Marts (Gold)
        run_analytics()
        
        # Step 5: Data Quality Assertions
        passed = run_quality_checks()
        if not passed:
            print("[STOP] Pipeline halted due to quality check failures.")
            sys.exit(1)
            
        # Step 6: Generate Analytics Dashboard, PDF Report, and Individual HTML Cards
        generate_dashboard()
        create_pdf_report()
        generate_social_cards_page()
        generate_individual_cards()
        print_executive_bulletin()
        
        print("[SUCCESS] ALL INDIVIDUAL HTML CARDS & PIPELINE GENERATED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"[ERROR] Pipeline execution failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
