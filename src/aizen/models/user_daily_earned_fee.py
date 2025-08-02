from src.aizen.database import Base 
from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, Numeric
from sqlalchemy.sql import func

class UserDailyEarnedFee(Base):
    __tablename__ = "user_daily_earned_fees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fee_earned = Column(Numeric(precision=30, scale=20))
    created_at = Column(TIMESTAMP, server_default=func.now())