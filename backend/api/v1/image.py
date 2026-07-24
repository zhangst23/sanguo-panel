from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.site import Site
import os
import subprocess

router = APIRouter()

IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif"}


def _uploads_dir(site: Site) -> str:
    return os.path.join(site.root_path, "wp-content", "uploads")


def _scan_images(root: str):
    total = 0
    size = 0
    files = []
    if not os.path.isdir(root):
        return 0, 0, []
    for dirpath, _, fnames in os.walk(root):
        for fn in fnames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in IMG_EXTS:
                p = os.path.join(dirpath, fn)
                try:
                    s = os.path.getsize(p)
                except OSError:
                    continue
                total += 1
                size += s
                files.append(p)
    return total, size, files


@router.get("/sites/{site_id}/stats")
def get_image_stats(site_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    uploads = _uploads_dir(site)
    total, size, _ = _scan_images(uploads)
    webp = 0
    if os.path.isdir(uploads):
        for dp, _, fns in os.walk(uploads):
            webp += sum(1 for f in fns if f.lower().endswith(".webp"))
    return {
        "total_images": total,
        "optimized_images": webp,
        "unoptimized_images": max(total - webp, 0),
        "total_size_mb": round(size / 1024 / 1024, 2),
        "space_saved_mb": 0,
        "webp_converted": webp,
        "avif_converted": 0,
    }


@router.post("/sites/{site_id}/optimize")
def optimize_images(
    site_id: int,
    quality: int = 80,
    convert_webp: bool = False,
    convert_avif: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Real lossy/lossless compression of the media library (uploads)."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    uploads = _uploads_dir(site)
    total, before_size, files = _scan_images(uploads)

    jpg = png = gif = 0
    for p in files:
        ext = os.path.splitext(p)[1].lower()
        try:
            if ext in (".jpg", ".jpeg"):
                subprocess.run(
                    ["jpegoptim", f"--max={int(quality)}", "--strip-all", "--all-progressive", "-q", p],
                    capture_output=True, timeout=60,
                )
                jpg += 1
            elif ext == ".png":
                tmp = p + ".pngq.png"
                r = subprocess.run(
                    ["pngquant", "--quality=60-85", "--force", "--output", tmp, p],
                    capture_output=True, timeout=60,
                )
                if r.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) < os.path.getsize(p):
                    os.replace(tmp, p)
                elif os.path.exists(tmp):
                    os.remove(tmp)
                subprocess.run(["optipng", "-o2", "-quiet", p], capture_output=True, timeout=60)
                png += 1
            elif ext == ".gif":
                subprocess.run(["optipng", "-o2", "-quiet", p], capture_output=True, timeout=60)
                gif += 1
        except Exception:
            continue

    _, after_size, _ = _scan_images(uploads)
    saved = max(before_size - after_size, 0)
    return {
        "success": True,
        "message": f"图片优化完成 for {site.domain}",
        "details": {
            "jpeg": jpg, "png": png, "gif": gif,
            "before_mb": round(before_size / 1024 / 1024, 2),
            "after_mb": round(after_size / 1024 / 1024, 2),
            "saved_mb": round(saved / 1024 / 1024, 2),
        },
    }
