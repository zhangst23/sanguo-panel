from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import stat
import mimetypes
import io
from datetime import datetime

from backend.api import deps
from backend.models.user import User
from backend.models.site import Site

router = APIRouter()


def _resolve_site_root(site: Site, requested_path: Optional[str]) -> str:
    """校验请求路径必须在站点根目录内，防止越权访问。"""
    site_root = os.path.realpath(site.root_path) if site.root_path else ""
    if not site_root or not os.path.exists(site_root):
        raise HTTPException(status_code=404, detail="站点根目录不存在")

    if not requested_path:
        return site_root
    target = os.path.realpath(requested_path)
    # 必须在 site_root 之下
    if os.path.commonpath([site_root, target]) != site_root:
        raise HTTPException(status_code=403, detail="禁止访问站点根目录之外的路径")
    return target


@router.get("/list")
def list_files(
    site_id: int,
    path: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """列出指定目录下的文件/文件夹"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    try:
        target = _resolve_site_root(site, path)
    except HTTPException:
        raise

    if not os.path.isdir(target):
        raise HTTPException(status_code=400, detail="目标不是目录")

    items = []
    try:
        for name in sorted(os.listdir(target)):
            full_path = os.path.join(target, name)
            try:
                st = os.stat(full_path)
                is_dir = stat.S_ISDIR(st.st_mode)
                # 权限字符串
                mode = stat.filemode(st.st_mode)
                size = st.st_size if not is_dir else 0
                mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                items.append({
                    "name": name,
                    "path": full_path,
                    "is_dir": is_dir,
                    "size": size,
                    "mode": mode,
                    "mtime": mtime,
                })
            except (PermissionError, FileNotFoundError):
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问此目录")

    # 目录排在前面
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {"items": items, "current_path": target, "site_root": site.root_path}


@router.post("/mkdir")
def create_folder(
    site_id: int,
    path: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """创建文件夹"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    try:
        target = _resolve_site_root(site, path)
        if os.path.exists(target):
            raise HTTPException(status_code=400, detail="路径已存在")
        os.makedirs(target, exist_ok=False)
        return {"success": True, "path": target}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {e}")


@router.post("/rename")
def rename_item(
    site_id: int,
    src: str,
    dst: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """重命名文件/文件夹"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    try:
        src_path = _resolve_site_root(site, src)
        dst_path = _resolve_site_root(site, dst)
        if not os.path.exists(src_path):
            raise HTTPException(status_code=404, detail="源路径不存在")
        if os.path.exists(dst_path):
            raise HTTPException(status_code=400, detail="目标路径已存在")
        os.rename(src_path, dst_path)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名失败: {e}")


@router.post("/delete")
def delete_item(
    site_id: int,
    path: str,
    is_dir: bool = False,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """删除文件/文件夹"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    try:
        target = _resolve_site_root(site, path)
        if not os.path.exists(target):
            raise HTTPException(status_code=404, detail="路径不存在")
        if is_dir:
            shutil.rmtree(target)
        else:
            os.remove(target)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")


@router.post("/chmod")
def chmod_item(
    site_id: int,
    path: str,
    mode: int = 0o777,
    recursive: bool = True,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """放开权限（chmod 777）"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    try:
        target = _resolve_site_root(site, path)
        if not os.path.exists(target):
            raise HTTPException(status_code=404, detail="路径不存在")

        count = 0
        if os.path.isdir(target):
            if recursive:
                for root, dirs, files in os.walk(target):
                    for d in dirs:
                        try:
                            os.chmod(os.path.join(root, d), mode)
                            count += 1
                        except Exception:
                            pass
                    for f in files:
                        try:
                            os.chmod(os.path.join(root, f), mode)
                            count += 1
                        except Exception:
                            pass
            else:
                os.chmod(target, mode)
                count = 1
        else:
            os.chmod(target, mode)
            count = 1
        return {"success": True, "changed": count, "mode": oct(mode)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"权限修改失败: {e}")


@router.get("/size")
def calc_size(
    site_id: int,
    path: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """递归计算目录大小"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    try:
        target = _resolve_site_root(site, path)
        if not os.path.exists(target):
            raise HTTPException(status_code=404, detail="路径不存在")

        total = 0
        file_count = 0
        if os.path.isdir(target):
            for root, dirs, files in os.walk(target):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total += os.path.getsize(fp)
                        file_count += 1
                    except (OSError, FileNotFoundError):
                        pass
        else:
            total = os.path.getsize(target)
            file_count = 1

        return {
            "path": target,
            "size": total,
            "size_human": _format_size(total),
            "file_count": file_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算失败: {e}")


@router.post("/upload")
async def upload_files(
    site_id: int = Form(...),
    path: str = Form(""),
    files: List[UploadFile] = File(...),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """上传文件到指定目录"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    try:
        target = _resolve_site_root(site, path)
        if not os.path.isdir(target):
            raise HTTPException(status_code=400, detail="目标不是目录")
        saved = []
        for f in files:
            # 安全文件名：去掉路径分隔符
            safe_name = os.path.basename(f.filename or "file")
            dest = os.path.join(target, safe_name)
            with open(dest, "wb") as out:
                shutil.copyfileobj(f.file, out)
            saved.append(safe_name)
        return {"success": True, "saved": saved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}")


@router.get("/download")
def download_file(
    site_id: int,
    path: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """下载文件"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    try:
        target = _resolve_site_root(site, path)
        if not os.path.exists(target):
            raise HTTPException(status_code=404, detail="文件不存在")
        if os.path.isdir(target):
            raise HTTPException(status_code=400, detail="不能直接下载目录")
        return FileResponse(target, filename=os.path.basename(target))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {e}")


def _format_size(size: int) -> str:
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    n = float(size)
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.2f} {units[i]}"
