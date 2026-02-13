from sqlalchemy import Column, String, Integer, JSON, Enum, ForeignKey, Boolean, BigInteger, DateTime
from sqlalchemy.orm import relationship
import enum
from backend.models.base import Base

class BackupType(str, enum.Enum):
    manual = "manual"
    schedule = "schedule"

class BackupStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    in_progress = "in_progress"

class BackupScope(str, enum.Enum):
    full_db = "full_db"
    site_only = "site_only"

class Backup(Base):
    __tablename__ = "backups"
    
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    name = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False) # bytes
    type = Column(Enum(BackupType), default=BackupType.manual)
    status = Column(Enum(BackupStatus), default=BackupStatus.success)
    include_db = Column(Boolean, default=True)
    include_files = Column(Boolean, default=True)
    backup_scope = Column(Enum(BackupScope), default=BackupScope.site_only)
    md5 = Column(String(32))
    
    site = relationship("Site")

class BackupSchedule(Base):
    __tablename__ = "backup_schedules"
    
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    name = Column(String(100), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    retention_days = Column(Integer, default=30)
    include_db = Column(Boolean, default=True)
    include_files = Column(Boolean, default=True)
    remote_storage = Column(JSON) # e.g. FTP, OSS config
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    
    site = relationship("Site")
