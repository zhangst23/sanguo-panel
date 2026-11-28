"""通知提醒工具。

SMTP / Webhook 配置以 GlobalOption（JSON）持久化，避免改动数据库表结构；
告警记录以 JSON 文件保存，仅保留最近 100 条。
"""
import os
import json
import time
import ssl
import socket
import smtplib
import base64
import threading
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Dict, List

import requests
from sqlalchemy.orm import Session

from backend.models.config import GlobalOption

_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_UTILS_DIR)
PANEL_ROOT = os.path.dirname(_BACKEND_DIR)
RECORDS_FILE = os.path.join(PANEL_ROOT, "backup", "notification_records.json")
MAX_RECORDS = 100
_lock = threading.Lock()

SMTP_KEY = "notification_smtp"
WEBHOOK_KEY = "notification_webhook"
RULES_KEY = "notification_rules"
THRESHOLDS_KEY = "notification_thresholds"

RULE_KEYS = [
    "cpu_high", "mem_low", "oom", "disk_high", "service_restart",
    "ssl_expiring", "db_backup_fail", "remote_backup_fail", "cron_fail",
    "site_expiring", "system_update", "panel_update", "fake_crawler",
]

SMTP_FIELDS = [
    "host", "port", "encryption", "username", "password", "from_email", "admin_email"
]

DEFAULT_SMTP: Dict[str, Any] = {
    "host": "", "port": 587, "encryption": "STARTTLS", "username": "",
    "password": "", "from_email": "", "admin_email": "",
}
DEFAULT_WEBHOOK: Dict[str, Any] = {"channel": "wecom", "url": ""}
DEFAULT_RULES: Dict[str, bool] = {k: (k != "fake_crawler") for k in RULE_KEYS}
DEFAULT_THRESHOLDS: Dict[str, int] = {"hit_count": 10, "window_hours": 24}

EXPORT_PREFIX = "SGCFG1:"


# --------------------------------------------------------------------------
# 配置读写（GlobalOption）
# --------------------------------------------------------------------------
def get_option(db: Session, key: str, default: Dict[str, Any]) -> Dict[str, Any]:
    option = db.query(GlobalOption).filter(GlobalOption.option_key == key).first()
    result = dict(default)
    if option and isinstance(option.option_value, dict):
        result.update(option.option_value)
    return result


def set_option(db: Session, key: str, value: Dict[str, Any], description: str = "") -> None:
    option = db.query(GlobalOption).filter(GlobalOption.option_key == key).first()
    if not option:
        db.add(GlobalOption(option_key=key, option_value=value, description=description))
    else:
        option.option_value = value
        if description:
            option.description = description
    db.commit()


def get_smtp(db: Session) -> Dict[str, Any]:
    return get_option(db, SMTP_KEY, DEFAULT_SMTP)


def get_webhook(db: Session) -> Dict[str, Any]:
    return get_option(db, WEBHOOK_KEY, DEFAULT_WEBHOOK)


def get_rules(db: Session) -> Dict[str, bool]:
    return get_option(db, RULES_KEY, DEFAULT_RULES)


def get_thresholds(db: Session) -> Dict[str, int]:
    return get_option(db, THRESHOLDS_KEY, DEFAULT_THRESHOLDS)


# --------------------------------------------------------------------------
# 告警记录（JSON 文件，最近 100 条）
# --------------------------------------------------------------------------
def load_records() -> List[Dict[str, Any]]:
    try:
        with open(RECORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data[:MAX_RECORDS]
    except Exception:
        pass
    return []


def save_records(records: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(RECORDS_FILE), exist_ok=True)
    with _lock:
        with open(RECORDS_FILE, "w", encoding="utf-8") as f:
            json.dump(records[:MAX_RECORDS], f, ensure_ascii=False, indent=2)


def add_record(record_type: str, level: str, content: str) -> Dict[str, Any]:
    """追加一条告警记录（最新在前），供面板各监控模块调用。"""
    record = {
        "id": int(time.time() * 1000),
        "time": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        "type": record_type,
        "level": "恢复" if level == "恢复" else "告警",
        "content": content,
    }
    records = load_records()
    records.insert(0, record)
    save_records(records)
    return record


# --------------------------------------------------------------------------
# SMTP 邮件
# --------------------------------------------------------------------------
def _sender(cfg: Dict[str, Any]) -> str:
    return cfg.get("from_email") or cfg.get("username") or "noreply@localhost"


def _recipient(cfg: Dict[str, Any]) -> str:
    return cfg.get("admin_email") or cfg.get("from_email") or cfg.get("username") or ""


def _connect(cfg: Dict[str, Any]):
    host = cfg.get("host") or ""
    port = int(cfg.get("port") or 587)
    encryption = cfg.get("encryption") or "STARTTLS"
    if encryption == "SSL/TLS":
        return smtplib.SMTP_SSL(host, port, timeout=4)
    client = smtplib.SMTP(host, port, timeout=4)
    client.ehlo()
    if encryption == "STARTTLS":
        client.starttls(context=ssl.create_default_context())
        client.ehlo()
    return client


def _login(client, cfg: Dict[str, Any]) -> None:
    if cfg.get("username"):
        client.login(cfg["username"], cfg.get("password") or "")


def send_mail(cfg: Dict[str, Any], subject: str, body: str, to: str = None) -> str:
    """发送邮件；返回收件人地址。"""
    if not cfg.get("host"):
        raise ValueError("请先配置并保存 SMTP 服务器")
    recipient = to or _recipient(cfg)
    if not recipient:
        raise ValueError("请配置管理员通知邮箱或发件邮箱")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _sender(cfg)
    msg["To"] = recipient
    msg.set_content(body)

    client = _connect(cfg)
    try:
        _login(client, cfg)
        client.sendmail(_sender(cfg), [recipient], msg.as_string())
    finally:
        try:
            client.quit()
        except Exception:
            pass
    return recipient


def diagnose_smtp(cfg: Dict[str, Any]) -> str:
    """按 DNS -> 连接 -> 加密 -> 认证 -> 提交 顺序诊断，报告中不含密码。"""
    lines: List[str] = []
    host = cfg.get("host") or ""
    port = int(cfg.get("port") or 587)
    encryption = cfg.get("encryption") or "STARTTLS"

    if not host:
        return "[失败] 尚未配置 SMTP 服务器，请先保存配置。"

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        ips = sorted({info[4][0] for info in infos})
        lines.append(f"[OK] DNS 解析 {host} -> {', '.join(ips[:3])}")
    except Exception as e:
        lines.append(f"[失败] DNS 解析 {host}: {e}")
        return "\n".join(lines)

    try:
        with socket.create_connection((host, port), timeout=3):
            lines.append(f"[OK] TCP 连接 {host}:{port}")
    except Exception as e:
        lines.append(f"[失败] TCP 连接 {host}:{port}: {e}")
        return "\n".join(lines)

    client = None
    try:
        if encryption == "SSL/TLS":
            client = smtplib.SMTP_SSL(host, port, timeout=3)
            lines.append("[OK] SSL/TLS 握手")
        else:
            client = smtplib.SMTP(host, port, timeout=3)
            client.ehlo()
            if encryption == "STARTTLS":
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
                lines.append("[OK] STARTTLS 升级")
            else:
                lines.append("[跳过] 未启用加密")
    except Exception as e:
        lines.append(f"[失败] 加密握手 ({encryption}): {e}")
        return "\n".join(lines)

    try:
        if cfg.get("username"):
            _login(client, cfg)
            lines.append("[OK] 认证成功")
        else:
            lines.append("[跳过] 未配置 SMTP 用户名")
    except Exception as e:
        lines.append(f"[失败] 认证: {e}")

    try:
        recipient = _recipient(cfg)
        if not recipient:
            raise ValueError("未配置管理员通知邮箱或发件邮箱")
        msg = EmailMessage()
        msg["Subject"] = "三国面板 SMTP 诊断测试"
        msg["From"] = _sender(cfg)
        msg["To"] = recipient
        msg.set_content("这是一封来自三国面板的 SMTP 诊断测试邮件。")
        client.sendmail(_sender(cfg), [recipient], msg.as_string())
        lines.append(f"[OK] 测试邮件已提交至 {recipient}")
    except Exception as e:
        lines.append(f"[失败] 测试邮件提交: {e}")

    try:
        client.quit()
    except Exception:
        pass
    return "\n".join(lines)


def export_smtp(cfg: Dict[str, Any]) -> str:
    data = {key: cfg.get(key, DEFAULT_SMTP.get(key, "")) for key in SMTP_FIELDS}
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return EXPORT_PREFIX + base64.urlsafe_b64encode(raw).decode("ascii")


def import_smtp(code: str) -> Dict[str, Any]:
    if not code.startswith(EXPORT_PREFIX):
        raise ValueError("配置码格式不正确，请以 SGCFG1: 开头")
    try:
        raw = base64.urlsafe_b64decode(code[len(EXPORT_PREFIX):].encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        raise ValueError("配置码无法解析")
    if not isinstance(data, dict):
        raise ValueError("配置码内容无效")
    result = dict(DEFAULT_SMTP)
    for key in SMTP_FIELDS:
        if key in data:
            result[key] = data[key]
    return result


# --------------------------------------------------------------------------
# Webhook 推送
# --------------------------------------------------------------------------
def send_webhook(cfg: Dict[str, Any], title: str, content: str) -> str:
    url = cfg.get("url") or ""
    if not url:
        raise ValueError("尚未配置 Webhook URL")
    channel = cfg.get("channel") or "wecom"
    text = f"{title}\n{content}"
    if channel == "wecom":
        payload = {"msgtype": "text", "text": {"content": text}}
    elif channel == "dingtalk":
        payload = {"msgtype": "text", "text": {"content": text}}
    else:
        payload = {"msg_type": "text", "content": {"text": text}}

    response = requests.post(url, json=payload, timeout=4)
    response.raise_for_status()
    try:
        data = response.json()
        if isinstance(data, dict) and data.get("errcode") not in (None, 0):
            raise ValueError(data.get("errmsg") or "Webhook 返回错误")
    except ValueError as e:
        if "Webhook" in str(e):
            raise
    return response.text[:200]
