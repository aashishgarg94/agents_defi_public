from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, BigInteger, Float
from src.aizen.database import Base

class CryptoPrice(Base):
    __tablename__ = "crypto_prices"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False)
    date = Column(DateTime, nullable=False)
    open_price = Column(DECIMAL(18, 8))
    high_price = Column(DECIMAL(18, 8))
    low_price = Column(DECIMAL(18, 8))
    close_price = Column(DECIMAL(18, 8))
    volume = Column(BigInteger)
    rsi = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    volatility = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    atr = Column(Float)
    price_range = Column(Float)
    vwap = Column(Float)

    __table_args__ = ({"sqlite_autoincrement": True},)

