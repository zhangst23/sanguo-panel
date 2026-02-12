from sqlalchemy import Column, String, Integer, JSON, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import enum
from backend.models.base import Base

class StatusEnum(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    deleted = "deleted"

class SharedDatabase(Base):
    __tablename__ = "shared_databases"
    
    name = Column(String(100), nullable=False)
    db_host = Column(String(100), default="localhost")
    db_port = Column(Integer, default=3306)
    db_name = Column(String(64), nullable=False)
    db_user = Column(String(64), nullable=False)
    db_password = Column(String(255), nullable=False)
    charset = Column(String(32), default="utf8mb4")
    collation = Column(String(32), default="utf8mb4_unicode_ci")
    max_table_count = Column(Integer)
    status = Column(Enum(StatusEnum), default=StatusEnum.active)
    notes = Column(String)
    
    sites = relationship("Site", back_populates="shared_db")

class Site(Base):
    __tablename__ = "sites"
    
    domain = Column(String(255), unique=True, index=True, nullable=False)
    aliases = Column(JSON)
    root_path = Column(String(255), nullable=False)
    php_version = Column(String(10), default="8.2")
    
    shared_db_id = Column(Integer, ForeignKey("shared_databases.id"), nullable=False)
    table_prefix = Column(String(64), nullable=False)
    
    ssl_status = Column(Integer, default=0) # 0: off, 1: on, 2: force https
    status = Column(Enum(StatusEnum), default=StatusEnum.active)
    notes = Column(String)
    
    # Performance & Cache
    performance_preset = Column(String(20), default="balanced") # basic, balanced, ultimate
    lscache_enabled = Column(Boolean, default=True)
    redis_enabled = Column(Boolean, default=True)
    opcache_enabled = Column(Boolean, default=True)
    browser_cache_enabled = Column(Boolean, default=True)
    
    shared_db = relationship("SharedDatabase", back_populates="sites")
