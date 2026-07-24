from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.site import Site
import os

router = APIRouter()


def _walk_assets(root: str, exts):
    if not os.path.isdir(root):
        return []
    out = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(exts) and ".min." not in fn.lower():
                out.append(os.path.join(dp, fn))
    return out


def _minify_file(path: str, kind: str) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            src = f.read()
        before = len(src.encode("utf-8"))
        if kind == "css":
            import rcssmin
            out = rcssmin.cssmin(src)
        else:
            import rjsmin
            out = rjsmin.jsmin(src)
        base, ext = os.path.splitext(path)
        min_path = base + ".min" + ext
        with open(min_path, "w", encoding="utf-8") as f:
            f.write(out)
        after = len(out.encode("utf-8"))
        return max(before - after, 0)
    except Exception:
        return 0


@router.get("/sites/{site_id}/status")
def get_asset_status(site_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    root = site.root_path
    css = _walk_assets(root, ".css")
    js = _walk_assets(root, ".js")
    total_size = 0
    for p in css + js:
        try:
            total_size += os.path.getsize(p)
        except OSError:
            pass
    return {
        "css_files": len(css),
        "js_files": len(js),
        "total_assets": len(css) + len(js),
        "optimizable_size_kb": round(total_size / 1024, 1),
        "css_minified": False,
        "js_minified": False,
    }


@router.post("/sites/{site_id}/optimize")
def optimize_assets(
    site_id: int,
    minify_css: bool = True,
    minify_js: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Real CSS/JS minification: writes .min.css/.min.js alongside originals."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    root = site.root_path

    css_saved = js_saved = 0
    css_n = js_n = 0
    if minify_css:
        for p in _walk_assets(root, ".css"):
            css_saved += _minify_file(p, "css")
            css_n += 1
    if minify_js:
        for p in _walk_assets(root, ".js"):
            js_saved += _minify_file(p, "js")
            js_n += 1

    return {
        "success": True,
        "message": f"资源优化完成 for {site.domain}",
        "details": {
            "css_minified": css_n, "js_minified": js_n,
            "saved_kb": round((css_saved + js_saved) / 1024, 1),
        },
    }
