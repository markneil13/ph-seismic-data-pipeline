import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def create_document():
    doc = docx.Document()
    
    # Set page margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("Finance Data Engineering, Analysis, Data Science & AI\nProject Proposals & Architectural Specifications")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(27, 54, 93) # Navy Blue

    # Subtitle
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run("Prepared for Peer Review with Claude, ChatGPT, and Grok\nDate: October 2026")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(12)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(90, 105, 120)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Executive Overview
    h1 = doc.add_heading("1. Purpose & Executive Overview", level=1)
    h1.runs[0].font.color.rgb = RGBColor(27, 54, 93)
    
    p = doc.add_paragraph(
        "This document presents four detailed, end-to-end finance project specifications designed to demonstrate mastery across four critical disciplines: "
        "Data Engineering (DE), Data Analysis (DA), Data Science & Machine Learning (DS), and Artificial Intelligence / Large Language Models (AI/LLM). "
        "Each project is designed to deliver production-grade deliverables (interactive dashboards, executive reports, real-time alert systems, or credit memos)."
    )
    p.paragraph_format.space_after = Pt(10)

    p_intent = doc.add_paragraph(
        "Purpose of Peer Review: Use this document to evaluate and refine these project architectures using Claude, ChatGPT, and Grok. "
        "Each section includes targeted questions and review prompts to solicit feedback on data pipeline scalability, model selection, LLM accuracy, and resume impact."
    )
    p_intent.paragraph_format.space_after = Pt(14)

    # Projects List
    projects = [
        {
            "id": 1,
            "title": "Project 1: AI-Powered Wealth Management & Portfolio Intelligence Platform",
            "tagline": "End-to-end personal finance & portfolio optimization engine with RAG over earnings reports",
            "de": [
                "API Ingestion: Automated batch/streaming ingestion from Yahoo Finance, Alpha Vantage, and SEC EDGAR APIs.",
                "Storage & Lakehouse: DuckDB + Polars local analytical engine, parquet columnar format, PostgreSQL data warehouse for persistence.",
                "Orchestration & Quality: Prefect or Apache Airflow for DAG scheduling; Great Expectations / Pydantic for data contract validation."
            ],
            "da": [
                "Performance Metrics: Cumulative returns, CAGR, Beta vs S&P 500, Sector & Asset Class concentration breaks.",
                "Risk Analytics: Sharpe Ratio, Sortino Ratio, Maximum Drawdown, Value at Risk (VaR), rolling volatility analysis.",
                "Visual Dashboards: Interactive Plotly / Streamlit layout with dynamic date range selectors and benchmark overlays."
            ],
            "ds": [
                "Modern Portfolio Theory (MPT): Markowitz Efficient Frontier optimization for optimal asset weighting under risk/return targets.",
                "Monte Carlo Simulations: 10,000-path stochastic modeling for 10-to-30-year wealth projections and retirement success probabilities.",
                "Forecasting: ARIMA / Prophet / LSTM baseline price movement forecasting for tactical asset rebalancing."
            ],
            "ai": [
                "Financial RAG Pipeline: Vector database (ChromaDB/Qdrant) indexing quarterly 10-K and 10-Q filings.",
                "AI Market Intelligence Agent: Gemini / LLM multi-document analysis extracting business risks and management commentary.",
                "Automated Digest: Generates weekly executive portfolio summaries explaining market movements with cited SEC sources."
            ],
            "deliverables": [
                "Interactive Web Dashboard (Streamlit / Standalone HTML).",
                "Automated Weekly PDF/Markdown Executive Investment Digest.",
                "Monte Carlo Wealth Projection Simulator tool."
            ],
            "stack": "Python, DuckDB, Polars, PostgreSQL, Prefect, Streamlit, Plotly, SciPy, ChromaDB, Gemini LLM API."
        },
        {
            "id": 2,
            "title": "Project 2: Corporate Credit Risk & Financial Distress Prediction Engine",
            "tagline": "FinTech credit scoring pipeline with ML bankruptcy prediction and AI automated credit memos",
            "de": [
                "Financial Statement Ingestion: Automated extraction of 10-K balance sheets, income statements, and cash flow data.",
                "Feature Store: Standardized financial ratio feature engineering pipeline built with dbt and Polars.",
                "Data Quality: Strict data validation rules preventing missing values and ensuring accounting equation consistency."
            ],
            "da": [
                "Financial Ratio Analysis: Altman Z-Score, DuPont breakdown (ROE breakdown into margin, turnover, leverage), Liquidity & Solvency ratios.",
                "Peer Group Benchmarking: Industry cross-sectional ranking and percentile scoring.",
                "Underwriting Dashboards: Executive summary dashboards highlighting default risk triggers."
            ],
            "ds": [
                "Default Classification: XGBoost / LightGBM supervised learning model predicting 12-month Probability of Default (PD).",
                "Loss Estimation: Loss Given Default (LGD) and Exposure at Default (EAD) expected loss calculations.",
                "Model Explainability: SHAP (SHapley Additive exPlanations) values to break down exact feature contributions per company."
            ],
            "ai": [
                "AI Underwriter Agent: Synthesizes quantitative financial ratios + SHAP feature importance + text notes into formal credit memos.",
                "Risk Factor Summarizer: LLM reads audit notes and legal risk disclosures to flag qualitative default threats."
            ],
            "deliverables": [
                "Credit Risk Underwriting Dashboard.",
                "SHAP Model Governance & Explainability Report.",
                "Automated 2-Page Executive Credit Underwriting Memo PDF."
            ],
            "stack": "Python, dbt, Polars, DuckDB, XGBoost, LightGBM, SHAP, Streamlit, Gemini LLM API, ReportLab/WeasyPrint."
        },
        {
            "id": 3,
            "title": "Project 3: Real-Time Market Anomaly Detection & Volatility Alert System",
            "tagline": "High-throughput streaming pipeline for flash-crash detection and instant AI root-cause alerts",
            "de": [
                "Stream Ingestion: High-frequency WebSocket ingestion from crypto/stock exchanges (Binance, Coinbase, Polygon.io).",
                "Message Streaming: Apache Kafka / Redpanda message broker handling raw tick data.",
                "Real-time Aggregation: Rolling window aggregations (1-min, 5-min candles) with Faust or Polars streaming engine."
            ],
            "da": [
                "Technical Indicators: Real-time RSI, Bollinger Bands, Moving Average Convergence Divergence (MACD), Volume Surges.",
                "Order Book Imbalance: Bid-ask spread dynamics, depth pressure indicators.",
                "Live Analytics UI: Real-time auto-refreshing streaming dashboards."
            ],
            "ds": [
                "Unsupervised Anomaly Detection: Isolation Forest and Autoencoders trained to detect abnormal price/volume spikes.",
                "Volatility Modeling: GARCH(1,1) model for short-term price variance and volatility clustering forecasts."
            ],
            "ai": [
                "News Sentiment Agent: Monitors financial news RSS feeds and X/Twitter API upon anomaly detection.",
                "Instant AI Cause Summarizer: Correlates detected price anomaly with real-time news headlines to explain 'WHY' market moved."
            ],
            "deliverables": [
                "Live Streaming Anomaly Dashboard (Grafana / Streamlit).",
                "Automated Discord / Telegram Bot triggering instant alerts with AI explanations.",
                "Volatility Strategy Backtesting Report."
            ],
            "stack": "Python, Kafka/Redpanda, Faust/Polars, Grafana, Isolation Forest, GARCH (arch library), Gemini LLM API, Telegram Bot API."
        },
        {
            "id": 4,
            "title": "Project 4: Financial NLP & Earnings Call Intelligence Research Agent",
            "tagline": "Multi-document GenAI research copilot for equity analysts parsing transcripts and sentiment shifts",
            "de": [
                "Document Crawler: Scraper and crawler fetching quarterly earnings call transcripts and earnings releases.",
                "Text Chunking & Metadata Pipeline: Smart semantic chunking preserving speaker roles (CEO, CFO, Analyst) and financial quarters.",
                "Vector DB Management: Managed ChromaDB / Qdrant vector index with hybrid search (dense + BM25 sparse keyword)."
            ],
            "da": [
                "Sentiment Trend Analysis: Historical executive sentiment tracking over 8 consecutive quarters vs stock price outcome.",
                "Topic Shift Analysis: Comparative tracking of executive keyword emphasis (e.g. inflation, AI capex, hiring freezes)."
            ],
            "ds": [
                "Domain NLP Sentiment: FinBERT fine-tuned model classifying sentence-level financial sentiment.",
                "Topic Modeling: BERTopic for unsupervised theme extraction across industry transcript corpora."
            ],
            "ai": [
                "Multi-Document Financial RAG: RAG agent capable of multi-company comparative query answering with exact line citations.",
                "Executive Summary Generator: Automated 1-page summary of earnings calls capturing guidance, surprises, and QA sentiment."
            ],
            "deliverables": [
                "Interactive AI Equity Research Copilot Web UI.",
                "Quantitative Earnings Sentiment & Guidance Dashboard.",
                "Automated Quarterly Earnings Briefings."
            ],
            "stack": "Python, BeautifulSoup/Scrapy, ChromaDB/Qdrant, FinBERT (HuggingFace), BERTopic, LangChain/LlamaIndex, Streamlit, Gemini LLM."
        }
    ]

    for proj in projects:
        doc.add_heading(proj["title"], level=1).runs[0].font.color.rgb = RGBColor(27, 54, 93)
        
        p_tag = doc.add_paragraph()
        r_tag = p_tag.add_run(f"Tagline: {proj['tagline']}")
        r_tag.font.italic = True
        r_tag.font.bold = True
        r_tag.font.color.rgb = RGBColor(0, 102, 153)
        p_tag.paragraph_format.space_after = Pt(8)

        # 4 Pillars
        doc.add_heading("Key Components & Architecture", level=2).runs[0].font.color.rgb = RGBColor(40, 80, 120)
        
        # DE
        p_de = doc.add_paragraph()
        r_de_h = p_de.add_run("1. Data Engineering (DE):\n")
        r_de_h.bold = True
        for item in proj["de"]:
            p_bullet = doc.add_paragraph(style='List Bullet')
            p_bullet.add_run(item)
            p_bullet.paragraph_format.space_after = Pt(3)

        # DA
        p_da = doc.add_paragraph()
        r_da_h = p_da.add_run("2. Data Analysis (DA):\n")
        r_da_h.bold = True
        for item in proj["da"]:
            p_bullet = doc.add_paragraph(style='List Bullet')
            p_bullet.add_run(item)
            p_bullet.paragraph_format.space_after = Pt(3)

        # DS
        p_ds = doc.add_paragraph()
        r_ds_h = p_ds.add_run("3. Data Science & Machine Learning (DS):\n")
        r_ds_h.bold = True
        for item in proj["ds"]:
            p_bullet = doc.add_paragraph(style='List Bullet')
            p_bullet.add_run(item)
            p_bullet.paragraph_format.space_after = Pt(3)

        # AI
        p_ai = doc.add_paragraph()
        r_ai_h = p_ai.add_run("4. Artificial Intelligence & LLM Integration (AI):\n")
        r_ai_h.bold = True
        for item in proj["ai"]:
            p_bullet = doc.add_paragraph(style='List Bullet')
            p_bullet.add_run(item)
            p_bullet.paragraph_format.space_after = Pt(3)

        # Deliverables & Stack
        doc.add_heading("Tangible Deliverables & Tech Stack", level=2).runs[0].font.color.rgb = RGBColor(40, 80, 120)
        p_del = doc.add_paragraph()
        p_del.add_run("Tangible Deliverables:").bold = True
        for item in proj["deliverables"]:
            p_bullet = doc.add_paragraph(style='List Bullet')
            p_bullet.add_run(item)
            p_bullet.paragraph_format.space_after = Pt(3)

        p_stk = doc.add_paragraph()
        r_stk_lbl = p_stk.add_run("Recommended Tech Stack: ")
        r_stk_lbl.bold = True
        p_stk.add_run(proj["stack"])
        p_stk.paragraph_format.space_after = Pt(12)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Comparison Matrix Section
    h_comp = doc.add_heading("3. Project Comparison Matrix", level=1)
    h_comp.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    table = doc.add_table(rows=5, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'

    headers = ["Project Name", "DE Complexity", "DS/ML Focus", "AI/LLM Depth", "Business Value"]
    hdr_cells = table.rows[0].cells
    for i, header_text in enumerate(headers):
        hdr_cells[i].text = header_text
        set_cell_background(hdr_cells[i], "1B365D") # Navy blue
        for paragraph in hdr_cells[i].paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                run.font.size = Pt(10)

    matrix_data = [
        ["1. Wealth Management", "Medium (Batch/Lakehouse)", "High (MPT, Monte Carlo)", "High (SEC RAG, Digest)", "Very High (Personal / FinTech)"],
        ["2. Credit Risk Engine", "Medium (dbt/Feature Store)", "Very High (XGBoost, SHAP)", "Medium (Credit Memo Agent)", "Very High (Banking / Risk)"],
        ["3. Real-Time Anomaly", "Very High (Kafka/Streaming)", "High (GARCH, Isolation Forest)", "Medium (News Sentiment Agent)", "High (Trading / Market Ops)"],
        ["4. Financial NLP Agent", "High (Scraper, Vector DB)", "High (FinBERT, BERTopic)", "Very High (Multi-Doc RAG)", "High (Equity Research / Hedge Funds)"]
    ]

    for row_idx, data in enumerate(matrix_data):
        row_cells = table.rows[row_idx + 1].cells
        bg_color = "F2F4F7" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, cell_value in enumerate(data):
            row_cells[col_idx].text = cell_value
            set_cell_background(row_cells[col_idx], bg_color)
            for paragraph in row_cells[col_idx].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # Peer Review Prompts Section
    h_prompt = doc.add_heading("4. Peer Review Prompts for Claude, ChatGPT & Grok", level=1)
    h_prompt.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    p_pintro = doc.add_paragraph(
        "Copy and paste the prompt templates below into Claude, ChatGPT, or Grok to perform a comprehensive peer review of these project specifications:"
    )
    p_pintro.paragraph_format.space_after = Pt(8)

    prompts = [
        ("Prompt 1: Architectural & Technical Feasibility Check",
         "\"I am planning a portfolio project combining Data Engineering, Data Analysis, Data Science, and AI for the finance domain. "
         "Here are 4 project proposals [Paste contents of this doc]. Please review them and tell me:\n"
         "1. Which project has the best balance of data pipeline engineering complexity and machine learning rigor?\n"
         "2. Are there any hidden technical pitfalls or bottleneck risks in the proposed DE or DS stacks?\n"
         "3. How can I optimize the data storage (e.g., DuckDB vs PostgreSQL vs Parquet) for maximum performance on a single machine before scaling?\""),
        
        ("Prompt 2: Resume & Portfolio Impact Review",
         "\"As a Senior Principal Data Engineer / Lead AI Engineer, review these 4 project concepts [Paste contents of this doc]. "
         "Which project would impress hiring managers the most for a Lead Data Engineer or Data Scientist role? "
         "Provide specific recommendations on metrics, deliverables, or cloud architecture upgrades (e.g., AWS/GCP, Snowflake, Airflow) to make it production-ready.\""),

        ("Prompt 3: Customizing Project #1 (Wealth Management Platform)",
         "\"I want to proceed with Project #1 (AI-Powered Wealth Management & Portfolio Intelligence Platform). "
         "Help me refine the project scope:\n"
         "1. Give me a step-by-step modular repository structure (folder architecture).\n"
         "2. Recommend the exact API endpoints to use for free market data and SEC filings.\n"
         "3. Write a sample Python snippet demonstrating how to integrate DuckDB with Monte Carlo simulation and Gemini LLM RAG.\"")
    ]

    for title, text in prompts:
        p_ptitle = doc.add_paragraph()
        r_ptitle = p_ptitle.add_run(title)
        r_ptitle.bold = True
        r_ptitle.font.color.rgb = RGBColor(0, 102, 153)
        p_ptitle.paragraph_format.space_after = Pt(3)

        p_box = doc.add_paragraph()
        p_box.paragraph_format.left_indent = Inches(0.2)
        p_box.paragraph_format.right_indent = Inches(0.2)
        r_box = p_box.add_run(text)
        r_box.font.name = "Consolas"
        r_box.font.size = Pt(9)
        r_box.font.color.rgb = RGBColor(40, 40, 40)
        p_box.paragraph_format.space_after = Pt(10)

    # Save document
    file_path = r"c:\Users\marki\Desktop\uncloud\Personal\AI Pursuits\data engineering lol\Finance_DE_DA_DS_AI_Project_Proposals.docx"
    doc.save(file_path)
    print(f"Successfully generated DOCX at: {file_path}")

if __name__ == "__main__":
    create_document()
