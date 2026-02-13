from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
import subprocess
import os
import re

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

@router.get("/optimization/status")
def get_optimization_status(current_user=Depends(get_current_user)):
    """
    Check if Linux optimizations are applied
    """
    if os.name == 'nt':
        return {
            "tcp_bbr": True,
            "file_limits": 65535,
            "swappiness": 10,
            "io_scheduler": "none",
            "ntp_status": "active",
            "optimized": True
        }

    status = {
        "tcp_bbr": False,
        "file_limits": 0,
        "swappiness": 60,
        "io_scheduler": "unknown",
        "ntp_status": "inactive",
        "optimized": False
    }

    # Check BBR
    res = run_shell("sysctl net.core.default_qdisc")
    if "fq" in res["stdout"]:
        res = run_shell("sysctl net.ipv4.tcp_congestion_control")
        if "bbr" in res["stdout"]:
            status["tcp_bbr"] = True

    # Check file limits
    res = run_shell("ulimit -n")
    try:
        status["file_limits"] = int(res["stdout"].strip())
    except:
        pass

    # Check swappiness
    res = run_shell("cat /proc/sys/vm/swappiness")
    try:
        status["swappiness"] = int(res["stdout"].strip())
    except:
        pass

    # Check NTP (chrony or ntp)
    res = run_shell("systemctl is-active chrony || systemctl is-active ntp")
    status["ntp_status"] = "active" if res["success"] else "inactive"

    # Summary
    if status["tcp_bbr"] and status["file_limits"] >= 65535 and status["swappiness"] <= 10:
        status["optimized"] = True

    return status

@router.post("/optimization/apply")
def apply_optimization(current_user=Depends(get_current_user)):
    """
    Apply Linux system optimizations
    """
    if os.name == 'nt':
        return {"success": True, "message": "Optimizations applied (Mocked for Windows)"}

    # This would typically run a shell script or a series of commands
    commands = [
        # TCP & Kernel
        'echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf',
        'echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf',
        'echo "vm.swappiness=10" >> /etc/sysctl.conf',
        'echo "fs.file-max=1000000" >> /etc/sysctl.conf',
        'sysctl -p',
        
        # File Limits
        'echo "* soft nofile 65535" >> /etc/security/limits.conf',
        'echo "* hard nofile 65535" >> /etc/security/limits.conf',
        
        # Time Sync
        'apt-get update && apt-get install -y chrony || yum install -y chrony',
        'systemctl enable --now chrony',
    ]
    
    results = []
    for cmd in commands:
        res = run_shell(cmd)
        results.append({"command": cmd, "success": res["success"]})

    return {"success": True, "details": results}

@router.get("/services/removable")
def get_removable_services(current_user=Depends(get_current_user)):
    """
    Get list of potentially unnecessary services
    """
    if os.name == 'nt':
        return [
            {"name": "cups", "description": "Common Unix Printing System", "active": False},
            {"name": "bluetooth", "description": "Bluetooth support", "active": True},
            {"name": "postfix", "description": "Mail Transfer Agent", "active": False}
        ]

    unnecessary = ["cups", "bluetooth", "postfix", "avahi-daemon", "modemmanager"]
    results = []
    for svc in unnecessary:
        res = run_shell(f"systemctl is-active {svc}")
        results.append({
            "name": svc,
            "description": f"{svc} service",
            "active": res["success"]
        })
    return results

@router.post("/services/disable")
def disable_service(service_name: str, current_user=Depends(get_current_user)):
    """
    Disable a specific service
    """
    if os.name == 'nt':
        return {"success": True, "message": f"Service {service_name} disabled (Mocked)"}

    res = run_shell(f"systemctl disable --now {service_name}")
    return {"success": res["success"], "message": res["stdout"] if res["success"] else res["stderr"]}
