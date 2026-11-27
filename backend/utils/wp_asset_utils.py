"""Helpers for the local WordPress core / theme / plugin package library."""

import os
import re
import shutil
import subprocess
import zipfile

import requests

from backend.models.config import GlobalOption
from backend.models.wp_asset import WpAsset

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PACKAGES_DIR = os.path.join(PROJECT_ROOT, "backend", "assets", "packages")
KIND_DIRS = {"core": "core", "theme": "themes", "plugin": "plugins"}
DEFAULT_WP_VERSION = "6.5.5"
DEFAULT_OPTION_KEY = "default_wp_version"
CORE_DOWNLOAD_URL = "https://cn.wordpress.org/wordpress-{version}-zh_CN.zip"
MAX_UPLOAD_SIZE = 200 * 1024 * 1024
VERSION_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")


def validate_version(version: str) -> str:
    """Accept only numeric WordPress versions so they are safe in file names."""
    value = (version or "").strip()
    if not VERSION_RE.match(value):
        raise ValueError("版本号格式不正确，例如 6.5.5")
    return value


def get_default_wp_version(db) -> str:
    option = db.query(GlobalOption).filter(GlobalOption.option_key == DEFAULT_OPTION_KEY).first()
    value = option.option_value if option else None
    return validate_version(value) if value else DEFAULT_WP_VERSION


def set_default_wp_version(db, version: str) -> str:
    version = validate_version(version)
    option = db.query(GlobalOption).filter(GlobalOption.option_key == DEFAULT_OPTION_KEY).first()
    if not option:
        db.add(GlobalOption(option_key=DEFAULT_OPTION_KEY, option_value=version,
                            description="新建站点使用的 WordPress 默认版本"))
    else:
        option.option_value = version
    db.commit()
    return version


def package_dir(kind: str) -> str:
    directory = os.path.join(PACKAGES_DIR, KIND_DIRS[kind])
    os.makedirs(directory, exist_ok=True)
    return directory


def core_filename(version: str) -> str:
    return f"wordpress-{validate_version(version)}-zh_CN.zip"


def core_zip_path(version: str) -> str:
    return os.path.join(package_dir("core"), core_filename(version))


def asset_filename(kind: str, slug: str, version: str = None) -> str:
    safe_slug = re.sub(r"[^a-zA-Z0-9_.-]", "-", (slug or "package").strip())[:80]
    safe_version = re.sub(r"[^a-zA-Z0-9_.-]", "-", version.strip())[:32] if version else ""
    suffix = f"-{safe_version}" if safe_version else ""
    return f"{safe_slug}{suffix}.zip"


def to_relative_path(path: str) -> str:
    return os.path.relpath(path, PROJECT_ROOT).replace(os.sep, "/")


def resolve_package_path(file_path: str) -> str:
    """Resolve a stored path and refuse anything outside the package library."""
    if not file_path or not isinstance(file_path, str):
        raise ValueError("资源文件路径无效")
    base = os.path.realpath(PACKAGES_DIR)
    full = os.path.realpath(file_path if os.path.isabs(file_path)
                            else os.path.join(PROJECT_ROOT, file_path))
    if full != base and not full.startswith(base + os.sep):
        raise ValueError("资源文件路径超出允许目录")
    return full


def is_valid_zip(path: str) -> bool:
    if not os.path.isfile(path) or not zipfile.is_zipfile(path):
        return False
    try:
        with zipfile.ZipFile(path) as zf:
            return bool(zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return False


def fetch_core_package(version: str) -> str:
    """Return a cached core zip, downloading it from wordpress.org once if needed."""
    version = validate_version(version)
    target = core_zip_path(version)
    if is_valid_zip(target):
        return target

    url = CORE_DOWNLOAD_URL.format(version=version)
    temp = target + ".part"
    try:
        response = requests.get(url, timeout=(15, 180), stream=True)
        response.raise_for_status()
        with open(temp, "wb") as out:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    out.write(chunk)
    except Exception as exc:
        if os.path.exists(temp):
            os.remove(temp)
        raise RuntimeError(f"WordPress {version} 下载失败: {exc}") from exc

    if not is_valid_zip(temp):
        os.remove(temp)
        raise RuntimeError(f"WordPress {version} 下载内容不是有效的 zip 包")
    os.replace(temp, target)
    return target


def ensure_core_package(version: str) -> str:
    return fetch_core_package(version)


def extract_core_package(zip_path: str, target_dir: str) -> None:
    """Extract a core zip into target_dir, stripping the usual wordpress/ prefix."""
    os.makedirs(target_dir, exist_ok=True)
    base = os.path.realpath(target_dir)
    with zipfile.ZipFile(zip_path) as zf:
        names = [name for name in zf.namelist() if not name.endswith("/")]
        prefix = "wordpress/" if names and all(n.startswith("wordpress/") for n in names) else ""
        for name in zf.namelist():
            relative = name[len(prefix):] if prefix and name.startswith(prefix) else name
            if not relative or relative.endswith("/"):
                continue
            destination = os.path.realpath(os.path.join(base, relative.replace("/", os.sep)))
            if destination != base and not destination.startswith(base + os.sep):
                raise RuntimeError("WordPress 安装包包含非法路径")
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with zf.open(name) as source, open(destination, "wb") as out:
                shutil.copyfileobj(source, out)


def install_default_assets(db, php_path: str, wp_cli_path: str, site_root: str) -> str:
    """Install all enabled default themes/plugins from local zips into a new site."""
    defaults = (db.query(WpAsset)
                  .filter(WpAsset.is_default.is_(True), WpAsset.enabled.is_(True),
                          WpAsset.kind.in_(["theme", "plugin"]))
                  .order_by(WpAsset.kind, WpAsset.id).all())
    installed, failed = [], []
    for asset in defaults:
        try:
            path = resolve_package_path(asset.file_path)
            if not os.path.isfile(path):
                raise FileNotFoundError(os.path.basename(path))
            subprocess.run(
                [php_path, wp_cli_path, asset.kind, "install", path,
                 "--activate", "--force", f"--path={site_root}", "--allow-root"],
                check=True, capture_output=True, timeout=300,
            )
            installed.append(asset.name or asset.slug or os.path.basename(path))
        except Exception as exc:
            print(f"Failed to install default {asset.kind} {asset.name}: {exc}")
            failed.append(asset.name or asset.slug or str(exc))
    notes = ""
    if installed:
        notes += "\n✅ 已安装默认资源: " + ", ".join(installed)
    if failed:
        notes += "\n⚠️ 默认资源安装失败: " + ", ".join(failed)
    return notes
