import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "wealth"
PARQUET_DIR = DATA_DIR / "parquet"
DUCKDB_PATH = DATA_DIR / "wealth_intelligence.duckdb"

# Create directories if they do not exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PARQUET_DIR.mkdir(parents=True, exist_ok=True)

# Default Portfolio Settings
DEFAULT_PORTFOLIO = {
    "AAPL": {"weight": 0.25, "name": "Apple Inc.", "sector": "Technology"},
    "MSFT": {"weight": 0.25, "name": "Microsoft Corp.", "sector": "Technology"},
    "NVDA": {"weight": 0.20, "name": "NVIDIA Corp.", "sector": "Technology"},
    "GOOGL": {"weight": 0.15, "name": "Alphabet Inc.", "sector": "Communication Services"},
    "AMZN": {"weight": 0.15, "name": "Amazon.com Inc.", "sector": "Consumer Cyclical"}
}

BENCHMARK_TICKER = "SPY"  # S&P 500 ETF Trust
RISK_FREE_RATE = 0.045     # 4.5% Risk-Free Rate baseline

# Default Date Range
START_DATE = "2021-01-01"
END_DATE = None  # Fetch up to current date

# AI / Gemini Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
