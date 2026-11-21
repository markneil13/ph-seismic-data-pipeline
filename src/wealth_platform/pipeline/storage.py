import duckdb
import polars as pl
from pathlib import Path
from typing import List, Dict
from src.wealth_platform.config import DUCKDB_PATH, PARQUET_DIR

class WealthStorage:
    def __init__(self, db_path: Path = DUCKDB_PATH):
        self.db_path = str(db_path)
        self.conn = duckdb.connect(self.db_path)
        self._init_tables()

    def _init_tables(self):
        """Creates table schemas if they do not exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS fact_daily_prices (
                date DATE,
                ticker VARCHAR,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                adj_close DOUBLE,
                volume BIGINT,
                PRIMARY KEY (date, ticker)
            );
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dim_assets (
                ticker VARCHAR PRIMARY KEY,
                name VARCHAR,
                sector VARCHAR,
                market_cap DOUBLE,
                pe_ratio DOUBLE,
                dividend_yield DOUBLE
            );
        """)

    def save_prices(self, df_prices: pl.DataFrame):
        """Saves daily prices into DuckDB and Parquet storage."""
        # Convert polars to pandas/arrow for duckdb ingestion
        df_py = df_prices.to_pandas()
        
        # Upsert into DuckDB
        self.conn.register("tmp_prices", df_py)
        self.conn.execute("""
            INSERT OR REPLACE INTO fact_daily_prices 
            SELECT * FROM tmp_prices;
        """)
        self.conn.unregister("tmp_prices")
        
        # Export Parquet
        parquet_path = PARQUET_DIR / "fact_daily_prices.parquet"
        df_prices.write_parquet(parquet_path)
        print(f"[Storage] Successfully stored {len(df_prices)} price records to DuckDB and Parquet ({parquet_path.name}).")

    def save_metadata(self, metadata: List[Dict]):
        """Saves company metadata dimensions."""
        df_meta = pl.DataFrame(metadata).to_pandas()
        self.conn.register("tmp_meta", df_meta)
        self.conn.execute("""
            INSERT OR REPLACE INTO dim_assets 
            SELECT * FROM tmp_meta;
        """)
        self.conn.unregister("tmp_meta")

    def load_prices(self, tickers: List[str] = None) -> pl.DataFrame:
        """Loads price records from DuckDB as Polars DataFrame."""
        if tickers:
            ticker_list = ", ".join([f"'{t}'" for t in tickers])
            query = f"SELECT * FROM fact_daily_prices WHERE ticker IN ({ticker_list}) ORDER BY date ASC"
        else:
            query = "SELECT * FROM fact_daily_prices ORDER BY date ASC"
        
        df_arrow = self.conn.execute(query).fetch_arrow_table()
        return pl.from_arrow(df_arrow)

    def load_asset_metadata(self) -> List[Dict]:
        """Loads metadata for all assets."""
        query = "SELECT * FROM dim_assets"
        df_arrow = self.conn.execute(query).fetch_arrow_table()
        return pl.from_arrow(df_arrow).to_dicts()

    def close(self):
        self.conn.close()
