from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user, get_current_active_superuser
from backend.models.site import Site
from backend.schemas.site import Site as SiteSchema
from typing import List, Any
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

def run_redis_cli(command: str, db: Session = None):
    """
    Run a redis-cli command, automatically adding the password if set.
    """
    password = None
    if db:
        from backend.models.config import GlobalOption
        opt = db.query(GlobalOption).filter(GlobalOption.option_key == "redis_password").first()
        if opt and opt.option_value:
            password = opt.option_value
            
    if password:
        # Note: Using -a in CLI can show password in process list, 
        # but for a local panel this is often acceptable or can be mitigated.
        full_command = f"redis-cli -a \"{password}\" --no-auth-warning {command}"
    else:
        full_command = f"redis-cli {command}"
        
    return run_shell(full_command)

@router.get("/redis/status")
def get_redis_status(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    """
    Get detailed Redis status and metrics
    """
    if os.name == 'nt':
        # Mock for Windows development
        return {
            "status": "running",
            "version": "7.0.0 (Mocked)",
            "uptime_in_seconds": 3600,
            "used_memory_human": "24.5M",
            "maxmemory_human": "256M",
            "connected_clients": 5,
            "keyspace_hits": 1250,
            "keyspace_misses": 150,
            "hit_rate": 89.2,
            "mem_fragmentation_ratio": 1.2
        }
    
    # Run redis-cli info
    res = run_redis_cli("info", db)
    if not res["success"]:
        return {"status": "stopped", "error": res["stderr"]}
    
    info = res["stdout"]
    metrics = {
        "status": "running",
        "version": re.search(r"redis_version:(.*)", info).group(1).strip() if re.search(r"redis_version:(.*)", info) else "unknown",
        "uptime_in_seconds": int(re.search(r"uptime_in_seconds:(.*)", info).group(1).strip()) if re.search(r"uptime_in_seconds:(.*)", info) else 0,
        "used_memory_human": re.search(r"used_memory_human:(.*)", info).group(1).strip() if re.search(r"used_memory_human:(.*)", info) else "0B",
        "maxmemory_human": re.search(r"maxmemory_human:(.*)", info).group(1).strip() if re.search(r"maxmemory_human:(.*)", info) else "0B",
        "connected_clients": int(re.search(r"connected_clients:(.*)", info).group(1).strip()) if re.search(r"connected_clients:(.*)", info) else 0,
    }
    
    hits = int(re.search(r"keyspace_hits:(.*)", info).group(1).strip()) if re.search(r"keyspace_hits:(.*)", info) else 0
    misses = int(re.search(r"keyspace_misses:(.*)", info).group(1).strip()) if re.search(r"keyspace_misses:(.*)", info) else 0
    total = hits + misses
    metrics["keyspace_hits"] = hits
    metrics["keyspace_misses"] = misses
    metrics["hit_rate"] = round((hits / total * 100), 2) if total > 0 else 0
    metrics["mem_fragmentation_ratio"] = float(re.search(r"mem_fragmentation_ratio:(.*)", info).group(1).strip()) if re.search(r"mem_fragmentation_ratio:(.*)", info) else 0
    
    return metrics

@router.post("/redis/clear")
def clear_redis_cache(
    site_id: int = None,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_active_superuser)
):
    """
    Clear Redis cache (FLUSHALL or specific site)
    """
    if os.name == 'nt':
        return {"success": True, "message": "Redis cleared (Mocked on Windows)"}
        
    if site_id:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        
        # Isolation uses site.id % 16
        redis_db = site.id % 16
        res = run_redis_cli(f"-n {redis_db} flushdb", db)
    else:
        res = run_redis_cli("flushall", db)
        
    if res["success"]:
        return {"success": True, "message": f"Redis cache cleared successfully {'for site ' + site.domain if site_id else ''}"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to clear Redis: {res['stderr']}")

from pydantic import BaseModel

class RedisConfigUpdate(BaseModel):
    maxmemory_mb: int
    policy: str = "allkeys-lru"
    password: str = None

@router.get("/redis/config")
def get_redis_config(
    current_user: Any = Depends(get_current_user)
):
    """
    Get current Redis configuration from redis.conf
    """
    config = {
        "maxmemory_mb": 256,
        "policy": "allkeys-lru",
        "has_password": False
    }
    
    if os.name == 'nt':
        return config

    conf_path = "/etc/redis/redis.conf"
    if os.path.exists(conf_path):
        try:
            with open(conf_path, "r") as f:
                content = f.read()
            
            # Extract maxmemory
            mm = re.search(r"^maxmemory\s+(\d+)([a-zA-Z]*)", content, re.MULTILINE)
            if mm:
                val = int(mm.group(1))
                unit = mm.group(2).lower()
                if unit == 'gb' or unit == 'g':
                    config["maxmemory_mb"] = val * 1024
                else:
                    config["maxmemory_mb"] = val
            
            # Extract policy
            pol = re.search(r"^maxmemory-policy\s+(.*)", content, re.MULTILINE)
            if pol:
                config["policy"] = pol.group(1).strip()
            
            # Check password
            pw = re.search(r"^requirepass\s+(.*)", content, re.MULTILINE)
            if pw:
                config["has_password"] = True
        except Exception as e:
            print(f"Error reading redis.conf: {str(e)}")
            
    return config

@router.post("/redis/config")
def update_redis_config(
    config: RedisConfigUpdate,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_active_superuser)
):
    """
    Update Redis memory limit, eviction policy, and password
    """
    maxmemory_mb = config.maxmemory_mb
    policy = config.policy
    password = config.password
    
    if os.name == 'nt':
        return {"success": True, "message": "Redis config updated (Mocked on Windows)"}
        
    # Set via redis-cli first
    run_redis_cli(f"config set maxmemory {maxmemory_mb}mb", db)
    run_redis_cli(f"config set maxmemory-policy {policy}", db)
    if password is not None:
        # Note: we use run_shell directly for setting password to avoid recursion 
        # or auth errors before the new password is set.
        run_shell(f"redis-cli config set requirepass \"{password}\"")
    
    # Persist to redis.conf
    conf_path = "/etc/redis/redis.conf"
    if os.path.exists(conf_path):
        try:
            with open(conf_path, "r") as f:
                content = f.read()
            
            # Update maxmemory
            if re.search(r"^maxmemory\s+.*", content, re.MULTILINE):
                content = re.sub(r"^maxmemory\s+.*", f"maxmemory {maxmemory_mb}mb", content, flags=re.MULTILINE)
            else:
                content += f"\nmaxmemory {maxmemory_mb}mb"
            
            # Update policy
            if re.search(r"^maxmemory-policy\s+.*", content, re.MULTILINE):
                content = re.sub(r"^maxmemory-policy\s+.*", f"maxmemory-policy {policy}", content, flags=re.MULTILINE)
            else:
                content += f"\nmaxmemory-policy {policy}"
            
            # Update password
            if password is not None:
                if re.search(r"^requirepass\s+.*", content, re.MULTILINE):
                    if password:
                        content = re.sub(r"^requirepass\s+.*", f"requirepass \"{password}\"", content, flags=re.MULTILINE)
                    else:
                        content = re.sub(r"^requirepass\s+.*", "", content, flags=re.MULTILINE)
                elif password:
                    content += f"\nrequirepass \"{password}\""
            
            with open(conf_path, "w") as f:
                f.write(content)
                
            # If password changed, we need to update all sites' wp-config.php
            if password is not None:
                from backend.models.config import GlobalOption
                # Store in global options for panel use
                opt = db.query(GlobalOption).filter(GlobalOption.option_key == "redis_password").first()
                if not opt:
                    opt = GlobalOption(option_key="redis_password", option_value=password)
                    db.add(opt)
                else:
                    opt.option_value = password
                db.commit()
                
                # Update all sites
                from backend.utils.site_utils import update_wp_config_redis
                sites = db.query(Site).filter(Site.redis_enabled == True).all()
                for site in sites:
                    update_wp_config_redis(site, password)
                    
        except Exception as e:
            print(f"Failed to persist Redis config: {str(e)}")
            
    return {"success": True, "message": "Redis configuration updated and persisted"}

@router.get("/sites/{site_id}", response_model=SiteSchema)
def get_site_cache_settings(
    site_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    return site

@router.post("/sites/{site_id}/purge")
def purge_site_cache(
    site_id: int,
    cache_type: str = "all", # all, lscache, redis, opcache
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    results = []
    
    if cache_type in ["all", "redis"]:
        if site.redis_enabled:
            try:
                # Reuse the clear_redis_cache logic
                redis_db = site.id % 16
                res = run_redis_cli(f"-n {redis_db} flushdb", db)
                if res["success"]:
                    results.append("Redis cache cleared")
                else:
                    results.append(f"Redis clear failed: {res['stderr']}")
            except Exception as e:
                results.append(f"Redis error: {str(e)}")
        else:
            results.append("Redis is not enabled for this site")

    if cache_type in ["all", "lscache"]:
        if site.lscache_enabled:
            # Mock LSCache purge (usually involves deleting files in lscache folder)
            results.append("LSCache purged (Mocked)")
        else:
            results.append("LSCache is not enabled for this site")
            
    if cache_type in ["all", "opcache"]:
        # Mock OPcache reset
        results.append("PHP OPcache reset (Mocked)")

    return {"message": f"Purge completed for {site.domain}", "details": results}

@router.post("/sites/{site_id}/preset")
def apply_performance_preset(
    site_id: int,
    preset: str, # basic, balanced, ultimate
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=44, detail="Site not found")
    
    if preset == "basic":
        site.lscache_enabled = False
        site.redis_enabled = False
        site.opcache_enabled = True
        site.browser_cache_enabled = True
    elif preset == "balanced":
        site.lscache_enabled = True
        site.redis_enabled = True
        site.opcache_enabled = True
        site.browser_cache_enabled = True
    elif preset == "ultimate":
        site.lscache_enabled = True
        site.redis_enabled = True
        site.opcache_enabled = True
        site.browser_cache_enabled = True
        # Additional "ultimate" settings could be added here
    else:
        raise HTTPException(status_code=400, detail="Invalid preset")
    
    site.performance_preset = preset
    db.commit()
    db.refresh(site)

    # Apply the preset to the OLS / WordPress stack (not just the DB record)
    try:
        set_lscache_plugin(site, site.lscache_enabled)
        update_wp_config_redis(site)
    except Exception as e:
        print(f"Error applying performance preset to {site.domain}: {str(e)}")

    return site
