from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class PoolDetails(BaseModel):
    chain: str = Field(..., example="mainnet")
    fee_tier: float = Field(..., example=0.3)
    token_pair: str = Field(..., example="ETH/USDC")


class LiquidityRange(BaseModel):
    lower: float = Field(..., example=0.8, description="Percentage representation (e.g., 10% -> 0.1)")
    higher: float = Field(..., example=0.8, description="Percentage representation (e.g., 10% -> 0.1)")

class RebalanceTriggerCondition(BaseModel):
    by: float = Field(..., example=2.5, description="Percentage threshold (e.g., 25% -> 0.25)")
    lower: float = Field(..., example=1, description="Percentage below (e.g., 10% -> 0.1)")
    higher: float = Field(..., example=1, description="Percentage above (e.g., 10% -> 0.1)")


class RebalanceTriggers(BaseModel):
    below: RebalanceTriggerCondition
    above: RebalanceTriggerCondition


class AgentConfig(BaseModel):
    pool_details: PoolDetails
    liquidity_range: LiquidityRange
    buffer: float = Field(..., example=0.1, description="Percentage (e.g., 10% -> 0.1)")
    max_slippage: float = Field(..., example=0.5, description="Percentage (e.g., 5% -> 0.05)")
    rebalance_timeframe: int = Field(..., example=15, description="Time in minutes")
    time_buffer: int = Field(..., example=30, description="Time in minutes")
    tags: List[str] = Field(...)
    rebalance_strategies: List[str] = Field(
        ...,
        example=["Rsi", "Bollinger Bands", "Volatility"],
        description="List of technical indicators to use for rebalancing. Allowed values: 'Rsi', 'Bollinger Bands', 'Volatility', 'ATR', 'MACD'"
    )
    rebalance_triggers: Optional[RebalanceTriggers] = Field(
        None,
        description="Optional dual-trigger rebalance setup for price deviation"
    )


class AgentResponse(BaseModel):
    answer: str
    config: Optional[AgentConfig] = None
