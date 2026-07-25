"""面板运维工具：更新检测、git pull、面板重启。"""
import subprocess
import os
import uuid
import threading
from datetime import datetime
from typing import Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _run_cmd(cmd: list[str], cwd: str = PROJECT_ROOT, timeout: int = 8) -> tuple[int, str, str]:
    """执行命令并返回 (returncode, stdout, stderr)，安全封装的 subprocess。"""
    try:
        r = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout ({timeout}s)"
    except FileNotFoundError:
        return -2, "", f"command not found: {cmd[0]}"


def check_update() -> dict:
    """检测面板是否有可用的 git 更新。返回 {available, current_commit, latest_commit, commit_message, error}。"""
    result = {
        "available": False,
        "current_commit": "",
        "latest_commit": "",
        "commit_message": "",
        "error": None,
    }

    # 1) 确认是 git 仓库且有 remote
    rc, _, _ = _run_cmd(["git", "rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        result["error"] = "not a git repository"
        return result

    rc, remote, _ = _run_cmd(["git", "remote", "get-url", "origin"])
    if rc != 0:
        result["error"] = "no remote 'origin' configured"
        return result

    # 2) fetch
    rc, _, stderr = _run_cmd(["git", "fetch", "origin"], timeout=8)
    if rc != 0:
        result["error"] = f"git fetch failed: {stderr}"
        return result

    # 3) current HEAD
    rc, current, _ = _run_cmd(["git", "rev-parse", "HEAD"])
    if rc != 0:
        result["error"] = "git rev-parse HEAD failed"
        return result
    result["current_commit"] = current[:8]

    # 4) upstream (origin/main) HEAD —— 适配可能分支名不是 main 的情况
    upstream_ref = "@{u}"
    rc, upstream, _ = _run_cmd(["git", "rev-parse", upstream_ref])
    if rc != 0:
        # 尝试 origin/main
        rc, upstream, _ = _run_cmd(["git", "rev-parse", "origin/main"])
        if rc != 0:
            result["error"] = "cannot resolve upstream HEAD (no tracking branch?)"
            return result

    result["latest_commit"] = upstream[:8]

    # 5) 是否领先
    if result["current_commit"] != result["latest_commit"]:
        result["available"] = True
        # 尝试取 commit message
        rc, msg, _ = _run_cmd(["git", "log", "-1", "--format=%s", upstream[:8]])
        if rc == 0:
            result["commit_message"] = msg

    return result


def _update_task_in_db(task_uuid: str, status: str, message: str):
    """在后台线程里更新任务记录。需要独立的 DB session。"""
    from backend.core.database import SessionLocal
    from backend.models.task import Task, TaskStatus

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_uuid == task_uuid).first()
        if task:
            task.status = TaskStatus(status) if status in ("completed", "failed", "running") else task.status
            task.message = message or task.message
            if status == "running":
                task.started_at = datetime.utcnow()
            elif status in ("completed", "failed"):
                task.completed_at = datetime.utcnow()
            db.commit()
    except Exception:
        pass
    finally:
        db.close()


def _create_task(db_session, task_type: str, created_by: int) -> str:
    """在数据库里创建一条任务记录，返回 task_uuid。"""
    from backend.models.task import Task
    task_uuid = str(uuid.uuid4())
    task = Task(
        task_uuid=task_uuid,
        type=task_type,
        status="pending",
        created_by=created_by,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task_uuid


def run_update_async(task_uuid: str):
    """后台线程：git pull ff-only + restart。"""
    _update_task_in_db(task_uuid, "running", "正在 git pull …")

    rc, stdout, stderr = _run_cmd(["git", "pull", "--ff-only"], timeout=30)
    if rc == 0:
        _update_task_in_db(task_uuid, "running", f"git pull 成功: {stdout or 'up to date'}")
        # 然后重启
        run_restart_async(task_uuid, is_final=True)
    else:
        _update_task_in_db(task_uuid, "failed", f"git pull 失败: {stderr}")


def run_restart_async(task_uuid: str, is_final: bool = False):
    """后台线程：nohup ./start.sh restart。"""
    import time

    if not is_final:
        _update_task_in_db(task_uuid, "running", "正在重启面板服务 …")

    start_script = os.path.join(PROJECT_ROOT, "start.sh")
    if not os.path.isfile(start_script):
        _update_task_in_db(task_uuid, "failed", f"脚本不存在: {start_script}")
        return

    try:
        subprocess.Popen(
            ["nohup", "bash", start_script, "restart"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        # 更新为 running（实际上 restart 杀了自身后就没了，这里先更新 message）
        _update_task_in_db(task_uuid, "running", "重启命令已发出，面板即将恢复 …")
    except Exception as e:
        _update_task_in_db(task_uuid, "failed", f"启动重启脚本失败: {str(e)}")
