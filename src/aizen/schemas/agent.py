from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Dict, Any, Optional

DEFAULT_CONFIG = {
    "tags": [
      "uniswap-v3",
      "auto-rebalance",
      "rsi-signal",
      "bolliner-band"
    ],
    "buffer": 0.025,
    "time_buffer": 30,
    "max_slippage": 0.05,
    "pool_details": {
      "chain": "mainnet",
      "fee_tier": 0.3,
      "token_pair": "ETH/USDC"
    },
    "liquidity_range": {
      "lower": 0.08,
      "higher": 0.08
    },
    "rebalance_timeframe": 15,
    "rebalance_strategies": [
      "Rsi",
      "Bollinger Bands"
    ]
}

class AgentBase(BaseModel):
    name: str
    image: str
    description: str
    performance: str
    aum: str
    il: str
    daily_rebalance: str
    weekly_reward: str
    tags: List[str]  # Convert JSON field to a list of strings
    trending: bool
    risk_level: str
    strategy_type: str
    created_date: datetime
    agent_role: str
    agent_instructions: str
    agent_goals: str
    agent_capabilities: List[str]
    selected_tools: List[str]
    category: str
    config: Dict[str, Any]
    is_deployed: bool


class AgentCreate(AgentBase):
    pass


class AgentResponse(AgentBase):
    id: int  # Add id for response

class BuildAgentRequest(BaseModel):
    id: int
    name: str
    category: str
    config: Dict[str, Any]
    is_deployed: bool
    description: str
    user_id: int
    clone_fee: str
    subscription_fee: float

class GetAgent(BaseModel):
    agent_id: int
    user_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class DeployAgent(BaseModel):
    user_id: int
    agent_id: int
    is_deployed: bool

class DeleteAgent(BaseModel):
    user_id: int
    agent_id: int

class CloneAgent(BaseModel):
    user_id: int
    agent_id: int
    name: str

    class Config:
        from_attributes = True  # Ensures SQLAlchemy ORM objects are converted properly
