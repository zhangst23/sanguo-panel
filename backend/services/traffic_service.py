"""
站点流量分析服务。

说明：PyPI 上的 logparser(0.8.4) 是日志「格式」解析库（loghub），并不提供
访客统计 / 热门页面这类 Web 分析能力。因此这里实现一个高性能、开箱即用的
访问日志分析器，行为对齐需求描述：性能好（流式逐行解析、时钟序可提前结束）、
自动排除爬虫（按 User-Agent 命中常见 bot 特征）。

当日访客数量会写入本地 SQLite（backend/data/traffic.db）的 traffic_daily 表，
表不存在时自动创建。
"""
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

# ---------- 路径 ----------
SERVICES_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SERVICES_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'traffic.db')

# ---------- 日志解析 ----------
# nginx / Apache combined 格式
LOG_RE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<proto>[^"]*)"\s+'
    r'(?P<status>\d{3})\s+(?P<bytes>\S+)\s+'
    r'"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)"'
)
# 兼容 common 格式（无 referer / user-agent）
LOG_RE_COMMON = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<proto>[^"]*)"\s+'
    r'(?P<status>\d{3})\s+(?P<bytes>\S+)'
)

TIME_FMT = "%d/%b/%Y:%H:%M:%S %z"

BOT_PATTERNS = (
    'bot', 'spider', 'crawl', 'slurp', 'bingpreview', 'googlebot', 'yandex',
    'baidu', 'facebookexternalhit', 'semrush', 'ahrefs', 'mj12', 'dotbot',
    'petalbot', 'applebot', 'crawler', 'archive', 'feed', 'monitor',
    'python-requests', 'curl', 'wget', 'go-http', 'httpclient', 'scrapy',
    'zgrab', 'masscan', 'nmap', 'nikto', 'wpscan', 'headless', 'phantom',
)

STATIC_EXT = {
    '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp',
    '.woff', '.woff2', '.ttf', '.eot', '.map', '.json', '.xml', '.txt',
    '.bmp', '.pdf', '.zip', '.gz', '.webmanifest', '.ogg', '.mp3', '.mp4',
}


def _match(line):
    m = LOG_RE.match(line)
    if m:
        return m
    return LOG_RE_COMMON.match(line)


def _is_bot(ua):
    if not ua:
        return False
    u = ua.lower()
    return any(p in u for p in BOT_PATTERNS)


def _normalize_path(path):
    q = path.find('?')
    if q != -1:
        path = path[:q]
    f = path.find('#')
    if f != -1:
        path = path[:f]
    return path


def _is_static(path):
    _, ext = os.path.splitext(path)
    return ext.lower() in STATIC_EXT


def _parse_time(s):
    try:
        return datetime.strptime(s, TIME_FMT)
    except Exception:
        return None


def _bytes(val):
    if not val or val == '-':
        return 0
    try:
        return int(val)
    except ValueError:
        return 0


# ---------- 日志路径定位 ----------
def resolve_access_log(domain, root_path=None):
    """根据站点域名/根目录定位 access.log，找不到返回 None。"""
    override = os.environ.get('ACCESS_LOG_PATH')
    if override and os.path.isfile(override):
        return override
    candidates = []
    if domain:
        candidates += [
            f"/usr/local/lsws/logs/{domain}.access.log",
            f"/var/log/nginx/{domain}.access.log",
            f"/var/www/{domain}/logs/access.log",
            f"/www/wwwroot/{domain}/log/access.log",
            f"/home/wwwroot/{domain}/logs/access.log",
        ]
    if root_path:
        candidates += [
            os.path.join(root_path, 'logs', 'access.log'),
            os.path.join(root_path, 'log', 'access.log'),
        ]
    candidates += [
        "/usr/local/lsws/logs/access.log",
        "/var/log/nginx/access.log",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def get_site_log(site_id):
    """返回 (log_path, site) 或 (None, None)。"""
    from backend.core.database import SessionLocal
    from backend.models.site import Site
    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == site_id).first()
    finally:
        db.close()
    if not site:
        return None, None
    log = resolve_access_log(site.domain, getattr(site, 'root_path', None))
    return log, site


# ---------- 解析 ----------
def analyze_day(log_path, target_date):
    """解析 target_date 当天访问，返回访客/请求/带宽/小时分布/热门页面。"""
    visitors_set = set()
    requests = 0
    bandwidth = 0
    hourly_req = [0] * 24
    hourly_vis = [set() for _ in range(24)]
    hourly_bw = [0.0] * 24
    page_hits = Counter()
    page_vis = defaultdict(set)

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = _match(line)
            if not m:
                continue
            dt = _parse_time(m.group('time'))
            if dt is None:
                continue
            d = dt.date()
            if d < target_date:
                continue
            if d > target_date:
                # 日志按时间顺序追加，超过当天即可提前结束
                break
            if _is_bot(m.group('ua')):
                continue
            ip = m.group('ip')
            visitors_set.add(ip)
            requests += 1
            b = _bytes(m.group('bytes'))
            bandwidth += b
            hour = dt.hour
            hourly_req[hour] += 1
            hourly_vis[hour].add(ip)
            hourly_bw[hour] += b / (1024 * 1024)
            path = _normalize_path(m.group('path'))
            method = m.group('method').upper()
            if method in ('GET', 'POST') and path not in ('', '-') and not _is_static(path):
                page_hits[path] += 1
                page_vis[path].add(ip)

    top = page_hits.most_common(10)
    top_pages = [{
        'rank': i + 1,
        'path': p,
        'hits': h,
        'visitors': len(page_vis[p]),
    } for i, (p, h) in enumerate(top)]

    return {
        'visitors': len(visitors_set),
        'requests': requests,
        'bandwidth': round(bandwidth / (1024 * 1024), 2),
        'hourly_requests': hourly_req,
        'hourly_visitors': [len(s) for s in hourly_vis],
        'hourly_bandwidth': [round(x, 2) for x in hourly_bw],
        'top_pages': top_pages,
    }


def analyze_all_days(log_path, site_id, limit_days=30):
    """遍历整份日志，按天聚合并写库；返回最近 limit_days 天数据。"""
    day_vis = defaultdict(set)
    day_req = defaultdict(int)
    day_bw = defaultdict(int)
    min_date = (datetime.now() - timedelta(days=limit_days)).date()

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = _match(line)
            if not m:
                continue
            dt = _parse_time(m.group('time'))
            if dt is None:
                continue
            if _is_bot(m.group('ua')):
                continue
            d = dt.date()
            if d < min_date:
                continue
            day_vis[d].add(m.group('ip'))
            day_req[d] += 1
            day_bw[d] += _bytes(m.group('bytes'))

    for d in day_vis:
        upsert_daily(
            site_id, d.strftime('%Y-%m-%d'),
            len(day_vis[d]), day_req[d], round(day_bw[d] / (1024 * 1024), 2),
        )
    return get_daily_range(site_id, limit_days)


# ---------- SQLite ----------
def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = __import__('sqlite3').connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS traffic_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            visitors INTEGER NOT NULL DEFAULT 0,
            requests INTEGER NOT NULL DEFAULT 0,
            bandwidth REAL NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(site_id, date)
        )"""
    )
    return conn


def upsert_daily(site_id, date, visitors, requests, bandwidth):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = _conn()
    try:
        conn.execute(
            """INSERT INTO traffic_daily (site_id, date, visitors, requests, bandwidth, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(site_id, date) DO UPDATE SET
                 visitors=excluded.visitors,
                 requests=excluded.requests,
                 bandwidth=excluded.bandwidth,
                 updated_at=excluded.updated_at""",
            (site_id, date, visitors, requests, bandwidth, now),
        )
        conn.commit()
    finally:
        conn.close()


def get_daily_range(site_id, days=30):
    conn = _conn()
    try:
        cur = conn.execute(
            "SELECT date, visitors, requests, bandwidth FROM traffic_daily "
            "WHERE site_id=? AND date >= date('now', ?) ORDER BY date ASC",
            (site_id, f'-{days - 1} days'),
        )
        return [{
            'date': r[0], 'visitors': r[1], 'requests': r[2], 'bandwidth': r[3]
        } for r in cur.fetchall()]
    finally:
        conn.close()
