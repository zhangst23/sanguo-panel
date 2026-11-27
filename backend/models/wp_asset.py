from sqlalchemy import Column, String, Integer, Boolean, Text
from backend.models.base import Base


class WpAsset(Base):
    """Local WordPress core / theme / plugin package registry."""

    __tablename__ = "wp_assets"

    kind = Column(String(16), nullable=False, index=True)  # core | theme | plugin
    name = Column(String(128), nullable=False, default="")
    slug = Column(String(128), nullable=True)
    version = Column(String(32), nullable=True)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, default=0)
    source = Column(String(16), default="upload")  # official | upload
    is_default = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
