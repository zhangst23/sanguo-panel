from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class BackupType(str, Enum):
    manual = "manual"
    schedule = "schedule"

class BackupStatus(str, Enum):
    success = "success"
    failed = "failed"
    in_progress = "in_progress"

class BackupScope(str, Enum):
    full_db = "full_db"
    site_only = "site_only"

class BackupBase(BaseModel):
    site_id: int
    name: str
    type: BackupType = BackupType.manual
    include_db: bool = True
    include_files: bool = True
    backup_scope: BackupScope = BackupScope.site_only

class BackupCreate(BackupBase):
    pass

class Backup(BackupBase):
    id: int
    file_path: str
    file_size: int
    status: BackupStatus
    md5: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BackupScheduleBase(BaseModel):
    site_id: int
    name: str
    cron_expression: str
    enabled: bool = True
    retention_days: int = 30
    include_db: bool = True
    include_files: bool = True

class BackupScheduleCreate(BackupScheduleBase):
    pass

class BackupSchedule(BackupScheduleBase):
    id: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
