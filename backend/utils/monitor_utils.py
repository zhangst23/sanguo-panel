import psutil
import os
import time
from datetime import datetime

def get_system_metrics():
    """获取系统基础指标"""
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "network": get_network_io(),
        "timestamp": datetime.now().isoformat()
    }

def get_network_io():
    """获取网络吞吐量"""
    net_io = psutil.net_io_counters()
    return {
        "sent": net_io.bytes_sent,
        "recv": net_io.bytes_recv
    }

def get_ols_stats():
    """
    解析 OpenLiteSpeed 统计信息
    实战中应读取 /tmp/lshttpd/.rtreport 或使用 OLS 管理接口
    """
    # 模拟 OLS 统计
    return {
        "qps": 15.4,
        "total_requests": 12580,
        "status_codes": [
            {"name": "2xx", "value": 11000},
            {"name": "3xx", "value": 800},
            {"name": "4xx", "value": 500},
            {"name": "5xx", "value": 280}
        ],
        "cache_hit_rate": 85.2,
        "ttfb": 118
    }

def get_mariadb_stats():
    """
    获取 MariaDB 性能指标
    需连接数据库查询 performance_schema
    """
    # 模拟数据库统计
    return {
        "avg_query_time": 0.042,
        "slow_queries": 8,
        "table_count": 1250,
        "alert": False # 超过 5000 时为 True
    }

def get_redis_stats():
    """
    获取 Redis 运行状态
    """
    # 模拟 Redis 统计
    return {
        "hit_rate": 94.5,
        "used_memory": "156MB",
        "keys": 4200
    }
