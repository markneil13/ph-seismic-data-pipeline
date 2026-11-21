from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

class StockPriceRow(BaseModel):
    date: date
    ticker: str
    open: float = Field(..., ge=0)
    high: float = Field(..., ge=0)
    low: float = Field(..., ge=0)
    close: float = Field(..., ge=0)
    adj_close: float = Field(..., ge=0)
    volume: int = Field(..., ge=0)

    @model_validator(mode="after")
    def check_high_low_bounds(self):
        if self.high < self.low:
            raise ValueError(f"High price ({self.high}) cannot be lower than low price ({self.low})")
        return self

class CompanyInfo(BaseModel):
    ticker: str
    name: str
    sector: str
    industry: Optional[str] = "N/A"
    market_cap: Optional[float] = 0.0
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = 0.0

def validate_price_records(records: List[dict]) -> List[dict]:
    """Validates list of dictionary records against StockPriceRow schema."""
    valid_records = []
    errors = 0
    for record in records:
        try:
            validated = StockPriceRow(**record)
            valid_records.append(validated.model_dump())
        except Exception as e:
            errors += 1
    if errors > 0:
        print(f"[Validation Warning] Dropped {errors} invalid price records.")
    return valid_records
