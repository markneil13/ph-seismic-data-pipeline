import pytest
import numpy as np
import polars as pl
from src.wealth_platform.pipeline.validation import validate_price_records
from src.wealth_platform.analytics.portfolio_metrics import PortfolioAnalyticsEngine
from src.wealth_platform.ml.portfolio_optimizer import MarkowitzOptimizer
from src.wealth_platform.ml.monte_carlo import MonteCarloSimulator

def test_validation_schema():
    records = [
        {"date": "2023-01-01", "ticker": "AAPL", "open": 150.0, "high": 155.0, "low": 149.0, "close": 152.0, "adj_close": 152.0, "volume": 1000000},
        {"date": "2023-01-02", "ticker": "AAPL", "open": 152.0, "high": 140.0, "low": 150.0, "close": 145.0, "adj_close": 145.0, "volume": 1000000} # Invalid high < low
    ]
    validated = validate_price_records(records)
    assert len(validated) == 1
    assert validated[0]["ticker"] == "AAPL"

def test_portfolio_analytics():
    dates = pl.date_range(start=pl.date(2023, 1, 1), end=pl.date(2023, 12, 31), interval="1d", eager=True)
    n = len(dates)
    
    np.random.seed(42)
    aapl_prices = 100 * (1 + np.random.normal(0.001, 0.01, n)).cumprod()
    spy_prices = 100 * (1 + np.random.normal(0.0005, 0.008, n)).cumprod()

    df_aapl = pl.DataFrame({"date": dates, "ticker": ["AAPL"]*n, "open": aapl_prices, "high": aapl_prices, "low": aapl_prices, "close": aapl_prices, "adj_close": aapl_prices, "volume": [10000]*n})
    df_spy = pl.DataFrame({"date": dates, "ticker": ["SPY"]*n, "open": spy_prices, "high": spy_prices, "low": spy_prices, "close": spy_prices, "adj_close": spy_prices, "volume": [10000]*n})
    
    prices_df = pl.concat([df_aapl, df_spy])
    weights = {"AAPL": 1.0}

    engine = PortfolioAnalyticsEngine(prices_df, weights, benchmark_ticker="SPY")
    metrics = engine.compute_all_metrics()

    assert "sharpe_ratio" in metrics
    assert "cagr" in metrics
    assert "max_drawdown" in metrics
    assert metrics["max_drawdown"] <= 0.0

def test_monte_carlo_simulation():
    simulator = MonteCarloSimulator(expected_annual_return=0.10, annual_volatility=0.15)
    res = simulator.run_simulation(initial_investment=50000, monthly_cashflow=500, years=10, num_simulations=500)
    
    p5 = res["percentiles"]["5th_conservative"][-1]
    p50 = res["percentiles"]["50th_median"][-1]
    p95 = res["percentiles"]["95th_optimistic"][-1]

    assert p5 < p50 < p95
    assert p50 > 50000
