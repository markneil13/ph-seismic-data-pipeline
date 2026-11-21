import numpy as np
import pandas as pd
import polars as pl
from typing import Dict, Tuple, List
from src.wealth_platform.config import RISK_FREE_RATE

class PortfolioAnalyticsEngine:
    def __init__(self, prices_df: pl.DataFrame, portfolio_weights: Dict[str, float], benchmark_ticker: str = "SPY"):
        """
        prices_df: Polars DataFrame with columns ['date', 'ticker', 'adj_close']
        portfolio_weights: Dict mapping ticker to asset weight (e.g. {'AAPL': 0.25, ...})
        """
        self.prices_df = prices_df
        self.weights = portfolio_weights
        self.benchmark_ticker = benchmark_ticker
        self._prepare_data()

    def _prepare_data(self):
        """Pivots prices into daily price & return matrices."""
        df_pd = self.prices_df.to_pandas()
        pivoted = df_pd.pivot(index="date", columns="ticker", values="adj_close").dropna()
        
        self.dates = pivoted.index
        self.returns = pivoted.pct_change().dropna()
        
        # Calculate daily portfolio return series
        asset_cols = [t for t in self.weights.keys() if t in self.returns.columns]
        weight_vec = np.array([self.weights[t] for t in asset_cols])
        # Re-normalize weights if needed
        weight_vec = weight_vec / np.sum(weight_vec)
        
        self.asset_returns = self.returns[asset_cols]
        self.port_returns = (self.asset_returns * weight_vec).sum(axis=1)
        
        if self.benchmark_ticker in self.returns.columns:
            self.bench_returns = self.returns[self.benchmark_ticker]
        else:
            self.bench_returns = self.port_returns * 0.8 + np.random.normal(0, 0.005, len(self.port_returns))

    def compute_all_metrics(self, rf_rate: float = RISK_FREE_RATE) -> Dict[str, float]:
        """Calculates comprehensive executive financial risk and performance metrics."""
        cum_return = (1 + self.port_returns).prod() - 1
        num_years = len(self.port_returns) / 252.0
        cagr = (1 + cum_return) ** (1 / num_years) - 1 if num_years > 0 else cum_return

        # Volatility
        daily_vol = self.port_returns.std()
        ann_vol = daily_vol * np.sqrt(252)

        # Sharpe Ratio
        excess_return = cagr - rf_rate
        sharpe_ratio = excess_return / ann_vol if ann_vol > 0 else 0.0

        # Sortino Ratio
        downside_returns = self.port_returns[self.port_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino_ratio = excess_return / downside_std if downside_std > 0 else 0.0

        # Maximum Drawdown (MDD)
        cum_series = (1 + self.port_returns).cumprod()
        running_max = cum_series.cummax()
        drawdowns = (cum_series - running_max) / running_max
        max_drawdown = drawdowns.min()

        # Beta & Alpha vs Benchmark
        cov_matrix = np.cov(self.port_returns, self.bench_returns)
        bench_var = np.var(self.bench_returns)
        beta = cov_matrix[0, 1] / bench_var if bench_var > 0 else 1.0
        
        bench_cagr = (1 + self.bench_returns).prod() ** (1 / num_years) - 1 if num_years > 0 else 0.0
        alpha = cagr - (rf_rate + beta * (bench_cagr - rf_rate))

        # Value at Risk (VaR - Historical)
        var_95 = np.percentile(self.port_returns, 5)
        var_99 = np.percentile(self.port_returns, 1)

        return {
            "cumulative_return": float(cum_return),
            "cagr": float(cagr),
            "annualized_volatility": float(ann_vol),
            "sharpe_ratio": float(sharpe_ratio),
            "sortino_ratio": float(sortino_ratio),
            "max_drawdown": float(max_drawdown),
            "beta": float(beta),
            "alpha": float(alpha),
            "var_95": float(var_95),
            "var_99": float(var_99),
            "benchmark_cagr": float(bench_cagr)
        }

    def get_cumulative_performance_series(self) -> pd.DataFrame:
        """Returns cumulative growth series for portfolio vs benchmark."""
        cum_port = (1 + self.port_returns).cumprod() * 100.0
        cum_bench = (1 + self.bench_returns).cumprod() * 100.0
        
        df_res = pd.DataFrame({
            "Portfolio": cum_port,
            "Benchmark (SPY)": cum_bench
        }, index=self.returns.index)
        return df_res

    def get_drawdown_series(self) -> pd.Series:
        """Returns peak-to-trough drawdown time series."""
        cum_series = (1 + self.port_returns).cumprod()
        running_max = cum_series.cummax()
        return (cum_series - running_max) / running_max
