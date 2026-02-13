from sqlalchemy import Column, String, Integer, JSON, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from backend.models.base import Base

class TaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

class Task(Base):
    __tablename__ = "tasks"
    
    task_uuid = Column(String(36), unique=True, index=True, nullable=False)
    type = Column(String(50), nullable=False) # backup, optimize, migrate, image_optimize, etc.
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.pending)
    progress = Column(Integer, default=0) # 0-100
    message = Column(String)
    result = Column(JSON)
    error = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    site = relationship("Site")
    user = relationship("User")
