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
    db_name = Column(String(64)) # The actual database name created for this site
    table_prefix = Column(String(64), nullable=False)
    
    ssl_status = Column(Integer, default=0) # 0: off, 1: on, 2: force https
    status = Column(Enum(StatusEnum), default=StatusEnum.active)
    notes = Column(String)
    
    # Performance & Cache
    performance_preset = Column(String(20), default="balanced") # basic, balanced, ultimate
    lscache_enabled = Column(Boolean, default=True) # OpenLiteSpeed 技术底座 (LSCache)
    mariadb_optimized = Column(Boolean, default=True) # MariaDB 专属优化
    redis_enabled = Column(Boolean, default=True) # Redis 对象缓存
    opcache_enabled = Column(Boolean, default=True) # OPcache 深度优化
    browser_cache_enabled = Column(Boolean, default=True) # 浏览器缓存
    static_optimization = Column(Boolean, default=True) # 全站静态化
    image_optimization = Column(Boolean, default=True) # 图片自动化压缩
    assets_optimization = Column(Boolean, default=True) # CSS/JS 合并
    
    ssl_expire_at = Column(String(32)) # YYYY-MM-DD
    backup_count = Column(Integer, default=0)
    
    # SSL Extended Config
    ssl_mode = Column(String(20), default="none") # none, cloudflare, letsencrypt
    ssl_email = Column(String(255))
    ssl_auto_renew = Column(Boolean, default=True)
    https_force = Column(Boolean, default=True)
    
    shared_db = relationship("SharedDatabase", back_populates="sites")
