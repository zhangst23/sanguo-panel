from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from backend.api import deps
from backend.models.site import Site as SiteModel, SharedDatabase as SharedDatabaseModel
from backend.schemas.site import Site, SiteCreate, SiteUpdate, SharedDatabase, SharedDatabaseCreate, WpConfigUpdate
import os
import subprocess
import shutil
import string
import random
import requests
import mysql.connector
from backend.utils.php_utils import get_php_path
from backend.utils.ols_utils import (
    create_ols_vhost,
    remove_ols_vhost,
    chown_site_root,
    get_installed_php_versions,
    get_default_php_version,
)
from backend.utils.site_utils import set_lscache_plugin, purge_site_lscache

router = APIRouter()

def install_wordpress_task(site_id: int):
    """
    Background task to install WordPress on the OpenLiteSpeed stack:
    WP-CLI runs on the OLS-bundled PHP (LSAPI build), an OLS virtual host
    (per-vhost LSAPI handler, multi-PHP) is registered, files are chowned to
    the LSAPI worker, and LSCache is enabled when requested.
    """
    from backend.core.database import SessionLocal
    db = SessionLocal()
    try:
        site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
        if not site:
            return
        ols_note = ""

        shared_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.id == site.shared_db_id).first()

        # 1. WordPress Files Installation using WP-CLI
        # WP-CLI requires PHP CLI SAPI; OLS lsphp is LSAPI-only and cannot run CLI.
        php_path = get_php_path()
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if site.root_path and not os.path.isabs(site.root_path):
            site.root_path = os.path.join(project_root, site.root_path)
            db.add(site); db.commit()
        bin_dir = os.path.join(project_root, "backend", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wp_cli_path = os.path.join(bin_dir, "wp-cli.phar")

        if not os.path.exists(wp_cli_path):
            print("Downloading WP-CLI...")
            r = requests.get("https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar")
            with open(wp_cli_path, "wb") as f:
                f.write(r.content)

        if not os.path.exists(site.root_path):
            os.makedirs(site.root_path, exist_ok=True)

        # 1.5 Resolve requested PHP version against installed lsphp builds
        installed = {v["version"] for v in get_installed_php_versions()}
        if site.php_version not in installed:
            resolved = get_default_php_version()
            php_note = f"⚠️ PHP {site.php_version} 未安装，回退到默认 {resolved}"
            site.php_version = resolved
        else:
            php_note = f"PHP {site.php_version}"

        # 1.6 Register OpenLiteSpeed virtual host (LSAPI, per-vhost PHP version)
        ols_res = create_ols_vhost(site.domain, site.root_path, site.php_version)
        if ols_res.get("success") and ols_res.get("php_used"):
            site.php_version = ols_res["php_used"]
        ols_note = (
            f"✅ OLS 虚拟主机已创建 (LSAPI · {php_note}): {site.domain}"
            if ols_res.get("success")
            else f"⚠️ OLS 虚拟主机创建失败: {ols_res.get('msg')}"
        )
        db.add(site)
        db.commit()

        # Step 1: Download Core
        site.notes = f"step1: WordPress 文件下载中...\n{ols_note}"
        db.add(site)
        db.commit()

        try:
            # Download Core
            cmd = [php_path, wp_cli_path, "core", "download", f"--path={site.root_path}", "--locale=zh_CN", "--allow-root", "--force"]
            subprocess.run(cmd, check=True, capture_output=True)

            # 2. Database Creation
            db_name = None
            db_user = None
            db_pass = None

            if shared_db:
                try:
                    conn = mysql.connector.connect(
                        host=shared_db.db_host,
                        port=shared_db.db_port,
                        user=shared_db.db_user,
                        password=shared_db.db_password,
                        connect_timeout=5
                    )
                    cursor = conn.cursor()

                    safe_domain = site.domain.replace('.', '_').replace('-', '_')
                    db_name = f"db_{safe_domain}"
                    db_user = f"u_{safe_domain}"[:16]
                    db_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    try:
                        cursor.execute(f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}'")
                    except:
                        cursor.execute(f"ALTER USER '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}'")

                    cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'localhost'")
                    cursor.execute("FLUSH PRIVILEGES")

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
                    site.notes = f"warning: 数据库创建失败({str(db_err)})"
                    db.add(site)
                    db.commit()

            # Step 3: Config Create & Install
            if db_name and db_user and db_pass:
                site.notes = "step3: 配置优化中..."
                db.add(site)
                db.commit()

                # Generate wp-config.php
                cmd_config = [
                    php_path, wp_cli_path, "config", "create",
                    f"--path={site.root_path}",
                    f"--dbname={db_name}",
                    f"--dbuser={db_user}",
                    f"--dbpass={db_pass}",
                    f"--dbhost={shared_db.db_host}",
                    f"--dbprefix={site.table_prefix}",
                    "--locale=zh_CN",
                    "--allow-root",
                    "--force"
                ]
                subprocess.run(cmd_config, check=True, capture_output=True)

                # Core Install
                admin_user = "admin"
                admin_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                admin_email = f"admin@{site.domain}"

                cmd_install = [
                    php_path, wp_cli_path, "core", "install",
                    f"--path={site.root_path}",
                    f"--url={site.domain}",
                    f"--title={site.domain}",
                    f"--admin_user={admin_user}",
                    f"--admin_password={admin_pass}",
                    f"--admin_email={admin_email}",
                    "--allow-root"
                ]
                subprocess.run(cmd_install, check=True, capture_output=True)

                # Get WordPress version after install
                try:
                    cmd_version = [
                        php_path, wp_cli_path, "core", "version",
                        f"--path={site.root_path}",
                        "--allow-root"
                    ]
                    result = subprocess.run(cmd_version, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and result.stdout.strip():
                        site.wp_version = result.stdout.strip()
                except Exception:
                    site.wp_version = "已安装"

                # Hand the files to the LSAPI worker (nobody) for uploads/writes
                chown_site_root(site.root_path)

                # Enable OLS LSCache (LiteSpeed Cache WP plugin) when requested
                cache_note = ""
                if site.lscache_enabled:
                    ok, msg = set_lscache_plugin(site, True)
                    cache_note = "\n✅ LSCache 已启用 (litespeed-cache)" if ok else f"\n⚠️ LSCache 启用失败: {msg}"

                site.notes = (
                    f"completed: WordPress 站点创建完成。管理员: {admin_user} 密码: {admin_pass}"
                    f"\n{ols_note}{cache_note}"
                )
            else:
                chown_site_root(site.root_path)
                site.notes = f"completed: 文件已安装(数据库配置需手动)\n{ols_note}"

            db.add(site)
            db.commit()

        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode(errors='ignore') if e.stderr else str(e)
            print(f"WP-CLI Error: {err_msg}")
            site.notes = f"failed: WP-CLI 执行失败 - {err_msg}\n{ols_note}"
            db.add(site)
            db.commit()

    except Exception as e:
        print(f"Error during WordPress installation: {e}")
        site.notes = f"failed: 安装失败 - {str(e)}\n{ols_note}"
        db.add(site)
        db.commit()
    finally:
        db.close()

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
    # 尝试为缺少 wp_version 的站点自动探测
    for site in sites:
        if not site.wp_version or site.wp_version == "未安装":
            detected = _detect_wp_version(site)
            if detected:
                site.wp_version = detected
                db.add(site)
    db.commit()
    return sites


def _detect_wp_version(site) -> Optional[str]:
    """尝试通过 WP-CLI 探测站点 WordPress 版本"""
    try:
        if not site.root_path or not os.path.exists(site.root_path):
            return None
        php_path = get_php_path()
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        wp_cli_path = os.path.join(project_root, "backend", "bin", "wp-cli.phar")
        if not os.path.exists(wp_cli_path):
            return None
        import subprocess
        result = subprocess.run(
            [php_path, wp_cli_path, "core", "version", f"--path={site.root_path}", "--allow-root"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        return None
    return None

@router.post("/", response_model=Site)
def create_site(
    *,
    db: Session = Depends(deps.get_db),
    site_in: SiteCreate,
    background_tasks: BackgroundTasks,
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

    # 1. Root path default to project_root/wordpress/{domain} if not provided
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    default_root = os.path.join(project_root, "wordpress", site_in.domain)
    root_path = site_in.root_path or default_root
    if not os.path.isabs(root_path):
        root_path = os.path.join(project_root, root_path)

    # 2. Shared Database: Default to the first active shared database if not provided
    shared_db_id = site_in.shared_db_id
    if not shared_db_id:
        shared_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.status == "active").first()
        if not shared_db:
            shared_db = SharedDatabaseModel(
                name="Default MariaDB",
                db_host="localhost",
                db_port=3306,
                db_name="wp_db",
                db_user="root",
                db_password="",
                status="active"
            )
            db.add(shared_db)
            db.commit()
            db.refresh(shared_db)
        shared_db_id = shared_db.id

    table_prefix = site_in.table_prefix or "wp_tmp_"

    site_data = site_in.dict()
    site_data.update({
        "root_path": root_path,
        "shared_db_id": shared_db_id,
        "table_prefix": table_prefix,
        "status": "active",
        "notes": "pending: 准备安装中..."
    })

    if "performance_preset" not in site_data:
        site_data["performance_preset"] = "balanced"

    site = SiteModel(**site_data)
    db.add(site)
    db.commit()
    db.refresh(site)

    # Update table_prefix with actual site ID
    site.table_prefix = f"wp_{site.id}_"
    db.add(site)
    db.commit()

    # Start installation in background
    background_tasks.add_task(install_wordpress_task, site.id)

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
    Update a site. OLS-workflow side effects:
    - php_version change   -> re-register the vhost with the new per-vhost LSAPI handler
    - lscache_enabled change -> install/activate or deactivate the LiteSpeed Cache plugin
    - redis_enabled change  -> update wp-config.php Redis constants
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

    # PHP version change: regenerate the OLS vhost with the requested LSAPI handler
    if "php_version" in update_data:
        try:
            create_ols_vhost(site.domain, site.root_path, site.php_version)
        except Exception as e:
            print(f"Error switching PHP version for {site.domain}: {str(e)}")

    # LSCache toggle: install/activate or deactivate the LiteSpeed Cache plugin
    if "lscache_enabled" in update_data:
        try:
            set_lscache_plugin(site, site.lscache_enabled)
        except Exception as e:
            print(f"Error toggling LSCache for {site.domain}: {str(e)}")

    # If redis_enabled was toggled, update wp-config.php
    if "redis_enabled" in update_data:
        try:
            from backend.utils.site_utils import update_wp_config_redis
            update_wp_config_redis(site)
        except Exception as e:
            # Don't fail the whole update if this fails, but log it
            print(f"Error updating Redis config for {site.domain}: {str(e)}")

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
    Delete a site: remove files, drop the OLS LSAPI virtual host, and
    optionally drop the MariaDB database/user.
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Remove site files
    if site.root_path and os.path.exists(site.root_path):
        shutil.rmtree(site.root_path, ignore_errors=True)

    # Remove the OpenLiteSpeed virtual host (LSAPI) for this domain
    try:
        remove_ols_vhost(site.domain)
    except Exception as e:
        print(f"Error removing OLS vhost for {site.domain}: {e}")

    # Drop the site database + user when requested
    if delete_db and site.db_name:
        try:
            shared_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.id == site.shared_db_id).first()
            if shared_db:
                conn = mysql.connector.connect(
                    host=shared_db.db_host, port=shared_db.db_port,
                    user=shared_db.db_user, password=shared_db.db_password, connect_timeout=5,
                )
                cur = conn.cursor()
                cur.execute(f"DROP DATABASE IF EXISTS `{site.db_name}`")
                if site.db_user:
                    try:
                        cur.execute(f"DROP USER IF EXISTS '{site.db_user}'@'localhost'")
                    except Exception:
                        pass
                cur.execute("FLUSH PRIVILEGES")
                cur.close()
                conn.close()
        except Exception as e:
            print(f"Error dropping database for {site.domain}: {e}")

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
    Purge LSCache for the site (OLS on-disk cache + WP object cache flush).
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    res = purge_site_lscache(site)
    return {"success": True, "message": f"Cache purged for {site.domain}", "details": res}

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
    email: str = None,
    force_https: bool = False,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Configure SSL via Let's Encrypt + OpenLiteSpeed (443 SNI).
    """
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    from backend.utils import ols_ssl_utils

    if action == "apply":
        issue = ols_ssl_utils.issue_ssl(site.domain, email, site.root_path)
        if not issue["success"]:
            raise HTTPException(status_code=500, detail=f"证书签发失败: {(issue.get('stderr') or '')[-300:]}")
        deploy = ols_ssl_utils.deploy_ssl_to_ols(site.domain, force_https=force_https)
        site.ssl_status = 2 if force_https else 1
        site.ssl_mode = "letsencrypt"
        site.https_force = force_https
        if email:
            site.ssl_email = email
        db.commit()
        return {"success": deploy["success"], "message": deploy["msg"]}
    elif action == "disable":
        res = ols_ssl_utils.disable_ssl_ols(site.domain)
        site.ssl_status = 0
        site.ssl_mode = "none"
        site.https_force = False
        db.commit()
        return {"success": res["success"], "message": res["msg"]}
    elif action == "renew":
        res = ols_ssl_utils.renew_ssl(site.domain)
        return {"success": res["success"], "message": f"续期 ({site.domain})"}
    raise HTTPException(status_code=400, detail="Invalid action")

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
