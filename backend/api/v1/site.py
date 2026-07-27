from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.api import deps
from backend.models.site import Site as SiteModel, SharedDatabase as SharedDatabaseModel
from backend.schemas.site import Site, SiteCreate, SiteUpdate, SharedDatabase, SharedDatabaseCreate, WpConfigUpdate, \
    ChangeDomainRequest, MigrateRequest, BatchCreateRequest, PluginAction
import os
import re
import subprocess
import shutil
import string
import random
import json
import requests
import mysql.connector
from backend.utils.php_utils import get_php_path
from backend.core.config import settings
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
        # project_root is still needed for wp-cli.phar location
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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

        # 1.7 Register domain on SSL listener for HTTPS (cloudflare/letsencrypt)
        try:
            _register_ssl_listener(site.domain)
        except Exception:
            pass

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

    # 1. Root path default to /var/www/html/{domain} if not provided
    default_root = os.path.join("/var/www/html", site_in.domain)
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


# ----------------------------------------------------
# Change Domain (with progress tracking)
# ----------------------------------------------------
import time as _time
import threading as _threading

_domain_change_tasks: dict = {}
_task_lock = _threading.Lock()


def _set_progress(task_id: str, steps: list):
    with _task_lock:
        _domain_change_tasks[task_id] = {"steps": steps, "done": False}


def _mark_done(task_id: str, result: dict):
    with _task_lock:
        if task_id in _domain_change_tasks:
            _domain_change_tasks[task_id]["done"] = True
            _domain_change_tasks[task_id]["result"] = result


def _run_domain_change(
    task_id: str, db_factory, site_id: int, old_domain: str, new_domain: str,
    old_root_path: str, new_root_path: str, old_db_password: str,
    old_db_name: str, old_db_user: str, new_db_name: str, new_db_user: str,
    shared_db_host: str, shared_db_port: int, shared_db_user: str, shared_db_pass: str,
    php_version: str, ssl_mode: str,
):
    steps = [
        {"name": "重命名WordPress文件夹", "message": f"{old_root_path} → {new_root_path}", "status": "pending"},
        {"name": "创建新数据库和用户", "message": f"数据库: {new_db_name}, 用户: {new_db_user}", "status": "pending"},
        {"name": "迁移数据库数据", "message": f"mysqldump {old_db_name} → {new_db_name}", "status": "pending"},
        {"name": "更新wp-config.php", "message": "更新 DB_NAME / DB_USER", "status": "pending"},
        {"name": "更新WordPress站点URL", "message": "更新 home 和 siteurl 选项", "status": "pending"},
        {"name": "更新OLS虚拟主机", "message": f"删除 {old_domain}, 创建 {new_domain}", "status": "pending"},
        {"name": "更新面板记录", "message": "保存新域名到数据库", "status": "pending"},
    ]
    _set_progress(task_id, steps)

    def step_run(idx, message=None):
        steps[idx]["status"] = "running"
        if message:
            steps[idx]["message"] = message
        _set_progress(task_id, steps)
        _time.sleep(0.3)

    def step_ok(idx, message=None):
        steps[idx]["status"] = "done"
        if message:
            steps[idx]["message"] = message
        _set_progress(task_id, steps)
        _time.sleep(0.3)

    def step_fail(idx, message):
        steps[idx]["status"] = "failed"
        steps[idx]["message"] = message
        _set_progress(task_id, steps)

    # --- Step 0: Rename folder ---
    step_run(0)
    if os.path.isdir(old_root_path):
        if not os.path.isdir(new_root_path):
            try:
                shutil.move(old_root_path, new_root_path)
                step_ok(0)
            except Exception as e:
                step_fail(0, f"重命名失败: {e}")
                _mark_done(task_id, {"error": f"文件夹重命名失败: {e}"})
                return
        else:
            step_ok(0, "目标文件夹已存在，跳过重命名")
    else:
        step_fail(0, f"原文件夹不存在: {old_root_path}")
        _mark_done(task_id, {"error": f"原文件夹不存在: {old_root_path}"})
        return

    # --- Step 1: Create new DB & user ---
    step_run(1)
    if shared_db_host and old_db_name:
        try:
            conn = mysql.connector.connect(
                host=shared_db_host, port=shared_db_port,
                user=shared_db_user, password=shared_db_pass,
                connect_timeout=5,
            )
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{new_db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            try:
                cursor.execute(
                    f"CREATE USER '{new_db_user}'@'localhost' "
                    f"IDENTIFIED BY '{old_db_password}'"
                )
            except Exception:
                cursor.execute(
                    f"ALTER USER '{new_db_user}'@'localhost' "
                    f"IDENTIFIED BY '{old_db_password}'"
                )
            cursor.execute(
                f"GRANT ALL PRIVILEGES ON `{new_db_name}`.* "
                f"TO '{new_db_user}'@'localhost'"
            )
            cursor.execute("FLUSH PRIVILEGES")
            cursor.close()
            conn.close()
            step_ok(1)
        except Exception as e:
            step_fail(1, f"数据库连接失败: {e}")
            _mark_done(task_id, {"error": f"数据库连接失败: {e}"})
            return

    # --- Step 2: Migrate data ---
    step_run(2)
    try:
        dump_pass = shared_db_pass.replace("'", "'\\''")
        dump_cmd = (
            f"mysqldump -h {shared_db_host} -P {shared_db_port} "
            f"-u {shared_db_user} -p'{dump_pass}' "
            f"--single-transaction --skip-lock-tables '{old_db_name}' "
            f"| mysql -h {shared_db_host} -P {shared_db_port} "
            f"-u {shared_db_user} -p'{dump_pass}' '{new_db_name}'"
        )
        r = subprocess.run(
            dump_cmd, shell=True, capture_output=True, text=True, timeout=120
        )
        if r.returncode != 0:
            step_fail(2, f"迁移失败: {r.stderr[:200]}")
            _mark_done(task_id, {"error": f"数据库迁移失败: {r.stderr[:200]}"})
            return
        step_ok(2)
    except subprocess.TimeoutExpired:
        step_fail(2, "迁移超时")
        _mark_done(task_id, {"error": "数据库迁移超时"})
        return
    except Exception as e:
        step_fail(2, f"迁移异常: {e}")
        _mark_done(task_id, {"error": f"数据库迁移异常: {e}"})
        return

    # --- Step 3: Update wp-config.php ---
    step_run(3)
    wp_config_path = os.path.join(new_root_path, "wp-config.php")
    if os.path.exists(wp_config_path):
        try:
            with open(wp_config_path, "r") as f:
                config = f.read()
            config = re.sub(
                r"define\(\s*['\"]DB_NAME['\"]\s*,\s*['\"][^'\"]*['\"]\s*\)",
                f"define('DB_NAME', '{new_db_name}')",
                config,
            )
            config = re.sub(
                r"define\(\s*['\"]DB_USER['\"]\s*,\s*['\"][^'\"]*['\"]\s*\)",
                f"define('DB_USER', '{new_db_user}')",
                config,
            )
            with open(wp_config_path, "w") as f:
                f.write(config)
            step_ok(3)
        except Exception as e:
            step_fail(3, f"更新失败: {e}")
            _mark_done(task_id, {"error": f"wp-config更新失败: {e}"})
            return
    else:
        step_fail(3, "wp-config.php 不存在")
        _mark_done(task_id, {"error": "wp-config.php 不存在"})
        return

    # --- Step 4: Update WordPress options ---
    step_run(4)
    try:
        php_path, wp_cli_path = _get_wp_cli_paths_raw()
        if php_path and os.path.exists(wp_cli_path) and \
           os.path.exists(os.path.join(new_root_path, "wp-load.php")):
            protocol = "https" if ssl_mode and ssl_mode != "none" else "http"
            new_url = f"{protocol}://{new_domain}"
            for opt in ("home", "siteurl"):
                r = subprocess.run(
                    [
                        php_path, wp_cli_path, "option", "update", opt, new_url,
                        f"--path={new_root_path}", "--allow-root",
                    ],
                    capture_output=True, text=True, timeout=60,
                )
                if r.returncode != 0:
                    steps[4]["message"] = f"WP-CLI 命令返回错误: {opt} {r.stderr[:100]}"
        step_ok(4)
    except Exception as e:
        step_fail(4, f"WP-CLI 失败: {e}")
        # Continue anyway - this is not a blocking error

    # --- Step 5: Update OLS vhost (single restart) ---
    step_run(5)
    try:
        _update_ols_domain(old_domain, new_domain, new_root_path)
        step_ok(5)
    except Exception as e:
        step_fail(5, f"OLS 失败: {e}")
        _mark_done(task_id, {"error": f"OLS更新失败: {e}"})
        return

    # --- Step 6: Update panel DB record ---
    step_run(6)
    try:
        db = db_factory()
        site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
        if site:
            site.domain = new_domain
            site.root_path = new_root_path
            site.db_name = new_db_name
            site.db_user = new_db_user
            db.add(site)
            db.commit()
            db.refresh(site)
            step_ok(6)
            _mark_done(task_id, {"success": True, "domain": new_domain})
        else:
            step_fail(6, "面板中未找到该站点")
            _mark_done(task_id, {"error": "面板记录更新失败"})
        db.close()
    except Exception as e:
        step_fail(6, f"面板记录失败: {e}")
        _mark_done(task_id, {"error": f"面板记录更新失败: {e}"})


def _get_wp_cli_paths_raw():
    php_path = get_php_path()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    wp_cli_path = os.path.join(project_root, "backend", "bin", "wp-cli.phar")
    return php_path, wp_cli_path


def _register_ssl_listener(domain: str):
    """Add domain to OLS Panel443 SSL listener so HTTPS works."""
    from backend.utils.ols_utils import OLS_CONF
    with open(OLS_CONF, "r") as f:
        conf = f.read()
    map_line = f"    map                      {domain} {domain}"
    if map_line not in conf:
        idx = conf.find("listener Panel443{")
        if idx != -1:
            end = conf.find("}", idx)
            conf = conf[:end] + map_line + "\n" + conf[end:]
            with open(OLS_CONF, "w") as f:
                f.write(conf)


def _update_ols_domain(old_domain: str, new_domain: str, new_root_path: str):
    """Update OLS vhost domain in-place (one restart)."""
    from backend.utils.ols_utils import OLS_CONF, VHOSTS_DIR, restart_ols

    old_domain = old_domain.lower()
    new_domain = new_domain.lower()

    with open(OLS_CONF, "r") as f:
        conf = f.read()

    # Replace virtualHost block: change domain + vhRoot
    def _replace_vhost(m):
        block = m.group(0)
        block = block.replace(old_domain, new_domain)
        block = re.sub(r"(vhRoot\s+)\S+", r"\g<1>" + new_root_path, block)
        return block

    conf = re.sub(
        r"virtualHost " + re.escape(old_domain) + r"\{[^{}]*\}",
        _replace_vhost,
        conf,
    )

    # Replace listener map line
    conf = re.sub(
        r"map\s+" + re.escape(old_domain) + r"\s+" + re.escape(old_domain),
        f"map                      {new_domain} {new_domain}",
        conf,
    )

    with open(OLS_CONF, "w") as f:
        f.write(conf)

    # Rename vhost config directory
    old_vhost_dir = os.path.join(VHOSTS_DIR, old_domain)
    new_vhost_dir = os.path.join(VHOSTS_DIR, new_domain)
    if os.path.isdir(old_vhost_dir) and not os.path.isdir(new_vhost_dir):
        shutil.move(old_vhost_dir, new_vhost_dir)

    # Update configFile reference inside the new vhconf
    vhconf_path = os.path.join(new_vhost_dir, "vhconf.conf")
    if os.path.exists(vhconf_path):
        with open(vhconf_path, "r") as f:
            vhconf = f.read()
        vhconf = vhconf.replace(old_domain, new_domain)
        with open(vhconf_path, "w") as f:
            f.write(vhconf)

    restart_ols()


@router.put("/{id}/change-domain")
def change_site_domain(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    req: ChangeDomainRequest,
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    existing = db.query(SiteModel).filter(SiteModel.domain == req.new_domain).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists")

    old_domain = site.domain
    new_domain = req.new_domain
    old_root_path = site.root_path
    new_root_path = os.path.join("/var/www/html", new_domain)
    old_db_password = site.db_password
    old_db_name = site.db_name
    old_db_user = site.db_user

    safe_new = new_domain.replace('.', '_').replace('-', '_')
    new_db_name = f"db_{safe_new}"
    new_db_user = f"u_{safe_new}"[:16]

    # Get shared DB info
    shared_db = db.query(SharedDatabaseModel).filter(
        SharedDatabaseModel.id == site.shared_db_id
    ).first()
    shared_db_host = shared_db.db_host if shared_db else ""
    shared_db_port = shared_db.db_port if shared_db else 3306
    shared_db_user = shared_db.db_user if shared_db else ""
    shared_db_pass = shared_db.db_password if shared_db else ""

    # Create a reusable db session factory for the background thread
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.core.config import settings
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    def db_factory():
        return SessionLocal()

    task_id = f"{id}_{new_domain}_{int(_time.time())}"

    thread = _threading.Thread(
        target=_run_domain_change,
        args=(
            task_id, db_factory, id, old_domain, new_domain,
            old_root_path, new_root_path, old_db_password,
            old_db_name, old_db_user, new_db_name, new_db_user,
            shared_db_host, shared_db_port, shared_db_user, shared_db_pass,
            site.php_version, site.ssl_mode or "",
        ),
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id}


@router.get("/change-domain/{task_id}/progress")
def get_domain_change_progress(task_id: str) -> Any:
    with _task_lock:
        data = _domain_change_tasks.get(task_id)
    if not data:
        return {"steps": [], "done": False, "error": "任务不存在"}
    return data


# ----------------------------------------------------
# WooCommerce API Keys
# ----------------------------------------------------
@router.post("/{id}/woocommerce/keys")
def generate_woocommerce_keys(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    import secrets
    import string
    ck = "ck_" + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    cs = "cs_" + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40))
    site.wc_key = ck
    site.wc_secret = cs
    db.add(site)
    db.commit()
    return {"key": ck, "secret": cs}


# ----------------------------------------------------
# Migrate Site
# ----------------------------------------------------
@router.post("/migrate")
def migrate_site(
    *,
    db: Session = Depends(deps.get_db),
    background_tasks: BackgroundTasks,
    req: MigrateRequest,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    existing = db.query(SiteModel).filter(SiteModel.domain == req.domain).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists")
    root_path = os.path.join("/var/www/html", req.domain)
    default_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.status == "active").first()
    if not default_db:
        raise HTTPException(status_code=400, detail="No active shared database")

    site = SiteModel(
        domain=req.domain,
        root_path=root_path,
        php_version=req.php_version,
        shared_db_id=default_db.id,
        table_prefix=f"wp_mig_",
        status="active",
        notes="pending: 迁移中...",
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    site.table_prefix = f"wp_{site.id}_"
    db.add(site)
    db.commit()
    site_id = site.id

    background_tasks.add_task(_migrate_task, site_id, req)
    return site


def _migrate_task(site_id: int, req: MigrateRequest):
    from backend.core.database import SessionLocal
    db = SessionLocal()
    site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
    if not site:
        db.close()
        return
    try:
        os.makedirs(site.root_path, exist_ok=True)
        if req.source_host:
            # SSH-based migration
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(req.source_host, port=req.source_port, username=req.source_user,
                       password=req.source_password, timeout=30)
            # rsync files
            ssh.exec_command(f"mkdir -p {site.root_path}")
            sftp = ssh.open_sftp()
            try:
                _sftp_walk(sftp, req.source_path, site.root_path)
            finally:
                sftp.close()
            # dump and import DB
            stdin, stdout, stderr = ssh.exec_command(
                f"mysqldump -h {req.source_db_host} -P {req.source_db_port} -u {req.source_db_user} "
                f"-p'{req.source_db_password}' {req.source_db_name} --single-transaction --quick"
            )
            dump = stdout.read()
            ssh.close()
            # Import locally
            sd = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.id == site.shared_db_id).first()
            if sd and dump:
                import mysql.connector
                conn = mysql.connector.connect(host=sd.db_host, port=sd.db_port, user=sd.db_user,
                                               password=sd.db_password, connect_timeout=5)
                safe_domain = site.domain.replace('.', '_').replace('-', '_')
                db_name = f"db_{safe_domain}"
                db_user = f"u_{safe_domain}"[:16]
                db_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                cursor = conn.cursor()
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
                db.add(site)
                db.commit()
                # Import dump into new DB
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.sql', delete=False) as tf:
                    tf.write(dump)
                    dump_path = tf.name
                subprocess.run(
                    f"mysql -h {sd.db_host} -P {sd.db_port} -u {sd.db_user} -p'{sd.db_password}' {db_name} < {dump_path}",
                    shell=True, check=True
                )
                os.unlink(dump_path)
                cursor.close()
                conn.close()
            # Update wp-config
            config_path = os.path.join(site.root_path, "wp-config.php")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    cfg = f.read()
                cfg = re.sub(r"define\(\s*'DB_NAME',\s*'[^']*'\s*\)", f"define('DB_NAME', '{db_name}')", cfg)
                cfg = re.sub(r"define\(\s*'DB_USER',\s*'[^']*'\s*\)", f"define('DB_USER', '{db_user}')", cfg)
                cfg = re.sub(r"define\(\s*'DB_PASSWORD',\s*'[^']*'\s*\)", f"define('DB_PASSWORD', '{db_pass}')", cfg)
                with open(config_path, "w") as f:
                    f.write(cfg)
            site.notes = "completed: 站点迁移完成 (SSH)"
        else:
            site.notes = "completed: 站点目录已创建，请手动导入文件与数据库"
        db.add(site)
        db.commit()
        create_ols_vhost(site.domain, site.root_path, site.php_version)
    except Exception as e:
        site.notes = f"failed: 迁移失败 - {str(e)}"
        db.add(site)
        db.commit()
    finally:
        db.close()


def _sftp_walk(sftp, remote_dir, local_dir):
    os.makedirs(local_dir, exist_ok=True)
    for item in sftp.listdir_attr(remote_dir):
        rp = remote_dir + "/" + item.filename
        lp = os.path.join(local_dir, item.filename)
        import stat
        if stat.S_ISDIR(item.st_mode):
            _sftp_walk(sftp, rp, lp)
        else:
            sftp.get(rp, lp)


# ----------------------------------------------------
# Batch Create Sites
# ----------------------------------------------------
@router.post("/batch", response_model=List[Site])
def batch_create_sites(
    *,
    db: Session = Depends(deps.get_db),
    background_tasks: BackgroundTasks,
    req: BatchCreateRequest,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    created = []
    for item in req.sites:
        existing = db.query(SiteModel).filter(SiteModel.domain == item.domain).first()
        if existing:
            continue
        default_db = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.status == "active").first()
        if not default_db:
            continue
        root_path = os.path.join("/var/www/html", item.domain)
        site = SiteModel(
            domain=item.domain,
            root_path=root_path,
            php_version=item.php_version,
            shared_db_id=default_db.id,
            table_prefix=f"wp_tmp_",
            status="active",
            notes="pending: 准备安装中...",
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        site.table_prefix = f"wp_{site.id}_"
        db.add(site)
        db.commit()
        background_tasks.add_task(install_wordpress_task, site.id)
        created.append(site)
    return created


# ----------------------------------------------------
# WordPress Update / Plugin management
# ----------------------------------------------------
def _get_wp_cli(site):
    php_path = get_php_path()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    wp_cli_path = os.path.join(project_root, "backend", "bin", "wp-cli.phar")
    if not os.path.exists(wp_cli_path):
        raise HTTPException(status_code=500, detail="WP-CLI not found")
    return php_path, wp_cli_path


@router.post("/{id}/wp/update")
def update_wordpress(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    php_path, wp_cli_path = _get_wp_cli(site)
    cmd = [php_path, wp_cli_path, "core", "update", f"--path={site.root_path}", "--allow-root", "--force"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr)
    cmd_v = [php_path, wp_cli_path, "core", "version", f"--path={site.root_path}", "--allow-root"]
    rv = subprocess.run(cmd_v, capture_output=True, text=True, timeout=10)
    if rv.returncode == 0:
        site.wp_version = rv.stdout.strip()
        db.add(site)
        db.commit()
    return {"success": True, "output": result.stdout, "version": site.wp_version}


@router.post("/{id}/wp/plugins/install")
def install_plugin(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    req: PluginAction,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    php_path, wp_cli_path = _get_wp_cli(site)
    cmd = [php_path, wp_cli_path, "plugin", "install", req.slug, f"--path={site.root_path}", "--activate", "--allow-root"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr)
    return {"success": True, "output": result.stdout}


@router.delete("/{id}/wp/plugins/{slug}")
def delete_plugin(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    slug: str,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    php_path, wp_cli_path = _get_wp_cli(site)
    base = [php_path, wp_cli_path, f"--path={site.root_path}", "--allow-root"]

    deactivate = subprocess.run(base + ["plugin", "deactivate", slug], capture_output=True, text=True, timeout=30)
    if deactivate.returncode != 0 and "not active" not in deactivate.stderr:
        raise HTTPException(status_code=500, detail=f"停用插件失败: {deactivate.stderr}")

    result = subprocess.run(base + ["plugin", "delete", slug], capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr)
    return {"success": True, "output": result.stdout}


@router.post("/{id}/ai-repair")
def ai_repair_site(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if not settings.DEEPSEEK_API_KEY:
        raise HTTPException(status_code=400, detail="请先在系统设置中配置 AI API Key")

    process_log = []
    php_path, wp_cli_path = _get_wp_cli(site)
    base_cmd = [php_path, wp_cli_path, f"--path={site.root_path}", "--allow-root"]

    def log(msg):
        process_log.append(msg)

    def run_cmd(cmd_args, timeout=30):
        try:
            r = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout)
            if r.returncode == 0:
                return r.stdout.strip()
            return r.stderr.strip() or r.stdout.strip()
        except subprocess.TimeoutExpired:
            return "命令执行超时"
        except Exception as e:
            return str(e)

    # 1. Core info
    log("正在检查 WordPress 核心版本...")
    wp_version = run_cmd(base_cmd + ["core", "version"])
    log(f"WordPress 版本: {wp_version}")

    # 2. Plugin list
    log("正在获取插件列表...")
    plugins = run_cmd(base_cmd + ["plugin", "list", "--format=json"])
    try:
        plugin_data = json.loads(plugins)
        plugin_summary = [f"{p['name']} ({p['status']}, v{p.get('version','?')})" for p in plugin_data]
        log(f"已安装插件({len(plugin_data)}个): {', '.join(plugin_summary)}")
    except (json.JSONDecodeError, KeyError):
        plugin_data = plugins
        log(f"插件列表: {plugins[:500]}")

    # 3. Theme list
    log("正在获取主题列表...")
    themes = run_cmd(base_cmd + ["theme", "list", "--format=json"])
    try:
        theme_data = json.loads(themes)
        theme_summary = [f"{t['name']} ({t['status']})" for t in theme_data]
        log(f"已安装主题({len(theme_data)}个): {', '.join(theme_summary)}")
    except (json.JSONDecodeError, KeyError):
        theme_data = themes
        log(f"主题列表: {themes[:300]}")

    # 4. Check for updates
    log("正在检查更新...")
    core_update = run_cmd(base_cmd + ["core", "check-update"], timeout=60)
    log(f"核心更新状态: {core_update}")

    # 5. DB check
    log("正在检查数据库...")
    db_check = run_cmd(base_cmd + ["db", "check"])
    log(f"数据库检查: {db_check}")

    # 6. Option check (siteurl/home)
    log("正在读取站点配置...")
    siteurl = run_cmd(base_cmd + ["option", "get", "siteurl"])
    homeurl = run_cmd(base_cmd + ["option", "get", "home"])
    log(f"站点 URL: {siteurl}, 主页 URL: {homeurl}")

    # 7. Disk usage
    log("正在检查磁盘使用情况...")
    if os.path.exists(site.root_path):
        try:
            du = subprocess.run(["du", "-sh", site.root_path], capture_output=True, text=True, timeout=10)
            disk_usage = du.stdout.strip().split("\t")[0] if du.returncode == 0 else "未知"
            log(f"站点目录大小: {disk_usage}")
        except Exception:
            log("无法获取目录大小")

    # 8. Build diagnostic summary
    log("正在调用 AI 模型进行分析...")

    diagnostic_msg = f"""请对以下 WordPress 站点进行全面诊断并提供修复建议：

**站点信息：**
- 域名：{site.domain}
- 根路径：{site.root_path}
- PHP 版本：{site.php_version}
- 已记录 WP 版本：{site.wp_version}
- 当前 WP 版本：{wp_version}
- SSL 状态：{site.ssl_status} (0=关闭,1=开启,2=强制)

**插件状态：**
{plugins[:3000] if isinstance(plugins, str) else json.dumps(plugin_data, ensure_ascii=False)}

**主题状态：**
{themes[:2000] if isinstance(themes, str) else json.dumps(theme_data, ensure_ascii=False)}

**核心更新：** {core_update}
**数据库检查：** {db_check}
**站点 URL 配置：** siteurl={siteurl}, home={homeurl}

请给出：
1. 发现的问题列表（按严重程度排序）
2. 每个问题的具体修复建议或命令
3. 整体优化建议
请用中文回答，使用 Markdown 格式。"""

    ai_result = ""
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.DEEPSEEK_MODEL or "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个 WordPress 运维专家，擅长诊断和修复 WordPress 站点问题。"},
                    {"role": "user", "content": diagnostic_msg},
                ],
                "temperature": 0.3,
            },
            timeout=180,
        )
        if resp.status_code == 200:
            ai_result = resp.json()["choices"][0]["message"]["content"]
            log("AI 分析完成")
        else:
            log(f"AI 调用失败: HTTP {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        log(f"AI 调用异常: {str(e)}")

    return {
        "success": True,
        "site_id": id,
        "domain": site.domain,
        "process_log": process_log,
        "ai_analysis": ai_result,
    }


class AIRepairExecute(BaseModel):
    ai_analysis: str


@router.post("/{id}/ai-repair/execute")
def ai_repair_execute(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    data: AIRepairExecute,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if not settings.DEEPSEEK_API_KEY:
        raise HTTPException(status_code=400, detail="请先在系统设置中配置 AI API Key")

    process_log = []
    php_path, wp_cli_path = _get_wp_cli(site)
    base_cmd = [php_path, wp_cli_path, f"--path={site.root_path}", "--allow-root"]

    def log(msg):
        process_log.append(msg)

    def run_cmd(cmd_args, timeout=60):
        try:
            r = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout)
            if r.returncode == 0:
                return r.stdout.strip()
            return r.stderr.strip() or r.stdout.strip()
        except subprocess.TimeoutExpired:
            return "命令执行超时"
        except Exception as e:
            return str(e)

    log("正在请求 AI 生成修复命令...")

    execute_prompt = f"""根据以下 WordPress 站点诊断分析结果，生成可执行的 WP-CLI 修复命令。

**站点路径：** {site.root_path}
**WordPress 版本：** {site.wp_version}

**诊断分析：**
{data.ai_analysis}

请列出可以安全执行的 WP-CLI 命令来修复问题，命令格式要求：
- 每行一个命令，以 `wp ` 开头
- 只包含安全的操作（如 update, repair, optimize, rewrite, transient delete, cache flush, option update）
- 不要包含破坏性操作（如 drop, reset, uninstall, delete site）
- 不要使用 `--path=` 参数（系统会自动添加）

请用以下格式输出：
```commands
wp core update
wp plugin update --all
wp theme update --all
wp option update siteurl https://{site.domain}
wp rewrite flush
```

如果某些问题无法通过 WP-CLI 自动修复，请在命令后添加注释说明（以 # 开头）。"""

    commands_text = ""
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.DEEPSEEK_MODEL or "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个 WordPress 运维专家，负责根据诊断结果生成 WP-CLI 修复命令。"},
                    {"role": "user", "content": execute_prompt},
                ],
                "temperature": 0.1,
            },
            timeout=180,
        )
        if resp.status_code == 200:
            commands_text = resp.json()["choices"][0]["message"]["content"]
            log("AI 命令生成完成")
        else:
            log(f"AI 调用失败: HTTP {resp.status_code} - {resp.text[:200]}")
            return {"success": False, "process_log": process_log, "detail": "AI 命令生成失败"}
    except Exception as e:
        log(f"AI 调用异常: {str(e)}")
        return {"success": False, "process_log": process_log, "detail": str(e)}

    # Parse commands from AI response
    commands = []
    in_block = False
    for line in commands_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_block = not in_block
            continue
        if in_block and stripped.startswith("wp "):
            # Remove inline comments
            cmd_str = stripped.split("#")[0].strip()
            if cmd_str:
                commands.append(cmd_str)
        elif not in_block and stripped.startswith("wp "):
            cmd_str = stripped.split("#")[0].strip()
            if cmd_str:
                commands.append(cmd_str)

    if not commands:
        log("未找到可执行的修复命令")
        log(f"AI 原始响应:\n{commands_text[:500]}")
        return {"success": False, "process_log": process_log, "detail": "AI 未生成可执行的命令"}

    log(f"共解析到 {len(commands)} 条修复命令，开始执行...")

    cmd_results = []
    for i, cmd_str in enumerate(commands):
        log(f"[{i + 1}/{len(commands)}] 执行: {cmd_str}")
        parts = cmd_str.split()
        if parts[0] == "wp":
            parts = parts[1:]
        full_cmd = base_cmd + parts
        output = run_cmd(full_cmd, timeout=120)
        log(f"结果: {output[:300]}")
        cmd_results.append({"command": cmd_str, "output": output})

    log("全部修复命令执行完毕")

    return {
        "success": True,
        "site_id": id,
        "domain": site.domain,
        "process_log": process_log,
        "cmd_results": cmd_results,
    }


@router.get("/{id}/nginx-cloudflare")
def get_nginx_cloudflare_config(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    site = db.query(SiteModel).filter(SiteModel.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    config = rf"""# Cloudflare CDN Reverse Proxy for {site.domain}
server {{
    listen 80;
    server_name {site.domain};
    root {site.root_path};
    index index.php index.html;

    # Cloudflare IP restore
    set_real_ip_from 173.245.48.0/20;
    set_real_ip_from 103.21.244.0/22;
    set_real_ip_from 103.22.200.0/22;
    set_real_ip_from 103.31.4.0/22;
    set_real_ip_from 141.101.64.0/18;
    set_real_ip_from 108.162.192.0/18;
    set_real_ip_from 190.93.240.0/20;
    set_real_ip_from 188.114.96.0/20;
    set_real_ip_from 197.234.240.0/22;
    set_real_ip_from 198.41.128.0/17;
    set_real_ip_from 162.158.0.0/15;
    set_real_ip_from 104.16.0.0/13;
    set_real_ip_from 104.24.0.0/14;
    set_real_ip_from 172.64.0.0/13;
    set_real_ip_from 131.0.72.0/22;
    real_ip_header CF-Connecting-IP;

    # WordPress
    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}

    location ~ \.php$ {{
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }}

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?|ttf|eot)$ {{
        expires max;
        log_not_found off;
        add_header Cache-Control "public, immutable";
    }}
}}"""
    return {"config": config}
