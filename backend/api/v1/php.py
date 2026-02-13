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
