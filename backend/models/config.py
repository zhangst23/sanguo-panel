from sqlalchemy import Column, String, Integer, JSON, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from backend.models.base import Base

class SiteOption(Base):
    __tablename__ = "site_options"
    
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    option_key = Column(String(100), nullable=False)
    option_value = Column(JSON)
    
    site = relationship("Site")

class GlobalOption(Base):
    __tablename__ = "global_options"
    
    option_key = Column(String(100), unique=True, nullable=False)
    option_value = Column(JSON)
    description = Column(String(255))
