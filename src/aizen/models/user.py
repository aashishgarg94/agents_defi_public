from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func  # Recommended for timestamps
from src.aizen.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    private_key = Column(String, nullable=True)  # Encrypt in production!
    public_key = Column(String, nullable=False)
    created_date = Column(DateTime, server_default=func.now())  # Best practice for timestamps
    wallet_address = Column(String, unique=True, nullable=False)
    auth_wallet_address = Column(String, unique=True, nullable=False)