"""面板备份工具。

将 /sanguo-panel 目录（排除 venv、backup 等）与面板数据库打包到
/sanguo-panel/backup，支持「每周日 23:00」定时备份与一键恢复。
备份元数据与定时配置以 JSON 文件存储，避免改动数据库表结构。
"""
import os
import json
import tarfile
import tempfile
import shutil
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# 路径推导：本文件位于 <panel>/backend/utils/panel_backup_utils.py
_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_UTILS_DIR)
PANEL_ROOT = os.path.dirname(_BACKEND_DIR)            # /sanguo-panel
BACKUP_DIR = os.path.join(PANEL_ROOT, "backup")
META_FILE = os.path.join(BACKUP_DIR, "panel_backups.json")
CONFIG_FILE = os.path.join(BACKUP_DIR, "panel_backup_config.json")
PANEL_DB = os.path.join(_BACKEND_DIR, "panel.db")

# 打包时排除的目录（venv / backup 为硬性要求，其余为常见体积大户）
EXCLUDE_DIRS = {"venv", "backup", ".git", "node_modules", "__pycache__"}
DB_SUFFIXES = (".db", ".db-journal", ".db-wal", ".db-shm")

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "cron": "0 23 * * 0",
    "description": "每周日 23:00",
    "last_run": None,
}

_lock = threading.Lock()


def _ensure() -> None:
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _next_slot(now: datetime) -> datetime:
    """下一个周日 23:00。"""
    days_until = (6 - now.weekday()) % 7  # Sunday == 6
    if days_until == 0 and (now.hour, now.minute) >= (23, 0):
        days_until = 7
    return (now + timedelta(days=days_until)).replace(hour=23, minute=0, second=0, microsecond=0)


def _last_slot(now: datetime) -> datetime:
    """刚过去的那个周日 23:00。"""
    days_since = (now.weekday() + 1) % 7  # Monday == 0 -> 1; Sunday == 6 -> 0
    return (now - timedelta(days=days_since)).replace(hour=23, minute=0, second=0, microsecond=0)


# ------------------------- 定时配置 -------------------------
def load_config() -> Dict[str, Any]:
    _ensure()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg.setdefault("enabled", True)
            cfg.setdefault("cron", "0 23 * * 0")
            cfg.setdefault("description", "每周日 23:00")
            cfg.setdefault("last_run", None)
            return cfg
        except Exception:
            pass
    cfg = dict(DEFAULT_CONFIG)
    save_config(cfg)
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    _ensure()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_config_with_next() -> Dict[str, Any]:
    cfg = load_config()
    cfg["next_run"] = _next_slot(datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    return cfg


# ------------------------- 元数据记录 -------------------------
def load_records() -> List[Dict[str, Any]]:
    _ensure()
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_records(records: List[Dict[str, Any]]) -> None:
    _ensure()
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def _new_record(trigger: str) -> Dict[str, Any]:
    rid = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    archive_name = f"panel_backup_{rid}.tar.gz"
    return {
        "id": rid,
        "name": archive_name,
        "file_path": os.path.join(BACKUP_DIR, archive_name),
        "file_size": 0,
        "created_at": _now_iso(),
        "trigger": trigger,
        "status": "running",
        "error": None,
    }


# ------------------------- 备份 -------------------------
def begin_panel_backup(trigger: str = "manual") -> Dict[str, Any]:
    with _lock:
        records = load_records()
        rec = _new_record(trigger)
        records.insert(0, rec)
        save_records(records)
        return rec


def finalize_panel_backup(rec_id: str) -> Optional[Dict[str, Any]]:
    records = load_records()
    rec = next((r for r in records if r["id"] == rec_id), None)
    if not rec:
        return None
    try:
        _build_archive(rec["file_path"])
        rec["file_size"] = os.path.getsize(rec["file_path"])
        rec["status"] = "success"
    except Exception as e:  # pragma: no cover
        rec["status"] = "failed"
        rec["error"] = str(e)
    save_records(records)
    return rec


def create_panel_backup(trigger: str = "manual") -> Dict[str, Any]:
    """同步创建完整备份（供调度线程等后台上下文直接调用）。"""
    rec = begin_panel_backup(trigger)
    return finalize_panel_backup(rec["id"])


def _build_archive(archive_path: str) -> None:
    if os.path.exists(archive_path):
        os.remove(archive_path)
    with tarfile.open(archive_path, "w:gz") as tar:
        for root, dirs, files in os.walk(PANEL_ROOT):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for fn in files:
                full = os.path.join(root, fn)
                if full == archive_path:
                    continue
                if full.endswith(DB_SUFFIXES):
                    continue
                rel = os.path.relpath(full, PANEL_ROOT)
                try:
                    tar.add(full, arcname=rel)
                except Exception:
                    continue
        # 面板数据库以干净副本形式单独存放
        if os.path.exists(PANEL_DB):
            tar.add(PANEL_DB, arcname="panel_db/panel.db")


# ------------------------- 恢复 -------------------------
def begin_restore(backup_id: str) -> Dict[str, Any]:
    records = load_records()
    rec = next((r for r in records if r["id"] == backup_id), None)
    if not rec:
        raise ValueError("备份不存在")
    rec["status"] = "running"
    rec["error"] = None
    save_records(records)
    return rec


def finalize_restore(backup_id: str) -> Optional[Dict[str, Any]]:
    records = load_records()
    rec = next((r for r in records if r["id"] == backup_id), None)
    if not rec:
        return None
    try:
        _restore_archive(rec["file_path"])
        rec["status"] = "success"
    except Exception as e:  # pragma: no cover
        rec["status"] = "failed"
        rec["error"] = str(e)
    save_records(records)
    return rec


def restore_panel_backup(backup_id: str) -> Dict[str, Any]:
    begin_restore(backup_id)
    return finalize_restore(backup_id)


def _restore_archive(archive_path: str) -> None:
    if not os.path.exists(archive_path):
        raise FileNotFoundError(archive_path)
    with tarfile.open(archive_path, "r:gz") as tar:
        members = tar.getmembers()
        for m in members:
            if m.name.startswith("panel_db/"):
                continue
            try:
                tar.extract(m, PANEL_ROOT)
            except Exception:
                continue
        db_member = next((m for m in members if m.name == "panel_db/panel.db"), None)
        if db_member is not None:
            tmp = tempfile.mkdtemp()
            try:
                tar.extract(db_member, tmp)
                src = os.path.join(tmp, "panel_db", "panel.db")
                if os.path.exists(src):
                    shutil.copyfile(src, PANEL_DB)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)


def delete_panel_backup(backup_id: str) -> bool:
    records = load_records()
    rec = next((r for r in records if r["id"] == backup_id), None)
    if not rec:
        return False
    try:
        if rec.get("file_path") and os.path.exists(rec["file_path"]):
            os.remove(rec["file_path"])
    except Exception:
        pass
    records = [r for r in records if r["id"] != backup_id]
    save_records(records)
    return True


# ------------------------- 定时调度 -------------------------
def maybe_run_scheduled_backup() -> Optional[Dict[str, Any]]:
    """由调度线程调用：若已到本周日 23:00 且本周尚未运行，则执行一次定时备份。"""
    cfg = load_config()
    if not cfg.get("enabled"):
        return None
    now = datetime.now()
    slot = _last_slot(now)
    last = _parse_iso(cfg.get("last_run"))
    if now >= slot and (last is None or last < slot):
        rec = create_panel_backup(trigger="schedule")
        cfg["last_run"] = _now_iso()
        save_config(cfg)
        return rec
    return None


def start_scheduler() -> None:
    """在 FastAPI lifespan 中启动的后台调度线程（每周日 23:00 触发）。"""
    def _loop() -> None:
        while True:
            try:
                maybe_run_scheduled_backup()
            except Exception:
                pass
            time.sleep(60)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
