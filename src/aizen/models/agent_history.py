from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, func, BOOLEAN, Float
from src.aizen.database import Base

class AgentHistory(Base):
    __tablename__ = "agent_history"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, nullable=False)
    last_rebalanced_at = Column(DateTime, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    rebalance_decision = Column(BOOLEAN, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=True)
    rebalance_logic = Column(Text, nullable = True)
    rebalance_bias = Column(Float, nullable=True)
    positive_bias = Column(BOOLEAN, nullable = True)