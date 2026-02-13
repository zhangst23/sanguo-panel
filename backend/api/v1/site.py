from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.api import deps
from backend.models.site import Site as SiteModel, SharedDatabase as SharedDatabaseModel
from backend.schemas.site import Site, SiteCreate, SiteUpdate, SharedDatabase, SharedDatabaseCreate

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
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a site.
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    db.delete(site)
    db.commit()
    return site

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
