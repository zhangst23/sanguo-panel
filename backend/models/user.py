from sqlalchemy import Column, String, Boolean, DateTime, Integer
from backend.models.base import Base

class User(Base):
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100))
    avatar = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login_at = Column(DateTime)
    token_version = Column(Integer, default=0)
