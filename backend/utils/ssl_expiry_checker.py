import subprocess
import ssl
import socket
import time
import threading
from datetime import datetime, timedelta
from backend.core.database import SessionLocal
from backend.models.site import Site


def _get_cert_expiry(hostname, port=443):
    """Connect to hostname:port and return the cert notAfter date string (YYYY-MM-DD)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                expiry_str = cert.get("notAfter", "")
                if expiry_str:
                    dt = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                    return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # Fallback: use openssl (works for local files too)
    try:
        r = subprocess.run(
            ["openssl", "s_client", "-servername", hostname, "-connect", f"{hostname}:{port}"],
            input=b"", capture_output=True, timeout=15
        )
        r2 = subprocess.run(
            ["openssl", "x509", "-noout", "-enddate"],
            input=r.stdout, capture_output=True, timeout=10
        )
        output = r2.stdout.decode()
        for line in output.splitlines():
            if line.startswith("notAfter="):
                expiry_str = line.split("=", 1)[1].strip()
                dt = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    return None


def check_all_sites_ssl():
    """Check SSL expiry for all active sites and update ssl_expire_at."""
    db = SessionLocal()
    try:
        sites = db.query(Site).filter(Site.status == "active").all()
        for site in sites:
            if site.ssl_mode == "letsencrypt":
                # Check local Let's Encrypt cert
                cert_path = f"/etc/letsencrypt/live/{site.domain}/fullchain.pem"
                try:
                    r = subprocess.run(
                        ["openssl", "x509", "-in", cert_path, "-noout", "-enddate"],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in r.stdout.splitlines():
                        if line.startswith("notAfter="):
                            expiry_str = line.split("=", 1)[1].strip()
                            dt = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                            site.ssl_expire_at = dt.strftime("%Y-%m-%d")
                            break
                except Exception:
                    pass
            elif site.ssl_mode == "cloudflare":
                expiry = _get_cert_expiry(site.domain, 443)
                if expiry:
                    site.ssl_expire_at = expiry
            db.add(site)
        db.commit()
    except Exception as e:
        print(f"[SSL Checker] Error: {e}")
    finally:
        db.close()


def start_ssl_checker():
    """Run initial check, then schedule daily checks via background thread."""
    print("[SSL Checker] Starting initial SSL expiry check...")
    check_all_sites_ssl()

    def daily_loop():
        while True:
            time.sleep(24 * 3600)
            print("[SSL Checker] Running daily SSL expiry check...")
            check_all_sites_ssl()

    t = threading.Thread(target=daily_loop, daemon=True)
    t.start()
