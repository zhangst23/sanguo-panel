"""
OpenLiteSpeed SSL management via Let's Encrypt (certbot HTTP-01 webroot).

OLS 1.9.x PlainConf does NOT support a per-vhost ``ssl{}`` block in the
included vhconf, so SSL is configured at the LISTENER level (matching the
built-in admin server on 7080): a ``Panel443`` secure listener holds
``keyFile``/``certFile`` and maps each SSL-enabled domain to its vhost.
Force-HTTPS is implemented as a vhost rewrite rule.
"""
import os
import re
import shutil
import subprocess

from backend.utils.ols_utils import (
    LSWS_HOME,
    OLS_CONF,
    VHOSTS_DIR,
    restart_ols,
)

LE_LIVE = "/etc/letsencrypt/live"
PANEL443 = "Panel443"


def _cert_paths(domain: str):
    base = os.path.join(LE_LIVE, domain)
    return base, os.path.join(base, "privkey.pem"), os.path.join(base, "fullchain.pem")


def issue_ssl(domain: str, email: str, root_path: str, staging: bool = False) -> dict:
    """Obtain a Let's Encrypt cert via certbot HTTP-01 webroot."""
    domain = domain.lower()
    cmd = [
        "certbot", "certonly", "--webroot", "-w", root_path,
        "-d", domain, "--agree-tos", "-n", "--cert-name", domain,
    ]
    if email:
        cmd += ["-m", email]
    else:
        cmd += ["--register-unsafely-without-email"]
    if staging:
        cmd.append("--staging")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception as e:
        return {"success": False, "stderr": str(e)}
    base, key, cert = _cert_paths(domain)
    ok = r.returncode == 0 and os.path.exists(key) and os.path.exists(cert)
    return {"success": ok, "stdout": r.stdout, "stderr": r.stderr, "cert_dir": base}


def renew_ssl(domain: str = None) -> dict:
    """Renew certs (optionally one domain) and restart OLS to pick them up."""
    hook = f"{LSWS_HOME}/bin/lswsctrl restart"
    if domain:
        cmd = ["certbot", "renew", "--cert-name", domain.lower(), "--deploy-hook", hook]
    else:
        cmd = ["certbot", "renew", "--deploy-hook", hook]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        return {"success": False, "stderr": str(e)}
    return {"success": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr}


def _force_https_rules() -> str:
    return (
        "# Force HTTPS\n"
        "RewriteCond %{HTTPS} off\n"
        "RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]\n"
    )


def _set_force_https(vh: str, force_https: bool) -> str:
    fh = _force_https_rules()
    if force_https:
        if "# Force HTTPS" not in vh and "<<<END_rules\n" in vh:
            vh = vh.replace("<<<END_rules\n", "<<<END_rules\n" + fh, 1)
    else:
        vh = re.sub(
            r"# Force HTTPS\nRewriteCond %\{HTTPS\} off\nRewriteRule .*?\[R=301,L\]\n",
            "", vh, flags=re.DOTALL,
        )
    return vh


def _ensure_panel443_ssl(conf: str, domain: str) -> str:
    """Ensure a Panel443 secure listener exists with the domain's cert + map."""
    _, key, cert = _cert_paths(domain)
    if "listener Panel443{" in conf:
        line = f"    map                      {domain} {domain}\n"
        if line.strip() not in conf:
            pat = re.compile(r"(listener " + re.escape(PANEL443) + r"\{.*?\n)\}", re.DOTALL)
            m = pat.search(conf)
            if m:
                conf = conf[: m.end() - 1] + line + conf[m.end() - 1 :]
        return conf
    block = (
        "\nlistener Panel443{\n"
        "    address                  *:443\n"
        "    secure                   1\n"
        f"    keyFile                  {key}\n"
        f"    certFile                 {cert}\n"
        f"    map                      {domain} {domain}\n"
        "}\n"
    )
    return conf + block


def _remove_listener_map(conf: str, domain: str) -> str:
    conf = re.sub(r"\s*map\s+\S+\s+" + re.escape(domain) + r"\n", "\n", conf)
    pat = re.compile(r"\n?listener Panel443\{.*?\n\}\n?", re.DOTALL)
    m = pat.search(conf)
    if m and "map" not in m.group(0):
        conf = pat.sub("\n", conf)
    return conf


def _validate_ols():
    try:
        r = subprocess.run(
            [f"{LSWS_HOME}/bin/lshttpd", "-t"],
            capture_output=True, text=True, timeout=20,
        )
    except Exception as e:
        return False, str(e)
    out = (r.stdout or "") + (r.stderr or "")
    # lshttpd -t exits non-zero on mere WARNs (e.g. root-owned docroots), which
    # are non-fatal; only real [ERROR] lines indicate a broken config.
    ok = "[ERROR]" not in out
    return ok, out


def deploy_ssl_to_ols(domain: str, force_https: bool = False) -> dict:
    """Deploy an already-issued cert to OLS via the Panel443 secure listener."""
    domain = domain.lower()
    _, key, cert = _cert_paths(domain)
    if not (os.path.exists(key) and os.path.exists(cert)):
        return {"success": False, "msg": f"证书文件不存在，请先签发: {LE_LIVE}/{domain}"}
    vhconf_path = os.path.join(VHOSTS_DIR, domain, "vhconf.conf")
    if not os.path.exists(vhconf_path):
        return {"success": False, "msg": "虚拟主机配置不存在"}

    bak_conf = OLS_CONF + ".sslbak"
    bak_vh = vhconf_path + ".sslbak"
    shutil.copy2(OLS_CONF, bak_conf)
    shutil.copy2(vhconf_path, bak_vh)

    try:
        with open(vhconf_path) as f:
            vh = f.read()
        vh = _set_force_https(vh, force_https)
        with open(vhconf_path, "w") as f:
            f.write(vh)

        with open(OLS_CONF) as f:
            conf = f.read()
        conf = _ensure_panel443_ssl(conf, domain)
        with open(OLS_CONF, "w") as f:
            f.write(conf)

        ok, out = _validate_ols()
        if not ok:
            shutil.move(bak_conf, OLS_CONF)
            shutil.move(bak_vh, vhconf_path)
            restart_ols()
            return {"success": False, "msg": f"OLS 配置校验失败，已回滚: {out[-300:]}"}

        os.remove(bak_conf)
        os.remove(bak_vh)
        res = restart_ols()
        return {
            "success": res["success"],
            "msg": f"SSL 已部署到 OLS 443 ({domain})" + ("，并强制 HTTPS" if force_https else ""),
        }
    except Exception as e:
        try:
            shutil.move(bak_conf, OLS_CONF)
            shutil.move(bak_vh, vhconf_path)
            restart_ols()
        except Exception:
            pass
        return {"success": False, "msg": f"部署异常已回滚: {e}"}


def disable_ssl_ols(domain: str) -> dict:
    """Remove the 443 mapping (and the listener if empty) + force_https rule."""
    domain = domain.lower()
    vhconf_path = os.path.join(VHOSTS_DIR, domain, "vhconf.conf")
    bak_conf = OLS_CONF + ".sslbak"
    bak_vh = vhconf_path + ".sslbak"
    shutil.copy2(OLS_CONF, bak_conf)
    if os.path.exists(vhconf_path):
        shutil.copy2(vhconf_path, bak_vh)

    try:
        if os.path.exists(vhconf_path):
            with open(vhconf_path) as f:
                vh = f.read()
            vh = re.sub(
                r"# Force HTTPS\nRewriteCond %\{HTTPS\} off\nRewriteRule .*?\[R=301,L\]\n",
                "", vh, flags=re.DOTALL,
            )
            with open(vhconf_path, "w") as f:
                f.write(vh)

        with open(OLS_CONF) as f:
            conf = f.read()
        conf = _remove_listener_map(conf, domain)
        with open(OLS_CONF, "w") as f:
            f.write(conf)

        ok, out = _validate_ols()
        if not ok:
            shutil.move(bak_conf, OLS_CONF)
            if os.path.exists(bak_vh):
                shutil.move(bak_vh, vhconf_path)
            restart_ols()
            return {"success": False, "msg": f"OLS 配置校验失败，已回滚: {out[-300:]}"}

        os.remove(bak_conf)
        if os.path.exists(bak_vh):
            os.remove(bak_vh)
        restart_ols()
        return {"success": True, "msg": f"SSL 已禁用 ({domain})"}
    except Exception as e:
        try:
            shutil.move(bak_conf, OLS_CONF)
            if os.path.exists(bak_vh):
                shutil.move(bak_vh, vhconf_path)
            restart_ols()
        except Exception:
            pass
        return {"success": False, "msg": f"禁用异常已回滚: {e}"}


def get_ssl_status(domain: str) -> dict:
    """Report cert presence, OLS deployment (Panel443 map), issuer and expiry."""
    domain = domain.lower()
    _, key, cert = _cert_paths(domain)
    has_cert = os.path.exists(key) and os.path.exists(cert)
    deployed = False
    try:
        with open(OLS_CONF) as f:
            conf = f.read()
        deployed = "listener Panel443{" in conf and (
            f"map                      {domain} {domain}" in conf
        )
    except Exception:
        pass
    issuer = "None"
    expiry = None
    if has_cert:
        try:
            r = subprocess.run(
                ["openssl", "x509", "-in", cert, "-noout", "-enddate", "-issuer"],
                capture_output=True, text=True, timeout=10,
            )
            for line in r.stdout.splitlines():
                if line.startswith("notAfter="):
                    expiry = line.split("=", 1)[1].strip()
                if line.startswith("issuer="):
                    issuer = line.split("=", 1)[1].strip()
        except Exception:
            pass
    return {
        "has_cert": has_cert,
        "deployed": deployed,
        "issuer": issuer,
        "expiry": expiry,
        "cert_dir": _cert_paths(domain)[0],
    }
