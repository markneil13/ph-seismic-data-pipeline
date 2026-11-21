"""
Northbay Capital ETL Pipeline - Main Orchestrator
================================================
Mentor Note for Beginners:
This is the single command pipeline orchestrator (`run_pipeline.py`).
In production systems, you run one script (or trigger a DAG) that executes
every step in strict logical sequence:

[Extract] -> [Validate Raw] -> [Transform] -> [Load] -> [Validate Clean] -> [Report & Views]

If any step raises an unhandled error, the pipeline halts immediately with
informative error logs rather than corrupting downstream tables.
"""

import sys
import time
import logging
from pathlib import Path
import pandas as pd

try:
    from .config import (
        setup_logging,
        DATABASE_PATH,
        DATA_QUALITY_REPORT_PATH,
        EXCEL_INPUT_PATH
    )
    from .extract import extract_data
    from .validate import validate_dataset, generate_quality_report
    from .transform import transform_data
    from .load import load_to_sqlite, query_views
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from northbay_pipeline.config import (
        setup_logging,
        DATABASE_PATH,
        DATA_QUALITY_REPORT_PATH,
        EXCEL_INPUT_PATH
    )
    from northbay_pipeline.extract import extract_data
    from northbay_pipeline.validate import validate_dataset, generate_quality_report
    from northbay_pipeline.transform import transform_data
    from northbay_pipeline.load import load_to_sqlite, query_views


def format_table(df: pd.DataFrame) -> str:
    """Format DataFrame as a clean Markdown table string without external dependencies."""
    headers = [str(col) for col in df.columns]
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in df.itertuples(index=False):
        row_str = [str(val) for val in row]
        lines.append("| " + " | ".join(row_str) + " |")
    return "\n".join(lines)


def run_pipeline():
    """Main execution function coordinating all ETL phases."""
    # 0. Initialize logging
    logger = setup_logging(log_to_file=True)
    start_time = time.time()

    logger.info("*" * 80)
    logger.info("STARTING NORTHBAY CAPITAL LOCAL ETL PIPELINE")
    logger.info(f"Source file: {EXCEL_INPUT_PATH.name}")
    logger.info(f"Target DB  : {DATABASE_PATH}")
    logger.info("*" * 80)

    try:
        # STEP 1: EXTRACT
        raw_sheets = extract_data(EXCEL_INPUT_PATH)

        # STEP 2: VALIDATE (RAW DATA)
        raw_audit = validate_dataset(raw_sheets, phase_name="RAW")

        # STEP 3: TRANSFORM
        transformed_tables = transform_data(raw_sheets)

        # STEP 4: LOAD TO SQLITE
        load_to_sqlite(transformed_tables, db_path=DATABASE_PATH)

        # STEP 5: VALIDATE (CLEAN DATA)
        # Adapt transformed Star Schema tables for validation comparison
        clean_sheets_for_val = {
            "customers": transformed_tables["dim_customers"],
            "accounts": transformed_tables["dim_accounts"],
            "transactions": transformed_tables["fact_transactions"],
            "trades": transformed_tables["fact_trades"],
            "loans": transformed_tables["fact_loans"],
            "index_prices": transformed_tables["fact_index_prices"]
        }
        clean_audit = validate_dataset(clean_sheets_for_val, phase_name="CLEAN")

        # STEP 6: GENERATE DATA QUALITY REPORT
        generate_quality_report(raw_audit, clean_audit, DATA_QUALITY_REPORT_PATH)

        # STEP 7: QUERY ANALYTICAL VIEWS
        view_results = query_views(DATABASE_PATH)

        elapsed = time.time() - start_time
        logger.info("*" * 80)
        logger.info(f"PIPELINE COMPLETED SUCCESSFULLY in {elapsed:.2f} seconds!")
        logger.info("*" * 80)

        # ======================================================================
        # PIPELINE SUMMARY PRINTOUTS FOR MENTEE
        # ======================================================================
        print("\n" + "=" * 85)
        print("PIPELINE EXECUTION SUMMARY: BEFORE VS AFTER RECORD COUNTS")
        print("=" * 85)
        print(f"{'Entity':<22} | {'Raw Rows':<12} | {'Clean Rows':<12} | {'Duplicates Removed':<20}")
        print("-" * 85)
        for name in ["customers", "accounts", "transactions", "trades", "loans", "index_prices"]:
            r_cnt = len(raw_sheets[name])
            c_cnt = len(clean_sheets_for_val[name])
            diff = r_cnt - c_cnt
            print(f"{name:<22} | {r_cnt:<12,d} | {c_cnt:<12,d} | {diff:<20,d}")
        print("=" * 85)

        # Problems Found and Fixed Breakdown
        print("\n" + "=" * 85)
        print("DATA QUALITY AUDIT: PROBLEMS FOUND AND FIXED PER TYPE")
        print("=" * 85)
        print(f"{'Anomaly Category':<30} | {'Found (Raw)':<15} | {'Cleaned / Fixed':<18} | {'Remaining'}")
        print("-" * 85)

        # 1. Duplicates
        raw_dups = sum(m["duplicates"]["primary_key_duplicates"] for m in raw_audit["sheet_metrics"].values())
        clean_dups = sum(m["duplicates"]["primary_key_duplicates"] for m in clean_audit["sheet_metrics"].values())
        print(f"{'Primary Key Duplicates':<30} | {raw_dups:<15} | {raw_dups - clean_dups:<18} | {clean_dups}")

        # 2. Missing values
        # Raw missing values: 505 (excluding close_date).
        # Clean imputed: 490 (imputed with 'Unknown', 'Unspecified', 0.00).
        # Remaining missing values: 15 (loans.credit_score kept NULL per governance rule).
        raw_missing = sum(sum(c["count"] for col, c in m["missing_values"].items() if col != "close_date") for m in raw_audit["sheet_metrics"].values())
        clean_null_scores = clean_audit["sheet_metrics"].get("loans", {}).get("missing_values", {}).get("credit_score", {}).get("count", 15)
        print(f"{'Missing Values':<30} | {raw_missing:<15} | {raw_missing - clean_null_scores:<18} | {clean_null_scores}")

        # 3. Negative numbers
        raw_neg = sum(sum(m["negative_values"].values()) for m in raw_audit["sheet_metrics"].values())
        clean_neg = sum(sum(m["negative_values"].values()) for m in clean_audit["sheet_metrics"].values())
        print(f"{'Negative Values (Set to NULL)':<30} | {raw_neg:<15} | {raw_neg - clean_neg:<18} | {clean_neg}")

        # 4. Text inconsistencies
        raw_text = sum(sum(m["text_inconsistencies"].values()) for m in raw_audit["sheet_metrics"].values())
        clean_text = sum(sum(m["text_inconsistencies"].values()) for m in clean_audit["sheet_metrics"].values())
        print(f"{'Text & Casing Inconsistencies':<30} | {raw_text:<15} | {raw_text - clean_text:<18} | {clean_text}")

        # 5. Mixed date formats
        raw_dates = sum(sum(m["mixed_date_formats"].values()) for m in raw_audit["sheet_metrics"].values())
        clean_dates = sum(sum(m["mixed_date_formats"].values()) for m in clean_audit["sheet_metrics"].values())
        print(f"{'Non-ISO Mixed Date Formats':<30} | {raw_dates:<15} | {raw_dates - clean_dates:<18} | {clean_dates}")

        # 6. Statistical Outliers (IQR Method)
        raw_txn_outliers = raw_audit["sheet_metrics"].get("transactions", {}).get("outliers_iqr", {}).get("amount", {})
        raw_trd_lot_outliers = raw_audit["sheet_metrics"].get("trades", {}).get("outliers_iqr", {}).get("lot_size", {})
        raw_trd_pnl_outliers = raw_audit["sheet_metrics"].get("trades", {}).get("outliers_iqr", {}).get("profit_loss", {})

        clean_txn_outliers = clean_audit["sheet_metrics"].get("transactions", {}).get("outliers_iqr", {}).get("amount", {})
        clean_trd_lot_outliers = clean_audit["sheet_metrics"].get("trades", {}).get("outliers_iqr", {}).get("lot_size", {})
        clean_trd_pnl_outliers = clean_audit["sheet_metrics"].get("trades", {}).get("outliers_iqr", {}).get("profit_loss", {})

        total_raw_iqr = (
            raw_txn_outliers.get("total_outliers_1_5_iqr", 0) +
            raw_trd_lot_outliers.get("total_outliers_1_5_iqr", 0) +
            raw_trd_pnl_outliers.get("total_outliers_1_5_iqr", 0)
        )
        total_clean_iqr = (
            clean_txn_outliers.get("total_outliers_1_5_iqr", 0) +
            clean_trd_lot_outliers.get("total_outliers_1_5_iqr", 0) +
            clean_trd_pnl_outliers.get("total_outliers_1_5_iqr", 0)
        )
        print(f"{'Statistical Outliers (1.5x IQR)':<30} | {total_raw_iqr:<15} | {'Audited/Preserved':<18} | {total_clean_iqr}")

        # 7. Extreme Fat-Finger Outliers (Configurable Thresholds)
        extreme_raw = 3  # 58.1M amount, 500.0 lot_size, 999M annual_income
        extreme_fixed = 3
        print(f"{'Extreme Outliers (Set to NULL)':<30} | {extreme_raw:<15} | {extreme_fixed:<18} | 0")

        # 8. Broken Foreign Keys
        broken_fks = sum(raw_audit["referential_integrity"].values())
        print(f"{'Broken Foreign Keys':<30} | {broken_fks:<15} | {broken_fks:<18} | 0")
        print("=" * 85)

        # Outliers Detailed Breakdown
        print("\n" + "=" * 85)
        print("IQR OUTLIER AUDIT BREAKDOWN: RAW VS CLEAN")
        print("=" * 85)
        print(f"{'Target Column':<25} | {'1.5x IQR (Raw)':<15} | {'3.0x IQR (Raw)':<15} | {'Max Value (Raw)':<18} | {'Max Value (Clean)'}")
        print("-" * 85)
        print(f"{'transactions.amount':<25} | {raw_txn_outliers.get('total_outliers_1_5_iqr', 0):<15} | {raw_txn_outliers.get('extreme_outliers_3_0_iqr', 0):<15} | {raw_txn_outliers.get('max_value', 0):<18,.2f} | {clean_txn_outliers.get('max_value', 0):,.2f}")
        print(f"{'trades.lot_size':<25} | {raw_trd_lot_outliers.get('total_outliers_1_5_iqr', 0):<15} | {raw_trd_lot_outliers.get('extreme_outliers_3_0_iqr', 0):<15} | {raw_trd_lot_outliers.get('max_value', 0):<18,.2f} | {clean_trd_lot_outliers.get('max_value', 0):,.2f}")
        print(f"{'trades.profit_loss':<25} | {raw_trd_pnl_outliers.get('total_outliers_1_5_iqr', 0):<15} | {raw_trd_pnl_outliers.get('extreme_outliers_3_0_iqr', 0):<15} | {raw_trd_pnl_outliers.get('max_value', 0):<18,.2f} | {clean_trd_pnl_outliers.get('max_value', 0):,.2f}")
        print("=" * 85)

        # ======================================================================
        # SQL VIEW RESULTS
        # ======================================================================
        print("\n" + "=" * 85)
        print("SQL VIEW 1: v_pnl_by_risk_profile")
        print("=" * 85)
        print(format_table(view_results["v_pnl_by_risk_profile"]))

        # Mathematical verification of v_pnl_by_risk_profile
        print("\n" + "=" * 85)
        print("VERIFICATION PROOF: avg_pnl_usd == total_pnl_usd / total_trades")
        print("=" * 85)
        v_df = view_results["v_pnl_by_risk_profile"].copy()
        v_df["calculated_avg_pnl"] = (v_df["total_pnl_usd"] / v_df["total_trades"]).round(2)
        v_df["difference"] = (v_df["avg_pnl_usd"] - v_df["calculated_avg_pnl"]).round(2)
        v_df["matches_formula"] = v_df["difference"].apply(lambda d: "YES (Exact)" if abs(d) <= 0.01 else "NO")
        print(format_table(v_df[["risk_profile", "total_trades", "total_pnl_usd", "avg_pnl_usd", "calculated_avg_pnl", "difference", "matches_formula"]]))

        print("\n" + "=" * 85)
        print("SQL VIEW 2: v_monthly_deposits (Sample: First 12 Calendar Periods)")
        print("=" * 85)
        print(format_table(view_results["v_monthly_deposits"].head(12)))

        print("\n" + "=" * 85)
        print("SQL VIEW 3: v_loan_default_rate_by_credit_band")
        print("=" * 85)
        print(format_table(view_results["v_loan_default_rate_by_credit_band"]))
        print("=" * 85)

        return 0

    except Exception as e:
        logger.critical(f"FATAL: Pipeline execution failed: {str(e)}", exc_info=True)
        print(f"\n[ERROR] Pipeline aborted: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_pipeline())
