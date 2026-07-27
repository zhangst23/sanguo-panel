from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from backend.api import deps
from backend.models.user import User
from backend.utils import monitor_utils
from backend.services import traffic_service
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

@router.get("/traffic")
async def get_traffic_stats(
    range: str = "day",
    site_id: int = None,
    current_user: User = Depends(deps.get_current_active_user)
):
    """获取站点流量统计（基于访问日志，当日访客写入 SQLite）。"""
    if not site_id:
        return _mock_traffic(range)
    log, _site = traffic_service.get_site_log(site_id)
    if not log:
        data = _mock_traffic(range)
        data["source"] = "mock"
        data["has_data"] = False
        return data
    today = datetime.now().date()
    if range == "month":
        rows = traffic_service.get_daily_range(site_id, 30)
        if not rows:
            rows = traffic_service.analyze_all_days(log, site_id, 30)
        return {
            "range": "month",
            "categories": [r["date"] for r in rows],
            "requests": [r["requests"] for r in rows],
            "visitors": [r["visitors"] for r in rows],
            "bandwidth": [r["bandwidth"] for r in rows],
            "source": "real",
            "has_data": bool(rows),
        }
    day = traffic_service.analyze_day(log, today)
    traffic_service.upsert_daily(
        site_id, today.strftime("%Y-%m-%d"),
        day["visitors"], day["requests"], day["bandwidth"],
    )
    return {
        "range": "day",
        "categories": [f"{h:02d}:00" for h in range(24)],
        "requests": day["hourly_requests"],
        "visitors": day["hourly_visitors"],
        "bandwidth": day["hourly_bandwidth"],
        "source": "real",
        "has_data": day["requests"] > 0,
    }


@router.get("/traffic-top-pages")
async def get_traffic_top_pages(
    site_id: int = None,
    current_user: User = Depends(deps.get_current_active_user)
):
    """获取站点热门页面 TOP 10（基于当日访问日志，自动排除爬虫）。"""
    if not site_id:
        return {"top_pages": _mock_top_pages(), "source": "mock"}
    log, _site = traffic_service.get_site_log(site_id)
    if not log:
        return {"top_pages": _mock_top_pages(), "source": "mock", "has_data": False}
    today = datetime.now().date()
    day = traffic_service.analyze_day(log, today)
    return {
        "top_pages": day["top_pages"],
        "source": "real",
        "has_data": bool(day["top_pages"]),
    }


def _mock_traffic(range):
    import random
    now = datetime.now()
    if range == "month":
        points = 30
        categories, requests, visitors, bandwidth = [], [], [], []
        for i in range(points):
            d = now - timedelta(days=(points - 1 - i))
            categories.append(d.strftime("%m-%d"))
            requests.append(random.randint(2000, 12000))
            visitors.append(random.randint(500, 4000))
            bandwidth.append(round(random.uniform(50, 400), 1))
    else:
        points = 24
        categories, requests, visitors, bandwidth = [], [], [], []
        for i in range(points):
            h = now - timedelta(hours=(points - 1 - i))
            categories.append(f"{h.hour:02d}:00")
            requests.append(random.randint(100, 1500))
            visitors.append(random.randint(20, 400))
            bandwidth.append(round(random.uniform(2, 40), 1))
    return {
        "range": range,
        "categories": categories,
        "requests": requests,
        "visitors": visitors,
        "bandwidth": bandwidth,
    }


def _mock_top_pages():
    import random
    paths = [
        "/", "/about", "/products", "/blog", "/contact", "/shop",
        "/cart", "/checkout", "/login", "/sitemap.xml",
    ]
    return [{
        "rank": i + 1,
        "path": p,
        "hits": random.randint(50, 2000),
        "visitors": random.randint(20, 800),
    } for i, p in enumerate(paths)]
