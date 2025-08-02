from sqlalchemy import Column, Integer, String, JSON, DateTime
from src.aizen.database import Base
from datetime import datetime

class UserChat(Base):
    __tablename__ = "user_chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    agent_id = Column(Integer, nullable=False)
    user_query = Column(String, nullable=False)
    response = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
