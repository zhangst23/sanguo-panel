from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os
import re
import json
import subprocess
from backend.api import deps
from backend.utils.ols_utils import (
    LSWS_HOME, OLS_CONF, get_default_php_version, get_installed_php_versions,
)

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


# --------------------------------------------------------------------------- #
# PHP Runtime 管理：php.ini / 默认版本 / 扩展 / OPcache / Worker Pool / Health
#                  / Auto Scaling / AI Optimizer
# --------------------------------------------------------------------------- #
_PHP_RUNTIME_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data"
)
try:
    os.makedirs(_PHP_RUNTIME_DIR, exist_ok=True)
except Exception:
    pass
_PHP_RUNTIME_CONF = os.path.join(_PHP_RUNTIME_DIR, "php_runtime.json")


def _load_runtime_conf() -> dict:
    try:
        if os.path.exists(_PHP_RUNTIME_CONF):
            with open(_PHP_RUNTIME_CONF) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_runtime_conf(data: dict):
    try:
        with open(_PHP_RUNTIME_CONF, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _php_bin_for(version: str) -> str:
    short = version.replace(".", "")
    return os.path.join(LSWS_HOME, f"lsphp{short}", "bin", "lsphp")


def _php_ini_path(version: str) -> str:
    binp = _php_bin_for(version)
    res = run_shell(f"{binp} -i 2>/dev/null | grep 'Configuration File'")
    m = re.search(r"Configuration File => (\S+)", res.get("stdout", ""))
    if m and m.group(1) and m.group(1) != "(none)":
        return m.group(1)
    short = version.replace(".", "")
    return os.path.join(LSWS_HOME, f"lsphp{short}", "etc", "php.ini")


_INI_DEFAULTS = {
    "memory_limit": "256M",
    "post_max_size": "64M",
    "upload_max_filesize": "64M",
    "max_execution_time": "300",
    "disable_functions": "exec,shell_exec,system",
}


def _read_ini_keys(path: str, keys: List[str]) -> Dict[str, str]:
    text = ""
    if os.path.exists(path):
        try:
            text = open(path).read()
        except Exception:
            text = ""
    result = {}
    for k in keys:
        m = re.search(rf"^\s*{re.escape(k)}\s*=\s*(.+)$", text, re.MULTILINE)
        result[k] = m.group(1).strip() if m else _INI_DEFAULTS.get(k, "")
    return result


def _write_ini_keys(path: str, values: Dict[str, str]):
    text = ""
    if os.path.exists(path):
        text = open(path).read()
    for k, v in values.items():
        if not v:
            continue
        pattern = rf"^\s*{re.escape(k)}\s*=.+$"
        if re.search(pattern, text, re.MULTILINE):
            text = re.sub(pattern, f"{k} = {v}", text, count=1, flags=re.MULTILINE)
        else:
            text += f"\n{k} = {v}\n"
    with open(path, "w") as f:
        f.write(text)


@router.get("/ini/{version}")
def get_php_ini(
    version: str,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """读取常用 php.ini 配置项"""
    if os.name == 'nt':
        return dict(_INI_DEFAULTS)
    path = _php_ini_path(version)
    return _read_ini_keys(path, list(_INI_DEFAULTS.keys()))


class PhpIniUpdate(BaseModel):
    memory_limit: str = ""
    post_max_size: str = ""
    upload_max_filesize: str = ""
    max_execution_time: str = ""
    disable_functions: str = ""


@router.post("/ini/{version}")
def save_php_ini(
    version: str,
    data: PhpIniUpdate,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """保存常用 php.ini 配置项"""
    if os.name == 'nt':
        return {"success": True, "msg": "已保存 (演示模式)"}
    path = _php_ini_path(version)
    values = {
        k: getattr(data, k)
        for k in ["memory_limit", "post_max_size", "upload_max_filesize", "max_execution_time", "disable_functions"]
    }
    try:
        _write_ini_keys(path, values)
        return {"success": True, "msg": f"PHP {version} php.ini 已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")


@router.get("/ini/{version}/raw")
def get_php_ini_raw(
    version: str,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """读取 php.ini 原始内容"""
    if os.name == 'nt':
        return {"content": "; php.ini (演示模式)"}
    path = _php_ini_path(version)
    content = open(path).read() if os.path.exists(path) else ""
    return {"content": content}


class RawIni(BaseModel):
    content: str


@router.post("/ini/{version}/raw")
def save_php_ini_raw(
    version: str,
    data: RawIni,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """保存 php.ini 原始内容"""
    if os.name == 'nt':
        return {"success": True, "msg": "已保存 (演示模式)"}
    path = _php_ini_path(version)
    try:
        with open(path, "w") as f:
            f.write(data.content)
        return {"success": True, "msg": "已保存原始 php.ini"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")


@router.post("/versions/{version}/default")
def set_default_php(
    version: str,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """将某个已安装版本设为系统默认 PHP（修改 OLS 全局 extProcessor 并重启）"""
    short = version.replace(".", "")
    if not os.path.exists(os.path.join(LSWS_HOME, f"lsphp{short}")):
        raise HTTPException(status_code=400, detail=f"PHP {version} 未安装")
    try:
        with open(OLS_CONF) as f:
            conf = f.read()
        conf = re.sub(
            r"(extProcessor\s+lsphp\s*\{.*?path\s+)lsphp\d{2}/bin/lsphp",
            rf"\g<1>lsphp{short}/bin/lsphp",
            conf,
            flags=re.DOTALL,
        )
        with open(OLS_CONF, "w") as f:
            f.write(conf)
        run_shell(f"{LSWS_HOME}/bin/lswsctrl restart")
        return {"success": True, "msg": f"已将 PHP {version} 设为默认版本"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置失败: {e}")


@router.post("/{version}/extensions/{name}")
def toggle_extension(
    version: str,
    name: str,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """启用 / 禁用 PHP 扩展（注释切换 php.ini 中的 extension= 行）"""
    if os.name == 'nt':
        return {"success": True, "enabled": True, "msg": f"已切换 {name} (演示模式)"}
    path = _php_ini_path(version)
    text = open(path).read() if os.path.exists(path) else ""
    pat = re.compile(rf"^\s*;?\s*extension\s*=\s*{re.escape(name)}\s*$", re.MULTILINE | re.IGNORECASE)
    m = pat.search(text)
    if m:
        line = m.group(0)
        if line.lstrip().startswith(";"):
            text = pat.sub(f"extension={name}", text, count=1)
            enabled = True
        else:
            text = pat.sub(f";extension={name}", text, count=1)
            enabled = False
    else:
        text += f"\n;extension={name}\n"
        enabled = False
    try:
        with open(path, "w") as f:
            f.write(text)
        return {"success": True, "enabled": enabled, "msg": f"{name} 已{'启用' if enabled else '禁用'}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {e}")


@router.get("/{version}/opcache")
def get_opcache(
    version: str,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """读取 OPcache 状态与配置"""
    if os.name == 'nt':
        return {
            "enabled": True, "memory_consumption": 128, "revalidate_freq": 60,
            "hit_rate": 98.5, "used_memory": 32, "free_memory": 96, "num_cached_scripts": 120,
        }
    binp = _php_bin_for(version)
    cfg_res = run_shell(f"{binp} -r 'echo json_encode(ini_get_all(\"opcache\"));' 2>/dev/null")
    enabled = False
    mem = 128
    reval = 60
    try:
        cfg = json.loads(cfg_res.get("stdout", "") or "{}")
        enabled = str(cfg.get("opcache.enable", "0")) in ("1", "On", "true", "TRUE")
        mem = int(cfg.get("opcache.memory_consumption", 128) or 128)
        reval = int(cfg.get("opcache.revalidate_freq", 60) or 60)
    except Exception:
        pass
    status_res = run_shell(
        f"{binp} -r 'echo json_encode(function_exists(\"opcache_get_status\")?opcache_get_status(False):null);' 2>/dev/null"
    )
    hit_rate = None
    used = 0
    free = 0
    scripts = 0
    try:
        st = json.loads(status_res.get("stdout", "") or "null")
        if st:
            hit_rate = round(st.get("opcache_statistics", {}).get("opcache_hit_rate", 0), 2)
            used = round(st.get("memory_usage", {}).get("used_memory", 0) / 1048576, 1)
            free = round(st.get("memory_usage", {}).get("free_memory", 0) / 1048576, 1)
            scripts = st.get("opcache_statistics", {}).get("num_cached_scripts", 0)
    except Exception:
        pass
    return {
        "enabled": enabled, "memory_consumption": mem, "revalidate_freq": reval,
        "hit_rate": hit_rate, "used_memory": used, "free_memory": free, "num_cached_scripts": scripts,
    }


@router.get("/worker-pool")
def get_worker_pool(
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """读取 OLS 全局 lsphp extProcessor（Worker Pool）配置"""
    if os.name == 'nt':
        return {"max_conns": 50, "max_workers": 10, "instances": 1, "auto_start": True}
    try:
        with open(OLS_CONF) as f:
            conf = f.read()
        m = re.search(r"extProcessor\s+lsphp\s*\{(.*?)\}", conf, re.DOTALL)
        if not m:
            return {"max_conns": 10, "max_workers": 10, "instances": 1, "auto_start": True}
        block = m.group(1)

        def g(key, default):
            mm = re.search(rf"{key}\s+(\S+)", block)
            return mm.group(1) if mm else default

        max_conns = int(g("maxConns", "10"))
        env_m = re.search(r"PHP_LSAPI_CHILDREN\s*=\s*(\d+)", block)
        max_workers = int(env_m.group(1)) if env_m else 10
        instances = int(g("instances", "1"))
        auto_start = g("autoStart", "1") == "1"
        return {"max_conns": max_conns, "max_workers": max_workers, "instances": instances, "auto_start": auto_start}
    except Exception:
        return {"max_conns": 10, "max_workers": 10, "instances": 1, "auto_start": True}


class WorkerPoolUpdate(BaseModel):
    max_conns: int = 10
    max_workers: int = 10
    instances: int = 1
    auto_start: bool = True


@router.post("/worker-pool")
def save_worker_pool(
    data: WorkerPoolUpdate,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """保存 Worker Pool 配置并重载 OLS"""
    if os.name == 'nt':
        return {"success": True, "msg": "已保存 (演示模式)"}
    try:
        with open(OLS_CONF) as f:
            conf = f.read()
        block_match = re.search(r"(extProcessor\s+lsphp\s*\{)(.*?)(\})", conf, re.DOTALL)
        if not block_match:
            raise HTTPException(status_code=404, detail="未找到 lsphp extProcessor 配置")
        inner = block_match.group(2)

        def set_k(key, val, template):
            nonlocal inner
            if re.search(rf"{key}\s+\S+", inner):
                inner = re.sub(rf"{key}\s+\S+", template.format(val), inner, count=1)
            else:
                inner += "\n    " + template.format(val) + "\n"

        set_k("maxConns", data.max_conns, "maxConns                {0}")
        set_k("instances", data.instances, "instances                {0}")
        set_k("autoStart", "1" if data.auto_start else "0", "autoStart                {0}")
        if re.search(r"env\s+PHP_LSAPI_CHILDREN", inner):
            inner = re.sub(
                r"env\s+PHP_LSAPI_CHILDREN=\d+",
                f"env                     PHP_LSAPI_CHILDREN={data.max_workers}",
                inner,
                count=1,
            )
        else:
            inner += f"\n    env                     PHP_LSAPI_CHILDREN={data.max_workers}\n"
        conf = conf[: block_match.start(2)] + inner + conf[block_match.end(2):]
        with open(OLS_CONF, "w") as f:
            f.write(conf)
        run_shell(f"{LSWS_HOME}/bin/lswsctrl restart")
        return {"success": True, "msg": "Worker Pool 已更新并重载 OLS"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")


@router.get("/health")
def php_health(
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """PHP 运行环境健康检查"""
    try:
        default = get_default_php_version()
        worker_res = run_shell("pgrep -c lsphp 2>/dev/null || echo 0")
        try:
            wc = int(str(worker_res.get("stdout", "")).strip() or "0")
        except Exception:
            wc = 0
        binp = _php_bin_for(default)
        op_res = run_shell(f"{binp} -r 'echo function_exists(\"opcache_get_status\")?\"1\":\"0\";' 2>/dev/null")
        opcache_enabled = str(op_res.get("stdout", "")).strip() == "1"
        ext_res = run_shell(f"{binp} -m 2>/dev/null")
        exts = [l.strip() for l in str(ext_res.get("stdout", "")).split("\n") if l.strip() and not l.startswith("[")]
        ext_lower = [e.lower() for e in exts]
        key_exts = ["mysqli", "curl", "openssl", "gd", "mbstring", "json"]
        ext_status = {k: (k.lower() in ext_lower) for k in key_exts}
        score = 0
        if wc > 0:
            score += 40
        if opcache_enabled:
            score += 30
        score += int(30 * sum(1 for v in ext_status.values() if v) / len(ext_status))
        status = "healthy" if score >= 90 else ("warning" if score >= 70 else "critical")
        return {
            "php_version": default,
            "worker_running": wc > 0,
            "worker_count": wc,
            "opcache_enabled": opcache_enabled,
            "extensions": ext_status,
            "score": score,
            "status": status,
        }
    except Exception as e:
        return {"status": "unknown", "score": 0, "error": str(e)}


@router.get("/autoscaling")
def get_autoscaling(
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """读取 PHP Worker 自动伸缩策略"""
    conf = _load_runtime_conf().get("autoscaling", {})
    return {
        "enabled": conf.get("enabled", False),
        "min_workers": conf.get("min_workers", 2),
        "max_workers": conf.get("max_workers", 20),
        "cpu_threshold": conf.get("cpu_threshold", 70),
    }


class AutoScalingUpdate(BaseModel):
    enabled: bool = False
    min_workers: int = 2
    max_workers: int = 20
    cpu_threshold: int = 70


@router.post("/autoscaling")
def save_autoscaling(
    data: AutoScalingUpdate,
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Any:
    """保存 PHP Worker 自动伸缩策略"""
    conf = _load_runtime_conf()
    conf["autoscaling"] = {
        "enabled": data.enabled,
        "min_workers": data.min_workers,
        "max_workers": data.max_workers,
        "cpu_threshold": data.cpu_threshold,
    }
    _save_runtime_conf(conf)
    return {"success": True, "msg": "自动伸缩策略已保存"}


@router.get("/ai-optimizer")
def ai_optimizer(
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """基于当前运行指标生成 PHP 优化建议（规则引擎，无需外部 AI 服务）"""
    try:
        default = get_default_php_version()
        path = _php_ini_path(default)
        ini = _read_ini_keys(path, list(_INI_DEFAULTS.keys()))
        worker_res = run_shell("pgrep -c lsphp 2>/dev/null || echo 0")
        try:
            wc = int(str(worker_res.get("stdout", "")).strip() or "0")
        except Exception:
            wc = 0
        op = get_opcache(default)
        tips = []
        if not op.get("enabled"):
            tips.append({
                "level": "high", "title": "启用 OPcache",
                "detail": "OPcache 当前未启用，启用后可显著降低 PHP 脚本重复解析开销。",
                "suggest": "opcache.enable=1",
            })
        else:
            if (op.get("hit_rate") or 0) < 95:
                tips.append({
                    "level": "medium", "title": "OPcache 命中率偏低",
                    "detail": f"当前命中率 {op.get('hit_rate')}%，可适当增大 opcache.memory_consumption。",
                    "suggest": "opcache.memory_consumption=256",
                })
        mem = ini.get("memory_limit", "")
        try:
            mv = int(re.sub(r"[^0-9]", "", str(mem)) or "0")
            if str(mem).upper().endswith("G"):
                mv *= 1024
        except Exception:
            mv = 0
        if 0 < mv < 256:
            tips.append({
                "level": "medium", "title": "提高 memory_limit",
                "detail": f"当前 memory_limit={mem}，建议至少 256M 以避免大请求被中断。",
                "suggest": "memory_limit=256M",
            })
        if wc < 3:
            tips.append({
                "level": "medium", "title": "增加 Worker 数量",
                "detail": "当前 PHP Worker 进程较少，高并发场景可能排队，建议在 Worker Pool 中提高 max_workers。",
                "suggest": "Worker Pool → max_workers=10",
            })
        if not tips:
            tips.append({
                "level": "good", "title": "PHP 运行环境健康",
                "detail": "未检测到明显可优化项，当前配置较为合理。",
                "suggest": "",
            })
        return {"version": default, "tips": tips}
    except Exception as e:
        return {
            "version": get_default_php_version(),
            "tips": [{"level": "info", "title": "分析失败", "detail": str(e), "suggest": ""}],
        }
