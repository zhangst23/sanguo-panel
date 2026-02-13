from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.site import Site
from typing import List

router = APIRouter()

@router.get("/sites/{site_id}/stats")
def get_image_stats(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    # Mock image stats
    return {
        "total_images": 1250,
        "optimized_images": 850,
        "unoptimized_images": 400,
        "space_saved_mb": 156.4,
        "webp_converted": 620,
        "avif_converted": 120
    }

@router.post("/sites/{site_id}/optimize")
def optimize_images(
    site_id: int,
    quality: int = 80,
    convert_webp: bool = True,
    convert_avif: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    # Mock optimization process
    return {
        "message": f"Image optimization started for {site.domain}",
        "tasks": [
            "Scanning media library...",
            f"Compacting 400 images (Quality: {quality})...",
            "Generating WebP versions..." if convert_webp else "Skipping WebP",
            "Generating AVIF versions..." if convert_avif else "Skipping AVIF"
        ],
        "estimated_time": "5 minutes"
    }
