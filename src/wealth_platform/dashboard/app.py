import os
import sys
from pathlib import Path

# Ensure project root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.wealth_platform.config import DEFAULT_PORTFOLIO, BENCHMARK_TICKER
from src.wealth_platform.pipeline.ingestion import fetch_ticker_data, fetch_company_metadata
from src.wealth_platform.pipeline.storage import WealthStorage
from src.wealth_platform.analytics.portfolio_metrics import PortfolioAnalyticsEngine
from src.wealth_platform.ml.portfolio_optimizer import MarkowitzOptimizer
from src.wealth_platform.ml.monte_carlo import MonteCarloSimulator
from src.wealth_platform.ai.sec_rag_agent import SECFinancialRAGAgent
from src.wealth_platform.ai.digest_generator import ExecutiveDigestGenerator

# Page Config
st.set_page_config(
    page_title="AI Wealth & Portfolio Intelligence Platform",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1B365D;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.0rem;
        color: #5A6978;
        margin-bottom: 20px;
    }
    .stMetric {
        background-color: #F8F9FA;
        padding: 10px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_pipeline_data(tickers):
    storage = WealthStorage()
    all_tickers = list(set(tickers + [BENCHMARK_TICKER]))
    df_prices = fetch_ticker_data(all_tickers)
    meta = fetch_company_metadata(all_tickers)
    storage.save_prices(df_prices)
    storage.save_metadata(meta)
    storage.close()
    return df_prices, meta

# Sidebar - Portfolio Configuration
st.sidebar.image("https://img.icons8.com/color/96/briefcase.png", width=64)
st.sidebar.title("⚙️ Portfolio Configuration")

available_tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]
selected_tickers = st.sidebar.multiselect(
    "Select Asset Universe",
    options=available_tickers,
    default=available_tickers
)

if not selected_tickers:
    st.error("Please select at least one ticker from the sidebar.")
    st.stop()

# Asset Weights Slider
st.sidebar.subheader("Asset Allocations (%)")
custom_weights = {}
raw_weights = []

for t in selected_tickers:
    default_w = int(DEFAULT_PORTFOLIO.get(t, {}).get("weight", 1.0 / len(selected_tickers)) * 100)
    w = st.sidebar.slider(f"{t} Weight", 0, 100, default_w, 5)
    raw_weights.append(w)
    custom_weights[t] = w

# Normalize weights
sum_w = sum(raw_weights)
if sum_w == 0:
    portfolio_weights = {t: 1.0 / len(selected_tickers) for t in selected_tickers}
else:
    portfolio_weights = {t: custom_weights[t] / sum_w for t in selected_tickers}

# Load Data
with st.spinner("Loading analytical data and market prices..."):
    df_prices, asset_meta = load_pipeline_data(selected_tickers)

# Compute Engine Analytics
analytics_engine = PortfolioAnalyticsEngine(df_prices, portfolio_weights, BENCHMARK_TICKER)
metrics = analytics_engine.compute_all_metrics()

# App Header
st.markdown('<div class="main-title">🏛️ Wealth Management & Portfolio Intelligence Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">AI-Powered Data Engineering, Quantitative Risk Analytics, Markowitz Optimization & Cashflow Testing</div>', unsafe_allow_html=True)

# Main Navigation Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Performance Cockpit",
    "📈 Markowitz Optimizer",
    "🔮 Monte Carlo Simulator",
    "💸 Cash Flow & Withdrawal Sandbox",
    "🤖 AI Research Copilot & Digest"
])

# ---------------------------------------------------------
# TAB 1: PERFORMANCE COCKPIT
# ---------------------------------------------------------
with tab1:
    st.subheader("Key Portfolio Performance & Risk KPIs")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Cumulative Return", f"{metrics['cumulative_return']*100:.2f}%")
    col2.metric("Annualized CAGR", f"{metrics['cagr']*100:.2f}%", f"SPY: {metrics['benchmark_cagr']*100:.2f}%")
    col3.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    col4.metric("Sortino Ratio", f"{metrics['sortino_ratio']:.2f}")
    col5.metric("Max Drawdown", f"{metrics['max_drawdown']*100:.2f}%")

    st.markdown("---")
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Cumulative Growth vs S&P 500 Benchmark ($100 Base)")
        df_cum = analytics_engine.get_cumulative_performance_series()
        fig_cum = px.line(df_cum, x=df_cum.index, y=["Portfolio", "Benchmark (SPY)"],
                          labels={"value": "Portfolio Value ($)", "date": "Date"},
                          color_discrete_map={"Portfolio": "#1B365D", "Benchmark (SPY)": "#D9534F"})
        fig_cum.update_layout(legend_title_text="", hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_cum, use_container_width=True)

    with c2:
        st.subheader("Asset Allocation Breakdown")
        df_weights = pd.DataFrame([
            {"Asset": t, "Weight": w * 100} for t, w in portfolio_weights.items()
        ])
        fig_pie = px.pie(df_weights, values="Weight", names="Asset", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Set2)
        fig_pie.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    # Drawdown Chart
    st.subheader("Historical Portfolio Peak-to-Trough Drawdowns")
    s_dd = analytics_engine.get_drawdown_series() * 100
    fig_dd = px.area(x=s_dd.index, y=s_dd.values, labels={"x": "Date", "y": "Drawdown (%)"},
                     color_discrete_sequence=["#D9534F"])
    fig_dd.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_dd, use_container_width=True)

# ---------------------------------------------------------
# TAB 2: MARKOWITZ EFFICIENT FRONTIER OPTIMIZER
# ---------------------------------------------------------
with tab2:
    st.subheader("Modern Portfolio Theory (MPT) Efficient Frontier")
    st.write("Quantitative optimization utilizing SciPy to determine mathematical asset weights for Maximum Sharpe and Minimum Risk.")

    optimizer = MarkowitzOptimizer(df_prices, selected_tickers)
    df_random, df_frontier, max_sharpe_res, min_vol_res = optimizer.generate_efficient_frontier()

    c1, c2 = st.columns([2, 1])
    
    with c1:
        fig_ef = px.scatter(df_random, x="volatility", y="return", color="sharpe",
                            labels={"volatility": "Annualized Volatility (Risk)", "return": "Expected Annual Return"},
                            title="Random Portfolios Cloud & Efficient Frontier Curve",
                            color_continuous_scale="Viridis")
        
        # Add Frontier Line
        fig_ef.add_trace(go.Scatter(x=df_frontier["frontier_volatility"], y=df_frontier["frontier_return"],
                                    mode="lines", name="Efficient Frontier", line=dict(color="#1B365D", width=3)))
        
        # Highlight Max Sharpe & Min Volatility
        fig_ef.add_trace(go.Scatter(x=[max_sharpe_res["volatility"]], y=[max_sharpe_res["expected_return"]],
                                    mode="markers", name="Max Sharpe Ratio", marker=dict(size=14, color="gold", symbol="star")))
        fig_ef.add_trace(go.Scatter(x=[min_vol_res["volatility"]], y=[min_vol_res["expected_return"]],
                                    mode="markers", name="Min Volatility", marker=dict(size=12, color="red", symbol="diamond")))

        st.plotly_chart(fig_ef, use_container_width=True)

    with c2:
        st.subheader("Optimization Results")
        
        st.markdown("**⭐ Maximum Sharpe Ratio Portfolio**")
        st.json(max_sharpe_res["weights"])
        st.caption(f"Expected Return: {max_sharpe_res['expected_return']*100:.1f}% | Volatility: {max_sharpe_res['volatility']*100:.1f}% | Sharpe: {max_sharpe_res['sharpe_ratio']:.2f}")

        st.markdown("---")
        
        st.markdown("**🛡️ Minimum Volatility Portfolio**")
        st.json(min_vol_res["weights"])
        st.caption(f"Expected Return: {min_vol_res['expected_return']*100:.1f}% | Volatility: {min_vol_res['volatility']*100:.1f}%")

# ---------------------------------------------------------
# TAB 3: MONTE CARLO RETIREMENT SIMULATOR
# ---------------------------------------------------------
with tab3:
    st.subheader("Stochastic Wealth & Retirement Forecast")
    
    col_a, col_b, col_c, col_d = st.columns(4)
    init_inv = col_a.number_input("Initial Principal ($)", 10000, 1000000, 100000, step=10000)
    monthly_contrib = col_b.number_input("Monthly Deposit ($)", 0, 10000, 1000, step=250)
    horizon_years = col_c.slider("Time Horizon (Years)", 5, 40, 20)
    inflation_rate = col_d.slider("Expected Inflation Rate (%)", 0.0, 8.0, 2.5, 0.5) / 100.0

    # Run Monte Carlo
    exp_return = max_sharpe_res["expected_return"]
    exp_vol = max_sharpe_res["volatility"]
    
    simulator = MonteCarloSimulator(exp_return, exp_vol)
    mc_res = simulator.run_simulation(
        initial_investment=init_inv,
        monthly_cashflow=monthly_contrib,
        years=horizon_years,
        num_simulations=3000,
        inflation_rate=inflation_rate
    )

    percentiles = mc_res["percentiles"]
    months_x = np.arange(0, mc_res["months"] + 1) / 12.0

    # Plot Percentile Fan Chart
    fig_mc = go.Figure()
    fig_mc.add_trace(go.Scatter(x=months_x, y=percentiles["95th_optimistic"], mode="lines", name="95th Percentile (Optimistic)", line=dict(color="#28A745")))
    fig_mc.add_trace(go.Scatter(x=months_x, y=percentiles["50th_median"], mode="lines", name="50th Percentile (Median)", line=dict(color="#1B365D", width=3)))
    fig_mc.add_trace(go.Scatter(x=months_x, y=percentiles["5th_conservative"], mode="lines", name="5th Percentile (Conservative)", line=dict(color="#DC3545")))

    fig_mc.update_layout(title="Wealth Accumulation Trajectory Across 3,000 Stochastic Paths",
                          xaxis_title="Years", yaxis_title="Portfolio Wealth ($)",
                          hovermode="x unified")
    st.plotly_chart(fig_mc, use_container_width=True)

    # Terminal Wealth Summary Tiles
    t_stats = mc_res["terminal_wealth_stats"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("5th % Conservative", f"${t_stats['p5_nominal']:,.0f}")
    m2.metric("50th % Median Wealth", f"${t_stats['p50_nominal']:,.0f}")
    m3.metric("95th % Optimistic", f"${t_stats['95_nominal']:,.0f}")
    m4.metric("Real Inflation-Adjusted", f"${t_stats['p50_real_inflation_adjusted']:,.0f}")

# ---------------------------------------------------------
# TAB 4: CASH FLOW & WITHDRAWAL SANDBOX (WHAT-IF TESTING)
# ---------------------------------------------------------
with tab4:
    st.subheader("💸 Cash Flow & Withdrawal Testing Sandbox")
    st.write("Test 'What-If' scenario cash adjustments: withdraw or deposit lump-sums, simulate monthly retirement income withdrawals, and test portfolio survival rates.")

    box_c1, box_c2 = st.columns([1, 1])
    
    with box_c1:
        st.markdown("### 📥 1. Cash Injections / Withdrawals Settings")
        base_wealth = st.number_input("Starting Portfolio Wealth ($)", 10000, 5000000, 250000, step=25000, key="sb_base")
        
        cash_adj_type = st.radio("One-Time Lump Sum Action Today:", ["No Action", "Withdraw Cash Today", "Deposit Cash Today"], horizontal=True)
        
        if cash_adj_type == "Withdraw Cash Today":
            lump_amount = -st.number_input("Amount to Withdraw ($)", 1000, 500000, 25000, step=5000, key="sb_lump_w")
        elif cash_adj_type == "Deposit Cash Today":
            lump_amount = st.number_input("Amount to Deposit ($)", 1000, 500000, 25000, step=5000, key="sb_lump_d")
        else:
            lump_amount = 0.0

        st.markdown("---")
        st.markdown("### 🔄 2. Recurring Monthly Cash Flow")
        cf_direction = st.radio("Monthly Cash Flow Type:", ["Deposit (Savings)", "Withdrawal (Retirement Income)"], horizontal=True)
        
        if cf_direction == "Deposit (Savings)":
            monthly_flow = st.number_input("Monthly Deposit Amount ($)", 0, 20000, 1500, step=250, key="sb_m_dep")
        else:
            monthly_flow = -st.number_input("Monthly Withdrawal Amount ($)", 0, 20000, 1500, step=250, key="sb_m_wdr")

        sim_years = st.slider("Testing Duration (Years)", 5, 35, 20, key="sb_years")

    # Run Sandbox Simulation
    exp_return = max_sharpe_res["expected_return"]
    exp_vol = max_sharpe_res["volatility"]
    
    sandbox_sim = MonteCarloSimulator(exp_return, exp_vol)
    
    # Baseline (No adjustment)
    res_base = sandbox_sim.run_simulation(
        initial_investment=base_wealth,
        monthly_cashflow=0.0,
        years=sim_years,
        num_simulations=2000,
        one_time_cash_adjustment=0.0
    )
    
    # Test Scenario
    res_test = sandbox_sim.run_simulation(
        initial_investment=base_wealth,
        monthly_cashflow=monthly_flow,
        years=sim_years,
        num_simulations=2000,
        one_time_cash_adjustment=lump_amount
    )

    with box_c2:
        st.markdown("### 📊 Scenario Impact & Survival Analysis")
        
        # Metrics Comparison Tiles
        s1, s2, s3 = st.columns(3)
        net_start = base_wealth + lump_amount
        s1.metric("Adjusted Start Capital", f"${net_start:,.0f}", delta=f"${lump_amount:,.0f}" if lump_amount != 0 else None)
        
        surv_pct = res_test["survival_rate"] * 100
        surv_delta = (res_test["survival_rate"] - res_base["survival_rate"]) * 100
        s2.metric("Portfolio Survival Rate", f"{surv_pct:.1f}%", delta=f"{surv_delta:+.1f}%" if surv_delta != 0 else None)
        
        p50_test = res_test["terminal_wealth_stats"]["p50_nominal"]
        p50_base = res_base["terminal_wealth_stats"]["p50_nominal"]
        p50_diff = p50_test - p50_base
        s3.metric("Projected Median Wealth", f"${p50_test:,.0f}", delta=f"${p50_diff:,.0f}")

        # Comparison Chart
        months_x = np.arange(0, res_test["months"] + 1) / 12.0
        p50_base_curve = res_base["percentiles"]["50th_median"]
        p50_test_curve = res_test["percentiles"]["50th_median"]

        fig_compare = go.Figure()
        fig_compare.add_trace(go.Scatter(x=months_x, y=p50_base_curve, mode="lines", name="Baseline (No Cash Change)", line=dict(color="#6C757D", dash="dash")))
        fig_compare.add_trace(go.Scatter(x=months_x, y=p50_test_curve, mode="lines", name="Tested Scenario Trajectory", line=dict(color="#1B365D", width=3)))
        
        fig_compare.update_layout(
            title=f"Median Wealth Comparison: Baseline vs Tested Scenario ({sim_years} Years)",
            xaxis_title="Years",
            yaxis_title="Portfolio Wealth ($)",
            hovermode="x unified"
        )
        st.plotly_chart(fig_compare, use_container_width=True)

        if surv_pct < 100.0:
            st.warning(f"⚠️ **Ruin Risk Warning**: Under this withdrawal rate, there is a **{(100 - surv_pct):.1f}% risk** of completely depleting the portfolio within {sim_years} years.")
        else:
            st.success(f"✅ **Safe Withdrawal Rate**: Portfolio has a **100% survival probability** over {sim_years} years under expected asset growth.")

# ---------------------------------------------------------
# TAB 5: AI RESEARCH COPILOT & EXECUTIVE DIGEST
# ---------------------------------------------------------
with tab5:
    st.subheader("🤖 AI Financial Research Copilot & SEC Intelligence RAG")
    st.write("Query financial insights, business risk factors, and revenue drivers indexed from SEC disclosures.")

    rag_agent = SECFinancialRAGAgent()
    user_query = st.text_input("Ask AI Financial Research Copilot:", "What are NVDA and AAPL supply chain risk factors?")
    
    if user_query:
        with st.spinner("AI RAG Agent analyzing financial context..."):
            answer = rag_agent.answer_financial_query(user_query)
            st.markdown(answer)

    st.markdown("---")
    st.subheader("📄 Automated Executive Investment Digest")
    
    if st.button("Generate Executive Digest"):
        digest_gen = ExecutiveDigestGenerator(metrics, max_sharpe_res, mc_res)
        md_digest = digest_gen.generate_markdown_digest()
        
        st.markdown(md_digest)
        st.download_button(
            label="📥 Download Executive Digest (.md)",
            data=md_digest,
            file_name="Executive_Portfolio_Digest.md",
            mime="text/markdown"
        )
