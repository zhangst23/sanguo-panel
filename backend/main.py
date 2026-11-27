import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.core.config import settings
from backend.api.v1.api import api_router
from fastapi.staticfiles import StaticFiles
from fastapi import Request, Response
from fastapi.responses import FileResponse
from backend.utils.pma_server import get_pma_manager
import httpx
import os
import re
from pathlib import Path

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print(f"--- {settings.PROJECT_NAME} is starting up ---")

    # Self-heal the panel database. If panel.db was removed or left empty
    # (e.g. after a manual reset or a code pull), every API endpoint would fail
    # with "no such table: users" and all pages would render without data.
    # Recreate the schema + default admin account in that case.
    try:
        from sqlalchemy import inspect
        from backend.core.database import engine
        if 'users' not in inspect(engine).get_table_names():
            from backend.init_db import init_db
            init_db()
            print("--- Database was empty: initialized schema and admin account ---")
    except Exception as e:
        print(f"--- Database auto-init failed: {e} ---")

    # Upgrade older panel.db files with columns added in newer versions.
    try:
        from backend.init_db import ensure_schema
        ensure_schema()
    except Exception as e:
        print(f"--- Database schema upgrade failed: {e} ---")

    # Ensure a dedicated MariaDB admin account exists (never use root for sites)
    try:
        from backend.core.database import SessionLocal
        from backend.models.site import SharedDatabase
        from backend.utils.db_admin import ensure_admin_account
        session = SessionLocal()
        shared_db = session.query(SharedDatabase).filter(
            SharedDatabase.status == "active"
        ).first()
        if shared_db:
            user, _password = ensure_admin_account(shared_db)
            if user:
                session.add(shared_db)
                session.commit()
                print(f"--- MariaDB admin account ready: {user} ---")
        session.close()
    except Exception as e:
        print(f"--- MariaDB admin account setup failed: {e} ---")

    # Start PMA PHP Server in a separate thread to avoid blocking lifespan
    import threading
    pma = get_pma_manager()
    if pma:
        threading.Thread(target=pma.start, daemon=True).start()

    # Start SSL expiry checker (initial + daily)
    from backend.utils.ssl_expiry_checker import start_ssl_checker
    threading.Thread(target=start_ssl_checker, daemon=True).start()

    # Start panel backup scheduler (每周日 23:00)
    from backend.utils import panel_backup_utils as pbu
    pbu.start_scheduler()

    yield
    # Shutdown logic
    print(f"--- {settings.PROJECT_NAME} is shutting down ---")
    if pma:
        pma.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api-docs",
    openapi_url="/api-docs/openapi.json",
    redoc_url=None,
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # If no origins specified, we still need CORS for local dev sometimes, 
    # but allow_credentials=True requires specific origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


# ---------------------------------------------------------------------------
# 操作日志：统一记录面板上的写操作（POST/PUT/PATCH/DELETE）。
# 此前只有少数几个接口会写入 tasks 表，导致“操作日志”页面长期为空。
# ---------------------------------------------------------------------------
def _operation_label(method: str, path: str) -> str:
    prefix = settings.API_V1_STR
    p = (path[len(prefix):] if path.startswith(prefix) else path).rstrip("/") or "/"
    exact = {
        ("POST", "/sites"): "创建站点",
        ("POST", "/sites/batch"): "批量建站",
        ("POST", "/sites/migrate"): "迁移站点",
        ("DELETE", "/sites"): "删除站点",
        ("POST", "/security/backup"): "创建备份",
        ("POST", "/system/update"): "面板更新",
        ("POST", "/system/restart"): "面板重启",
    }
    if (method, p) in exact:
        return exact[(method, p)]
    if p.startswith("/sites/") and re.match(r"^/sites/\d+$", p):
        return {"PUT": "修改站点", "DELETE": "删除站点"}.get(method, "站点操作")
    segment = p.strip("/").split("/")[0] if p.strip("/") else "panel"
    names = {
        "sites": "站点", "backup": "备份", "database": "数据库", "files": "文件",
        "php": "PHP", "system": "系统", "tools": "工具", "security": "安全",
        "ssl": "SSL", "cache": "缓存", "litespeed": "OpenLiteSpeed",
        "wp-assets": "WP资源", "monitor": "监控", "image": "图片", "cdn": "CDN",
        "ultimate": "极致优化", "assets": "资源", "linux": "系统",
    }
    actions = {"POST": "执行", "PUT": "修改", "PATCH": "更新", "DELETE": "删除"}
    return f"{actions.get(method, method)}{names.get(segment, segment)}"


def _record_operation(request: Request, response: Response, path: str, method: str) -> None:
    import uuid
    from jose import jwt
    from datetime import datetime
    from backend.core.database import SessionLocal
    from backend.models.task import Task, TaskStatus
    from backend.models.user import User
    from backend.schemas.token import TokenPayload

    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return
    try:
        payload = jwt.decode(
            auth.split(None, 1)[1], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = TokenPayload(**payload).sub
    except Exception:
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        succeeded = response.status_code < 400
        now = datetime.utcnow()
        db.add(Task(
            task_uuid=str(uuid.uuid4()),
            type=_operation_label(method, path)[:50],
            status=TaskStatus.completed if succeeded else TaskStatus.failed,
            progress=100 if succeeded else 0,
            message=f"{user.username} · {method} {path}",
            error=None if succeeded else f"HTTP {response.status_code}",
            created_by=user.id,
            started_at=now,
            completed_at=now,
        ))
        db.commit()
    finally:
        db.close()


@app.middleware("http")
async def operation_log_middleware(request: Request, call_next):
    response = await call_next(request)
    try:
        path = request.url.path
        method = request.method.upper()
        if (
            path.startswith(settings.API_V1_STR + "/")
            and method in ("POST", "PUT", "PATCH", "DELETE")
            and not path.startswith(settings.API_V1_STR + "/login")
            and not path.startswith(settings.API_V1_STR + "/tasks")
        ):
            _record_operation(request, response, path, method)
    except Exception as exc:
        # 日志失败绝不影响业务请求
        print(f"--- 操作日志记录失败: {exc} ---")
    return response


# phpMyAdmin Proxy
@app.api_route("/phpmyadmin/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def pma_proxy(request: Request, path: str):
    pma = get_pma_manager()
    if not pma:
        # Re-check if it was just installed
        import backend.utils.pma_server as pma_server
        pma_server.pma_manager = None 
        pma = get_pma_manager()
        if not pma:
            return Response(content="phpMyAdmin not installed in backend/phpmyadmin", status_code=404)
    
    # Ensure it's started (in case lifespan didn't start it or it crashed)
    if not pma.is_port_in_use():
        success = pma.start()
        if not success:
            return Response(
                content=f"PHP Server for phpMyAdmin failed to start: {pma.last_error}",
                status_code=503
            )
    
    url = f"http://{pma.host}:{pma.port}/{path}"
    if request.query_params:
        url += f"?{request.query_params}"

    # print(f"Proxying request: {request.method} {request.url} -> {url}")

    async with httpx.AsyncClient() as client:
        # Forward the request to the PHP server
        content = await request.body()
        
        # Prepare request to PHP server
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length"]}
        
        # Add original Host for PHP to handle absolute URLs correctly if needed
        headers["X-Forwarded-Host"] = request.headers.get("host", "")
        headers["X-Forwarded-Proto"] = request.url.scheme
        
        # Debug: Log incoming cookies
        cookie_header = headers.get("cookie", "")
        if "SanguoPMA" in cookie_header:
            print(f"--- PMA Proxy: Browser sent SanguoPMA cookie: {cookie_header[:50]}...")
        
        try:
            rp_resp = await client.request(
                method=request.method,
                url=url,
                content=content,
                headers=headers,
                follow_redirects=False,
                timeout=60.0 # Increase timeout to 60s
            )
            
            # Debug: Log all headers from PHP
            # print(f"--- PMA Proxy: PHP Response Headers: {list(rp_resp.headers.items())}")
            
            content = rp_resp.content
        except Exception as e:
            # Check if it's a connection error (server not running)
            error_detail = str(e)
            print(f"PMA Proxy Exception: {error_detail}") # Log to console
            print(f"Request: {request.method} {url}")
            print(f"Headers: {headers}")
            if "Connection refused" in error_detail or "WinError 10061" in error_detail:
                error_msg = pma.last_error if pma.last_error else "PHP Server for phpMyAdmin is not running."
                return Response(
                    content=f"{error_msg} Please check if PHP is installed and in your PATH.",
                    status_code=503
                )
            return Response(content=f"PMA Proxy Error: {error_detail}", status_code=502)

        # Return the response from the PHP server
        response = Response(
            content=rp_resp.content,
            status_code=rp_resp.status_code
        )
        
        # Forward headers correctly (avoiding dict collapse or comma merging)
        # Use raw headers to handle multiple Set-Cookie properly
        for name, value in rp_resp.headers.raw:
            # name and value are bytes from httpx
            name_str = name.decode('latin-1')
            name_lower = name_str.lower()
            
            if name_lower in ["content-length", "content-encoding", "transfer-encoding", "connection"]:
                continue
            
            val_str = value.decode('latin-1')
            if name_lower == "set-cookie":
                print(f"--- PMA Proxy: PHP setting cookie: {val_str}")
                response.headers.append("set-cookie", val_str)
            elif name_lower == "location":
                import urllib.parse
                location = val_str
                if location.startswith(('http://', 'https://')):
                    parsed_loc = urllib.parse.urlparse(location)
                    # Check if it's our PHP server redirecting
                    if not parsed_loc.netloc or \
                       parsed_loc.netloc == f"{pma.host}:{pma.port}" or \
                       parsed_loc.netloc == "127.0.0.1" or \
                       parsed_loc.netloc == "localhost":
                        
                        new_loc = parsed_loc.path
                        if not new_loc.startswith("/phpmyadmin"):
                            new_loc = "/phpmyadmin" + (new_loc if new_loc.startswith("/") else "/" + new_loc)
                        
                        if parsed_loc.query:
                            new_loc += f"?{parsed_loc.query}"
                        if parsed_loc.fragment:
                            new_loc += f"#{parsed_loc.fragment}"
                        response.headers.append("location", new_loc)
                    else:
                        response.headers.append("location", location)
                else:
                    if not location.startswith('/phpmyadmin'):
                        if location.startswith('/'):
                            location = f"/phpmyadmin{location}"
                        else:
                            location = f"/phpmyadmin/{location}"
                    response.headers.append("location", location)
            else:
                response.headers.append(name_str, val_str)
            
        return response

# ---------------------------------------------------------------------------
# Frontend SPA (production)
# When frontend/dist exists (built via `npm run build`), the backend serves the
# built panel UI on the same origin as the API. This makes the whole panel a
# single system service. In development the Vite dev server is used instead.
# ---------------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_FRONTEND_DIST_RESOLVED = FRONTEND_DIST.resolve()

if (FRONTEND_DIST / "index.html").is_file():
    if (FRONTEND_DIST / "assets").is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(FRONTEND_DIST / "assets")),
            name="assets",
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Never swallow API / docs / proxy / websocket paths.
        if full_path.startswith(("api/", "api-docs", "phpmyadmin", "ws/")):
            return Response(status_code=404)

        candidate = (_FRONTEND_DIST_RESOLVED / full_path).resolve()
        if (
            candidate == _FRONTEND_DIST_RESOLVED
            or _FRONTEND_DIST_RESOLVED in candidate.parents
        ) and candidate.is_file():
            return FileResponse(candidate)

        # index.html 必须每次重新校验：否则浏览器会缓存旧的主 JS bundle，
        # 其动态 import 指向已被构建替换的 chunk 文件名，导致菜单点击后页面无反应。
        return FileResponse(
            FRONTEND_DIST / "index.html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
else:
    @app.get("/")
    async def root():
        return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
