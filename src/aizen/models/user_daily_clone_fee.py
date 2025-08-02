from sqlalchemy import Column, Numeric, DateTime, Integer
from src.aizen.database import Base
from sqlalchemy.sql import func


class UserDailyCloneFee(Base):
    __tablename__ = "user_daily_clone_fees"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, nullable = False) 
    user_id = Column(Integer, nullable=False)
    sent_by_user_id = Column(Integer, nullable=False)
    fee_amount = Column(Numeric(precision=30, scale=20))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)