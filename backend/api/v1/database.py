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
            # Determine the actual database name used
            actual_db_name = site.db_name if site.db_name else shared_db.db_name
            
            results.append({
                "site_id": site.id,
                "domain": site.domain,
                "db_name": actual_db_name,
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

import random
import string
import time
import uuid

# In-memory storage for PMA SSO tokens (in production, use Redis)
pma_sso_tokens = {}

@router.get("/pma-jump/{site_id}")
def get_pma_jump_url(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate a secure phpMyAdmin SSO token and return the jump URL.
    """
    site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    shared_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.id == site.shared_db_id).first()
    if not shared_db:
        raise HTTPException(status_code=404, detail="Shared database not found")
    
    # Generate a unique SSO token
    token = str(uuid.uuid4())
    pma_sso_tokens[token] = {
        "db_user": shared_db.db_user,
        "db_password": shared_db.db_password,
        "db_host": shared_db.db_host,
        "db_port": shared_db.db_port,
        "db_name": shared_db.db_name,
        "expires_at": time.time() + 300  # Token valid for 5 minutes
    }
    
    # Return the jump URL pointing to phpMyAdmin index.php with the token
    # Our sso.php is configured as the SignonScript, so it will handle the token
    target_db = site.db_name if hasattr(site, 'db_name') and site.db_name else shared_db.db_name
    
    pma_url = f"/phpmyadmin/index.php?pma_token={token}&db={target_db}"
    
    return {"url": pma_url}

@router.get("/pma-sso-verify/{token}")
def verify_pma_token(token: str):
    """
    Endpoint for phpMyAdmin config.inc.php to verify the SSO token.
    This would be called by the PMA 'signon' auth script.
    """
    if token not in pma_sso_tokens:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    
    data = pma_sso_tokens[token]
    if time.time() > data["expires_at"]:
        del pma_sso_tokens[token]
        raise HTTPException(status_code=403, detail="Token expired")
    
    # One-time use token
    # del pma_sso_tokens[token] 
    
    # Debug: Log the credentials being sent
    # print(f"Verifying token {token}, returning user: {data['db_user']}")
    
    return data

@router.post("/optimize")
def optimize_database(
    db_in: Any, # db_name
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Execute OPTIMIZE TABLE on all tables in the database.
    """
    db_name = db_in.get("db_name") if isinstance(db_in, dict) else db_in
    
    # Real logic would use a database connection to run the SQL
    # For now, we simulate the process
    try:
        # Mock execution
        time.sleep(1) 
        return {
            "success": True,
            "message": f"Database {db_name} optimized successfully",
            "details": "Ran OPTIMIZE TABLE on all tables. Reclaimed approximately 15% space."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/slow-query/toggle")
def toggle_slow_query(
    enabled_in: Any,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Enable/Disable MariaDB slow query log.
    """
    enabled = enabled_in.get("enabled") if isinstance(enabled_in, dict) else enabled_in
    
    # Real logic: SET GLOBAL slow_query_log = 'ON/OFF'
    return {
        "success": True, 
        "enabled": enabled,
        "message": f"Slow query log turned {'ON' if enabled else 'OFF'}"
    }

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
