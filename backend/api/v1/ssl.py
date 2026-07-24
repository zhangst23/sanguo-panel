from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.site import Site
from backend.utils import ols_ssl_utils

router = APIRouter()


@router.get("/sites/{site_id}/status")
def get_ssl_status(
    site_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Real SSL status: cert presence, OLS deployment, issuer, expiry."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    st = ols_ssl_utils.get_ssl_status(site.domain)
    return {
        "status": site.ssl_status,  # 0 off, 1 on, 2 force https
        "has_cert": st["has_cert"],
        "deployed": st["deployed"],
        "issuer": st["issuer"],
        "expiry_date": st["expiry"],
        "domains": [site.domain] + (site.aliases or []),
    }


@router.post("/sites/{site_id}/apply")
def apply_ssl(
    site_id: int,
    email: str = None,
    force_https: bool = False,
    staging: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Issue a Let's Encrypt cert (certbot webroot) and deploy it to OLS 443."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # 1. Obtain the certificate
    issue = ols_ssl_utils.issue_ssl(site.domain, email, site.root_path, staging=staging)
    if not issue["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"证书签发失败: {(issue.get('stderr') or issue.get('stdout') or '')[-500:]}",
        )

    # 2. Deploy to OLS (443 SNI listener + vhost ssl block)
    deploy = ols_ssl_utils.deploy_ssl_to_ols(site.domain, force_https=force_https)
    if not deploy["success"]:
        raise HTTPException(status_code=500, detail=deploy["msg"])

    # 3. Persist state
    site.ssl_status = 2 if force_https else 1
    site.ssl_mode = "letsencrypt"
    site.https_force = force_https
    site.ssl_auto_renew = True
    if email:
        site.ssl_email = email
    try:
        st = ols_ssl_utils.get_ssl_status(site.domain)
        if st.get("expiry"):
            site.ssl_expire_at = st["expiry"]
    except Exception:
        pass
    db.commit()

    return {
        "success": True,
        "message": deploy["msg"],
        "status": site.ssl_status,
        "cert_dir": issue.get("cert_dir"),
    }


@router.post("/sites/{site_id}/disable")
def disable_ssl(
    site_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Remove the OLS ssl block + 443 mapping for the site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    res = ols_ssl_utils.disable_ssl_ols(site.domain)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["msg"])

    site.ssl_status = 0
    site.ssl_mode = "none"
    site.https_force = False
    db.commit()
    return {"success": True, "message": res["msg"], "status": 0}


@router.post("/sites/{site_id}/renew")
def renew_ssl(
    site_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Renew the site's cert (certbot renew) and restart OLS to pick it up."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    res = ols_ssl_utils.renew_ssl(site.domain)
    if not res["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"续期失败: {(res.get('stderr') or res.get('stdout') or '')[-500:]}",
        )
    return {"success": True, "message": f"证书已续期 ({site.domain})"}
