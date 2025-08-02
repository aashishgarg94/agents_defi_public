from sqlalchemy import Column, Integer, Numeric, Text, JSON, TIMESTAMP, Boolean, Float
from sqlalchemy.sql import func
from src.aizen.database import Base

class UserAgentPool(Base):
    __tablename__ = "user_agent_pools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable =False)
    agent_id = Column(Integer, nullable =False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    last_checked_at = Column(TIMESTAMP, nullable=True)
    liquidity_range = Column(JSON, nullable=False)
    liquidity_amounts = Column(JSON, nullable=False)
    position_id = Column(Integer, nullable=True)
    is_deployed = Column(Boolean, nullable=False, server_default="FALSE")