from pydantic import BaseModel
from datetime import datetime


class CryptoPriceBase(BaseModel):
    ticker: str
    date: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    rsi: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    volatility: float
    macd: float
    macd_signal: float
    macd_histogram: float
    atr: float
    price_range: float
    vwap: float

class CryptoPriceCreate(CryptoPriceBase):
    pass

class CryptoPriceResponse(CryptoPriceBase):
    id: int

    class Config:
        from_attributes = True


