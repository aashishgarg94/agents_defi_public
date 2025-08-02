from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, LargeBinary, ARRAY, Numeric, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func  # Recommended for timestamps
from src.aizen.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique = True, nullable=False)  # Maps to AgentName
    user_id = Column(Integer, nullable = False)
    description = Column(String, nullable=False)
    category = Column(Text, nullable=False)  # Maps to category
    is_deployed = Column(Boolean, default=False)  # Maps to isDeployed
    is_active = Column(Boolean, default= True)
    is_trending = Column(Boolean, default= False)
    config = Column(JSONB, nullable = False, default = {})

    # Optional fields (not in request payload but exist in the table)
    image = Column(LargeBinary, nullable=True, default=None)
    image_content = Column(String, nullable= True, default=None)
    performance = Column(String, nullable=True, default=None)
    aum = Column(String, nullable=True, default=None)
    il = Column(String, nullable=True, default=None)
    weekly_reward = Column(String, nullable=True, default=None)
    tags = Column(ARRAY(String), nullable=True)  # Assuming this stores AgentCapabilities
    created_date = Column(DateTime, server_default=func.now())  # Best practice for timestamps
    clone_fee = Column(Numeric(precision=30, scale=20), default=0)
    subscription_fee = Column(Float, default = 0)
    cloned_by = Column(Integer, nullable = True)


