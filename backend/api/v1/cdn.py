from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.v1.auth import get_current_user
from backend.models.site import Site
from typing import List

router = APIRouter()

@router.get("/sites/{site_id}/config")
def get_cdn_config(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    # Mock CDN config
    return {
        "provider": "Cloudflare",
        "status": "connected",
        "cname": f"cdn.{site.domain}",
        "api_key_last_4": "8k9x",
        "auto_purge_enabled": True
    }

@router.post("/sites/{site_id}/connect")
def connect_cdn(
    site_id: int,
    provider: str,
    api_key: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    # Mock CDN connection
    return {
        "message": f"Successfully connected {site.domain} to {provider} CDN",
        "cname": f"cdn.{site.domain}",
        "verification_status": "verified"
    }

@router.post("/sites/{site_id}/purge")
def purge_cdn_cache(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    # Mock CDN purge
    return {"message": "CDN global cache purge request sent."}
