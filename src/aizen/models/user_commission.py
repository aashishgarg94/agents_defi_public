from sqlalchemy import Column, Integer, Boolean, JSON, TIMESTAMP, ForeignKey, Numeric, DateTime
from sqlalchemy.sql import func
from src.aizen.database import Base

class UserCommission(Base):
    __tablename__ = "user_commissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_commissioned = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    paused_at = Column(TIMESTAMP, server_default=func.now())
    agent_id = Column(Integer, nullable = False)
    amount_eth = Column(Numeric(precision=30, scale=20))
    is_active = Column(Boolean, default=False)

