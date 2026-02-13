from typing import List, Optional
from pydantic import BaseModel, field_validator
import re
from datetime import datetime

class SiteBase(BaseModel):
    domain: str
    aliases: Optional[List[str]] = []
    root_path: str
    php_version: str = "8.2"
    shared_db_id: int
    table_prefix: str
    notes: Optional[str] = None

class SiteCreate(BaseModel):
    domain: str
    aliases: Optional[List[str]] = []
    root_path: Optional[str] = None
    php_version: str = "8.2"
    shared_db_id: Optional[int] = None
    table_prefix: Optional[str] = None
    performance_preset: str = "balanced"
    notes: Optional[str] = None

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        domain_regex = r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'
        if not re.match(domain_regex, v.lower()):
            raise ValueError('域名格式不正确，必须是根域名形式（如 example.com）')
        return v.lower()

class SiteUpdate(BaseModel):
    aliases: Optional[List[str]] = None
    php_version: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    performance_preset: Optional[str] = None
    lscache_enabled: Optional[bool] = None
    redis_enabled: Optional[bool] = None
    opcache_enabled: Optional[bool] = None
    browser_cache_enabled: Optional[bool] = None

class Site(SiteBase):
    id: int
    status: str
    performance_preset: str
    lscache_enabled: bool
    redis_enabled: bool
    opcache_enabled: bool
    browser_cache_enabled: bool
    ssl_expire_at: Optional[str] = None
    backup_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SharedDatabaseBase(BaseModel):
    name: str
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str
    db_user: str
    db_password: str
    charset: str = "utf8mb4"
    collation: str = "utf8mb4_unicode_ci"
    max_table_count: Optional[int] = None
    notes: Optional[str] = None

class SharedDatabaseCreate(SharedDatabaseBase):
    pass

class SharedDatabase(SharedDatabaseBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
