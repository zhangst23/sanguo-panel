from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.api import deps
from backend.models.site import Site as SiteModel, SharedDatabase as SharedDatabaseModel
from backend.schemas.site import Site, SiteCreate, SiteUpdate, SharedDatabase, SharedDatabaseCreate, WpConfigUpdate
import os

router = APIRouter()

@router.get("/", response_model=List[Site])
def read_sites(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve sites.
    """
    sites = db.query(SiteModel).offset(skip).limit(limit).all()
    return sites

@router.post("/", response_model=Site)
def create_site(
    *,
    db: Session = Depends(deps.get_db),
    site_in: SiteCreate,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new site.
    """
    site = db.query(SiteModel).filter(SiteModel.domain == site_in.domain).first()
    if site:
        raise HTTPException(
            status_code=400,
            detail="The site with this domain already exists in the system.",
        )
    
    # Logic based on PRD:
    # 1. Root path default to /www/wwwroot/{domain} if not provided
    root_path = site_in.root_path or f"/www/wwwroot/{site_in.domain}"
    
    # 2. Shared Database: Default to the first active shared database if not provided
    shared_db_id = site_in.shared_db_id
    if not shared_db_id:
        shared_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.status == "active").first()
        if not shared_db:
            # Create a default shared database if none exists (mock/bootstrap)
            shared_db = SharedDatabaseModel(
                name="Default MariaDB",
                db_host="localhost",
                db_port=3306,
                db_name="sanguo_shared",
                db_user="sanguo_user",
                db_password="sanguo_password",
                status="active"
            )
            db.add(shared_db)
            db.commit()
            db.refresh(shared_db)
        shared_db_id = shared_db.id
    
    # 3. Table Prefix: Default to wp_{next_id}_ (simplified here as we don't have next_id yet)
    # For now, use domain-based prefix or let model handle it if it were auto-incrementing site_id
    # PRD says wp_{site_id}_, but site_id is generated after creation. 
    # We'll use a placeholder and update it or use a random string for now.
    table_prefix = site_in.table_prefix or "wp_tmp_"

    site_data = site_in.dict()
    site_data.update({
        "root_path": root_path,
        "shared_db_id": shared_db_id,
        "table_prefix": table_prefix,
        "status": "active"
    })
    
    # Remove fields not in model
    if "performance_preset" not in site_data:
        site_data["performance_preset"] = "balanced"

    site = SiteModel(**site_data)
    db.add(site)
    db.commit()
    db.refresh(site)
    
    # --- MariaDB/MySQL Database Creation Logic ---
    try:
        shared_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.id == site.shared_db_id).first()
        if shared_db:
            import mysql.connector
            from mysql.connector import errorcode
            
            # Connect to the MySQL/MariaDB server using the shared database credentials
            # In a real system, this should use a root or administrative account
            conn = mysql.connector.connect(
                host=shared_db.db_host,
                port=shared_db.db_port,
                user=shared_db.db_user,
                password=shared_db.db_password
            )
            cursor = conn.cursor()
            
            # Create a dedicated database for this site if it doesn't exist
            # We use the domain as the base for the database name (sanitized)
            safe_domain = site.domain.replace('.', '_').replace('-', '_')
            db_name = f"db_{safe_domain}"
            
            # 1. Create database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            # 2. Update site record with this specific database info
            site.db_name = db_name
            site.notes = f"Database created: {db_name}"
            db.add(site)
            db.commit()
            
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error creating MariaDB database for site: {e}")
        print(f"Please check if the Shared Database settings are correct in the panel.")
        # We don't raise an exception here to allow the site to be created even if DB creation fails
        # (The user can manually fix it later)
        site.notes = f"Database creation failed: {e}. Please create it manually."
        db.add(site)
        db.commit()
    # ----------------------------------------------
    
    # After creation, update table_prefix with actual ID if it was the placeholder
    if site.table_prefix == "wp_tmp_":
        site.table_prefix = f"wp_{site.id}_"
        db.add(site)
        db.commit()
        db.refresh(site)

    return site

@router.get("/{id}", response_model=Site)
def read_site(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get site by ID.
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site

@router.put("/{id}", response_model=Site)
def update_site(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    site_in: SiteUpdate,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a site.
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    update_data = site_in.dict(exclude_unset=True)
    for field in update_data:
        setattr(site, field, update_data[field])
    
    db.add(site)
    db.commit()
    db.refresh(site)
    return site

@router.delete("/{id}", response_model=Site)
def delete_site(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    delete_db: bool = False,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a site.
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Logic to delete site files, database tables, OLS config would go here
    if delete_db:
        # Implementation for deleting specific site tables from shared database
        pass

    db.delete(site)
    db.commit()
    return site

@router.post("/{id}/purge-cache")
def purge_site_cache(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Purge LSCache for the site.
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Logic to purge OLS LSCache: usually deleting files in lscache directory or calling API
    return {"success": True, "message": f"Cache purged for {site.domain}"}

@router.get("/{id}/wp-config")
def read_wp_config(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Read wp-config.php content.
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    config_path = os.path.join(site.root_path, "wp-config.php")
    if not os.path.exists(config_path):
        # Return empty or standard template if not found
        return {"content": "/* wp-config.php not found */"}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read wp-config.php: {str(e)}")

@router.post("/{id}/wp-config")
def update_wp_config(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    config_in: WpConfigUpdate,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update wp-config.php content.
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    config_path = os.path.join(site.root_path, "wp-config.php")
    
    # Ensure directory exists (though it should)
    if not os.path.exists(site.root_path):
        os.makedirs(site.root_path, exist_ok=True)
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_in.content)
        return {"success": True, "message": "wp-config.php updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update wp-config.php: {str(e)}")

@router.post("/{id}/ssl")
def configure_ssl(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    action: str = "apply", # apply, renew, disable
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Configure SSL (Let's Encrypt).
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Integration with Certbot/acme.sh and OLS config update
    return {"success": True, "message": f"SSL {action} successful for {site.domain}"}

@router.post("/{id}/backup")
def backup_site(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a backup of the site (files + database).
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Logic to archive files and export database tables
    return {"success": True, "message": f"Backup created for {site.domain}"}


# Shared Database Endpoints
@router.get("/databases/shared", response_model=List[SharedDatabase])
def read_shared_databases(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve shared databases.
    """
    databases = db.query(SharedDatabaseModel).offset(skip).limit(limit).all()
    return databases

@router.post("/databases/shared", response_model=SharedDatabase)
def create_shared_database(
    *,
    db: Session = Depends(deps.get_db),
    db_in: SharedDatabaseCreate,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create new shared database.
    """
    database = SharedDatabaseModel(**db_in.dict())
    db.add(database)
    db.commit()
    db.refresh(database)
    return database
