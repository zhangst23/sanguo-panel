from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.site import Site
from backend.models.config import GlobalOption
import requests

router = APIRouter()
CF_API = "https://api.cloudflare.com/client/v4"


def _cf_token(db: Session):
    opt = db.query(GlobalOption).filter(GlobalOption.option_key == "cloudflare_api_token").first()
    return opt.option_value if opt else None


def _cf_zone_id(db: Session, domain: str):
    cache_key = f"cf_zone_id:{domain}"
    opt = db.query(GlobalOption).filter(GlobalOption.option_key == cache_key).first()
    if opt and opt.option_value:
        return opt.option_value
    token = _cf_token(db)
    if not token:
        return None
    try:
        r = requests.get(f"{CF_API}/zones", headers={"Authorization": f"Bearer {token}"}, params={"name": domain}, timeout=15)
        data = r.json()
        if data.get("success") and data.get("result"):
            zid = data["result"][0]["id"]
            db.add(GlobalOption(option_key=cache_key, option_value=zid))
            db.commit()
            return zid
    except Exception:
        pass
    return None


@router.get("/sites/{site_id}/config")
def get_cdn_config(site_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    token = _cf_token(db)
    zone_id = _cf_zone_id(db, site.domain) if token else None
    return {"provider": "Cloudflare", "status": "connected" if (token and zone_id) else "disconnected", "cname": f"cdn.{site.domain}", "api_token_set": bool(token), "zone_id": zone_id}


@router.post("/sites/{site_id}/connect")
def connect_cdn(site_id: int, api_token: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    try:
        r = requests.get(f"{CF_API}/zones", headers={"Authorization": f"Bearer {api_token}"}, params={"name": site.domain}, timeout=15)
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cloudflare API 不可达: {e}")
    if not data.get("success"):
        raise HTTPException(status_code=400, detail=f"Cloudflare 鉴权失败: {data.get('errors')}")
    opt = db.query(GlobalOption).filter(GlobalOption.option_key == "cloudflare_api_token").first()
    if not opt:
        opt = GlobalOption(option_key="cloudflare_api_token", option_value=api_token)
        db.add(opt)
    else:
        opt.option_value = api_token
    db.commit()
    zone_id = data["result"][0]["id"] if data.get("result") else None
    if zone_id:
        ck = f"cf_zone_id:{site.domain}"
        zo = db.query(GlobalOption).filter(GlobalOption.option_key == ck).first()
        if not zo:
            db.add(GlobalOption(option_key=ck, option_value=zone_id))
        else:
            zo.option_value = zone_id
        db.commit()
    return {"success": True, "message": f"已连接 {site.domain} 到 Cloudflare", "zone_id": zone_id, "status": "verified" if zone_id else "token-valid-but-zone-not-found"}


@router.post("/sites/{site_id}/purge")
def purge_cdn_cache(site_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    token = _cf_token(db)
    zone_id = _cf_zone_id(db, site.domain)
    if not token or not zone_id:
        raise HTTPException(status_code=400, detail="Cloudflare 未连接或找不到该域名的 zone")
    try:
        r = requests.post(f"{CF_API}/zones/{zone_id}/purge_cache", headers={"Authorization": f"Bearer {token}"}, json={"purge_everything": True}, timeout=20)
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cloudflare API 不可达: {e}")
    if not data.get("success"):
        raise HTTPException(status_code=500, detail=f"清除 CDN 缓存失败: {data.get('errors')}")
    return {"success": True, "message": f"Cloudflare 全量缓存已清除 ({site.domain})"}
