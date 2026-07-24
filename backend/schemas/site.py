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
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_permission: str = "site_only"
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
    mariadb_optimized: Optional[bool] = None
    redis_enabled: Optional[bool] = None
    opcache_enabled: Optional[bool] = None
    browser_cache_enabled: Optional[bool] = None
    static_optimization: Optional[bool] = None
    image_optimization: Optional[bool] = None
    assets_optimization: Optional[bool] = None
    ssl_mode: Optional[str] = None
    ssl_email: Optional[str] = None
    ssl_auto_renew: Optional[bool] = None
    https_force: Optional[bool] = None
    domain: Optional[str] = None

class ChangeDomainRequest(BaseModel):
    new_domain: str

    @field_validator('new_domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        domain_regex = r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'
        if not re.match(domain_regex, v.lower()):
            raise ValueError('域名格式不正确')
        return v.lower()

class MigrateRequest(BaseModel):
    domain: str
    source_host: Optional[str] = None
    source_port: int = 22
    source_user: Optional[str] = None
    source_password: Optional[str] = None
    source_path: Optional[str] = None
    source_db_host: Optional[str] = None
    source_db_port: int = 3306
    source_db_user: Optional[str] = None
    source_db_password: Optional[str] = None
    source_db_name: Optional[str] = None
    php_version: str = "8.2"

class BatchCreateItem(BaseModel):
    domain: str
    php_version: str = "8.2"

class BatchCreateRequest(BaseModel):
    sites: List[BatchCreateItem]

class PluginAction(BaseModel):
    slug: str

class Site(SiteBase):
    id: int
    status: str
    performance_preset: str
    lscache_enabled: bool
    mariadb_optimized: bool = True
    redis_enabled: bool
    opcache_enabled: bool
    browser_cache_enabled: bool
    static_optimization: bool = True
    image_optimization: bool = True
    assets_optimization: bool = True
    wp_hide_login_path: Optional[str] = None
    ssl_expire_at: Optional[str] = None
    backup_count: int = 0
    ssl_mode: str = "none"
    ssl_email: Optional[str] = None
    ssl_auto_renew: bool = True
    https_force: bool = True
    wp_version: str = "未安装"
    monitor_enabled: bool = False
    wc_key: Optional[str] = None
    wc_secret: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WpConfigUpdate(BaseModel):
    content: str

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
