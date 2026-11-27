from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator

from backend.utils.wp_asset_utils import validate_version


class WpAssetBase(BaseModel):
    kind: Literal["core", "theme", "plugin"]
    name: str
    slug: Optional[str] = None
    version: Optional[str] = None
    enabled: bool = True
    notes: Optional[str] = None


class WpAsset(WpAssetBase):
    id: int
    file_path: str
    file_size: int
    source: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WpAssetUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    version: Optional[str] = None
    enabled: Optional[bool] = None
    notes: Optional[str] = None


class VersionRequest(BaseModel):
    version: str

    @field_validator("version")
    @classmethod
    def check_version(cls, v: str) -> str:
        return validate_version(v)


class DefaultsResponse(BaseModel):
    default_version: str
    versions: List[str]
    default_themes: List[WpAsset] = []
    default_plugins: List[WpAsset] = []
