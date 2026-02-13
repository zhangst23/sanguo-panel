from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.site import Site as SiteModel, SharedDatabase as SharedDatabaseModel
from typing import List, Any
import random
import string

router = APIRouter()

@router.get("/list", response_model=List[Any])
def list_databases(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all databases associated with WordPress sites.
    """
    sites = db.query(SiteModel).all()
    results = []
    for site in sites:
        shared_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.id == site.shared_db_id).first()
        if shared_db:
            results.append({
                "site_id": site.id,
                "domain": site.domain,
                "db_name": shared_db.db_name,
                "db_user": shared_db.db_user,
                "db_password": shared_db.db_password,
                "created_at": site.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(site, 'created_at') and site.created_at else "N/A",
                "table_prefix": site.table_prefix
            })
    return results

@router.post("/change-password/{site_id}")
def change_db_password(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Change database password for a specific site's shared database.
    """
    site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    shared_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.id == site.shared_db_id).first()
    if not shared_db:
        raise HTTPException(status_code=404, detail="Shared database not found")
    
    # Generate new random password
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    shared_db.db_password = new_password
    db.commit()
    
    return {"success": True, "new_password": new_password}

@router.delete("/{site_id}")
def delete_database(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete database for a specific site.
    Note: In a real system, this would drop the actual database/user in MariaDB.
    """
    site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    shared_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.id == site.shared_db_id).first()
    if shared_db:
        db.delete(shared_db)
        db.commit()
    
    return {"success": True, "message": "Database record deleted"}

@router.get("/slow-queries")
def get_slow_queries(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Mock slow queries
    return [
        {"id": 1, "query": "SELECT * FROM wp_posts WHERE post_status = 'publish' ORDER BY post_date DESC LIMIT 10;", "execution_time": "1.2s", "timestamp": "2026-02-12 10:15:22"},
        {"id": 2, "query": "SELECT COUNT(*) FROM wp_comments WHERE comment_approved = '1';", "execution_time": "0.8s", "timestamp": "2026-02-12 10:20:05"},
        {"id": 3, "query": "UPDATE wp_options SET option_value = '...' WHERE option_name = 'rewrite_rules';", "execution_time": "1.5s", "timestamp": "2026-02-12 11:05:12"},
    ]

@router.post("/optimize")
def optimize_database(
    db_name: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Mock database optimization
    return {
        "message": f"Database {db_name} optimized successfully",
        "actions": [
            "Optimizing tables...",
            "Repairing overhead...",
            "Cleaning up transients...",
            "Updating indexes..."
        ],
        "space_reclaimed": "12.5 MB"
    }

@router.get("/tables/{db_name}")
def get_table_status(
    db_name: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Mock table status
    return [
        {"name": "wp_posts", "engine": "InnoDB", "rows": 1520, "data_length": "2.5MB", "index_length": "0.5MB", "overhead": "0KB"},
        {"name": "wp_options", "engine": "InnoDB", "rows": 450, "data_length": "1.2MB", "index_length": "0.2MB", "overhead": "128KB"},
        {"name": "wp_comments", "engine": "InnoDB", "rows": 5600, "data_length": "5.5MB", "index_length": "1.2MB", "overhead": "0KB"},
    ]
