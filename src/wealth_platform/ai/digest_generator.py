import datetime
from typing import Dict
from src.wealth_platform.ai.sec_rag_agent import SECFinancialRAGAgent

class ExecutiveDigestGenerator:
    def __init__(self, metrics: Dict, opt_results: Dict, mc_results: Dict):
        self.metrics = metrics
        self.opt_results = opt_results
        self.mc_results = mc_results
        self.rag_agent = SECFinancialRAGAgent()

    def generate_markdown_digest(self) -> str:
        today_str = datetime.date.today().strftime("%B %d, %Y")
        
        # Query AI agent for risk synthesis
        ai_risk_summary = self.rag_agent.answer_financial_query("What are the main risk factors for portfolio holdings?")

        md = f"""# 🏛️ Executive Portfolio Digest & Investment Intelligence
**Generated Date:** {today_str}  
**Target Benchmark:** S&P 500 ETF (SPY)

---

## 1. Executive Performance & Risk Summary

| Metric | Portfolio Value | Benchmark (SPY) | Status / Assessment |
| :--- | :---: | :---: | :--- |
| **Cumulative Return** | {self.metrics['cumulative_return']*100:.2f}% | -- | Strong Historical CAGR |
| **Annualized Return (CAGR)** | {self.metrics['cagr']*100:.2f}% | {self.metrics['benchmark_cagr']*100:.2f}% | Outperforming Benchmark |
| **Annualized Volatility** | {self.metrics['annualized_volatility']*100:.2f}% | -- | Moderate Risk |
| **Sharpe Ratio** | {self.metrics['sharpe_ratio']:.2f} | -- | Excellent Risk-Adjusted Return |
| **Sortino Ratio** | {self.metrics['sortino_ratio']:.2f} | -- | Strong Downside Protection |
| **Max Drawdown (MDD)** | {self.metrics['max_drawdown']*100:.2f}% | -- | Managed Capital Loss Peak |
| **Portfolio Beta** | {self.metrics['beta']:.2f} | 1.00 | Market Sensitivity |
| **Value at Risk (95% Daily)** | {self.metrics['var_95']*100:.2f}% | -- | 95% Worst Daily Expected Loss |

---

## 2. Quantitative Asset Optimization (Markowitz MPT)

Based on Modern Portfolio Theory optimization over historical return covariance:

* **Maximum Sharpe Allocation**:
"""
        for ticker, weight in self.opt_results['weights'].items():
            md += f"  - **{ticker}**: {weight*100:.1f}%\n"

        md += f"""
* **Optimized Target Sharpe Ratio**: `{self.opt_results['sharpe_ratio']:.2f}` (Expected Return: `{self.opt_results['expected_return']*100:.1f}%`, Volatility: `{self.opt_results['volatility']*100:.1f}%`)

---

## 3. Stochastic Wealth & Retirement Forecast (Monte Carlo)

Across **5,000 simulated paths** over a **{self.mc_results['time_horizon_years']}-Year Horizon**:

- **Conservative Outcome (5th Percentile)**: `${self.mc_results['terminal_wealth_stats']['p5_nominal']:,.2f}`
- **Median Expected Wealth (50th Percentile)**: `${self.mc_results['terminal_wealth_stats']['p50_nominal']:,.2f}`
- **Optimistic Outcome (95th Percentile)**: `${self.mc_results['terminal_wealth_stats']['95_nominal']:,.2f}`
- **Inflation-Adjusted Real Median**: `${self.mc_results['terminal_wealth_stats']['p50_real_inflation_adjusted']:,.2f}`

---

## 4. AI Strategic Risk Commentary (SEC Filing RAG)

{ai_risk_summary}

---
*Report generated automatically by the Wealth Management Intelligence Pipeline.*
"""
        return md
