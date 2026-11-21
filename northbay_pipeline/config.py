"""
Northbay Capital ETL Pipeline - Configuration Module
===================================================
Mentor Note for Beginners:
In professional data engineering, hardcoding file paths or configurations inside
transformation or load scripts leads to fragile code that breaks easily when moved.
Instead, we centralize all file paths, database connection strings, and system
constants in a dedicated `config.py` file. Any component needing a path imports it
from here.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# ==============================================================================
# 1. DIRECTORY PATHS
# ==============================================================================
# BASE_DIR is the root project directory where northbay_finance_dataset.xlsx lives
BASE_DIR = Path(__file__).resolve().parent.parent

# Pipeline root directory (where this script and modules live)
PIPELINE_DIR = Path(__file__).resolve().parent

# Sub-directories for output data and execution logs
LOGS_DIR = PIPELINE_DIR / "logs"
OUTPUT_DIR = PIPELINE_DIR / "output"

# Ensure output directories always exist before execution starts
LOGS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# File Paths
# The pipeline explicitly consumes the DIRTY version of the dataset
EXCEL_INPUT_PATH = BASE_DIR / "northbay_finance_dataset.xlsx"
DATABASE_PATH = OUTPUT_DIR / "northbay.db"
DATA_QUALITY_REPORT_PATH = OUTPUT_DIR / "data_quality_report.md"

# ==============================================================================
# 2. SHEET & SCHEMA DEFINITIONS
# ==============================================================================
# The sheet names expected in the source Excel workbook
SHEET_NAMES = [
    "customers",
    "accounts",
    "transactions",
    "index_prices",
    "trades",
    "loans",
    "data_dictionary"
]

# Primary keys for each entity (used for deduplication and referential integrity)
PRIMARY_KEYS = {
    "customers": "customer_id",
    "accounts": "account_id",
    "transactions": "transaction_id",
    "trades": "trade_id",
    "loans": "loan_id",
}

# Foreign key relationships: child_sheet -> (child_fk_column, parent_sheet, parent_pk_column)
FOREIGN_KEYS = {
    "accounts": [("customer_id", "customers", "customer_id")],
    "transactions": [("account_id", "accounts", "account_id")],
    "trades": [("account_id", "accounts", "account_id")],
    "loans": [("customer_id", "customers", "customer_id")],
}

# Expected strictly positive numeric columns
STRICTLY_POSITIVE_COLS = {
    "transactions": ["amount"],
    "trades": ["lot_size"],
    "loans": ["principal", "monthly_payment"],
    "customers": ["annual_income_php"]
}

# ==============================================================================
# CONFIGURABLE ANOMALY & OUTLIER THRESHOLDS
# ==============================================================================
# Mentor Note: Never hardcode magical numbers in your ETL transform scripts.
# Define them as explicit configuration parameters here so they can be tuned
# by data engineers and risk teams as business requirements evolve.
LOT_SIZE_OUTLIER_THRESHOLD = 10.0           # Max reasonable retail CFD lot size before flagging as anomaly
TRANSACTION_AMOUNT_OUTLIER_THRESHOLD = 10_000_000.0  # Max reasonable single retail transaction amount (PHP)
ANNUAL_INCOME_OUTLIER_THRESHOLD = 50_000_000.0       # Max realistic retail annual income (PHP) before sentinel/glitch

# Symbol catalog metadata for dim_symbol in Star Schema
SYMBOL_METADATA = {
    "US500":  {"name": "S&P 500 Index CFD",        "asset_class": "Equity Index", "region": "United States", "base_currency": "USD"},
    "US30":   {"name": "Dow Jones 30 CFD",         "asset_class": "Equity Index", "region": "United States", "base_currency": "USD"},
    "NAS100": {"name": "Nasdaq 100 CFD",           "asset_class": "Equity Index", "region": "United States", "base_currency": "USD"},
    "GER40":  {"name": "DAX 40 Index CFD",         "asset_class": "Equity Index", "region": "Europe",        "base_currency": "EUR"},
    "JPN225": {"name": "Nikkei 225 CFD",           "asset_class": "Equity Index", "region": "Asia",          "base_currency": "JPY"},
    "HK50":   {"name": "Hang Seng Index CFD",      "asset_class": "Equity Index", "region": "Asia",          "base_currency": "HKD"},
    "UK100":  {"name": "FTSE 100 Index CFD",       "asset_class": "Equity Index", "region": "Europe",        "base_currency": "GBP"},
}

# Reference date for derived age and snapshot calculations
REFERENCE_DATE = "2026-09-30"


# ==============================================================================
# 3. LOGGING CONFIGURATION
# ==============================================================================
def setup_logging(log_to_file: bool = True) -> logging.Logger:
    """
    Mentor Note for Beginners:
    Production pipelines must never use `print()`. `print()` output disappears when
    a terminal closes and cannot be filtered or redirected. Python's `logging`
    module records timestamps, severity levels (INFO, WARNING, ERROR), and module
    names to both the console and persistent log files for debugging.
    """
    logger = logging.getLogger("northbay_pipeline")
    logger.setLevel(logging.INFO)

    # Clear existing handlers to prevent duplicate lines if re-initialized
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter: Timestamp | Level | Module | Message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | [%(module)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Console Handler (outputs to terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (outputs to a timestamped file in logs/)
    if log_to_file:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = LOGS_DIR / f"pipeline_{timestamp_str}.log"
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Initialized file logging -> {log_file_path}")

    return logger
