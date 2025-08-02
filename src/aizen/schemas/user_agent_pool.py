from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class PoolDataBase(BaseModel):
    created_at: datetime
    last_rebalanced_at: Dict  # JSON
    rebalance_timeframe: int
    last_checked_at: datetime
    liquidity_range: Dict  # JSON
    liquidity_amounts: Dict  # JSON
    position_id: str
    user_id: str
    agent_id: str
    is_deployed: bool

class PoolDataCreate(PoolDataBase):
    pass  # Inherits all fields, useful for creating new entries

class PoolDataUpdate(BaseModel):
    last_rebalanced_at: Optional[Dict]
    last_checked_at: Optional[datetime]
    liquidity_range: Optional[Dict]
    liquidity_amounts: Optional[Dict]
    buffer: Optional[float]
    risk_tolerance: Optional[Dict]
    rebalance_strategies: Optional[Dict]
    is_deployed: Optional[bool]

class PoolDataResponse(PoolDataBase):
    id: int

    class Config:
        from_attributes = True