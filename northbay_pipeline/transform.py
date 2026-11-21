"""
Northbay Capital ETL Pipeline - Transform Module
===============================================
Mentor Note for Beginners:
The 'T' in ETL is where raw, messy data is shaped into clean, high-value,
business-ready assets. In this module, we implement:

1. Deduplication:
   Drop exact row duplicates and primary key collisions while preserving first records.
2. Text Normalization:
   Strip invisible leading/trailing whitespaces, standardize capitalization, and map
   known data-entry aliases (e.g., 'MNL' -> 'Manila', 'QC' -> 'Quezon City').
3. Date Parsing & Standardization:
   Parse mixed date strings into uniform datetime objects and serialize to ISO-8601 strings.
4. Auditable Anomaly Governance (Flagging instead of Deleting):
   A critical rule in data engineering: NEVER silently drop or mutate financial numbers
   without creating an audit trail. We add `is_flagged` (0 or 1) and `flag_reason`.
   - Negative amounts are corrected to positive (`abs()`) and tagged.
   - Extreme outliers (e.g., 50M PHP deposit or 500-lot trade) are preserved but flagged.
   - Glitched placeholders (e.g., 999,999,999 PHP income) are imputed with median and flagged.
5. Domain-Informed Imputation:
   Fill missing values using transparent business heuristics (e.g. median credit scores,
   inferring trade exit reasons from profit/loss).
6. Feature Engineering:
   Calculate `trade_duration_hours`, `trade_month`, `customer_age`, `is_win`, `credit_band`.
7. Star Schema Modeling:
   Generate dedicated `dim_date` and `dim_symbol` dimensions, and link fact tables
   via integer surrogate `date_key` (YYYYMMDD).
"""

import logging
import math
import pandas as pd
import numpy as np
from typing import Dict, Tuple

try:
    from .config import (
        PRIMARY_KEYS,
        SYMBOL_METADATA,
        REFERENCE_DATE,
        LOT_SIZE_OUTLIER_THRESHOLD,
        TRANSACTION_AMOUNT_OUTLIER_THRESHOLD,
        ANNUAL_INCOME_OUTLIER_THRESHOLD
    )
except ImportError:
    from config import (
        PRIMARY_KEYS,
        SYMBOL_METADATA,
        REFERENCE_DATE,
        LOT_SIZE_OUTLIER_THRESHOLD,
        TRANSACTION_AMOUNT_OUTLIER_THRESHOLD,
        ANNUAL_INCOME_OUTLIER_THRESHOLD
    )

logger = logging.getLogger("northbay_pipeline")


def clean_text(val: any) -> any:
    """Trim whitespace and standardize string values."""
    if pd.isna(val) or val is None:
        return val
    s = str(val).strip()
    return s if s != "" else np.nan


def transform_customers(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Clean and reshape customer records into dim_customers."""
    logger.info("Transforming 'customers' -> 'dim_customers'...")
    df = df_raw.copy()

    # 1. Deduplicate on primary key
    df.drop_duplicates(subset=["customer_id"], keep="first", inplace=True)

    # 2. Add audit flag columns
    df["is_flagged"] = 0
    df["flag_reason"] = ""
    df["raw_value"] = None

    # 3. Clean string columns
    str_cols = ["full_name", "gender", "city", "region", "country", "occupation", "risk_profile", "kyc_status", "acquisition_channel"]
    for c in str_cols:
        if c in df.columns:
            df[c] = df[c].apply(clean_text)

    # 4. Standardize text anomalies
    # City aliases mapping
    city_map = {
        "manila": "Manila",
        "manila ": "Manila",
        " Manila": "Manila",
        "MNL": "Manila",
        "MANILA": "Manila",
        "Metro Manila": "Manila",
        "quezon city": "Quezon City",
        "quezon city ": "Quezon City",
        " Quezon City": "Quezon City",
        "QUEZON CITY": "Quezon City",
        "QC": "Quezon City"
    }
    df["city"] = df["city"].astype(str).str.strip().replace(city_map)

    # Gender standardization
    gender_map = {
        "M": "Male",
        "male": "Male",
        " Male": "Male",
        "F": "Female",
        "female": "Female",
        " Female": "Female"
    }
    df["gender"] = df["gender"].astype(str).str.strip().replace(gender_map)

    # 5. Handle missing values
    df["occupation"] = df["occupation"].fillna("Unknown")
    df["acquisition_channel"] = df["acquisition_channel"].fillna("Unknown")

    # 6. Parse date columns (handling mixed formats)
    df["birth_date"] = pd.to_datetime(df["birth_date"], format="mixed").dt.strftime("%Y-%m-%d")
    df["signup_date"] = pd.to_datetime(df["signup_date"], format="mixed").dt.strftime("%Y-%m-%d")

    # 7. Add derived customer_age
    ref_dt = pd.to_datetime(REFERENCE_DATE)
    b_dates = pd.to_datetime(df["birth_date"])
    df["customer_age"] = ((ref_dt - b_dates).dt.days // 365).astype(int)

    # 8. Check and flag placeholder annual income outliers (> ANNUAL_INCOME_OUTLIER_THRESHOLD)
    # Mentor Note: Under the Golden Rule, we NEVER replace bad values with guesses or median imputation.
    # We set obvious errors to NULL, record raw_value, and flag the row.
    income_glitch = df["annual_income_php"] > ANNUAL_INCOME_OUTLIER_THRESHOLD
    for idx in df[income_glitch].index:
        raw_val = str(df.at[idx, "annual_income_php"])
        df.at[idx, "is_flagged"] = 1
        df.at[idx, "flag_reason"] = f"Annual income ({raw_val}) exceeds threshold; set to NULL"
        df.at[idx, "raw_value"] = raw_val
        df.at[idx, "annual_income_php"] = np.nan

    df["annual_income_php"] = df["annual_income_php"].round(2)
    df["is_active"] = df["is_active"].astype(bool)

    logger.info(f"dim_customers prepared: {len(df):,} records.")
    return df


def transform_accounts(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Clean and reshape account records into dim_accounts."""
    logger.info("Transforming 'accounts' -> 'dim_accounts'...")
    df = df_raw.copy()

    # 1. Deduplicate
    df.drop_duplicates(subset=["account_id"], keep="first", inplace=True)

    # 2. Trim strings
    for c in ["customer_id", "account_type", "currency", "status"]:
        df[c] = df[c].apply(clean_text)

    # 3. Standardize dates
    df["open_date"] = pd.to_datetime(df["open_date"], format="mixed").dt.strftime("%Y-%m-%d")
    df["close_date"] = pd.to_datetime(df["close_date"], format="mixed").dt.strftime("%Y-%m-%d")

    # Current balance round
    df["current_balance"] = df["current_balance"].round(2)

    logger.info(f"dim_accounts prepared: {len(df):,} records.")
    return df


def transform_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Clean and reshape transaction records into fact_transactions."""
    logger.info("Transforming 'transactions' -> 'fact_transactions'...")
    df = df_raw.copy()

    # 1. Deduplicate
    df.drop_duplicates(subset=["transaction_id"], keep="first", inplace=True)

    # 2. Audit flags
    df["is_flagged"] = 0
    df["flag_reason"] = ""
    df["raw_value"] = None

    # 3. Clean strings & standardize payment methods
    for c in ["account_id", "transaction_type", "currency", "payment_method", "status", "description"]:
        if c in df.columns:
            df[c] = df[c].apply(clean_text)

    df["payment_method"] = df["payment_method"].astype(str).str.strip()
    pm_map = {
        "gcash": "GCash",
        "GCASH": "GCash",
        "G-CASH": "GCash",
        "G-Cash": "GCash",
        "GCash": "GCash",
        "maya": "Maya",
        "MAYA": "Maya",
        "PayMaya": "Maya",
        "Maya": "Maya",
        "nan": "Unspecified",
        "None": "Unspecified",
        "": "Unspecified"
    }
    df["payment_method"] = df["payment_method"].replace(pm_map)
    df["payment_method"] = df["payment_method"].fillna("Unspecified")
    # For missing description, create a standard descriptive memo
    df["description"] = df["description"].fillna(df["transaction_type"] + " (" + df["currency"] + ")")

    # 5. Parse mixed timestamps
    parsed_ts = pd.to_datetime(df["timestamp"], format="mixed")
    df["timestamp"] = parsed_ts.dt.strftime("%Y-%m-%d %H:%M:%S")

    # Add surrogate date_key (YYYYMMDD integer) for star schema linking
    df["date_key"] = parsed_ts.dt.strftime("%Y%m%d").astype(int)

    # 6. Flag negative amounts & set to NULL (No guessing/abs sign assumption)
    neg_mask = df["amount"] < 0
    for idx in df[neg_mask].index:
        raw_amt = str(df.at[idx, "amount"])
        df.at[idx, "amount"] = np.nan
        df.at[idx, "raw_value"] = raw_amt
        df.at[idx, "is_flagged"] = 1
        df.at[idx, "flag_reason"] = f"Negative amount ({raw_amt}) set to NULL"

    # 7. Flag extreme outliers (> TRANSACTION_AMOUNT_OUTLIER_THRESHOLD) & set to NULL (No division by 1,000)
    outlier_mask = df["amount"] > TRANSACTION_AMOUNT_OUTLIER_THRESHOLD
    for idx in df[outlier_mask].index:
        raw_amt = str(df.at[idx, "amount"])
        df.at[idx, "amount"] = np.nan
        df.at[idx, "raw_value"] = raw_amt
        df.at[idx, "is_flagged"] = 1
        current_reason = str(df.at[idx, "flag_reason"] or "")
        df.at[idx, "flag_reason"] = (current_reason + f"; Extreme amount outlier ({raw_amt}) set to NULL").strip("; ")

    df["amount"] = df["amount"].round(2)
    logger.info(f"fact_transactions prepared: {len(df):,} records ({df['is_flagged'].sum()} flagged).")
    return df


def transform_trades(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Clean and reshape trade records into fact_trades."""
    logger.info("Transforming 'trades' -> 'fact_trades'...")
    df = df_raw.copy()

    # 1. Deduplicate
    df.drop_duplicates(subset=["trade_id"], keep="first", inplace=True)

    # 2. Audit flags
    df["is_flagged"] = 0
    df["flag_reason"] = ""
    df["raw_value"] = None

    # 3. Clean strings
    for c in ["account_id", "symbol", "direction", "close_reason"]:
        if c in df.columns:
            df[c] = df[c].apply(clean_text)

    # 4. Handle missing values
    # Impute swap_fee with 0.00
    df["swap_fee"] = df["swap_fee"].fillna(0.00).round(2)

    # Missing close_reason: per instructions, do NOT infer from P&L; set to "Unknown" and flag
    null_cr_mask = df["close_reason"].isna() | (df["close_reason"] == "") | (df["close_reason"] == "nan")
    for idx in df[null_cr_mask].index:
        df.at[idx, "close_reason"] = "Unknown"
        df.at[idx, "raw_value"] = "NULL"
        df.at[idx, "is_flagged"] = 1
        current_reason = str(df.at[idx, "flag_reason"] or "")
        df.at[idx, "flag_reason"] = (current_reason + "; Missing close_reason set to Unknown").strip("; ")

    # 5. Flag negative lot_size & set to NULL (No guessing/abs sign assumption)
    neg_lots = df["lot_size"] < 0
    for idx in df[neg_lots].index:
        raw_lot = str(df.at[idx, "lot_size"])
        df.at[idx, "lot_size"] = np.nan
        df.at[idx, "raw_value"] = raw_lot
        df.at[idx, "is_flagged"] = 1
        current_reason = str(df.at[idx, "flag_reason"] or "")
        df.at[idx, "flag_reason"] = (current_reason + f"; Negative lot size ({raw_lot}) set to NULL").strip("; ")

    # 6. Flag extreme lot size outliers (> LOT_SIZE_OUTLIER_THRESHOLD) & set to NULL (No division by 1,000)
    extreme_lots = df["lot_size"] > LOT_SIZE_OUTLIER_THRESHOLD
    for idx in df[extreme_lots].index:
        raw_lot = str(df.at[idx, "lot_size"])
        df.at[idx, "lot_size"] = np.nan
        df.at[idx, "raw_value"] = raw_lot
        df.at[idx, "is_flagged"] = 1
        current_reason = str(df.at[idx, "flag_reason"] or "")
        df.at[idx, "flag_reason"] = (current_reason + f"; Extreme lot size outlier ({raw_lot}) set to NULL").strip("; ")

    # 7. Parse datetime columns & add derived features
    o_time = pd.to_datetime(df["open_time"], format="mixed")
    c_time = pd.to_datetime(df["close_time"], format="mixed")

    df["open_time"] = o_time.dt.strftime("%Y-%m-%d %H:%M:%S")
    df["close_time"] = c_time.dt.strftime("%Y-%m-%d %H:%M:%S")

    # Star schema date_key based on trade entry date
    df["date_key"] = o_time.dt.strftime("%Y%m%d").astype(int)

    # Derived duration in hours
    duration_hours = (c_time - o_time).dt.total_seconds() / 3600.0
    df["trade_duration_hours"] = duration_hours.round(2)

    # Derived trade_month
    df["trade_month"] = o_time.dt.strftime("%Y-%m")

    # Derived is_win flag
    df["is_win"] = (df["profit_loss"] > 0).astype(int)

    # Round monetary/price columns
    for col in ["lot_size", "open_price", "close_price", "stop_loss", "take_profit", "commission", "profit_loss"]:
        df[col] = df[col].round(2)

    logger.info(f"fact_trades prepared: {len(df):,} records ({df['is_flagged'].sum()} flagged).")
    return df


def transform_loans(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Clean and reshape loan records into fact_loans."""
    logger.info("Transforming 'loans' -> 'fact_loans'...")
    df = df_raw.copy()

    # 1. Deduplicate
    df.drop_duplicates(subset=["loan_id"], keep="first", inplace=True)

    # 2. Audit flags
    df["is_flagged"] = 0
    df["flag_reason"] = ""
    df["raw_value"] = None
    df["credit_score_missing"] = 0

    # 3. Clean strings
    for c in ["customer_id", "loan_type", "status"]:
        if c in df.columns:
            df[c] = df[c].apply(clean_text)

    # 4. Handle missing credit_score:
    # Per instructions: Keep it NULL, add credit_score_missing flag, record raw_value, set is_flagged = 1
    null_score_mask = df["credit_score"].isna()
    for idx in df[null_score_mask].index:
        df.at[idx, "credit_score"] = np.nan
        df.at[idx, "credit_score_missing"] = 1
        df.at[idx, "raw_value"] = "NULL"
        df.at[idx, "is_flagged"] = 1
        df.at[idx, "flag_reason"] = "Missing credit score kept NULL"

    # 5. Flag negative principal & set to NULL (No guessing/abs sign assumption)
    neg_p = df["principal"] < 0
    for idx in df[neg_p].index:
        raw_p = str(df.at[idx, "principal"])
        df.at[idx, "principal"] = np.nan
        df.at[idx, "raw_value"] = raw_p
        df.at[idx, "is_flagged"] = 1
        current_reason = str(df.at[idx, "flag_reason"] or "")
        df.at[idx, "flag_reason"] = (current_reason + f"; Negative principal ({raw_p}) set to NULL").strip("; ")

    # 6. Parse start date & add star schema date_key
    s_date = pd.to_datetime(df["start_date"], format="mixed")
    df["start_date"] = s_date.dt.strftime("%Y-%m-%d")
    df["date_key"] = s_date.dt.strftime("%Y%m%d").astype(int)

    # 7. Add derived credit_band
    def assign_credit_band(score: any) -> any:
        if pd.isna(score) or score is None:
            return None
        score = int(score)
        if score < 580:
            return "Poor (<580)"
        elif score < 670:
            return "Fair (580-669)"
        elif score < 740:
            return "Good (670-739)"
        elif score < 800:
            return "Very Good (740-799)"
        return "Excellent (800+)"

    df["credit_band"] = df["credit_score"].apply(assign_credit_band)

    # Round monetary figures
    for col in ["principal", "monthly_payment", "amount_paid"]:
        df[col] = df[col].round(2)
    df["interest_rate"] = df["interest_rate"].round(4)

    logger.info(f"fact_loans prepared: {len(df):,} records ({df['is_flagged'].sum()} flagged).")
    return df


def generate_dim_date(cleaned_sheets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Mentor Note for Beginners:
    A Date Dimension (`dim_date`) is the backbone of star schemas. Instead of calling
    complex SQL date functions in every query, we precompute calendar attributes
    (year, quarter, month, day_of_week, weekend flag) for every single calendar day.
    """
    logger.info("Generating 'dim_date' dimension table...")

    # Collect min and max dates across all facts
    min_date = pd.to_datetime("2023-01-01")
    max_date = pd.to_datetime("2026-12-31")

    all_days = pd.date_range(start=min_date, end=max_date, freq="D")

    records = []
    for d in all_days:
        records.append({
            "date_key": int(d.strftime("%Y%m%d")),
            "full_date": d.strftime("%Y-%m-%d"),
            "year": int(d.year),
            "quarter": int((d.month - 1) // 3 + 1),
            "month": int(d.month),
            "month_name": d.strftime("%B"),
            "day": int(d.day),
            "day_of_week": int(d.dayofweek + 1),  # 1 = Monday, 7 = Sunday
            "day_name": d.strftime("%A"),
            "is_weekend": 1 if d.dayofweek >= 5 else 0,
            "is_month_end": 1 if d.is_month_end else 0
        })

    dim_date = pd.DataFrame(records)
    logger.info(f"dim_date generated: {len(dim_date):,} calendar days from {min_date.date()} to {max_date.date()}.")
    return dim_date


def generate_dim_symbol(index_prices_df: pd.DataFrame) -> pd.DataFrame:
    """Generate dim_symbol dimension table containing CFD ticker metadata."""
    logger.info("Generating 'dim_symbol' dimension table...")
    unique_symbols = sorted(index_prices_df["symbol"].unique())
    records = []

    for sym in unique_symbols:
        meta = SYMBOL_METADATA.get(sym, {
            "name": sym, "asset_class": "Other", "region": "Global", "base_currency": "USD"
        })
        records.append({
            "symbol": sym,
            "symbol_name": meta["name"],
            "asset_class": meta["asset_class"],
            "market_region": meta["region"],
            "base_currency": meta["base_currency"]
        })

    dim_symbol = pd.DataFrame(records)
    logger.info(f"dim_symbol generated: {len(dim_symbol)} CFD assets.")
    return dim_symbol


def transform_data(raw_sheets: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Execute end-to-end transformation pipeline across all sheets.
    Returns cleaned DataFrames structured for Star Schema loading.
    """
    logger.info("=" * 60)
    logger.info("STEP 3: TRANSFORM - Cleaning, Imputing, and Reshaping Data")
    logger.info("=" * 60)

    clean_customers = transform_customers(raw_sheets["customers"])
    clean_accounts = transform_accounts(raw_sheets["accounts"])
    clean_transactions = transform_transactions(raw_sheets["transactions"])
    clean_trades = transform_trades(raw_sheets["trades"])
    clean_loans = transform_loans(raw_sheets["loans"])
    
    # Index prices: deduplicate and round
    clean_index_prices = raw_sheets["index_prices"].copy()
    clean_index_prices.drop_duplicates(subset=["date", "symbol"], keep="first", inplace=True)
    clean_index_prices["date"] = pd.to_datetime(clean_index_prices["date"]).dt.strftime("%Y-%m-%d")
    clean_index_prices["date_key"] = pd.to_datetime(clean_index_prices["date"]).dt.strftime("%Y%m%d").astype(int)

    # Generate Star Schema dimensions
    dim_date = generate_dim_date(raw_sheets)
    dim_symbol = generate_dim_symbol(clean_index_prices)

    transformed_schema = {
        "dim_customers": clean_customers,
        "dim_accounts": clean_accounts,
        "dim_date": dim_date,
        "dim_symbol": dim_symbol,
        "fact_transactions": clean_transactions,
        "fact_trades": clean_trades,
        "fact_loans": clean_loans,
        "fact_index_prices": clean_index_prices
    }

    logger.info("Transformation step successfully complete.")
    return transformed_schema
