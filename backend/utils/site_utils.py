import os
import re
import subprocess
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

def update_wp_hide_login(site):
    """
    Update WordPress hide login path.
    Creates a Must-Use (MU) plugin in wp-content/mu-plugins/sanguo-hide-login.php
    """
    mu_plugin_dir = os.path.join(site.root_path, "wp-content", "mu-plugins")
    plugin_path = os.path.join(mu_plugin_dir, "sanguo-hide-login.php")
    
    if not site.wp_hide_login_path:
        if os.path.exists(plugin_path):
            try:
                os.remove(plugin_path)
            except Exception:
                pass
        return True
        
    try:
        os.makedirs(mu_plugin_dir, exist_ok=True)
        
        slug = site.wp_hide_login_path
        # Generate a secret key based on site ID and a hash
        import hashlib
        secret_key = hashlib.md5(f"sanguo_{site.id}_{slug}".encode()).hexdigest()
        
        content = f"""<?php
/*
Plugin Name: Sanguo Panel Hide Login
Description: Hides wp-admin and wp-login.php behind a custom slug. Generated by Sanguo Panel.
*/

if (!defined('ABSPATH')) exit;

add_action('init', function() {{
    $custom_slug = '{slug}';
    $secret_key = '{secret_key}';
    $request_uri = $_SERVER['REQUEST_URI'];
    $path = trim(parse_url($request_uri, PHP_URL_PATH), '/');
    
    // 1. If accessing the custom slug, set a cookie and redirect to wp-login.php
    if ($path === $custom_slug) {{
        setcookie('sanguo_hide_login', $secret_key, time() + 3600 * 24, '/');
        wp_redirect(site_url('wp-login.php'));
        exit;
    }}
    
    // 2. Block direct access to wp-login.php and wp-admin if not logged in and no cookie
    if ((strpos($request_uri, 'wp-login.php') !== false || strpos($request_uri, 'wp-admin') !== false) 
        && !isset($_COOKIE['sanguo_hide_login']) 
        && !is_user_logged_in()) {{
        
        // Allow access to admin-ajax.php and admin-post.php which are often used by themes/plugins
        if (strpos($request_uri, 'admin-ajax.php') !== false || strpos($request_uri, 'admin-post.php') !== false) {{
            return;
        }}
        
        status_header(403);
        wp_die('Access Denied. Please use your secret login URL.', '403 Forbidden', ['response' => 403]);
    }}
}}, 1);

// Optional: Filter login URL to use the custom slug instead of wp-login.php
add_filter('login_url', function($login_url, $redirect, $force_reauth) use ($custom_slug) {{
    return home_url('/' . $custom_slug);
}}, 10, 3);
?>"""
        
        with open(plugin_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Failed to update WordPress hide login for {site.domain}: {str(e)}")
        return False

def fix_site_permissions(site):
    """
    Restore standard WordPress permissions: 755 for directories, 644 for files.
    """
    if os.name == 'nt':
        return True # Permissions work differently on Windows
    
    try:
        root = site.root_path
        if not os.path.exists(root):
            return False
            
        # Faster to use find commands on Linux
        subprocess.run(f"find {root} -type d -exec chmod 755 {{}} \\;", shell=True)
        subprocess.run(f"find {root} -type f -exec chmod 644 {{}} \\;", shell=True)
        return True
    except Exception as e:
        print(f"Failed to fix permissions: {str(e)}")
        return False

def update_wp_xmlrpc(site, enabled):
    """
    Disable XML-RPC by adding a filter to a MU-plugin.
    """
    mu_plugin_dir = os.path.join(site.root_path, "wp-content", "mu-plugins")
    plugin_path = os.path.join(mu_plugin_dir, "sanguo-disable-xmlrpc.php")
    
    if enabled: # If XML-RPC should be enabled, remove the disabling plugin
        if os.path.exists(plugin_path):
            try:
                os.remove(plugin_path)
            except Exception:
                pass
        return True
        
    try:
        os.makedirs(mu_plugin_dir, exist_ok=True)
        content = """<?php
/*
Plugin Name: Sanguo Panel Disable XML-RPC
Description: Disables XML-RPC to prevent brute force attacks. Generated by Sanguo Panel.
*/
add_filter('xmlrpc_enabled', '__return_false');
?>"""
        with open(plugin_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Failed to update XML-RPC for {site.domain}: {str(e)}")
        return False


# --------------------------------------------------------------------------- #
# WP-CLI helpers (run on the OLS-bundled PHP / LSAPI build)
# --------------------------------------------------------------------------- #
def get_wp_cli_paths():
    """Return (php_path, wp_cli_path) using the system CLI PHP."""
    from backend.utils.php_utils import get_php_path
    php_path = get_php_path()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    wp_cli_path = os.path.join(project_root, "backend", "bin", "wp-cli.phar")
    return php_path, wp_cli_path


def _wp(php_path, wp_cli_path, site, *args):
    """Run a WP-CLI command for a site, returning the CompletedProcess."""
    return subprocess.run(
        [php_path, wp_cli_path, *args, f"--path={site.root_path}", "--allow-root"],
        capture_output=True, text=True, timeout=120,
    )


def set_lscache_plugin(site, enabled: bool):
    """Enable/disable the LiteSpeed Cache WP plugin (OLS LSCache) for a site.

    Returns (success: bool, message: str). Requires WP-CLI + an installed site.
    """
    php_path, wp_cli_path = get_wp_cli_paths()
    if not php_path or not os.path.exists(wp_cli_path):
        return False, "WP-CLI 不可用"
    if not site.root_path or not os.path.exists(os.path.join(site.root_path, "wp-load.php")):
        return False, "站点尚未安装 WordPress"

    try:
        if enabled:
            # install if missing (ignore error if already installed)
            _wp(php_path, wp_cli_path, site, "plugin", "install", "litespeed-cache")
            r = _wp(php_path, wp_cli_path, site, "plugin", "activate", "litespeed-cache")
            # ensure WP_CACHE is on
            _wp(php_path, wp_cli_path, site, "config", "set", "WP_CACHE", "true", "--raw")
            return r.returncode == 0, (r.stdout.strip() or "litespeed-cache 已启用")
        else:
            r = _wp(php_path, wp_cli_path, site, "plugin", "deactivate", "litespeed-cache")
            return r.returncode == 0, (r.stdout.strip() or "litespeed-cache 已停用")
    except Exception as e:
        return False, str(e)


def purge_site_lscache(site):
    """Purge a site's LSCache: OLS on-disk cache + WP object cache flush."""
    from backend.utils.ols_utils import purge_ols_lscache
    res = purge_ols_lscache(site.domain)
    php_path, wp_cli_path = get_wp_cli_paths()
    if php_path and os.path.exists(wp_cli_path) and os.path.exists(os.path.join(site.root_path, "wp-load.php")):
        try:
            _wp(php_path, wp_cli_path, site, "cache", "flush")
        except Exception:
            pass
    return res


def reset_site_opcache(site):
    """Best-effort OPcache reset for the site's PHP via WP-CLI eval."""
    php_path, wp_cli_path = get_wp_cli_paths()
    if not php_path or not os.path.exists(wp_cli_path):
        return False, "WP-CLI 不可用"
    if not os.path.exists(os.path.join(site.root_path, "wp-load.php")):
        return False, "站点尚未安装 WordPress"
    try:
        r = _wp(php_path, wp_cli_path, site, "eval", "if(function_exists('opcache_reset')){opcache_reset();}")
        return r.returncode == 0, "OPcache 已重置"
    except Exception as e:
        return False, str(e)
