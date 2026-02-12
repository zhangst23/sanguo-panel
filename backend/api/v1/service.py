from typing import Any
from fastapi import APIRouter, Depends, HTTPException
import subprocess
import os
from backend.api import deps

router = APIRouter()

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

@router.get("/{service_name}/status")
def get_service_status(
    service_name: str,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get system service status (e.g. lsws, mysql, redis)
    """
    # For Windows development, we might just mock this or use sc query
    if os.name == 'nt':
        # Mocking for windows dev
        return {"status": "running", "msg": f"Service {service_name} status checked (Mocked on Windows)"}
    
    # On Linux, use systemctl
    res = run_shell(f"systemctl is-active {service_name}")
    return {
        "status": "running" if res["success"] else "stopped",
        "raw": res["stdout"].strip()
    }

@router.post("/{service_name}/restart")
def restart_service(
    service_name: str,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Restart a system service.
    """
    if os.name == 'nt':
        return {"success": True, "msg": f"Service {service_name} restarted (Mocked on Windows)"}
    
    res = run_shell(f"systemctl restart {service_name}")
    if res["success"]:
        return {"success": True, "msg": f"Service {service_name} restarted successfully"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to restart service: {res['stderr']}")
