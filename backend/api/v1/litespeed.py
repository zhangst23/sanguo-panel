from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os
import re
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
    Read HTTP/2, HTTP/3, Brotli, LSCache status from the real OLS config.
    """
    if os.name == 'nt':
        return {"http2": True, "http3": True, "brotli": True, "lscache": True}
    try:
        with open(CONF_FILE) as f:
            conf = f.read()
        # HTTP/3: quicEnable in tuning{}
        http3 = re.search(r'quicEnable\s+(\d+)', conf)
        http3 = bool(http3 and http3.group(1).strip() == '1') if http3 else False
        # Brotli: enableBrCompress in tuning{}
        br = re.search(r'enableBrCompress\s+(\d+)', conf)
        brotli = bool(br and br.group(1).strip() in ('1', '4')) if br else False
        # LSCache: module cache ls_enabled
        lscache = re.search(r'module cache \{[^}]*ls_enabled\s+(\d+)', conf, re.DOTALL)
        lscache = bool(lscache and lscache.group(1).strip() == '1') if lscache else False
        # HTTP/2 is always on with TLS in OLS 1.9 (enableSpdy covers h2)
        return {"http2": True, "http3": http3, "brotli": brotli, "lscache": lscache}
    except Exception:
        return {"http2": True, "http3": False, "brotli": False, "lscache": False}


@router.post("/config/features/toggle")
def toggle_feature(
    data: FeatureToggle,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """Toggle an OLS feature by editing httpd_config.conf and restarting."""
    if os.name == 'nt':
        return {"success": True, "msg": f"Feature {data.feature} set to {data.enabled} (Mock)"}
    feature = data.feature.lower()
    on = "1" if data.enabled else "0"
    try:
        with open(CONF_FILE) as f:
            conf = f.read()
        if feature in ("http3", "quic"):
            conf = re.sub(r'quicEnable\s+\S+', f'quicEnable                   {on}', conf)
        elif feature in ("brotli",):
            # enableBrCompress uses 4=on(both static&dynamic) / 0=off
            val = "4" if data.enabled else "0"
            conf = re.sub(r'enableBrCompress\s+\S+', f'enableBrCompress             {val}', conf)
        elif feature in ("lscache", "cache"):
            newval = "1" if data.enabled else "0"
            conf = re.sub(r'(module cache \{[^}]*ls_enabled\s+)\S+', r'\g<1>' + newval, conf, flags=re.DOTALL)
        elif feature == "http2":
            # HTTP/2 tied to enableSpdy on secure listeners; nothing to toggle here
            return {"success": True, "msg": "HTTP/2 随 HTTPS 监听器自动启用，无需单独切换"}
        else:
            raise HTTPException(status_code=400, detail=f"未知特性: {data.feature}")
        with open(CONF_FILE, "w") as f:
            f.write(conf)
        run_shell(f"{LSWS_HOME}/bin/lswsctrl restart")
        return {"success": True, "msg": f"已{'启用' if data.enabled else '禁用'} {data.feature}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换失败: {e}")
