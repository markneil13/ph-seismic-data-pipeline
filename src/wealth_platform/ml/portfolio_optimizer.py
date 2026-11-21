import numpy as np
import pandas as pd
import polars as pl
from scipy.optimize import minimize
from typing import Dict, List, Tuple
from src.wealth_platform.config import RISK_FREE_RATE

class MarkowitzOptimizer:
    def __init__(self, prices_df: pl.DataFrame, asset_tickers: List[str]):
        """
        prices_df: Polars DataFrame with columns ['date', 'ticker', 'adj_close']
        asset_tickers: Tickers to include in optimization
        """
        self.tickers = asset_tickers
        self._prepare_matrices(prices_df)

    def _prepare_matrices(self, prices_df: pl.DataFrame):
        df_pd = prices_df.to_pandas()
        pivoted = df_pd.pivot(index="date", columns="ticker", values="adj_close").dropna()
        
        valid_tickers = [t for t in self.tickers if t in pivoted.columns]
        self.tickers = valid_tickers
        
        returns = pivoted[valid_tickers].pct_change().dropna()
        self.mean_returns = returns.mean() * 252.0  # Annualized expected return
        self.cov_matrix = returns.cov() * 252.0       # Annualized covariance matrix
        self.num_assets = len(valid_tickers)

    def _portfolio_performance(self, weights: np.ndarray, rf_rate: float = RISK_FREE_RATE) -> Tuple[float, float, float]:
        port_return = np.sum(self.mean_returns * weights)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
        sharpe = (port_return - rf_rate) / port_vol if port_vol > 0 else 0.0
        return port_return, port_vol, sharpe

    def optimize_max_sharpe(self, rf_rate: float = RISK_FREE_RATE) -> Dict:
        """Finds portfolio weights that maximize Sharpe ratio."""
        def neg_sharpe(weights):
            ret, vol, sharpe = self._portfolio_performance(weights, rf_rate)
            return -sharpe

        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        bounds = tuple((0.0, 1.0) for _ in range(self.num_assets))
        initial_guess = np.array([1.0 / self.num_assets] * self.num_assets)

        res = minimize(neg_sharpe, initial_guess, method='SLSQP', bounds=bounds, constraints=constraints)
        
        opt_weights = res.x
        ret, vol, sharpe = self._portfolio_performance(opt_weights, rf_rate)
        
        weight_dict = {ticker: round(float(w), 4) for ticker, w in zip(self.tickers, opt_weights)}
        
        return {
            "weights": weight_dict,
            "expected_return": round(float(ret), 4),
            "volatility": round(float(vol), 4),
            "sharpe_ratio": round(float(sharpe), 4)
        }

    def optimize_min_volatility(self, rf_rate: float = RISK_FREE_RATE) -> Dict:
        """Finds portfolio weights that minimize volatility."""
        def port_variance(weights):
            return self._portfolio_performance(weights, rf_rate)[1]

        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        bounds = tuple((0.0, 1.0) for _ in range(self.num_assets))
        initial_guess = np.array([1.0 / self.num_assets] * self.num_assets)

        res = minimize(port_variance, initial_guess, method='SLSQP', bounds=bounds, constraints=constraints)
        
        opt_weights = res.x
        ret, vol, sharpe = self._portfolio_performance(opt_weights, rf_rate)
        
        weight_dict = {ticker: round(float(w), 4) for ticker, w in zip(self.tickers, opt_weights)}
        
        return {
            "weights": weight_dict,
            "expected_return": round(float(ret), 4),
            "volatility": round(float(vol), 4),
            "sharpe_ratio": round(float(sharpe), 4)
        }

    def generate_efficient_frontier(self, num_portfolios: int = 50, rf_rate: float = RISK_FREE_RATE) -> pd.DataFrame:
        """Generates random portfolios and the smooth efficient frontier curve."""
        min_vol_res = self.optimize_min_volatility(rf_rate)
        max_sharpe_res = self.optimize_max_sharpe(rf_rate)
        
        target_returns = np.linspace(min_vol_res["expected_return"], self.mean_returns.max(), num_portfolios)
        frontier_vols = []
        frontier_returns = []

        for target in target_returns:
            constraints = (
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
                {'type': 'eq', 'fun': lambda w: np.sum(self.mean_returns * w) - target}
            )
            bounds = tuple((0.0, 1.0) for _ in range(self.num_assets))
            res = minimize(lambda w: np.sqrt(np.dot(w.T, np.dot(self.cov_matrix, w))), 
                           np.array([1.0 / self.num_assets] * self.num_assets),
                           method='SLSQP', bounds=bounds, constraints=constraints)
            if res.success:
                frontier_vols.append(res.fun)
                frontier_returns.append(target)

        # Generate Monte Carlo random portfolio cloud for visualization
        np.random.seed(42)
        random_vols = []
        random_returns = []
        random_sharpes = []

        for _ in range(500):
            w = np.random.random(self.num_assets)
            w /= np.sum(w)
            r, v, s = self._portfolio_performance(w, rf_rate)
            random_returns.append(r)
            random_vols.append(v)
            random_sharpes.append(s)

        df_random = pd.DataFrame({
            "return": random_returns,
            "volatility": random_vols,
            "sharpe": random_sharpes
        })
        
        df_frontier = pd.DataFrame({
            "frontier_volatility": frontier_vols,
            "frontier_return": frontier_returns
        })
        
        return df_random, df_frontier, max_sharpe_res, min_vol_res
