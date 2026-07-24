from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.site import Site as SiteModel, SharedDatabase as SharedDatabaseModel
from typing import List, Any
import random
import string
import time
import uuid
import os
import re
import mysql.connector

router = APIRouter()


def _shared_db_for_site(db: Session, site: SiteModel):
    return db.query(SharedDatabaseModel).filter(SharedDatabaseModel.id == site.shared_db_id).first()


def _admin_conn(shared_db: SharedDatabaseModel):
    if not shared_db:
        raise HTTPException(status_code=404, detail="未找到共享数据库凭据")
    return mysql.connector.connect(
        host=shared_db.db_host, port=shared_db.db_port,
        user=shared_db.db_user, password=shared_db.db_password, connect_timeout=5,
    )


def _get_admin_shared_db(db: Session):
    s = db.query(SharedDatabaseModel).filter(SharedDatabaseModel.status == "active").first()
    return s or db.query(SharedDatabaseModel).first()


@router.get("/list", response_model=List[Any])
def list_databases(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    sites = db.query(SiteModel).all()
    results = []
    for site in sites:
        shared_db = _shared_db_for_site(db, site)
        if shared_db:
            results.append({
                "site_id": site.id, "domain": site.domain,
                "db_name": site.db_name or shared_db.db_name,
                "db_user": site.db_user or shared_db.db_user,
                "db_password": site.db_password or shared_db.db_password,
                "db_permission": site.db_permission or "site_only",
                "created_at": site.created_at.strftime("%Y-%m-%d %H:%M:%S") if site.created_at else "N/A",
                "table_prefix": site.table_prefix,
            })
    return results


@router.get("/admin-credentials")
def get_admin_db_credentials(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    shared_db = _get_admin_shared_db(db)
    if not shared_db:
        raise HTTPException(status_code=404, detail="No active shared database found")
    return {"db_name": shared_db.db_name, "db_user": shared_db.db_user, "db_password": shared_db.db_password}


def _update_wp_config_db(site, password=None, user=None, name=None, host=None):
    config_path = os.path.join(site.root_path, "wp-config.php")
    if not os.path.exists(config_path):
        return False
    with open(config_path, "r", encoding="utf-8") as f:
        c = f.read()

    def set_const(key, val):
        nonlocal c
        c = re.sub(rf"define\s*\(\s*['\"]{key}['\"]\s*,\s*[^)]+\)\s*;",
                    f"define( '{key}', '{val}' );", c)
    if password is not None: set_const("DB_PASSWORD", password)
    if user is not None: set_const("DB_USER", user)
    if name is not None: set_const("DB_NAME", name)
    if host is not None: set_const("DB_HOST", host)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(c)
    return True


@router.post("/set-permission/{site_id}")
def set_db_permission(site_id: int, permission: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if permission not in ["site_only", "all_dbs"]:
        raise HTTPException(status_code=400, detail="Invalid permission type")
    if not site.db_user or not site.db_name:
        raise HTTPException(status_code=400, detail="站点缺少独立的数据库用户")
    shared_db = _shared_db_for_site(db, site)
    try:
        conn = _admin_conn(shared_db); cur = conn.cursor()
        try:
            cur.execute(f"REVOKE ALL PRIVILEGES ON *.* FROM '{site.db_user}'@'localhost'")
        except Exception:
            pass
        if permission == "all_dbs":
            cur.execute(f"GRANT ALL PRIVILEGES ON *.* TO '{site.db_user}'@'localhost'")
        else:
            cur.execute(f"GRANT ALL PRIVILEGES ON `{site.db_name}`.* TO '{site.db_user}'@'localhost'")
        cur.execute("FLUSH PRIVILEGES"); conn.commit(); cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"修改权限失败: {e}")
    site.db_permission = permission
    db.commit()
    return {"success": True, "permission": permission}


@router.post("/change-password/{site_id}")
def change_db_password(site_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if not site.db_user:
        raise HTTPException(status_code=400, detail="站点缺少独立的数据库用户")
    shared_db = _shared_db_for_site(db, site)
    new_password = "".join(random.choices(string.ascii_letters + string.digits, k=20))
    try:
        conn = _admin_conn(shared_db); cur = conn.cursor()
        try:
            cur.execute(f"ALTER USER '{site.db_user}'@'localhost' IDENTIFIED BY '{new_password}'")
        except Exception:
            cur.execute(f"CREATE USER '{site.db_user}'@'localhost' IDENTIFIED BY '{new_password}'")
        cur.execute(f"GRANT ALL PRIVILEGES ON `{site.db_name}`.* TO '{site.db_user}'@'localhost'")
        cur.execute("FLUSH PRIVILEGES"); conn.commit(); cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"修改密码失败: {e}")
    site.db_password = new_password
    db.commit()
    try:
        _update_wp_config_db(site, password=new_password)
    except Exception as e:
        print(f"更新 wp-config 密码失败 {site.domain}: {e}")
    return {"success": True, "new_password": new_password}


@router.delete("/{site_id}")
def delete_database(site_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    shared_db = _shared_db_for_site(db, site)
    dropped = []
    try:
        conn = _admin_conn(shared_db); cur = conn.cursor()
        if site.db_name:
            cur.execute(f"DROP DATABASE IF EXISTS `{site.db_name}`"); dropped.append(site.db_name)
        if site.db_user:
            try:
                cur.execute(f"DROP USER IF EXISTS '{site.db_user}'@'localhost'"); dropped.append(site.db_user)
            except Exception:
                pass
        cur.execute("FLUSH PRIVILEGES"); conn.commit(); cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除数据库失败: {e}")
    site.db_name = None; site.db_user = None; site.db_password = None
    db.commit()
    return {"success": True, "message": f"已删除: {', '.join(dropped)}"}


# phpMyAdmin SSO
pma_sso_tokens = {}


@router.get("/pma-jump/{site_id}")
def get_pma_jump_url(site_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    shared_db = _shared_db_for_site(db, site)
    if not shared_db:
        raise HTTPException(status_code=404, detail="Shared database not found")
    token = str(uuid.uuid4())
    pma_sso_tokens[token] = {
        "db_user": site.db_user or shared_db.db_user,
        "db_password": site.db_password or shared_db.db_password,
        "db_host": shared_db.db_host, "db_port": shared_db.db_port,
        "db_name": site.db_name or shared_db.db_name,
        "expires_at": time.time() + 300,
    }
    target_db = site.db_name or shared_db.db_name
    return {"url": f"/phpmyadmin/index.php?pma_token={token}&db={target_db}"}


@router.get("/pma-sso-verify/{token}")
def verify_pma_token(token: str):
    if token not in pma_sso_tokens:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    data = pma_sso_tokens[token]
    if time.time() > data["expires_at"]:
        del pma_sso_tokens[token]
        raise HTTPException(status_code=403, detail="Token expired")
    return data


@router.post("/optimize")
def optimize_database(db_name: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Run OPTIMIZE TABLE on every table in db_name."""
    shared_db = _get_admin_shared_db(db)
    if not shared_db:
        raise HTTPException(status_code=500, detail="无可用数据库凭据")
    try:
        conn = _admin_conn(shared_db); cur = conn.cursor()
        cur.execute(f"SHOW TABLES FROM `{db_name}`")
        tables = [r[0] for r in cur.fetchall()]
        results = []
        for t in tables:
            cur.execute(f"OPTIMIZE TABLE `{db_name}`.`{t}`")
            res = cur.fetchone()
            results.append({"table": t, "status": (res[3] if res else "OK")})
        cur.close(); conn.close()
        return {"success": True, "message": f"已对 {db_name} 的 {len(tables)} 张表执行 OPTIMIZE TABLE", "details": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"优化失败: {e}")


@router.post("/slow-query/toggle")
def toggle_slow_query(enabled_in: Any, long_query_time: float = 2.0, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Enable/disable MariaDB slow query log via SET GLOBAL."""
    enabled = enabled_in.get("enabled") if isinstance(enabled_in, dict) else bool(enabled_in)
    shared_db = _get_admin_shared_db(db)
    try:
        conn = _admin_conn(shared_db); cur = conn.cursor()
        cur.execute(f"SET GLOBAL slow_query_log = '{"ON" if enabled else "OFF"}'")
        if enabled:
            cur.execute(f"SET GLOBAL long_query_time = {float(long_query_time)}")
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换慢查询日志失败: {e}")
    return {"success": True, "enabled": enabled, "message": f"慢查询日志已 {'开启' if enabled else '关闭'}"}


@router.get("/slow-queries")
def get_slow_queries(limit: int = 50, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Parse the MariaDB slow query log file (real entries)."""
    shared_db = _get_admin_shared_db(db)
    log_file = None
    try:
        conn = _admin_conn(shared_db); cur = conn.cursor()
        cur.execute("SHOW VARIABLES LIKE 'slow_query_log_file'")
        row = cur.fetchone()
        if row:
            log_file = row[1]
        cur.close(); conn.close()
    except Exception:
        pass
    entries = []
    if log_file and os.path.exists(log_file):
        try:
            with open(log_file, "r", errors="ignore") as f:
                content = f.read()
            blocks = content.split("# Time:")[1:]
            for b in blocks[-limit:]:
                lines = b.strip().splitlines()
                ts = lines[0].strip() if lines else ""
                qt = ""; query = ""
                for ln in lines[1:]:
                    if "Query_time:" in ln:
                        qt = ln.split("Query_time:")[1].split()[0]
                    elif ln.startswith("#"):
                        continue
                    else:
                        query += ln.strip() + " "
                if query.strip():
                    entries.append({"timestamp": ts, "execution_time": qt, "query": query.strip()[:500]})
        except Exception:
            pass
    return entries


@router.get("/tables/{db_name}")
def get_table_status(db_name: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Real table status via SHOW TABLE STATUS."""
    shared_db = _get_admin_shared_db(db)
    try:
        conn = _admin_conn(shared_db); cur = conn.cursor()
        cur.execute(f"SHOW TABLE STATUS FROM `{db_name}`")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        cur.close(); conn.close()
        result = []
        for r in rows:
            d = dict(zip(cols, r))
            result.append({
                "name": d.get("Name"), "engine": d.get("Engine"),
                "rows": d.get("Rows"),
                "data_length": d.get("Data_length", 0),
                "index_length": d.get("Index_length", 0),
                "data_free": d.get("Data_free", 0),
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表状态失败: {e}")
