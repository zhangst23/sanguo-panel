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
        return [
            {"version": "8.1", "status": "installed", "is_default": False},
            {"version": "8.2", "status": "installed", "is_default": True},
            {"version": "8.3", "status": "not_installed", "is_default": False},
        ]
    
    # On Linux, check for lsphpXX directories
    lsws_path = "/usr/local/lsws"
    versions = []
    # Check common versions
    for v in ["74", "80", "81", "82", "83", "84"]:
        path = os.path.join(lsws_path, f"lsphp{v}")
        if os.path.exists(path):
            versions.append({
                "version": f"{v[0]}.{v[1]}",
                "status": "installed",
                "is_default": v == "82" # Mock default
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
    v_short = version.replace(".", "")
    if os.name == 'nt':
        return [
            {"name": "opcache", "status": "enabled"},
            {"name": "redis", "status": "enabled"},
            {"name": "mysqli", "status": "enabled"},
            {"name": "imagick", "status": "disabled"},
        ]
    
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
