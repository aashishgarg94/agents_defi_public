from pydantic import BaseModel, Field

class RebalanceDecision(BaseModel):
    answer: str = Field(..., description="Explanantion of why a bias was given")
    positive: bool = Field(..., description= "boolean to indicate a postive or negative bias. True for positive bias False for negative bias")
    bias: float =  Field(..., example=0.25, description="Percentage bias applied to liquidity range adjustments. Always positive value (e.g.,2.5% -> 0.025)")
