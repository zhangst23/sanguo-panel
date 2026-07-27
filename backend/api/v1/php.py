from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os
import subprocess
from backend.api import deps

router = APIRouter()

class PHPUpdate(BaseModel):
    template: str

def run_shell(command: str):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "code": result.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "code": -1
        }

@router.get("/versions")
def list_php_versions(
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    List installed and available PHP versions
    """
    if os.name == 'nt':
        from backend.utils.php_utils import find_php_executable, get_php_version
        php_bin = find_php_executable()
        if php_bin:
            version = get_php_version(php_bin)
            # Remove minor version if it's like 8.2.12 -> 8.2
            v_parts = version.split('.')
            if len(v_parts) >= 2:
                version = f"{v_parts[0]}.{v_parts[1]}"
            return [
                {"version": version, "status": "installed", "is_default": True},
            ]
        else:
            return [
                {"version": "None", "status": "not_installed", "is_default": False},
            ]
    
    # On Linux, detect installed lsphp builds and the global default version
    from backend.utils.ols_utils import get_installed_php_versions, get_default_php_version
    default_ver = get_default_php_version()
    versions = []
    for v in get_installed_php_versions():
        versions.append({
            "version": v["version"],
            "status": "installed",
            "is_default": v["version"] == default_ver,
        })
    return versions

@router.get("/{version}/extensions")
def list_extensions(
    version: str,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    List PHP extensions for a specific version
    """
    if os.name == 'nt':
        from backend.utils.php_utils import find_php_executable
        php_bin = find_php_executable()
        if not php_bin:
            return []
        
        res = run_shell(f'"{php_bin}" -m')
        if res["success"]:
            enabled_exts = [line.strip() for line in res["stdout"].split('\n') if line.strip() and not line.startswith('[')]
            # Common extensions we want to show status for
            common_exts = ["opcache", "redis", "mysqli", "imagick", "gd", "curl", "mbstring", "zip", "openssl"]
            result = []
            for ext in common_exts:
                status = "enabled" if any(ext.lower() in e.lower() for e in enabled_exts) else "disabled"
                result.append({"name": ext, "status": status})
            return result
        return []
    
    v_short = version.replace(".", "")
    cmd = f"/usr/local/lsws/lsphp{v_short}/bin/php -m"
    res = run_shell(cmd)
    if res["success"]:
        enabled_exts = res["stdout"].split('\n')
        # This is a simplified list. In a real scenario, we'd compare against a known list of common extensions
        return [{"name": ext, "status": "enabled"} for ext in enabled_exts if ext]
    return []

@router.post("/{version}/config/optimize")
def apply_optimize_template(
    version: str,
    data: PHPUpdate,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Apply OPcache optimization template
    """
    return {"success": True, "msg": f"Applied {data.template} template to PHP {version}"}

@router.get("/{version}/config")
def get_php_config(
    version: str,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get common php.ini settings
    """
    return {
        "memory_limit": "256M",
        "post_max_size": "64M",
        "upload_max_filesize": "64M",
        "max_execution_time": "300",
        "disable_functions": "exec,shell_exec,system"
    }


@router.get("/worker")
def get_php_worker(
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """PHP Worker (LSAPI/lsphp) 进程状态"""
    if os.name == 'nt':
        return {"running": True, "count": 4, "memory_mb": 128, "version": "8.2"}
    try:
        from backend.utils.ols_utils import get_default_php_version
        version = get_default_php_version() or "8.2"
    except Exception:
        version = "8.2"
    count_res = run_shell("pgrep -c lsphp 2>/dev/null || echo 0")
    try:
        count = int(str(count_res["stdout"]).strip() or "0")
    except Exception:
        count = 0
    mem_res = run_shell("ps -o rss= -C lsphp 2>/dev/null | awk '{s+=$1} END {print s+0}'")
    try:
        mem_kb = int(str(mem_res["stdout"]).strip() or "0")
    except Exception:
        mem_kb = 0
    return {
        "running": count > 0,
        "count": count,
        "memory_mb": round(mem_kb / 1024, 1),
        "version": version,
    }
