from sqlalchemy import Column, Integer, Numeric, DateTime
from src.aizen.database import Base
from datetime import datetime

class UserDailyStat(Base):
    __tablename__ = "user_daily_stat"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    total_assets = Column(Numeric, nullable=False)                # Sum from user_commission
    total_invested_eth = Column(Numeric, nullable=False)          # Sum of invested_eth from agent_stats
    total_reward_earned = Column(Numeric, nullable=False)         # Sum of reward_earned
    total_reward_percent = Column(Numeric, nullable=False)        # reward / invested_eth * 100
    total_impermanent_loss = Column(Numeric, nullable=False)      # Sum of impermanent_loss
    active_positions = Column(Integer, nullable=False)            # Count of is_active=True
    total_positions = Column(Integer, nullable=False)             # Count of all positions
    created_at = Column(DateTime, default=datetime.utcnow)
