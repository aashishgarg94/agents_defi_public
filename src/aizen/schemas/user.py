from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: str
    public_key: str
    private_key: str
    created_date: datetime
    wallet_address: str

class UserCreate(UserBase):
    password: str  # Include password only during creation

class UserResponse(UserBase):
    id: int 

class ChatRequest(BaseModel):
    user_id: int
    user_input: str
    agent_id: Optional[int] = None

class MyAgent(BaseModel):
    user_id: int

    class Config:
        from_attributes = True  # Ensures SQLAlchemy ORM objects are converted properly
