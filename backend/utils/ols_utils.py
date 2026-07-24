"""
OpenLiteSpeed (OLS) virtual host management utilities.

Newly created sites are served through OpenLiteSpeed using the native
LSAPI (lsphp) PHP handler, consistent with this panel's OpenLiteSpeed
technology stack. This module is the single place that knows how to
register / unregister a domain as an OLS virtual host on the shared
``Panel80`` (``*:80``) listener.
"""
import os
import re
import subprocess
import shlex

LSWS_HOME = "/usr/local/lsws"
OLS_CONF = os.path.join(LSWS_HOME, "conf", "httpd_config.conf")
VHOSTS_DIR = os.path.join(LSWS_HOME, "conf", "vhosts")

# OpenLiteSpeed bundled PHP (LSAPI SAPI). The very same binary runs WP-CLI in
# CLI mode, so the install step and the runtime use one identical PHP build.
OLS_PHP = "/usr/local/lsws/lsphp83/bin/lsphp"

# Web server user that the LSAPI worker (lsphp) runs as.
OLS_USER = "nobody"
OLS_GROUP = "nogroup"

# Marker before which new virtualHost blocks are inserted.
_VHOST_INSERT_MARKER = "listener Default{"
_PANEL_LISTENER = "Panel80"


def run_ols_shell(command: str, timeout: int = 30) -> dict:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "code": result.returncode,
        }
    except Exception as e:  # pragma: no cover
        return {"success": False, "stdout": "", "stderr": str(e), "code": -1}


def restart_ols() -> dict:
    """Gracefully restart OpenLiteSpeed so config changes take effect."""
    return run_ols_shell(f"{LSWS_HOME}/bin/lswsctrl restart")


def _vhconf_content() -> str:
    """Virtual host config: PHP handled by the global lsapi:lsphp handler."""
    return (
        "docRoot                   $VH_ROOT/\n"
        "indexFiles                index.php\n"
        "\n"
        "enableScript              1\n"
        "allowSymbolLink           1\n"
        "restrained                0\n"
        "\n"
        "# WordPress permalink rewrite (front controller index.php)\n"
        "# PHP is served by the global scriptHandler lsapi:lsphp (LSAPI)\n"
        "rewrite {\n"
        "    enable                1\n"
        "    rules                 <<<END_rules\n"
        "RewriteRule ^/index\\.php$ - [L]\n"
        "RewriteCond %{REQUEST_FILENAME} !-f\n"
        "RewriteCond %{REQUEST_FILENAME} !-d\n"
        "RewriteRule . /index.php [L]\n"
        "END_rules\n"
        "}\n"
    )


def create_ols_vhost(domain: str, root_path: str) -> dict:
    """Create an OLS virtual host for ``domain`` served via LSAPI.

    - writes ``conf/vhosts/<domain>/vhconf.conf``
    - registers a ``virtualHost`` block + maps it to the ``Panel80`` listener
    - gracefully restarts OLS
    Idempotent: safe to call again for an existing domain.
    """
    domain = domain.lower()
    vhost_dir = os.path.join(VHOSTS_DIR, domain)
    os.makedirs(vhost_dir, exist_ok=True)
    vhconf_path = os.path.join(vhost_dir, "vhconf.conf")
    with open(vhconf_path, "w") as f:
        f.write(_vhconf_content())

    try:
        with open(OLS_CONF, "r") as f:
            conf = f.read()
    except Exception as e:
        return {"success": False, "msg": f"无法读取 OLS 配置: {e}"}

    # 1) virtualHost block (insert before first 'listener Default{')
    if f"virtualHost {domain}" not in conf:
        vhost_block = (
            f"\n"
            f"virtualHost {domain}{{\n"
            f"    vhRoot                   {root_path}\n"
            f"    allowSymbolLink          1\n"
            f"    enableScript             1\n"
            f"    restrained               0\n"
            f"    setUIDMode               0\n"
            f"    chrootMode               0\n"
            f"    configFile               conf/vhosts/{domain}/vhconf.conf\n"
            f"}}\n"
        )
        if _VHOST_INSERT_MARKER in conf:
            conf = conf.replace(
                _VHOST_INSERT_MARKER, vhost_block + "\n" + _VHOST_INSERT_MARKER, 1
            )
        else:
            conf += "\n" + vhost_block

    # 2) listener map (inside the Panel80 block)
    map_line = f"    map                      {domain} {domain}\n"
    if map_line.strip() not in conf:
        pat = re.compile(r"(listener " + re.escape(_PANEL_LISTENER) + r"\{.*?\n)\}", re.DOTALL)
        m = pat.search(conf)
        if m:
            # insert just before the listener's closing brace
            conf = conf[: m.end() - 1] + map_line + conf[m.end() - 1 :]
        else:
            return {
                "success": False,
                "msg": f"未在 OLS 配置中找到 {_PANEL_LISTENER} 监听器，无法映射域名",
            }

    try:
        with open(OLS_CONF, "w") as f:
            f.write(conf)
    except Exception as e:
        return {"success": False, "msg": f"无法写入 OLS 配置: {e}"}

    res = restart_ols()
    if not res["success"]:
        return {"success": False, "msg": f"OLS 重启失败: {res['stderr']}"}
    return {
        "success": True,
        "msg": f"虚拟主机 {domain} 已创建并经 LSAPI 托管",
        "vhconf": vhconf_path,
    }


def remove_ols_vhost(domain: str) -> dict:
    """Remove the OLS virtual host (and its config dir) for ``domain``."""
    domain = domain.lower()
    try:
        with open(OLS_CONF, "r") as f:
            conf = f.read()
    except Exception as e:
        return {"success": False, "msg": f"无法读取 OLS 配置: {e}"}

    # remove the virtualHost block (flat block, no nested braces)
    vh_pat = re.compile(r"virtualHost " + re.escape(domain) + r"\{[^{}]*\}\n?", re.DOTALL)
    conf = vh_pat.sub("", conf)

    # remove the listener map line
    conf = re.sub(
        r"\s*map\s+" + re.escape(domain) + r"\s+" + re.escape(domain) + r"\n",
        "\n",
        conf,
    )

    try:
        with open(OLS_CONF, "w") as f:
            f.write(conf)
    except Exception as e:
        return {"success": False, "msg": f"无法写入 OLS 配置: {e}"}

    vhost_dir = os.path.join(VHOSTS_DIR, domain)
    if os.path.isdir(vhost_dir):
        import shutil

        shutil.rmtree(vhost_dir, ignore_errors=True)

    res = restart_ols()
    if not res["success"]:
        return {"success": False, "msg": f"OLS 重启失败: {res['stderr']}"}
    return {"success": True, "msg": f"虚拟主机 {domain} 已移除"}


def chown_site_root(root_path: str, owner: str = f"{OLS_USER}:{OLS_GROUP}") -> dict:
    """Hand the site files to the LSAPI worker user so PHP can write uploads.

    The backend runs as root and creates files owned by root; the LSAPI
    (lsphp) worker runs as ``nobody``, so we re-own the tree (root can still
    read/write regardless).
    """
    res = run_ols_shell(f"chown -R {owner} {shlex.quote(root_path)}")
    if not res["success"]:
        return res
    uploads = os.path.join(root_path, "wp-content", "uploads")
    os.makedirs(uploads, exist_ok=True)
    run_ols_shell(f"chown -R {owner} {shlex.quote(uploads)}")
    run_ols_shell(f"chmod -R 755 {shlex.quote(uploads)}")
    return {"success": True, "msg": f"已将 {root_path} 属主改为 {owner}"}
