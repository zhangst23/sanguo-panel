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
from datetime import datetime
import subprocess
import re
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
        return {
            "active": True,
            "rules": [
                {"port": "22", "protocol": "tcp", "description": "SSH"},
                {"port": "80", "protocol": "tcp", "description": "HTTP"},
                {"port": "443", "protocol": "tcp", "description": "HTTPS"},
            ]
        }

    res = run_shell("ufw status")
    stdout = res["stdout"]
    active = "Status: active" in stdout

    rules = []
    for line in stdout.splitlines():
        line = line.strip()
        # 形如 "22/tcp   ALLOW IN  Anywhere" 或 "22/tcp (v6)  ALLOW IN  Anywhere (v6)"
        m = re.match(r"^(\d+)/(tcp|udp)\b.*ALLOW", line)
        if m:
            rules.append({
                "port": m.group(1),
                "protocol": m.group(2),
                "description": "ALLOW",
            })
    return {"active": active, "rules": rules}

@router.post("/firewall/toggle")
def toggle_firewall(enable: bool, current_user=Depends(get_current_user)):
    if os.name == 'nt':
        return {"success": True}
    action = "enable" if enable else "disable"
    run_shell(f"ufw {action}")
    return {"success": True}

@router.post("/firewall/rule")
def add_firewall_rule(port: int, protocol: str = "tcp", comment: Optional[str] = None, current_user=Depends(get_current_user)):
    """开放指定端口（UFW），可选备注。"""
    if os.name == 'nt':
        return {"success": True}
    cmd = f"ufw allow {port}/{protocol}"
    if comment:
        safe = comment.replace('"', '')
        cmd += f' comment "{safe}"'
    run_shell(cmd)
    return {"success": True}

@router.post("/firewall/rule/delete")
def delete_firewall_rule(port: int, protocol: str = "tcp", current_user=Depends(get_current_user)):
    """删除指定端口规则（UFW）。"""
    if os.name == 'nt':
        return {"success": True}
    run_shell(f"ufw delete allow {port}/{protocol}")
    return {"success": True}

# 结构化封禁记录（内存存储，用于演示；真实环境由 fail2ban 客户端管理）
# 等级(level): permanent 永久封禁 / temp_24h 临时24h / temp_10m 临时10分钟 / ratelimit 限速
# 来源(source): web Web防护 / 404 404防御 / ssh SSH防护 / panel_scan 面板扫描防御 / manual 手动封禁
# 原因(reason): 触发封禁的具体说明；过期时间(expire_at): permanent=永久 / temp_*=计算得到的过期时间 / ratelimit=长期限速
F2B_BAN_RECORDS = [
    {"ip": "192.168.1.100", "level": "permanent", "source": "ssh", "count": 12, "banned_at": "2026-07-20 10:23", "reason": "SSH 暴力破解尝试", "expire_at": "永久", "paths": ["/wp-login.php", "/xmlrpc.php", "/admin", "/wp-admin"]},
    {"ip": "45.33.22.11", "level": "temp_24h", "source": "web", "count": 3, "banned_at": "2026-07-26 18:05", "reason": "触发 Web 访问频率限制", "expire_at": "2026-07-27 18:05", "paths": ["/", "/index.php", "/products", "/cart", "/checkout"]},
    {"ip": "10.0.0.45", "level": "temp_10m", "source": "404", "count": 7, "banned_at": "2026-07-27 09:41", "reason": "频繁请求不存在的页面 (404)", "expire_at": "2026-07-27 09:51", "paths": ["/nonexistent-1", "/missing-page", "/old-url", "/test", "/abc"]},
    {"ip": "8.8.8.8", "level": "ratelimit", "source": "panel_scan", "count": 2, "banned_at": "2026-07-27 11:12", "reason": "扫描面板登录入口", "expire_at": "长期限速", "paths": ["/wp-admin", "/admin", "/login", "/panel"]},
    {"ip": "203.0.113.7", "level": "permanent", "source": "manual", "count": 1, "banned_at": "2026-07-27 08:00", "reason": "管理员手动封禁", "expire_at": "永久", "paths": ["/"]},
]


# 人工启停覆盖：None 表示以系统实际状态为准，True/False 表示人工指定
F2B_ACTIVE_OVERRIDE = None


def _jail_for_source(source):
    return {
        "ssh": "sshd",
        "web": "nginx-limit-req",
        "404": "nginx-botsearch",
        "panel_scan": "sshd",
        "manual": "sshd",
    }.get(source, "sshd")


def _reason_for_source(source):
    return {
        "ssh": "SSH 暴力破解尝试",
        "web": "触发 Web 访问频率限制",
        "404": "频繁请求不存在的页面 (404)",
        "panel_scan": "扫描面板登录入口",
        "manual": "管理员手动封禁",
    }.get(source, "触发封禁规则")


def _expire_str(level, banned_at):
    from datetime import datetime, timedelta
    if level == "permanent":
        return "永久"
    if level == "ratelimit":
        return "长期限速"
    try:
        base = datetime.strptime(banned_at, "%Y-%m-%d %H:%M")
    except Exception:
        return "-"
    if level == "temp_24h":
        return (base + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    if level == "temp_10m":
        return (base + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
    return "-"


def _now_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@router.get("/fail2ban/status")
def get_fail2ban_status(current_user=Depends(get_current_user)):
    if os.name == 'nt':
        active = F2B_ACTIVE_OVERRIDE if F2B_ACTIVE_OVERRIDE is not None else True
        return {
            "active": active,
            "banned_ips": [r["ip"] for r in F2B_BAN_RECORDS],
            "config": {"bantime": 600, "findtime": 600, "maxretry": 5},
            "bans": F2B_BAN_RECORDS,
        }

    if F2B_ACTIVE_OVERRIDE is not None:
        active = F2B_ACTIVE_OVERRIDE
    else:
        res = run_shell("systemctl is-active fail2ban")
        active = res["stdout"].strip() == "active"

    config = {"bantime": 600, "findtime": 600, "maxretry": 5}

    if active:
        res_config = run_shell("fail2ban-client get sshd bantime")
        if res_config["success"]:
            try:
                config["bantime"] = int(res_config["stdout"].strip())
            except Exception:
                pass

    return {
        "active": active,
        "banned_ips": [r["ip"] for r in F2B_BAN_RECORDS],
        "config": config,
        "bans": F2B_BAN_RECORDS,
    }


@router.get("/fail2ban/bans")
def get_fail2ban_bans(current_user=Depends(get_current_user)):
    return {"bans": F2B_BAN_RECORDS}

@router.post("/fail2ban/ban")
def ban_ip(
    ip: str,
    level: str = "permanent",
    source: str = "manual",
    reason: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    """封禁指定 IP，并写入结构化记录（level/source/count/reason/expire_at）。"""
    if os.name != 'nt':
        jail = _jail_for_source(source)
        run_shell(f"fail2ban-client set {jail} banip {ip}")

    banned_at = _now_str()
    final_reason = reason or _reason_for_source(source)
    final_expire = _expire_str(level, banned_at)

    existing = next((r for r in F2B_BAN_RECORDS if r["ip"] == ip), None)
    if existing:
        existing["count"] += 1
        existing["level"] = level
        existing["source"] = source
        existing["banned_at"] = banned_at
        existing["reason"] = final_reason
        existing["expire_at"] = final_expire
    else:
        F2B_BAN_RECORDS.append({
            "ip": ip,
            "level": level,
            "source": source,
            "count": 1,
            "banned_at": banned_at,
            "reason": final_reason,
            "expire_at": final_expire,
        })
    return {"success": True, "bans": F2B_BAN_RECORDS}


@router.post("/fail2ban/unban")
def unban_ip(ip: str, current_user=Depends(get_current_user)):
    """解封指定 IP，并从记录中移除。"""
    global F2B_BAN_RECORDS
    if os.name != 'nt':
        jails = set(_jail_for_source(r["source"]) for r in F2B_BAN_RECORDS)
        jails.add("sshd")
        for jail in jails:
            run_shell(f"fail2ban-client set {jail} unbanip {ip}")

    F2B_BAN_RECORDS = [r for r in F2B_BAN_RECORDS if r["ip"] != ip]
    return {"success": True, "bans": F2B_BAN_RECORDS}


@router.post("/fail2ban/permanent")
def set_permanent(ip: str, current_user=Depends(get_current_user)):
    """将指定 IP 升级为永久封禁。"""
    existing = next((r for r in F2B_BAN_RECORDS if r["ip"] == ip), None)
    if existing:
        existing["level"] = "permanent"
        existing["banned_at"] = _now_str()
        existing["expire_at"] = "永久"
    return {"success": True, "bans": F2B_BAN_RECORDS}


@router.post("/fail2ban/config")
def update_fail2ban_config(config: dict, current_user=Depends(get_current_user)):
    if os.name == 'nt':
        return {"success": True}
    # config: { bantime: int, findtime: int, maxretry: int }
    bantime = config.get("bantime", 600)
    findtime = config.get("findtime", 600)
    maxretry = config.get("maxretry", 5)

    run_shell(f"fail2ban-client set sshd bantime {bantime}")
    run_shell(f"fail2ban-client set sshd findtime {findtime}")
    run_shell(f"fail2ban-client set sshd maxretry {maxretry}")

    return {"success": True}


@router.post("/fail2ban/start")
def start_fail2ban(current_user=Depends(get_current_user)):
    """启动 / 重启 Fail2ban 服务（人工操作）。"""
    global F2B_ACTIVE_OVERRIDE
    if os.name != 'nt':
        run_shell("systemctl start fail2ban || fail2ban-client start")
    F2B_ACTIVE_OVERRIDE = True
    return {"success": True, "active": True}


@router.post("/fail2ban/stop")
def stop_fail2ban(current_user=Depends(get_current_user)):
    """停止 Fail2ban 服务（人工操作）。"""
    global F2B_ACTIVE_OVERRIDE
    if os.name != 'nt':
        run_shell("systemctl stop fail2ban || fail2ban-client stop")
    F2B_ACTIVE_OVERRIDE = False
    return {"success": True, "active": False}


# --- 请求频率限制 (Rate Limit) ---
RATELIMIT_CONFIG = {
    "enabled": False,
    "limit_per_minute": 60,
    "burst": 300,
    "last_updated": None,
}


@router.get("/ratelimit")
def get_ratelimit(current_user=Depends(get_current_user)):
    return RATELIMIT_CONFIG


@router.post("/ratelimit")
def update_ratelimit(config: dict, current_user=Depends(get_current_user)):
    RATELIMIT_CONFIG["enabled"] = bool(config.get("enabled", RATELIMIT_CONFIG["enabled"]))
    RATELIMIT_CONFIG["limit_per_minute"] = int(config.get("limit_per_minute", RATELIMIT_CONFIG["limit_per_minute"]))
    RATELIMIT_CONFIG["burst"] = int(config.get("burst", RATELIMIT_CONFIG["burst"]))
    RATELIMIT_CONFIG["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"success": True, "config": RATELIMIT_CONFIG}


# --- 爬虫限速 (Bot Rate Limit) ---
BOT_RATELIMIT_CONFIG = {
    "enabled": False,
    "bot_limit_per_minute": 30,
    "bot_burst": 20,
    "last_updated": None,
}


@router.get("/bot-ratelimit")
def get_bot_ratelimit(current_user=Depends(get_current_user)):
    return BOT_RATELIMIT_CONFIG


@router.post("/bot-ratelimit")
def update_bot_ratelimit(config: dict, current_user=Depends(get_current_user)):
    BOT_RATELIMIT_CONFIG["enabled"] = bool(config.get("enabled", BOT_RATELIMIT_CONFIG["enabled"]))
    BOT_RATELIMIT_CONFIG["bot_limit_per_minute"] = int(config.get("bot_limit_per_minute", BOT_RATELIMIT_CONFIG["bot_limit_per_minute"]))
    BOT_RATELIMIT_CONFIG["bot_burst"] = int(config.get("bot_burst", BOT_RATELIMIT_CONFIG["bot_burst"]))
    BOT_RATELIMIT_CONFIG["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"success": True, "config": BOT_RATELIMIT_CONFIG}


# --- 白名单管理 (Whitelist) ---
# 官方白名单：由面板自动拉取（此处内置常见 CDN / 搜索引擎官方段，真实环境由后端定时同步）
F2B_OFFICIAL_WHITELIST = [
    # Cloudflare IPv4
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    # Cloudflare IPv6
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32",
    "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32",
    # Googlebot / Google Crawler IPv6
    "2001:4860:4801:10::/64", "2001:4860:4801:11::/64", "2001:4860:4801:12::/64",
    "2001:4860:4801:13::/64", "2001:4860:4801:14::/64", "2001:4860:4801:15::/64",
    "2001:4860:4801:16::/64", "2001:4860:4801:17::/64", "2001:4860:4801:18::/64",
    "2001:4860:4801:19::/64", "2001:4860:4801:1a::/64", "2001:4860:4801:1b::/64",
    "2001:4860:4801:1c::/64", "2001:4860:4801:1d::/64", "2001:4860:4801:1e::/64",
    "2001:4860:4801:1f::/64", "2001:4860:4801:20::/64", "2001:4860:4801:21::/64",
    "2001:4860:4801:22::/64", "2001:4860:4801:23::/64", "2001:4860:4801:24::/64",
    "2001:4860:4801:25::/64", "2001:4860:4801:26::/64", "2001:4860:4801:27::/64",
    "2001:4860:4801:28::/64", "2001:4860:4801:29::/64", "2001:4860:4801:2::/64",
    "2001:4860:4801:2a::/64", "2001:4860:4801:2b::/64", "2001:4860:4801:2c::/64",
    "2001:4860:4801:2d::/64", "2001:4860:4801:2e::/64", "2001:4860:4801:2f::/64",
    "2001:4860:4801:30::/64", "2001:4860:4801:31::/64", "2001:4860:4801:32::/64",
    "2001:4860:4801:33::/64", "2001:4860:4801:34::/64", "2001:4860:4801:35::/64",
    "2001:4860:4801:36::/64", "2001:4860:4801:37::/64", "2001:4860:4801:38::/64",
    "2001:4860:4801:39::/64", "2001:4860:4801:3a::/64", "2001:4860:4801:3b::/64",
    "2001:4860:4801:3c::/64", "2001:4860:4801:3d::/64", "2001:4860:4801:3e::/64",
    "2001:4860:4801:3f::/64", "2001:4860:4801:40::/64", "2001:4860:4801:41::/64",
    "2001:4860:4801:42::/64", "2001:4860:4801:44::/64", "2001:4860:4801:45::/64",
    "2001:4860:4801:46::/64", "2001:4860:4801:47::/64", "2001:4860:4801:48::/64",
    "2001:4860:4801:49::/64", "2001:4860:4801:4a::/64", "2001:4860:4801:4b::/64",
    "2001:4860:4801:4c::/64", "2001:4860:4801:4d::/64", "2001:4860:4801:4e::/64",
    "2001:4860:4801:50::/64", "2001:4860:4801:51::/64", "2001:4860:4801:52::/64",
    "2001:4860:4801:53::/64", "2001:4860:4801:54::/64", "2001:4860:4801:55::/64",
    "2001:4860:4801:56::/64", "2001:4860:4801:57::/64", "2001:4860:4801:58::/64",
    "2001:4860:4801:59::/64", "2001:4860:4801:5a::/64", "2001:4860:4801:5b::/64",
    "2001:4860:4801:5c::/64", "2001:4860:4801:5d::/64", "2001:4860:4801:5e::/64",
    "2001:4860:4801:5f::/64", "2001:4860:4801:60::/64", "2001:4860:4801:61::/64",
    "2001:4860:4801:62::/64", "2001:4860:4801:63::/64", "2001:4860:4801:64::/64",
    "2001:4860:4801:65::/64", "2001:4860:4801:66::/64", "2001:4860:4801:67::/64",
    "2001:4860:4801:68::/64", "2001:4860:4801:69::/64", "2001:4860:4801:6a::/64",
    "2001:4860:4801:6b::/64", "2001:4860:4801:6c::/64", "2001:4860:4801:6d::/64",
    "2001:4860:4801:6e::/64", "2001:4860:4801:6f::/64", "2001:4860:4801:70::/64",
    "2001:4860:4801:71::/64", "2001:4860:4801:72::/64", "2001:4860:4801:73::/64",
    "2001:4860:4801:74::/64", "2001:4860:4801:75::/64", "2001:4860:4801:76::/64",
    "2001:4860:4801:77::/64", "2001:4860:4801:78::/64", "2001:4860:4801:79::/64",
    "2001:4860:4801:7a::/64", "2001:4860:4801:7b::/64", "2001:4860:4801:7c::/64",
    "2001:4860:4801:7d::/64", "2001:4860:4801:7e::/64", "2001:4860:4801:7f::/64",
    "2001:4860:4801:80::/64", "2001:4860:4801:81::/64", "2001:4860:4801:82::/64",
    "2001:4860:4801:83::/64", "2001:4860:4801:84::/64", "2001:4860:4801:85::/64",
    "2001:4860:4801:86::/64", "2001:4860:4801:87::/64", "2001:4860:4801:88::/64",
    "2001:4860:4801:90::/64", "2001:4860:4801:91::/64", "2001:4860:4801:92::/64",
    "2001:4860:4801:93::/64", "2001:4860:4801:94::/64", "2001:4860:4801:95::/64",
    "2001:4860:4801:96::/64", "2001:4860:4801:97::/64", "2001:4860:4801:a0::/64",
    "2001:4860:4801:a1::/64", "2001:4860:4801:a2::/64", "2001:4860:4801:a3::/64",
    "2001:4860:4801:a4::/64", "2001:4860:4801:a5::/64", "2001:4860:4801:a6::/64",
    "2001:4860:4801:a7::/64", "2001:4860:4801:a8::/64", "2001:4860:4801:a9::/64",
    "2001:4860:4801:aa::/64", "2001:4860:4801:ab::/64", "2001:4860:4801:ac::/64",
    "2001:4860:4801:ad::/64", "2001:4860:4801:ae::/64", "2001:4860:4801:b0::/64",
    "2001:4860:4801:b1::/64", "2001:4860:4801:b2::/64", "2001:4860:4801:b3::/64",
    "2001:4860:4801:b4::/64", "2001:4860:4801:b5::/64", "2001:4860:4801:b6::/64",
    "2001:4860:4801:c::/64", "2001:4860:4801:f::/64",
    # Google Crawler IPv4
    "192.178.4.0/27", "192.178.4.128/27", "192.178.4.160/27", "192.178.4.192/27",
    "192.178.4.224/27", "192.178.4.32/27", "192.178.4.64/27", "192.178.4.96/27",
    "192.178.5.0/27", "192.178.6.0/27", "192.178.6.128/27", "192.178.6.160/27",
    "192.178.6.192/27", "192.178.6.224/27", "192.178.6.32/27", "192.178.6.64/27",
    "192.178.6.96/27", "192.178.7.0/27", "192.178.7.128/27", "192.178.7.160/27",
    "192.178.7.192/27", "192.178.7.224/27", "192.178.7.32/27", "192.178.7.64/27",
    "192.178.7.96/27",
    "34.100.182.96/28", "34.101.50.144/28", "34.118.254.0/28", "34.118.66.0/28",
    "34.126.178.96/28", "34.146.150.144/28", "34.147.110.144/28", "34.151.74.144/28",
    "34.152.50.64/28", "34.154.114.144/28", "34.155.98.32/28", "34.165.18.176/28",
    "34.175.160.64/28", "34.176.130.16/28", "34.22.85.0/27", "34.64.82.64/28",
    "34.65.242.112/28", "34.80.50.80/28", "34.88.194.0/28", "34.89.10.80/28",
    "34.89.198.80/28", "34.96.162.48/28", "35.247.243.240/28",
    # Googlebot 特殊爬虫 IPv4
    "66.249.64.0/27", "66.249.64.128/27", "66.249.64.160/27", "66.249.64.192/27",
    "66.249.64.224/27", "66.249.64.32/27", "66.249.64.64/27", "66.249.64.96/27",
    "66.249.65.0/27", "66.249.65.128/27", "66.249.65.160/27", "66.249.65.192/27",
    "66.249.65.224/27", "66.249.65.32/27", "66.249.65.64/27", "66.249.65.96/27",
    "66.249.66.0/27", "66.249.66.128/27", "66.249.66.160/27", "66.249.66.192/27",
    "66.249.66.224/27", "66.249.66.32/27", "66.249.66.64/27", "66.249.66.96/27",
    "66.249.67.0/27", "66.249.67.32/27", "66.249.67.64/27", "66.249.68.0/27",
    "66.249.68.128/27", "66.249.68.160/27", "66.249.68.192/27", "66.249.68.32/27",
    "66.249.68.64/27", "66.249.68.96/27", "66.249.69.0/27", "66.249.69.128/27",
    "66.249.69.160/27", "66.249.69.192/27", "66.249.69.224/27", "66.249.69.32/27",
    "66.249.69.64/27", "66.249.69.96/27", "66.249.70.0/27", "66.249.70.128/27",
    "66.249.70.160/27", "66.249.70.192/27", "66.249.70.224/27", "66.249.70.32/27",
    "66.249.70.64/27", "66.249.70.96/27", "66.249.71.0/27", "66.249.71.128/27",
    "66.249.71.160/27", "66.249.71.192/27", "66.249.71.224/27", "66.249.71.32/27",
    "66.249.71.64/27", "66.249.71.96/27", "66.249.72.0/27", "66.249.72.128/27",
    "66.249.72.160/27", "66.249.72.192/27", "66.249.72.224/27", "66.249.72.32/27",
    "66.249.72.64/27", "66.249.72.96/27", "66.249.73.0/27", "66.249.73.128/27",
    "66.249.73.160/27", "66.249.73.192/27", "66.249.73.224/27", "66.249.73.32/27",
    "66.249.73.64/27", "66.249.73.96/27", "66.249.74.0/27", "66.249.74.128/27",
    "66.249.74.160/27", "66.249.74.192/27", "66.249.74.224/27", "66.249.74.32/27",
    "66.249.74.64/27", "66.249.74.96/27", "66.249.75.0/27", "66.249.75.128/27",
    "66.249.75.160/27", "66.249.75.192/27", "66.249.75.224/27", "66.249.75.32/27",
    "66.249.75.64/27", "66.249.75.96/27", "66.249.76.0/27", "66.249.76.128/27",
    "66.249.76.160/27", "66.249.76.192/27", "66.249.76.224/27", "66.249.76.32/27",
    "66.249.76.64/27", "66.249.76.96/27", "66.249.77.0/27", "66.249.77.128/27",
    "66.249.77.160/27", "66.249.77.192/27", "66.249.77.224/27", "66.249.77.32/27",
    "66.249.77.64/27", "66.249.77.96/27", "66.249.78.0/27", "66.249.78.128/27",
    "66.249.78.160/27", "66.249.78.192/27", "66.249.78.224/27", "66.249.78.32/27",
    "66.249.78.64/27", "66.249.78.96/27", "66.249.79.0/27", "66.249.79.128/27",
    "66.249.79.160/27", "66.249.79.192/27", "66.249.79.224/27", "66.249.79.32/27",
    "66.249.79.64/27",
    # Bingbot (Microsoft)
    "157.55.39.0/24", "207.46.13.0/24", "40.77.167.0/24", "13.66.139.0/24",
    "13.66.144.0/24", "52.167.144.0/24", "13.67.10.16/28", "13.69.66.240/28",
    "13.71.172.224/28", "139.217.52.0/28", "191.233.204.224/28", "20.36.108.32/28",
    "20.43.120.16/28", "40.79.131.208/28", "40.79.186.176/28", "52.231.148.0/28",
    "20.79.107.240/28", "51.105.67.0/28", "20.125.163.80/28", "40.77.188.0/22",
    "65.55.210.0/24", "199.30.24.0/23", "40.77.202.0/24", "40.77.139.0/25",
    "20.74.197.0/28", "20.15.133.160/27", "40.77.177.0/24", "40.77.178.0/23",
]

WHITELIST_STATE = {
    "official": list(F2B_OFFICIAL_WHITELIST),
    "custom": ["1.2.3.4", "10.0.0.0/8"],
    "paths": ["/google*.html", "/BingSiteAuth.xml", "/custom-verify-*.txt"],
    "last_updated": "2026-07-27 02:00:07",
}


@router.get("/whitelist")
def get_whitelist(current_user=Depends(get_current_user)):
    return WHITELIST_STATE


@router.post("/whitelist/refresh")
def refresh_official_whitelist(current_user=Depends(get_current_user)):
    WHITELIST_STATE["official"] = list(F2B_OFFICIAL_WHITELIST)
    WHITELIST_STATE["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"success": True, "whitelist": WHITELIST_STATE}


@router.post("/whitelist/custom")
def update_custom_whitelist(payload: dict, current_user=Depends(get_current_user)):
    custom = payload.get("custom", [])
    if isinstance(custom, str):
        custom = [c.strip() for c in custom.splitlines() if c.strip()]
    WHITELIST_STATE["custom"] = list(custom)
    return {"success": True, "whitelist": WHITELIST_STATE}


@router.post("/whitelist/paths")
def update_path_whitelist(payload: dict, current_user=Depends(get_current_user)):
    paths = payload.get("paths", [])
    if isinstance(paths, str):
        paths = [p.strip() for p in paths.splitlines() if p.strip()]
    WHITELIST_STATE["paths"] = list(paths)
    return {"success": True, "whitelist": WHITELIST_STATE}


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
