"""
Northbay Capital ETL Pipeline - Extract Module
=============================================
Mentor Note for Beginners:
The 'E' in ETL stands for Extract. In this phase, our job is simply to fetch data
from the raw source (here, a multi-sheet Excel file) and bring it into our
processing environment as raw DataFrames.

Best practices demonstrated here:
1. Validate that the source file actually exists before attempting to read it.
2. Read sheet-by-sheet to monitor memory usage and catch corruption early.
3. Log record counts and column counts for observability and audit trails.
4. Avoid performing any transformations here; keep raw data unmodified so the
   Validate step can inspect the untouched raw state.
"""

import sys
import logging
import pandas as pd
from pathlib import Path
from typing import Dict

try:
    from .config import EXCEL_INPUT_PATH, SHEET_NAMES
except ImportError:
    from config import EXCEL_INPUT_PATH, SHEET_NAMES

logger = logging.getLogger("northbay_pipeline")


def extract_data(file_path: Path = EXCEL_INPUT_PATH) -> Dict[str, pd.DataFrame]:
    """
    Extract all sheets from the specified Excel workbook into a dictionary of DataFrames.

    Parameters:
        file_path (Path): Path to the Excel (.xlsx) file.

    Returns:
        Dict[str, pd.DataFrame]: Dictionary mapping sheet names to raw DataFrames.

    Raises:
        FileNotFoundError: If the source Excel file is not found.
        RuntimeError: If reading fails or any expected sheet is missing.
    """
    logger.info("=" * 60)
    logger.info("STEP 1: EXTRACT - Loading raw sheets from Excel")
    logger.info("=" * 60)

    # 1. Verify file presence
    if not file_path.exists():
        error_msg = f"Raw dataset not found at: {file_path.resolve()}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    logger.info(f"Connecting to source workbook: {file_path.name}")
    raw_sheets: Dict[str, pd.DataFrame] = {}

    try:
        # 2. Extract sheet-by-sheet using openpyxl engine
        for sheet_name in SHEET_NAMES:
            logger.info(f"Reading sheet: '{sheet_name}'...")
            df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
            
            # Record dataframe
            raw_sheets[sheet_name] = df
            row_count = len(df)
            col_count = len(df.columns)
            logger.info(f"   -> Successfully extracted '{sheet_name}': {row_count:,} rows, {col_count} columns.")

    except Exception as e:
        logger.error(f"Failed during extraction of sheet '{sheet_name}': {str(e)}", exc_info=True)
        raise RuntimeError(f"Extraction halted due to error: {str(e)}") from e

    total_extracted_rows = sum(len(df) for k, df in raw_sheets.items() if k != "data_dictionary")
    logger.info(f"Extraction complete! Total data records extracted: {total_extracted_rows:,} rows across {len(raw_sheets)} sheets.")
    return raw_sheets


if __name__ == "__main__":
    from .config import setup_logging
    setup_logging(log_to_file=False)
    extract_data()
