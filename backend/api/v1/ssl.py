from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.v1.auth import get_current_user
from backend.models.site import Site
from typing import List

router = APIRouter()

@router.get("/sites/{site_id}/status")
def get_ssl_status(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    # Mock SSL status
    # 0: No SSL, 1: Valid, 2: Expired, 3: Self-signed
    return {
        "status": site.ssl_status,
        "issuer": "Let's Encrypt" if site.ssl_status > 0 else "None",
        "expiry_date": "2026-05-12" if site.ssl_status > 0 else None,
        "domains": [site.domain] + (site.aliases or [])
    }

@router.post("/sites/{site_id}/apply")
def apply_ssl(
    site_id: int,
    force_https: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    # Mock Certbot process
    # In reality, this would call certbot command
    site.ssl_status = 2 if force_https else 1
    db.commit()
    
    return {"message": f"SSL certificate applied successfully for {site.domain}", "status": site.ssl_status}

@router.post("/sites/{site_id}/disable")
def disable_ssl(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    site.ssl_status = 0
    db.commit()
    
    return {"message": f"SSL disabled for {site.domain}", "status": 0}
