from sqlalchemy import Column, String, Integer, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import enum
from backend.models.base import Base

class FirewallProtocol(str, enum.Enum):
    tcp = "tcp"
    udp = "udp"
    both = "both"

class FirewallAction(str, enum.Enum):
    accept = "accept"
    drop = "drop"
    reject = "reject"

class FirewallRule(Base):
    __tablename__ = "firewall_rules"
    
    name = Column(String(100), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(Enum(FirewallProtocol), default=FirewallProtocol.tcp)
    action = Column(Enum(FirewallAction), default=FirewallAction.accept)
    enabled = Column(Boolean, default=True)
    description = Column(String(255))

class IPListType(str, enum.Enum):
    black = "black"
    white = "white"

class IPListScope(str, enum.Enum):
    global_ = "global"
    site = "site"

class IPList(Base):
    __tablename__ = "ip_lists"
    
    type = Column(Enum(IPListType), nullable=False)
    scope = Column(Enum(IPListScope), default=IPListScope.global_)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    ip = Column(String(50), nullable=False) # Single IP or CIDR
    description = Column(String(255))
    enabled = Column(Boolean, default=True)
    
    site = relationship("Site")
