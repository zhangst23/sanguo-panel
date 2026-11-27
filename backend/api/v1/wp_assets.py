import io
import os
import zipfile
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api import deps
from backend.models.wp_asset import WpAsset as WpAssetModel
from backend.schemas.wp_asset import (
    CliInstallRequest,
    DefaultsResponse,
    VersionRequest,
    WpAsset,
    WpAssetUpdate,
)
from backend.utils.wp_asset_utils import (
    asset_filename,
    core_zip_path,
    fetch_asset_with_wp_cli,
    fetch_core_package,
    get_default_wp_version,
    package_dir,
    resolve_package_path,
    set_default_wp_version,
    to_relative_path,
    validate_version,
)

router = APIRouter()


def _get_asset(db: Session, asset_id: int) -> WpAssetModel:
    asset = db.query(WpAssetModel).filter(WpAssetModel.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资源不存在")
    return asset


def _check_kind(kind: Optional[str]) -> Optional[str]:
    if kind is None:
        return None
    if kind not in ("core", "theme", "plugin"):
        raise HTTPException(status_code=400, detail="资源类型必须是 core / theme / plugin")
    return kind


@router.get("", response_model=List[WpAsset])
@router.get("/", response_model=List[WpAsset])
def list_assets(
    kind: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    query = db.query(WpAssetModel)
    kind = _check_kind(kind)
    if kind:
        query = query.filter(WpAssetModel.kind == kind)
    return query.order_by(WpAssetModel.kind, WpAssetModel.id).all()


@router.get("/defaults", response_model=DefaultsResponse)
def get_defaults(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    default_version = get_default_wp_version(db)
    versions = {default_version}
    for asset in db.query(WpAssetModel).filter(WpAssetModel.kind == "core").all():
        if asset.version:
            versions.add(asset.version)
    return {
        "default_version": default_version,
        "versions": sorted(versions, reverse=True),
        "default_themes": db.query(WpAssetModel).filter(
            WpAssetModel.kind == "theme", WpAssetModel.is_default.is_(True),
            WpAssetModel.enabled.is_(True)).all(),
        "default_plugins": db.query(WpAssetModel).filter(
            WpAssetModel.kind == "plugin", WpAssetModel.is_default.is_(True),
            WpAssetModel.enabled.is_(True)).all(),
    }


@router.put("/default-version")
def update_default_version(
    payload: VersionRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    version = set_default_wp_version(db, payload.version)
    return {"success": True, "default_version": version}


@router.post("/core/fetch", response_model=WpAsset)
def fetch_core(
    payload: VersionRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    """Fetch a WordPress version from the official site and register it locally."""
    version = validate_version(payload.version)
    try:
        path = fetch_core_package(version)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    asset = (db.query(WpAssetModel)
             .filter(WpAssetModel.kind == "core", WpAssetModel.version == version).first())
    if not asset:
        asset = WpAssetModel(kind="core", name=f"WordPress {version}", version=version,
                             source="official")
        db.add(asset)
    asset.file_path = to_relative_path(path)
    asset.file_size = os.path.getsize(path)
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/upload", response_model=WpAsset)
async def upload_asset(
    file: UploadFile = File(...),
    kind: str = Form(...),
    name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    kind = _check_kind(kind)
    if kind is None:
        raise HTTPException(status_code=400, detail="缺少资源类型")
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="请上传 .zip 格式的包")
    if kind == "core":
        if not version:
            raise HTTPException(status_code=400, detail="上传 WordPress 核心包必须填写版本号")
        version = validate_version(version)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(content) > 200 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件不能超过 200MB")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            if not names:
                raise ValueError("压缩包为空")
            if kind == "core" and not any(n.endswith("wp-settings.php") for n in names):
                raise ValueError("压缩包内没有 wp-settings.php，不是 WordPress 核心包")
    except (zipfile.BadZipFile, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"无效的 zip 包: {exc}")

    filename = (core_zip_path(version) if kind == "core"
                else os.path.join(package_dir(kind), asset_filename(kind, slug or name or "package", version)))
    with open(filename, "wb") as out:
        out.write(content)

    asset = WpAssetModel(
        kind=kind,
        name=(name or (f"WordPress {version}" if kind == "core" else os.path.splitext(file.filename)[0])),
        slug=slug if kind != "core" else None,
        version=version,
        file_path=to_relative_path(filename),
        file_size=len(content),
        source="upload",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/cli-install", response_model=WpAsset)
def cli_install_asset(
    payload: CliInstallRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    """通过 WP-CLI 按主题/插件名称（slug）下载并加入本地资源库。"""
    try:
        return fetch_asset_with_wp_cli(db, payload.kind, payload.slug)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"WP-CLI 安装失败: {exc}")


@router.put("/{asset_id}", response_model=WpAsset)
def update_asset(
    asset_id: int,
    payload: WpAssetUpdate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    asset = _get_asset(db, asset_id)
    for field in ("name", "slug", "version", "enabled", "notes"):
        value = getattr(payload, field)
        if value is not None:
            setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}")
def delete_asset(
    asset_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    asset = _get_asset(db, asset_id)
    try:
        path = resolve_package_path(asset.file_path)
        if os.path.isfile(path):
            os.remove(path)
    except ValueError:
        pass  # Never delete files outside the library; drop the stale record only.
    db.delete(asset)
    db.commit()
    return {"success": True}


@router.post("/{asset_id}/set-default")
def set_default(
    asset_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    asset = _get_asset(db, asset_id)
    if asset.kind == "core":
        if not asset.version:
            raise HTTPException(status_code=400, detail="该核心包没有版本号")
        set_default_wp_version(db, asset.version)

    others = (db.query(WpAssetModel)
              .filter(WpAssetModel.kind == asset.kind, WpAssetModel.id != asset.id).all())
    for other in others:
        other.is_default = False
    asset.is_default = True
    db.commit()
    db.refresh(asset)
    return {"success": True, "asset": asset}
