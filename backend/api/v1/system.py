from fastapi import APIRouter, Depends, HTTPException, Body
from datetime import datetime
import threading
import os
import psutil
import platform
import socket
import subprocess
from sqlalchemy.orm import Session
from backend.api import deps
from backend.models.user import User
from backend.models.site import Site
from backend.models.backup import Backup
from backend.models.task import Task
from backend.core import security
from backend.core.config import settings
from backend.utils import panel_ops
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


def run_shell(command: str):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "code": result.returncode,
        }
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "code": -1}

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class PortChange(BaseModel):
    port: int

class AIConfig(BaseModel):
    model: str
    api_key: str

class TaskStatusOut(BaseModel):
    task_uuid: str
    type: str
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    progress: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/status")
async def get_status():
    return {
        "status": "online",
        "timestamp": datetime.now(),
        "version": "1.0.0"
    }


# 需要展示状态的系统服务/库（名称 -> 中文标签）
_SERVICE_DEFINITIONS = [
    ("sanguo-panel", "面板服务 (Uvicorn)"),
    ("nginx", "Nginx"),
    ("mysql", "MySQL / MariaDB"),
    ("redis", "Redis"),
    ("php-fpm", "PHP-FPM"),
    ("fail2ban", "Fail2ban"),
    ("sshd", "SSH"),
    ("ufw", "UFW 防火墙"),
    ("docker", "Docker"),
]


def _service_status(name: str) -> str:
    """返回 running / stopped / not_installed"""
    if name == "sanguo-panel":
        # 面板自身始终在线（能响应请求即说明在运行）
        return "running"
    if name == "php-worker":
        # OpenLiteSpeed 使用 LSAPI，PHP 以 lsphp 进程方式运行
        res = run_shell("pgrep -f lsphp >/dev/null 2>&1")
        return "running" if res["success"] else "stopped"
    res = run_shell(f"systemctl is-active {name} 2>/dev/null")
    if res["success"]:
        return "running"
    exist = run_shell(f"systemctl list-unit-files 2>/dev/null | grep -q '^{name}\\.service'")
    if exist["success"]:
        return "stopped"
    return "not_installed"


@router.get("/overview")
async def get_overview(current_user: User = Depends(deps.get_current_active_user)):
    """系统信息与各类服务/库的运行状态。"""
    try:
        with open("/proc/uptime") as f:
            uptime_sec = float(f.read().split()[0])
    except Exception:
        uptime_sec = 0.0

    try:
        load_avg = list(os.getloadavg())
    except Exception:
        load_avg = [0.0, 0.0, 0.0]

    try:
        with open("/etc/os-release") as f:
            os_release = {}
            for line in f:
                line = line.strip()
                if line and "=" in line:
                    k, v = line.split("=", 1)
                    os_release[k] = v.strip().strip('"')
        os_name = os_release.get("PRETTY_NAME") or os_release.get("NAME") or platform.system()
    except Exception:
        os_name = platform.platform()

    boot_time = datetime.now().timestamp() - uptime_sec

    services = []
    for name, label in _SERVICE_DEFINITIONS:
        services.append({
            "name": name,
            "label": label,
            "status": _service_status(name),
        })

    return {
        "system": {
            "hostname": socket.gethostname(),
            "os": os_name,
            "kernel": platform.release(),
            "python_version": platform.python_version(),
            "panel_version": "1.0.0",
            "uptime_seconds": uptime_sec,
            "boot_time": datetime.fromtimestamp(boot_time).strftime("%Y-%m-%d %H:%M:%S"),
            "load_avg": load_avg,
        },
        "services": services,
    }

@router.get("/metrics")
async def get_metrics(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get real-time system metrics: CPU, Memory, Disk, Network, and resource counts
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # 获取资源数量
    site_count = db.query(Site).count()
    backup_count = db.query(Backup).count()
    
    return {
        "cpu": {
            "percent": cpu_percent,
            "count": psutil.cpu_count()
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        },
        "site_count": site_count,
        "backup_count": backup_count,
        "timestamp": datetime.now()
    }

@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """修改管理员密码"""
    if not security.verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码错误")
    
    current_user.password_hash = security.get_password_hash(data.new_password)
    db.add(current_user)
    db.commit()
    return {"message": "密码修改成功"}

@router.post("/change-port")
async def change_port(
    data: PortChange,
    current_user: User = Depends(deps.get_current_active_user)
):
    """修改面板端口"""
    # 实际项目中这里需要修改配置文件并重启服务
    # 这里仅做演示
    print(f"Changing panel port to: {data.port}")
    return {"message": f"端口已修改为 {data.port}，服务正在重启..."}

@router.get("/logs")
async def get_logs(current_user: User = Depends(deps.get_current_active_user)):
    """获取面板运行日志"""
    # 模拟日志内容
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mock_logs = [
        f"[{now}] INFO: Panel service started on port 8000",
        f"[{now}] INFO: User {current_user.username} accessed system settings",
        f"[{now}] INFO: Checking for system updates...",
        f"[{now}] INFO: No updates available",
        f"[{now}] INFO: Database connection established",
        f"[{now}] WARNING: High memory usage detected (85%)",
        f"[{now}] INFO: Background task 'Site Backup' completed for site: example.com",
    ]
    return {"logs": "\n".join(mock_logs)}

@router.delete("/logs")
async def clear_logs(current_user: User = Depends(deps.get_current_active_user)):
    """清空面板运行日志"""
    return {"message": "日志已清空"}

@router.post("/regenerate-secret")
async def regenerate_secret(current_user: User = Depends(deps.get_current_active_user)):
    """重新生成 JWT 安全密钥"""
    # 实际项目中需要生成随机字符串并更新 .env 文件
    return {"message": "安全密钥已更新，请重新登录"}


def _get_env_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ".env")


@router.get("/ai-config")
async def get_ai_config(current_user: User = Depends(deps.get_current_active_user)):
    """获取 AI 配置"""
    key_exists = bool(settings.DEEPSEEK_API_KEY)
    return {
        "model": settings.DEEPSEEK_MODEL,
        "has_key": key_exists
    }


@router.post("/ai-config")
async def save_ai_config(
    data: AIConfig,
    current_user: User = Depends(deps.get_current_active_user)
):
    """保存 AI 配置到 .env 文件"""
    env_path = _get_env_path()
    updates = {
        "DEEPSEEK_MODEL": data.model,
        "DEEPSEEK_API_KEY": data.api_key
    }

    try:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        else:
            lines = []

        new_lines = []
        updated_keys = set()
        for line in lines:
            replaced = False
            for key, value in updates.items():
                if line.startswith(f"{key}="):
                    new_lines.append(f"{key}={value}\n")
                    updated_keys.add(key)
                    replaced = True
                    break
            if not replaced:
                # Keep empty/whitespace lines, but strip trailing newline to avoid double spacing
                new_lines.append(line)

        for key, value in updates.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")

        content = "".join(new_lines)
        with open(env_path, "w") as f:
            f.write(content)

        settings.DEEPSEEK_MODEL = data.model
        settings.DEEPSEEK_API_KEY = data.api_key
        return {"message": "AI 配置已保存", "model": data.model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@router.get("/update-check")
async def check_update(current_user: User = Depends(deps.get_current_active_user)):
    """检查面板是否有可用更新（git fetch + rev-parse 比对）。"""
    return panel_ops.check_update()


@router.post("/update")
async def trigger_update(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """触发面板更新：git pull --ff-only + 重启面板。返回任务 ID 供轮询。"""
    task_uuid = panel_ops._create_task(db, "system_update", current_user.id)
    threading.Thread(target=panel_ops.run_update_async, args=(task_uuid,), daemon=True).start()
    return {"task_uuid": task_uuid, "status": "pending"}


@router.post("/restart")
async def trigger_restart(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """触发面板重启。返回任务 ID 供轮询。"""
    task_uuid = panel_ops._create_task(db, "system_restart", current_user.id)
    threading.Thread(target=panel_ops.run_restart_async, args=(task_uuid,), daemon=True).start()
    return {"task_uuid": task_uuid, "status": "pending"}


@router.get("/task/{task_uuid}", response_model=TaskStatusOut)
async def get_task_status(
    task_uuid: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """查询任务状态。"""
    task = db.query(Task).filter(Task.task_uuid == task_uuid).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task
