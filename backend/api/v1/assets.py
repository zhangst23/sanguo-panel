from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.site import Site
from typing import List

router = APIRouter()

@router.get("/sites/{site_id}/status")
def get_asset_status(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    # Mock asset status
    return {
        "css_minified": True,
        "js_minified": False,
        "critical_css_generated": False,
        "fonts_localized": True,
        "total_assets": 45,
        "optimizable_size_kb": 256
    }

@router.post("/sites/{site_id}/optimize")
def optimize_assets(
    site_id: int,
    minify_css: bool = True,
    minify_js: bool = True,
    generate_critical_css: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    # Mock asset optimization
    return {
        "message": f"Asset optimization completed for {site.domain}",
        "saved_size": "184 KB",
        "actions": [
            "Minifying CSS files...",
            "Concatenating JS bundles..." if minify_js else "Skipped JS",
            "Generating Critical CSS..." if generate_critical_css else "Skipped Critical CSS"
        ]
    }
