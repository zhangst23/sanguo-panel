from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from backend.api import deps
from backend.models.user import User
from backend.utils import monitor_utils
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/realtime")
async def get_realtime_metrics(current_user: User = Depends(deps.get_current_active_user)):
    """获取实时系统指标"""
    metrics = monitor_utils.get_system_metrics()
    return metrics

@router.get("/history")
async def get_history_metrics(
    metric_type: str = "cpu", 
    range_hours: int = 1,
    current_user: User = Depends(deps.get_current_active_user)
):
    """获取历史监控数据 (模拟数据，待时序数据库实现)"""
    now = datetime.now()
    data = []
    points = 60 # 返回60个点
    interval = (range_hours * 3600) / points
    
    import random
    for i in range(points):
        ts = now - timedelta(seconds=i * interval)
        val = random.uniform(10, 80) if metric_type == "cpu" else random.uniform(30, 90)
        data.append({
            "time": ts.strftime("%H:%M:%S"),
            "value": round(val, 2)
        })
    
    return sorted(data, key=lambda x: x["time"])

@router.get("/web-stats")
async def get_web_stats(current_user: User = Depends(deps.get_current_active_user)):
    """获取 Web 请求统计 (OLS 数据)"""
    return monitor_utils.get_ols_stats()

@router.get("/db-stats")
async def get_db_stats(current_user: User = Depends(deps.get_current_active_user)):
    """获取数据库统计信息"""
    return monitor_utils.get_mariadb_stats()

@router.get("/redis-stats")
async def get_redis_stats(current_user: User = Depends(deps.get_current_active_user)):
    """获取 Redis 统计信息"""
    return monitor_utils.get_redis_stats()
