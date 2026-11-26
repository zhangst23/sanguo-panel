"""
OpenLiteSpeed (OLS) virtual host management utilities.

Newly created sites are served through OpenLiteSpeed using the native
LSAPI (lsphp) PHP handler, consistent with this panel's OpenLiteSpeed
technology stack. This module is the single place that knows how to
register / unregister a domain as an OLS virtual host on the shared
``Panel80`` (``*:80``) listener, including multi-PHP version support
(per-vhost LSAPI handler) and LSCache purge.
"""
import os
import re
import subprocess
import shlex

LSWS_HOME = "/usr/local/lsws"
OLS_CONF = os.path.join(LSWS_HOME, "conf", "httpd_config.conf")
VHOSTS_DIR = os.path.join(LSWS_HOME, "conf", "vhosts")
CACHEDATA_DIR = os.path.join(LSWS_HOME, "cachedata")

# OpenLiteSpeed bundled PHP (LSAPI SAPI). The very same binary runs WP-CLI in
# CLI mode, so the install step and the runtime use one identical PHP build.
OLS_PHP = "/usr/local/lsws/lsphp83/bin/lsphp"

# Web server user that the LSAPI worker (lsphp) runs as.
OLS_USER = "nobody"
OLS_GROUP = "nogroup"

# Marker before which new virtualHost blocks are inserted.
_VHOST_INSERT_MARKER = "listener Default{"
_PANEL_LISTENER = "Panel80"

# 部分安装环境只生成了 Example 默认监听器，缺少 Panel80，导致建站时
# "未在 OLS 配置中找到 Panel80 监听器" 而无法映射域名（站点 521）。
_PANEL80_LISTENER_BLOCK = (
    "listener Panel80{\n"
    "    address                  *:80\n"
    "    secure                   0\n"
    "}\n"
)


def _ensure_panel80_listener(conf: str) -> str:
    """Ensure a ``Panel80`` (*:80) listener exists, creating it if missing."""
    if re.search(r"listener\s+" + re.escape(_PANEL_LISTENER) + r"\s*\{", conf):
        return conf
    if _VHOST_INSERT_MARKER in conf:
        return conf.replace(
            _VHOST_INSERT_MARKER, _PANEL80_LISTENER_BLOCK + "\n" + _VHOST_INSERT_MARKER, 1
        )
    return conf + "\n" + _PANEL80_LISTENER_BLOCK


# Cloudflare 以 Full/Strict 模式回源时访问的是 443 端口。若没有安全监听器，
# 域名会报 521。为所有站点准备一个共享自签证书，Cloudflare 在前代管对外证书。
_ORIGIN_CERT_DIR = os.path.join(LSWS_HOME, "conf", "certs")
_ORIGIN_KEY = os.path.join(_ORIGIN_CERT_DIR, "origin.key")
_ORIGIN_CERT = os.path.join(_ORIGIN_CERT_DIR, "origin.crt")


def _ensure_panel443_listener(conf: str) -> str:
    """Ensure a ``Panel443`` (*:443) secure listener with an origin cert."""
    if re.search(r"listener\s+Panel443\s*\{", conf):
        return conf
    os.makedirs(_ORIGIN_CERT_DIR, exist_ok=True)
    if not (os.path.exists(_ORIGIN_KEY) and os.path.exists(_ORIGIN_CERT)):
        run_ols_shell(
            "openssl req -x509 -nodes -newkey rsa:2048 -days 3650 "
            f"-keyout {_ORIGIN_KEY} -out {_ORIGIN_CERT} "
            "-subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost' >/dev/null 2>&1"
        )
    block = (
        "listener Panel443{\n"
        "    address                  *:443\n"
        "    secure                   1\n"
        f"    keyFile                  {_ORIGIN_KEY}\n"
        f"    certFile                 {_ORIGIN_CERT}\n"
        "}\n"
    )
    if _VHOST_INSERT_MARKER in conf:
        return conf.replace(_VHOST_INSERT_MARKER, block + "\n" + _VHOST_INSERT_MARKER, 1)
    return conf + "\n" + block


def _add_listener_map(conf: str, listener: str, domain: str) -> str:
    """Add ``map <domain> <domain>`` inside the named listener block."""
    pat = re.compile(r"(listener\s+" + re.escape(listener) + r"\s*\{.*?\n)\}", re.DOTALL)
    m = pat.search(conf)
    if not m:
        return conf
    line = f"    map                      {domain} {domain}\n"
    if line.strip() in m.group(0):
        return conf
    return conf[: m.end() - 1] + line + conf[m.end() - 1 :]


def sync_ols_aliases(main_domain: str, old_aliases: list, new_aliases: list) -> dict:
    """Add/remove OLS listener maps for site aliases, then restart OLS."""
    try:
        with open(OLS_CONF, "r") as f:
            conf = f.read()
    except Exception as e:
        return {"success": False, "msg": f"无法读取 OLS 配置: {e}"}

    removed = set(old_aliases or []) - set(new_aliases or [])
    added = set(new_aliases or []) - set(old_aliases or [])

    for alias in removed:
        # 只删除别名自身的 map，不动主域名
        conf = re.sub(
            r"\n[ \t]*map[ \t]+\S+[ \t]+" + re.escape(alias) + r"[ \t]*\n",
            "\n",
            conf,
        )

    listeners = [_PANEL_LISTENER, "Panel443"]
    if re.search(r"listener\s+Panel80v6\s*\{", conf):
        listeners.append("Panel80v6")
    for alias in added:
        for listener in listeners:
            conf = _add_listener_map(conf, listener, alias)

    try:
        with open(OLS_CONF, "w") as f:
            f.write(conf)
    except Exception as e:
        return {"success": False, "msg": f"无法写入 OLS 配置: {e}"}

    res = restart_ols()
    if not res["success"]:
        return {"success": False, "msg": f"OLS 重启失败: {res['stderr']}"}
    return {"success": True, "added": sorted(added), "removed": sorted(removed)}


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


# --------------------------------------------------------------------------- #
# Multi-PHP version support
# --------------------------------------------------------------------------- #
def get_installed_php_versions() -> list:
    """List installed lsphp versions under LSWS_HOME (e.g. 8.3)."""
    versions = []
    try:
        for name in os.listdir(LSWS_HOME):
            m = re.match(r"^lsphp(\d{2})$", name)
            if m:
                short = m.group(1)
                binp = os.path.join(LSWS_HOME, name, "bin", "lsphp")
                if os.path.exists(binp):
                    versions.append(
                        {
                            "version": f"{short[0]}.{short[1]}",
                            "short": short,
                            "path": binp,
                        }
                    )
    except Exception:
        pass
    return versions


def get_default_php_version() -> str:
    """PHP version used by the global ``extProcessor lsphp`` (fallback 8.3)."""
    try:
        with open(OLS_CONF, "r") as f:
            conf = f.read()
        m = re.search(
            r"extProcessor\s+lsphp\s*\{.*?path\s+lsphp(\d{2})/bin/lsphp",
            conf,
            re.DOTALL,
        )
        if m:
            short = m.group(1)
            return f"{short[0]}.{short[1]}"
    except Exception:
        pass
    return "8.3"


def _per_vhost_php_block(php_version: str):
    """Return ``(handler_block_str, php_used)``.

    - For the default (or uninstalled) version the handler block is empty,
      meaning the vhost inherits the global ``lsapi:lsphp`` handler.
    - For a non-default installed version a per-vhost ``extProcessor`` +
      ``scriptHandler`` is emitted so each site runs its own PHP version.
    """
    default_ver = get_default_php_version()
    if not php_version or php_version == default_ver:
        return "", default_ver
    short = php_version.replace(".", "")
    if not os.path.exists(os.path.join(LSWS_HOME, f"lsphp{short}", "bin", "lsphp")):
        # requested version not installed -> fall back to default
        return "", default_ver
    block = (
        "\n"
        f"extProcessor lsphp{short} {{\n"
        f"    type                    lsapi\n"
        f"    address                 uds://tmp/lshttpd/lsphp{short}.sock\n"
        f"    maxConns                10\n"
        f"    env                     PHP_LSAPI_CHILDREN=10\n"
        f"    initTimeout             60\n"
        f"    retryTimeout            0\n"
        f"    persistConn             1\n"
        f"    respBuffer              0\n"
        f"    autoStart               1\n"
        f"    path                    lsphp{short}/bin/lsphp\n"
        f"    backlog                 100\n"
        f"    instances               1\n"
        "}\n"
        "\n"
        "scriptHandler {\n"
        f"    add lsapi:lsphp{short}  php\n"
        "}\n"
    )
    return block, php_version


def _vhconf_content(php_version: str = None):
    """Build the vhost config. Returns ``(content_str, php_used)``."""
    handler, php_used = _per_vhost_php_block(php_version)
    parts = [
        "docRoot                   $VH_ROOT/\n"
        "indexFiles                index.php\n"
        "\n"
        "enableScript              1\n"
        "allowSymbolLink           1\n"
        "restrained                0\n",
    ]
    if handler:
        parts.append("# Per-vhost PHP (LSAPI) handler — multi-PHP support\n")
        parts.append(handler)
    else:
        parts.append("# PHP served by the global scriptHandler lsapi:lsphp (LSAPI)\n")
    parts.append(
        "# WordPress permalink rewrite (front controller index.php)\n"
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
    return "".join(parts), php_used


def create_ols_vhost(domain: str, root_path: str, php_version: str = None) -> dict:
    """Create an OLS virtual host for ``domain`` served via LSAPI.

    - writes ``conf/vhosts/<domain>/vhconf.conf`` (with per-vhost PHP handler
      when a non-default version is requested and installed)
    - registers a ``virtualHost`` block + maps it to the ``Panel80`` listener
    - gracefully restarts OLS
    Idempotent: safe to call again (e.g. to switch PHP version — the vhconf is
    rewritten and OLS restarted).
    """
    domain = domain.lower()
    vhost_dir = os.path.join(VHOSTS_DIR, domain)
    os.makedirs(vhost_dir, exist_ok=True)
    vhconf_path = os.path.join(vhost_dir, "vhconf.conf")
    content, php_used = _vhconf_content(php_version)
    # Preserve an already-deployed SSL block + force_https rule so that
    # regenerating the vhost (e.g. switching PHP version) doesn't wipe SSL.
    if os.path.exists(vhconf_path):
        try:
            old = open(vhconf_path).read()
            m = re.search(r"ssl \{.*?\n\}\n?", old, re.DOTALL)
            if m:
                content = content.rstrip() + "\n\n" + m.group(0)
            fh = re.search(
                r"# Force HTTPS\nRewriteCond %\{HTTPS\} off\nRewriteRule .*?\[R=301,L\]\n",
                old, re.DOTALL,
            )
            if fh and "<<<END_rules\n" in content:
                content = content.replace("<<<END_rules\n", "<<<END_rules\n" + fh.group(0), 1)
        except Exception:
            pass
    with open(vhconf_path, "w") as f:
        f.write(content)

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
    else:
        # vhost already exists: update its vhRoot (path correction / move)
        conf = re.sub(
            r"(virtualHost " + re.escape(domain) + r"\{\n    vhRoot\s+)\S+",
            r"\g<1>" + root_path,
            conf,
            count=1,
        )

    # 2) listener maps (auto-create listeners when missing)
    #    Panel80  -> Cloudflare Flexible / 直接 HTTP 回源
    #    Panel443 -> Cloudflare Full / Full(Strict) 回源，避免 521
    conf = _ensure_panel80_listener(conf)
    conf = _ensure_panel443_listener(conf)
    conf = _add_listener_map(conf, _PANEL_LISTENER, domain)
    conf = _add_listener_map(conf, "Panel443", domain)

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
        "msg": f"虚拟主机 {domain} 已创建并经 LSAPI 托管 (PHP {php_used})",
        "vhconf": vhconf_path,
        "php_used": php_used,
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


def purge_ols_lscache(domain: str) -> dict:
    """Purge OpenLiteSpeed LSCache on-disk entries for ``domain``.

    OLS stores cached pages under ``$LSWS_HOME/cachedata``; we remove any
    entries whose name contains the domain. (The WordPress LSCache plugin is
    also flushed via WP-CLI ``wp cache flush`` by the caller.)
    """
    domain = domain.lower()
    purged = []
    import shutil

    if os.path.isdir(CACHEDATA_DIR):
        try:
            for entry in os.listdir(CACHEDATA_DIR):
                if domain in entry.lower():
                    p = os.path.join(CACHEDATA_DIR, entry)
                    shutil.rmtree(p, ignore_errors=True)
                    purged.append(p)
        except Exception:
            pass
    # also touch the OLS cache to force a graceful invalidation
    run_ols_shell(f"touch {LSWS_HOME}/admin/conf/.cleancache 2>/dev/null || true")
    return {"success": True, "purged": purged, "msg": f"LSCache 已清除 ({domain})"}


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
