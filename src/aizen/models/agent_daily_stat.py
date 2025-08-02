from sqlalchemy import Column, Integer, Numeric, DateTime
from src.aizen.database import Base
from datetime import datetime

class AgentDailyStat(Base):
    __tablename__ = "agent_daily_stat"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, nullable=False, index=True)
    total_invested_eth = Column(Numeric, nullable=False, default = 0)          # Sum of invested_eth
    total_reward_earned = Column(Numeric, nullable=False, default = 0)         # Sum of reward_earned
    total_reward_percent = Column(Numeric, nullable=False, default = 0)        # reward / invested_eth * 100
    total_impermanent_loss = Column(Numeric, nullable=False, default = 0) 
    total_assets = Column(Numeric, nullable=False, default = 0)   
    created_at = Column(DateTime, default=datetime.utcnow)
