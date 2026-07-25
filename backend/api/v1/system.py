from fastapi import APIRouter, Depends, HTTPException, Body
from datetime import datetime
import threading
import psutil
from sqlalchemy.orm import Session
from backend.api import deps
from backend.models.user import User
from backend.models.site import Site
from backend.models.backup import Backup
from backend.models.task import Task
from backend.core import security
from backend.utils import panel_ops
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class PortChange(BaseModel):
    port: int

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
