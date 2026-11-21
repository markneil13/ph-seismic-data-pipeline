import numpy as np
import pandas as pd
from typing import Dict

class MonteCarloSimulator:
    def __init__(self, expected_annual_return: float, annual_volatility: float):
        self.mu = expected_annual_return
        self.sigma = annual_volatility

    def run_simulation(self, 
                       initial_investment: float = 100000.0, 
                       monthly_cashflow: float = 1000.0, # Positive = contribution, Negative = withdrawal
                       years: int = 20, 
                       num_simulations: int = 5000, 
                       inflation_rate: float = 0.025,
                       one_time_cash_adjustment: float = 0.0) -> Dict:
        """
        Runs stochastic simulation using Geometric Brownian Motion.
        Supports recurring monthly cashflows (deposits or withdrawals) and lump-sum cash adjustments.
        Floors wealth at 0.0 to track portfolio depletion/ruin risk.
        """
        months = years * 12
        dt = 1.0 / 12.0  # Monthly timestep
        
        # Adjust drift and volatility for monthly frequency
        monthly_mu = (self.mu - 0.5 * (self.sigma ** 2)) * dt
        monthly_sigma = self.sigma * np.sqrt(dt)

        np.random.seed(42)
        # Starting capital after lump-sum adjustment
        start_capital = max(0.0, initial_investment + one_time_cash_adjustment)
        
        simulation_matrix = np.zeros((num_simulations, months + 1))
        simulation_matrix[:, 0] = start_capital

        for t in range(1, months + 1):
            shocks = np.random.normal(0, 1, num_simulations)
            growth = np.exp(monthly_mu + monthly_sigma * shocks)
            
            # Previous month wealth * growth + monthly cashflow
            next_wealth = (simulation_matrix[:, t - 1] * growth) + monthly_cashflow
            # Floor at 0.0 (cannot have negative wealth)
            simulation_matrix[:, t] = np.maximum(0.0, next_wealth)

        # Calculate percentiles across time steps
        p5 = np.percentile(simulation_matrix, 5, axis=0)
        p50 = np.percentile(simulation_matrix, 50, axis=0)
        p95 = np.percentile(simulation_matrix, 95, axis=0)
        
        terminal_wealth = simulation_matrix[:, -1]
        
        # Survival rate (percent of paths that did not reach $0)
        depleted_paths = np.sum(terminal_wealth == 0.0)
        survival_rate = float((num_simulations - depleted_paths) / num_simulations)

        # Real terminal wealth adjusted for inflation
        inflation_factor = (1 + inflation_rate) ** years

        return {
            "time_horizon_years": years,
            "months": months,
            "num_simulations": num_simulations,
            "start_capital": start_capital,
            "monthly_cashflow": monthly_cashflow,
            "survival_rate": survival_rate,
            "percentiles": {
                "5th_conservative": p5,
                "50th_median": p50,
                "95th_optimistic": p95
            },
            "terminal_wealth_stats": {
                "p5_nominal": float(p5[-1]),
                "p50_nominal": float(p50[-1]),
                "95_nominal": float(p95[-1]),
                "p50_real_inflation_adjusted": float(p50[-1] / inflation_factor),
                "mean_terminal": float(np.mean(terminal_wealth)),
                "std_terminal": float(np.std(terminal_wealth))
            },
            "raw_matrix": simulation_matrix
        }

    def compute_target_success_rate(self, simulation_result: Dict, target_wealth: float) -> float:
        """Computes probability of achieving a target wealth goal at horizon end."""
        terminal_wealth = simulation_result["raw_matrix"][:, -1]
        success_count = np.sum(terminal_wealth >= target_wealth)
        return float(success_count / len(terminal_wealth))
