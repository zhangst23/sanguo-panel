import os
import subprocess
import glob

def find_php_executable():
    """
    Find the PHP executable in PATH or common installation directories.
    Returns the full path to the executable or None if not found.
    """
    php_bin = "php"
    php_found = False
    
    # 1. Check if php is in PATH
    try:
        # Use 'where' on Windows to get the full path
        if os.name == 'nt':
            res = subprocess.run(["where", "php"], capture_output=True, text=True, shell=True)
            if res.returncode == 0:
                php_bin = res.stdout.splitlines()[0].strip()
                php_found = True
        else:
            res = subprocess.run(["which", "php"], capture_output=True, text=True)
            if res.returncode == 0:
                php_bin = res.stdout.strip()
                php_found = True
    except Exception:
        pass

    # 2. If not in PATH, search common Windows/Linux installation paths
    if not php_found:
        if os.name == 'nt':
            # Check multiple drives and common installer paths
            drives = ['C', 'D', 'E', 'F']
            common_patterns = [
                r":\php\php.exe",
                r":\tools\php\php.exe",
                r":\xampp\php\php.exe",
                r":\laragon\bin\php\php-current\php.exe",
                r":\wamp64\bin\php\php*\php.exe",
                r":\wamp\bin\php\php*\php.exe",
                r":\Bitnami\wampstack-*\php\php.exe",
            ]
            
            for drive in drives:
                for pattern in common_patterns:
                    full_pattern = pattern.replace(":", drive + ":")
                    matches = glob.glob(full_pattern)
                    if matches:
                        # Pick the first one (usually latest or default)
                        php_bin = matches[0]
                        php_found = True
                        break
                if php_found: break
        else:
            # On Linux, check common paths
            for path in ["/usr/bin/php", "/usr/local/bin/php", "/usr/local/lsws/lsphp82/bin/php"]:
                if os.path.exists(path):
                    php_bin = path
                    php_found = True
                    break

    return php_bin if php_found else None

def get_php_version(php_bin):
    """
    Get the version of the PHP executable.
    """
    try:
        res = subprocess.run([php_bin, "-v"], capture_output=True, text=True, shell=(os.name == 'nt'))
        if res.returncode == 0:
            # First line is usually "PHP 8.2.12 (cli) ..."
            line = res.stdout.splitlines()[0]
            parts = line.split(' ')
            if len(parts) >= 2:
                return parts[1]
    except Exception:
        pass
    return "Unknown"
