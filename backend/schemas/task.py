from typing import Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime

class TaskBase(BaseModel):
    task_uuid: str
    type: str
    site_id: Optional[int] = None
    status: str
    progress: int
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class Task(TaskBase):
    id: int
    created_by: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
