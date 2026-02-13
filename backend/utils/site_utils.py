import os
import re
import shutil

def update_wp_config_redis(site, password=None):
    """
    Update wp-config.php to enable/disable Redis Object Cache settings.
    Includes database index isolation (site_id as DB index).
    """
    config_path = os.path.join(site.root_path, "wp-config.php")
    if not os.path.exists(config_path):
        return False
    
    # If password is not provided, try to get it from global options
    if password is None and site.redis_enabled:
        try:
            from backend.core.database import SessionLocal
            from backend.models.config import GlobalOption
            db = SessionLocal()
            opt = db.query(GlobalOption).filter(GlobalOption.option_key == "redis_password").first()
            if opt:
                password = opt.option_value
            db.close()
        except Exception:
            pass

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Remove existing Redis constants to avoid duplicates
        content = re.sub(r"define\s*\(\s*['\"]WP_REDIS_HOST['\"]\s*,.*?\)\s*;\s*", "", content)
        content = re.sub(r"define\s*\(\s*['\"]WP_REDIS_PORT['\"]\s*,.*?\)\s*;\s*", "", content)
        content = re.sub(r"define\s*\(\s*['\"]WP_REDIS_PASSWORD['\"]\s*,.*?\)\s*;\s*", "", content)
        content = re.sub(r"define\s*\(\s*['\"]WP_REDIS_DATABASE['\"]\s*,.*?\)\s*;\s*", "", content)
        content = re.sub(r"define\s*\(\s*['\"]WP_CACHE_KEY_SALT['\"]\s*,.*?\)\s*;\s*", "", content)
        content = re.sub(r"define\s*\(\s*['\"]WP_CACHE['\"]\s*,.*?\)\s*;\s*", "", content)
        
        if site.redis_enabled:
            # Prepare Redis config block
            # Use site.id as the Redis database index for isolation
            redis_db = site.id % 16 # Redis default has 16 DBs (0-15)
            
            pwd_line = f"define('WP_REDIS_PASSWORD', '{password}');\n" if password else ""
            
            redis_config = f"""
/* Redis Object Cache Settings */
define('WP_CACHE', true);
define('WP_REDIS_HOST', '127.0.0.1');
define('WP_REDIS_PORT', 6379);
{pwd_line}define('WP_REDIS_DATABASE', {redis_db});
define('WP_CACHE_KEY_SALT', '{site.domain}:');
"""
            # Insert before "That's all, stop editing!"
            stop_marker = "/* That's all, stop editing!"
            if stop_marker in content:
                content = content.replace(stop_marker, redis_config + stop_marker)
            else:
                content += redis_config
                
            # Copy object-cache.php drop-in
            deploy_redis_dropin(site)
        else:
            # If disabled, ensure WP_CACHE is false or removed
            content = content.replace("define('WP_CACHE', true);", "define('WP_CACHE', false);")
            # Remove object-cache.php drop-in
            remove_redis_dropin(site)
            
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return True
    except Exception as e:
        print(f"Failed to update wp-config.php for Redis: {str(e)}")
        return False

def deploy_redis_dropin(site):
    """
    Copy object-cache.php to wp-content/
    """
    # In a real environment, this file would be at a fixed location in the panel
    # For now, we use a placeholder path or check if it exists in assets
    asset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "redis", "object-cache.php")
    dest_path = os.path.join(site.root_path, "wp-content", "object-cache.php")
    
    if os.path.exists(asset_path):
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(asset_path, dest_path)
            # Set ownership if needed (on Linux)
            if os.name != 'nt':
                # Assuming www-data or similar, but this depends on system setup
                pass
            return True
        except Exception as e:
            print(f"Failed to deploy object-cache.php: {str(e)}")
            return False
    return False

def remove_redis_dropin(site):
    """
    Remove object-cache.php from wp-content/
    """
    dest_path = os.path.join(site.root_path, "wp-content", "object-cache.php")
    if os.path.exists(dest_path):
        try:
            os.remove(dest_path)
            return True
        except Exception as e:
            print(f"Failed to remove object-cache.php: {str(e)}")
            return False
    return True
