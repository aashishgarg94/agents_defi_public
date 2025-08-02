from pydantic import BaseModel
from typing import Dict, Any

# Schema for Creating a New UserConfig
class CreateUserCommission(BaseModel):
    user_id: int
    is_commissioned: bool
    agent_id: int
    amount_eth: str

class UpdateCommission(BaseModel):
    user_id: int
    agent_id: int
    is_active: bool
    is_commissioned: bool

class UpdateAmountEth(BaseModel):
    user_id: int
    agent_id: int
    amount_eth: str
    add: bool

# Schema for Reading UserConfig
    class Config:
        from_attributes = True  # Allows ORM conversion
