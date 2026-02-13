from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.utils.site_utils import update_wp_config_redis, update_wp_hide_login, fix_site_permissions, update_wp_xmlrpc
from backend.models.site import Site
from backend.models.backup import Backup as BackupModel, BackupSchedule as BackupScheduleModel
from backend.models.task import Task as TaskModel, TaskStatus
from backend.schemas.backup import Backup, BackupCreate, BackupSchedule, BackupScheduleCreate
from backend.utils.backup_utils import create_site_backup, restore_site_backup
from backend.core import security as security_utils
from backend.models.user import User
from typing import List, Optional
import subprocess
import os
import uuid

router = APIRouter()

# --- WordPress Security Endpoints ---

@router.post("/wordpress/hide-login")
def set_wp_hide_login(
    site_id: int,
    path: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    site.wp_hide_login_path = path
    db.commit()
    
    if update_wp_hide_login(site):
        return {"success": True, "path": path}
    else:
        raise HTTPException(status_code=500, detail="Failed to update WordPress configuration")

@router.post("/wordpress/toggle-xmlrpc")
def toggle_wp_xmlrpc(
    site_id: int,
    enable: bool,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Invert 'enable' logic because the frontend sends 'enable=true' to DISABLE it (based on UI context)
    # Actually, let's look at the UI again.
    # Frontend: handleBatchAction('toggle-xmlrpc', { enable: true }) -> "一键禁用"
    # So enable=true means WE WANT TO DISABLE XML-RPC.
    # The utils function update_wp_xmlrpc(site, enabled) expects enabled=False to disable it.
    
    if update_wp_xmlrpc(site, enabled=not enable):
        return {"success": True}
    else:
        raise HTTPException(status_code=500, detail="Failed to update XML-RPC configuration")

@router.post("/wordpress/fix-permissions")
def fix_wp_permissions(
    site_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    if fix_site_permissions(site):
        return {"success": True}
    else:
        raise HTTPException(status_code=500, detail="Failed to fix permissions")

# --- Admin Security Endpoints ---

@router.post("/password")
def change_password(
    old_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not security_utils.verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    current_user.password_hash = security_utils.get_password_hash(new_password)
    db.commit()
    return {"success": True}

@router.get("/settings")
def get_security_settings(current_user=Depends(get_current_user)):
    # This would normally come from a database table for settings
    return {
        "tokenExpiry": 1440,
        "twoFactor": False,
        "ipWhitelist": ""
    }

@router.post("/settings")
def update_security_settings(settings: dict, current_user=Depends(get_current_user)):
    # Mock update
    return {"success": True}

# --- System Security (Firewall & Fail2ban) ---

def run_shell(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "code": result.returncode
        }
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "code": -1}

# --- Security Endpoints ---

@router.get("/firewall/status")
def get_firewall_status(current_user=Depends(get_current_user)):
    if os.name == 'nt':
        return {"active": True, "rules": [{"port": "80", "protocol": "tcp", "description": "HTTP"}]}
    
    res = run_shell("systemctl is-active firewalld")
    active = res["stdout"].strip() == "active"
    
    rules = []
    if active:
        res = run_shell("firewall-cmd --list-ports")
        ports = res["stdout"].strip().split()
        for p in ports:
            port, proto = p.split('/')
            rules.append({"port": port, "protocol": proto})
            
    return {"active": active, "rules": rules}

@router.post("/firewall/toggle")
def toggle_firewall(enable: bool, current_user=Depends(get_current_user)):
    if os.name == 'nt': return {"success": True}
    action = "start" if enable else "stop"
    run_shell(f"systemctl {action} firewalld")
    run_shell(f"systemctl {'enable' if enable else 'disable'} firewalld")
    return {"success": True}

# 全局 Mock 数据，用于在 Windows 环境下模拟状态变更
F2B_MOCK_DATA = {
    "active": True,
    "banned_ips": ["1.2.3.4"],
    "config": {"bantime": 600, "findtime": 600, "maxretry": 5}
}

@router.get("/fail2ban/status")
def get_fail2ban_status(current_user=Depends(get_current_user)):
    if os.name == 'nt': 
        return F2B_MOCK_DATA
    
    res = run_shell("systemctl is-active fail2ban")
    active = res["stdout"].strip() == "active"
    
    banned_ips = []
    config = {"bantime": 600, "findtime": 600, "maxretry": 5}
    
    if active:
        # 获取所有 jail 的封禁 IP
        res = run_shell("fail2ban-client status")
        import re
        jails_match = re.search(r"Jail list:\s*(.*)", res["stdout"])
        if jails_match:
            jails = jails_match.group(1).replace(",", "").split()
            for jail in jails:
                res_jail = run_shell(f"fail2ban-client status {jail}")
                ip_match = re.search(r"Banned IP list:\s*(.*)", res_jail["stdout"])
                if ip_match:
                    ips = ip_match.group(1).split()
                    banned_ips.extend(ips)
        
        # 尝试读取基本配置 (从 jail.local 或 jail.conf)
        # 这里仅作示例，实际可能需要更复杂的解析
        res_config = run_shell("fail2ban-client get sshd bantime")
        if res_config["success"]:
            try:
                config["bantime"] = int(res_config["stdout"].strip())
            except: pass
            
    return {"active": active, "banned_ips": list(set(banned_ips)), "config": config}

@router.post("/fail2ban/ban")
def ban_ip(ip: str, current_user=Depends(get_current_user)):
    if os.name == 'nt': 
        if ip not in F2B_MOCK_DATA["banned_ips"]:
            F2B_MOCK_DATA["banned_ips"].append(ip)
        return {"success": True}
    # 默认封禁在 sshd jail 中，或者创建一个专门的 jail
    res = run_shell(f"fail2ban-client set sshd banip {ip}")
    if res["success"]:
        return {"success": True}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to ban IP: {res['stderr']}")

@router.post("/fail2ban/unban")
def unban_ip(ip: str, current_user=Depends(get_current_user)):
    if os.name == 'nt': 
        if ip in F2B_MOCK_DATA["banned_ips"]:
            F2B_MOCK_DATA["banned_ips"].remove(ip)
        return {"success": True}
    res = run_shell(f"fail2ban-client set sshd unbanip {ip}")
    if res["success"]:
        return {"success": True}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to unban IP: {res['stderr']}")

@router.post("/fail2ban/config")
def update_fail2ban_config(config: dict, current_user=Depends(get_current_user)):
    if os.name == 'nt': 
        F2B_MOCK_DATA["config"].update(config)
        return {"success": True}
    # config: { bantime: int, findtime: int, maxretry: int }
    bantime = config.get("bantime", 600)
    findtime = config.get("findtime", 600)
    maxretry = config.get("maxretry", 5)
    
    # 修改 fail2ban 配置通常需要修改文件并重启
    # 这里简写：直接使用 client 设置（部分设置支持热更新）
    run_shell(f"fail2ban-client set sshd bantime {bantime}")
    run_shell(f"fail2ban-client set sshd findtime {findtime}")
    run_shell(f"fail2ban-client set sshd maxretry {maxretry}")
    
    return {"success": True}

# --- Backup Endpoints ---

@router.get("/backups", response_model=List[Backup])
def list_backups(
    site_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(BackupModel)
    if site_id:
        query = query.filter(BackupModel.site_id == site_id)
    return query.order_by(BackupModel.created_at.desc()).all()

@router.post("/backups/create")
def create_backup(
    background_tasks: BackgroundTasks,
    target: str = "site",
    item_id: Optional[int] = None,
    include_db: bool = True,
    include_files: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if target == 'site' and item_id:
        site = db.query(Site).filter(Site.id == item_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        
        task_uuid = str(uuid.uuid4())
        new_task = TaskModel(
            task_uuid=task_uuid,
            type="backup",
            site_id=item_id,
            status=TaskStatus.pending,
            progress=0,
            message=f"Scheduled backup for {site.domain}",
            created_by=current_user.id
        )
        db.add(new_task)
        db.commit()

        background_tasks.add_task(create_site_backup, db, item_id, task_uuid, include_db, include_files)
        return {"success": True, "message": "Backup task started", "task_uuid": task_uuid}
    
    elif target == 'all':
        sites = db.query(Site).all()
        if not sites:
            return {"success": True, "message": "No sites to backup"}
        
        task_uuids = []
        for site in sites:
            task_uuid = str(uuid.uuid4())
            new_task = TaskModel(
                task_uuid=task_uuid,
                type="backup",
                site_id=site.id,
                status=TaskStatus.pending,
                progress=0,
                message=f"Scheduled full backup for {site.domain}",
                created_by=current_user.id
            )
            db.add(new_task)
            task_uuids.append(task_uuid)
            background_tasks.add_task(create_site_backup, db, site.id, task_uuid, include_db, include_files)
        
        db.commit()
        return {"success": True, "message": f"Backup tasks started for {len(sites)} sites", "task_uuids": task_uuids}
    
    return {"success": False, "message": "Unsupported backup target"}

@router.get("/backups/schedule", response_model=List[BackupSchedule])
def get_backup_schedules(
    site_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(BackupScheduleModel)
    if site_id:
        query = query.filter(BackupScheduleModel.site_id == site_id)
    return query.all()

@router.post("/backups/schedule")
def update_backup_schedule(
    schedule_in: BackupScheduleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Check if schedule exists for this site
    schedule = db.query(BackupScheduleModel).filter(
        BackupScheduleModel.site_id == schedule_in.site_id
    ).first()
    
    if schedule:
        for key, value in schedule_in.dict().items():
            setattr(schedule, key, value)
    else:
        schedule = BackupScheduleModel(**schedule_in.dict())
        db.add(schedule)
    
    db.commit()
    return {"success": True}

@router.get("/backups/{backup_id}/download")
def download_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    backup = db.query(BackupModel).filter(BackupModel.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    if backup.file_path and os.path.exists(backup.file_path):
        return FileResponse(
            backup.file_path, 
            filename=backup.name,
            media_type='application/zip'
        )
    raise HTTPException(status_code=404, detail="Backup file not found on disk")
@router.delete("/backups/{backup_id}")
def delete_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    backup = db.query(BackupModel).filter(BackupModel.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    # Delete physical file
    try:
        if backup.file_path and os.path.exists(backup.file_path):
            os.remove(backup.file_path)
    except Exception as e:
        print(f"Failed to delete physical file: {e}")

    db.delete(backup)
    db.commit()
    return {"success": True}

@router.post("/backups/{backup_id}/restore")
def restore_backup(
    backup_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    backup = db.query(BackupModel).filter(BackupModel.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    if not backup.file_path or not os.path.exists(backup.file_path):
        raise HTTPException(status_code=404, detail="Backup file not found on disk")

    site = db.query(Site).filter(Site.id == backup.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Associated site not found")

    task_uuid = str(uuid.uuid4())
    new_task = TaskModel(
        task_uuid=task_uuid,
        type="restore",
        site_id=site.id,
        status=TaskStatus.pending,
        progress=0,
        message=f"Scheduled restore for {site.domain} from {backup.name}",
        created_by=current_user.id
    )
    db.add(new_task)
    db.commit()

    background_tasks.add_task(restore_site_backup, db, backup.id, task_uuid)
    return {"success": True, "message": "Restore task started", "task_uuid": task_uuid}

@router.post("/migration/import")
def import_site(panel_type: str, file_path: str, current_user=Depends(get_current_user)):
    # Mock migration logic
    return {"success": True, "message": f"Starting migration from {panel_type}"}
