import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.wealth_platform.config import DEFAULT_PORTFOLIO, BENCHMARK_TICKER, DATA_DIR
from src.wealth_platform.pipeline.ingestion import fetch_ticker_data, fetch_company_metadata
from src.wealth_platform.pipeline.storage import WealthStorage
from src.wealth_platform.analytics.portfolio_metrics import PortfolioAnalyticsEngine
from src.wealth_platform.ml.portfolio_optimizer import MarkowitzOptimizer
from src.wealth_platform.ml.monte_carlo import MonteCarloSimulator
from src.wealth_platform.ai.digest_generator import ExecutiveDigestGenerator

def run_wealth_pipeline():
    print("=" * 70)
    print("[WEALTH PLATFORM] AI-POWERED WEALTH MANAGEMENT & PORTFOLIO INTELLIGENCE PIPELINE")
    print("=" * 70)

    # 1. Data Engineering Ingestion & Storage
    tickers = list(DEFAULT_PORTFOLIO.keys())
    all_tickers = list(set(tickers + [BENCHMARK_TICKER]))
    
    print(f"\n[Step 1/5] Ingesting market prices for {len(all_tickers)} assets...")
    df_prices = fetch_ticker_data(all_tickers)
    metadata = fetch_company_metadata(all_tickers)

    print("[Step 2/5] Persisting into DuckDB & Parquet Columnar Storage...")
    storage = WealthStorage()
    storage.save_prices(df_prices)
    storage.save_metadata(metadata)

    # 2. Data Analysis Engine
    print("\n[Step 3/5] Calculating Executive Portfolio Metrics & Risk Indicators...")
    portfolio_weights = {t: DEFAULT_PORTFOLIO[t]["weight"] for t in tickers}
    analytics_engine = PortfolioAnalyticsEngine(df_prices, portfolio_weights, BENCHMARK_TICKER)
    metrics = analytics_engine.compute_all_metrics()

    print(f"  > Cumulative Return:   {metrics['cumulative_return']*100:.2f}%")
    print(f"  > Annualized CAGR:     {metrics['cagr']*100:.2f}% (SPY: {metrics['benchmark_cagr']*100:.2f}%)")
    print(f"  > Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
    print(f"  > Sortino Ratio:       {metrics['sortino_ratio']:.2f}")
    print(f"  > Maximum Drawdown:    {metrics['max_drawdown']*100:.2f}%")

    # 3. Data Science & Quantitative ML Models
    print("\n[Step 4/5] Running Markowitz Optimization & Monte Carlo Simulations...")
    optimizer = MarkowitzOptimizer(df_prices, tickers)
    opt_results = optimizer.optimize_max_sharpe()
    print(f"  > Optimized Sharpe Weighting: {opt_results['weights']}")
    print(f"  > Max Sharpe Ratio:          {opt_results['sharpe_ratio']:.2f}")

    simulator = MonteCarloSimulator(opt_results['expected_return'], opt_results['volatility'])
    mc_results = simulator.run_simulation(initial_investment=100000.0, monthly_contribution=1000.0, years=20)
    print(f"  > 20-Yr Median Projected Wealth: ${mc_results['terminal_wealth_stats']['p50_nominal']:,.2f}")

    # 4. AI Strategic RAG & Digest Generation
    print("\n[Step 5/5] Generating AI Executive Investment Digest...")
    digest_gen = ExecutiveDigestGenerator(metrics, opt_results, mc_results)
    markdown_digest = digest_gen.generate_markdown_digest()

    digest_output_path = DATA_DIR / "Executive_Portfolio_Digest.md"
    with open(digest_output_path, "w", encoding="utf-8") as f:
        f.write(markdown_digest)

    print(f"\n[SUCCESS] Pipeline executed successfully! Executive digest saved to: {digest_output_path}")
    print("=" * 70)
    storage.close()

if __name__ == "__main__":
    run_wealth_pipeline()
