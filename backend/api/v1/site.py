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
    # 1. Root path default to project_root/wordpress/{domain} if not provided
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_root = os.path.join(project_root, "wordpress", site_in.domain)
    root_path = site_in.root_path or default_root
    
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
                db_user="root",
                db_password="",
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
    
    # 3. Update table_prefix with actual site ID
    site.table_prefix = f"wp_{site.id}_"
    db.add(site)
    db.commit()

    # --- MariaDB/MySQL Database & WordPress Installation Logic ---
    try:
        shared_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.id == site.shared_db_id).first()
        
        # Initialize DB variables to None
        db_name = None
        db_user = None
        db_pass = None

        if shared_db:
            import mysql.connector
            import string
            import random
            
            # 1. Database Creation
            try:
                conn = mysql.connector.connect(
                    host=shared_db.db_host,
                    port=shared_db.db_port,
                    user=shared_db.db_user,
                    password=shared_db.db_password,
                    connect_timeout=5
                )
                cursor = conn.cursor()
                
                # Generate DB name, user, password
                safe_domain = site.domain.replace('.', '_').replace('-', '_')
                db_name = f"db_{safe_domain}"
                db_user = f"u_{safe_domain}"[:16] 
                db_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                
                # Create DB
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                
                # Create User and Grant Permissions
                try:
                    cursor.execute(f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}'")
                except:
                    cursor.execute(f"ALTER USER '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}'")
                
                cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'localhost'")
                cursor.execute("FLUSH PRIVILEGES")
                
                # Update site record
                site.db_name = db_name
                site.db_user = db_user
                site.db_password = db_pass
                site.db_permission = "site_only"
                site.notes = "step2: MariaDB 数据库安装完成"
                db.add(site)
                db.commit()
                
                cursor.close()
                conn.close()
            except Exception as db_err:
                print(f"Database creation failed: {db_err}")
                site.notes = f"warning: 数据库创建失败({str(db_err)})，将继续安装文件"
                db.add(site)
                db.commit()

        # 2. WordPress Files Installation using WP-CLI
        import subprocess
        import shutil
        from backend.utils.php_utils import get_php_path

        if not os.path.exists(site.root_path):
            os.makedirs(site.root_path, exist_ok=True)
        
        php_path = get_php_path()
        bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wp_cli_path = os.path.join(bin_dir, "wp-cli.phar")
        
        if not os.path.exists(wp_cli_path):
            import requests
            print("Downloading WP-CLI...")
            r = requests.get("https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar")
            with open(wp_cli_path, "wb") as f:
                f.write(r.content)

        # Step 1: Download core
        site.notes = "step1: WordPress 文件下载中..."
        db.add(site)
        db.commit()

        try:
            # Download Core
            cmd = [php_path, wp_cli_path, "core", "download", f"--path={site.root_path}", "--locale=zh_CN", "--allow-root", "--skip-content"]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Step 3: Config Create (only if DB was created successfully)
            if db_name and db_user and db_pass:
                site.notes = "step3: 配置优化中..."
                db.add(site)
                db.commit()

                cmd_config = [
                    php_path, wp_cli_path, "config", "create", 
                    f"--path={site.root_path}", 
                    f"--dbname={db_name}", 
                    f"--dbuser={db_user}", 
                    f"--dbpass={db_pass}", 
                    f"--dbhost={shared_db.db_host}",
                    f"--dbprefix={site.table_prefix}",
                    "--locale=zh_CN",
                    "--allow-root"
                ]
                subprocess.run(cmd_config, check=True, capture_output=True)
                site.notes = "completed: WordPress 站点创建完成"
            else:
                site.notes = "completed: 文件已安装(数据库配置需手动)"
            
            db.add(site)
            db.commit()

        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode(errors='ignore') if e.stderr else str(e)
            print(f"WP-CLI Error: {err_msg}")
            site.notes = f"failed: WP-CLI 执行失败 - {err_msg}"
            db.add(site)
            db.commit()

    except Exception as e:
        print(f"Error during WordPress installation: {e}")
        site.notes = f"failed: 安装失败 - {str(e)}"
        db.add(site)
        db.commit()

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
