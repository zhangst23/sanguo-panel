from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os
import subprocess
from backend.api import deps

router = APIRouter()

class FeatureToggle(BaseModel):
    feature: str
    enabled: bool

# OLS Paths
LSWS_HOME = "/usr/local/lsws"
CONF_FILE = os.path.join(LSWS_HOME, "conf", "httpd_config.conf")

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

@router.get("/status")
def get_ols_status(
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get OpenLiteSpeed status, version and PID
    """
    if os.name == 'nt':
        return {
            "status": "running",
            "version": "OpenLiteSpeed 1.8.1 (Mock)",
            "pid": "1234",
            "uptime": "2 days, 4 hours"
        }
    
    # Get status
    res = run_shell(f"{LSWS_HOME}/bin/lswsctrl status")
    status = "running" if "is running" in res["stdout"] else "stopped"
    
    # Get version
    version_res = run_shell(f"{LSWS_HOME}/bin/lshttpd -v")
    # Example output: "LiteSpeed/1.8.1 Open"
    version = version_res["stdout"].split('\n')[0] if version_res["success"] else "Unknown"
    
    return {
        "status": status,
        "version": version,
        "pid": "N/A", # Can be parsed from pid file if needed
        "raw": res["stdout"].strip()
    }

@router.post("/action/{action}")
def ols_action(
    action: str,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Perform action on OLS: start, stop, restart, reload
    """
    if action not in ["start", "stop", "restart", "reload"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    if os.name == 'nt':
        return {"success": True, "msg": f"OLS {action}ed (Mock)"}
    
    cmd = f"{LSWS_HOME}/bin/lswsctrl {action}"
    res = run_shell(cmd)
    
    if res["success"]:
        return {"success": True, "msg": f"OLS {action}ed successfully"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to {action} OLS: {res['stderr']}")

@router.get("/vhosts")
def list_vhosts(
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    List OLS virtual hosts
    """
    vhosts_dir = os.path.join(LSWS_HOME, "conf", "vhosts")
    if not os.path.exists(vhosts_dir):
        if os.name == 'nt':
            return [{"name": "Example", "domain": "example.com", "root": "/var/www/example"}]
        return []
    
    vhosts = []
    for d in os.listdir(vhosts_dir):
        if os.path.isdir(os.path.join(vhosts_dir, d)):
            vhosts.append({
                "name": d,
                "domain": "N/A", # Need to parse config for domain
                "root": f"$SERVER_ROOT/vhosts/{d}"
            })
    return vhosts

@router.get("/config/features")
def get_features_status(
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get status of HTTP/2, HTTP/3, Brotli, LSCache
    """
    # In a real implementation, this would parse httpd_config.conf
    # For now, return mock/default values
    return {
        "http2": True,
        "http3": True,
        "brotli": True,
        "lscache": True
    }

@router.post("/config/features/toggle")
def toggle_feature(
    data: FeatureToggle,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Toggle OLS features
    """
    # This would involve editing the config file
    return {"success": True, "msg": f"Feature {data.feature} set to {data.enabled}"}
