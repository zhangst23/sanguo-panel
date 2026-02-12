from fastapi import APIRouter, Depends
from datetime import datetime
import psutil
from backend.api import deps
from backend.models.user import User

router = APIRouter()

@router.get("/status")
async def get_status():
    return {
        "status": "online",
        "timestamp": datetime.now(),
        "version": "1.0.0"
    }

@router.get("/metrics")
async def get_metrics(current_user: User = Depends(deps.get_current_active_user)):
    """
    Get real-time system metrics: CPU, Memory, Disk, Network
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
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
        "timestamp": datetime.now()
    }
