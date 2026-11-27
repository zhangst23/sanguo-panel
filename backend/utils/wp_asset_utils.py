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


def install_default_assets(db, php_path: str, wp_cli_path: str, site_root: str,
                           theme_id=None, plugin_ids=None) -> str:
    """Install themes/plugins into a new site from the local package library.

    When no explicit selection is provided, install everything flagged as a
    default (legacy behaviour). Otherwise install exactly the selected assets;
    an empty selection means "install nothing".
    """
    query = db.query(WpAsset).filter(
        WpAsset.enabled.is_(True), WpAsset.kind.in_(["theme", "plugin"]))
    if theme_id is None and plugin_ids is None:
        query = query.filter(WpAsset.is_default.is_(True))
    else:
        selected_ids = ([theme_id] if theme_id is not None else []) + list(plugin_ids or [])
        if not selected_ids:
            return ""
        query = query.filter(WpAsset.id.in_(selected_ids))
    defaults = query.order_by(WpAsset.kind, WpAsset.id).all()
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


def fetch_asset_with_wp_cli(db, kind: str, slug: str):
    """通过 WP-CLI 按名称/slug 从官方目录下载主题或插件并加入本地资源库。

    WP-CLI 的 ``plugin/theme install`` 需要完整的 WordPress 站点环境，因此这里
    临时创建一套 WordPress + 临时数据库，安装成功后把目录打包进资源库，最后
    清理临时文件与数据库。
    """
    import json
    import random
    import string
    import tempfile

    import mysql.connector

    from backend.models.site import SharedDatabase
    from backend.utils.db_admin import ensure_admin_account
    from backend.utils.site_utils import get_wp_cli_paths

    php_path, wp_cli_path = get_wp_cli_paths()
    if not php_path or not os.path.isfile(wp_cli_path):
        raise RuntimeError("WP-CLI 不可用，请检查 PHP 与 backend/bin/wp-cli.phar")

    shared_db = db.query(SharedDatabase).filter(SharedDatabase.status == "active").first()
    if not shared_db:
        raise RuntimeError("未找到可用的 MariaDB 配置")
    db_user, db_pass = ensure_admin_account(shared_db)
    if not db_user:
        raise RuntimeError("无法连接 MariaDB，请检查数据库配置")
    db.add(shared_db)
    db.commit()

    db_host = shared_db.db_host or "localhost"
    db_port = shared_db.db_port or 3306
    tmp_root = tempfile.mkdtemp(prefix="wp-cli-asset-")
    tmp_db = None

    def _connect():
        return mysql.connector.connect(
            host=db_host, port=int(db_port), user=db_user,
            password=db_pass or "", connect_timeout=10,
        )

    try:
        tmp_db = "wp_cli_tmp_" + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10))
        conn = _connect()
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE `{tmp_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        cur.close()
        conn.close()

        # 用本地默认核心包搭建临时站点
        zip_path = ensure_core_package(get_default_wp_version(db))
        wp_root = os.path.join(tmp_root, "wordpress")
        extract_core_package(zip_path, wp_root)

        def wp(*args, timeout=300):
            return subprocess.run(
                [php_path, wp_cli_path, *args, f"--path={wp_root}", "--allow-root"],
                capture_output=True, text=True, timeout=timeout,
            )

        def _failed(result):
            detail = (result.stderr or result.stdout or "WP-CLI 执行失败").strip()
            return RuntimeError(detail[-500:])

        config = wp("config", "create", f"--dbname={tmp_db}", f"--dbuser={db_user}",
                    f"--dbpass={db_pass}", f"--dbhost={db_host}", "--force")
        if config.returncode != 0:
            raise _failed(config)

        core = wp("core", "install", "--url=http://wp-cli.local", "--title=WP CLI",
                  "--admin_user=admin",
                  f"--admin_password={'tmp' + ''.join(random.choices(string.ascii_letters + string.digits, k=12))}",
                  "--admin_email=admin@wp-cli.local")
        if core.returncode != 0:
            raise _failed(core)

        install = wp(kind, "install", slug)
        if install.returncode != 0:
            raise _failed(install)

        info = {}
        detail = wp(kind, "get", slug, "--format=json")
        if detail.returncode == 0:
            try:
                info = json.loads(detail.stdout)
            except (ValueError, TypeError):
                pass

        # 定位安装后的目录（插件主文件是单文件时也能取到所在目录）
        path_args = ("plugin", "path", slug, "--dir") if kind == "plugin" else ("theme", "path", slug)
        found = wp(*path_args)
        source_dir = found.stdout.strip() if found.returncode == 0 else ""
        if not source_dir or not os.path.isdir(source_dir):
            base = os.path.join(wp_root, "wp-content", "themes" if kind == "theme" else "plugins")
            fallback = os.path.join(base, slug)
            source_dir = fallback if os.path.isdir(fallback) else ""
        if not source_dir:
            raise RuntimeError("下载成功但未找到资源目录")

        name = (info.get("title") or info.get("name") or slug)[:128]
        version = info.get("version")
        filename = os.path.join(package_dir(kind), asset_filename(kind, slug, version))
        shutil.make_archive(
            os.path.splitext(filename)[0], "zip",
            root_dir=os.path.dirname(source_dir), base_dir=os.path.basename(source_dir),
        )

        asset = (db.query(WpAsset)
                 .filter(WpAsset.kind == kind, WpAsset.slug == slug).first())
        if not asset:
            asset = WpAsset(kind=kind, name=name, slug=slug, source="official")
            db.add(asset)
        else:
            asset.name = name
        asset.version = version
        asset.file_path = to_relative_path(filename)
        asset.file_size = os.path.getsize(filename)
        asset.enabled = True
        db.commit()
        db.refresh(asset)
        return asset
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
        if tmp_db:
            try:
                conn = _connect()
                cur = conn.cursor()
                cur.execute(f"DROP DATABASE IF EXISTS `{tmp_db}`")
                conn.commit()
                cur.close()
                conn.close()
            except Exception:
                pass
