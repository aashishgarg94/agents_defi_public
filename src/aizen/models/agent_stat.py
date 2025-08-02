from sqlalchemy import Column, String, Numeric, DateTime, Integer, Boolean, JSON
from datetime import datetime
from src.aizen.database import Base

class AgentStat(Base):
    __tablename__ = 'agent_stats'

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    amount_eth = Column(Numeric, nullable=False)
    pool_details = Column(JSON, nullable = True, default = {})
    token0 = Column(String, nullable=False)
    token1 = Column(String, nullable=False)
    amount0 = Column(Numeric, nullable=False)
    amount1 = Column(Numeric, nullable=False)
    price_at_entry = Column(Numeric, nullable=False)
    invested_eth = Column(Numeric, nullable=False)
    tick_lower = Column(Integer, nullable=False)
    tick_upper = Column(Integer, nullable=False)
    position_id = Column(Integer, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    final_eth = Column(Numeric, nullable=True)
    removed_eth = Column(Numeric, nullable=True)
    reward_earned = Column(Numeric, default=0)
    impermanent_loss = Column(Numeric, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)