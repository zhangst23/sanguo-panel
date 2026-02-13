from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.site import Site
from backend.schemas.site import Site as SiteSchema
from typing import List

router = APIRouter()

@router.get("/sites/{site_id}", response_model=SiteSchema)
def get_site_cache_settings(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    return site

@router.post("/sites/{site_id}/purge")
def purge_site_cache(
    site_id: int,
    cache_type: str = "all", # all, lscache, redis, opcache
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    # Logic to purge cache would go here
    # For now, we'll just mock it
    return {"message": f"Purged {cache_type} cache for {site.domain}"}

@router.post("/sites/{site_id}/preset")
def apply_performance_preset(
    site_id: int,
    preset: str, # basic, balanced, ultimate
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    if preset == "basic":
        site.lscache_enabled = False
        site.redis_enabled = False
        site.opcache_enabled = True
        site.browser_cache_enabled = True
    elif preset == "balanced":
        site.lscache_enabled = True
        site.redis_enabled = True
        site.opcache_enabled = True
        site.browser_cache_enabled = True
    elif preset == "ultimate":
        site.lscache_enabled = True
        site.redis_enabled = True
        site.opcache_enabled = True
        site.browser_cache_enabled = True
        # Additional "ultimate" settings could be added here
    else:
        raise HTTPException(status_code=400, detail="Invalid preset")
    
    site.performance_preset = preset
    db.commit()
    db.refresh(site)
    return site
