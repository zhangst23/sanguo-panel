import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.core.config import settings
from backend.api.v1.api import api_router
from fastapi.staticfiles import StaticFiles
from fastapi import Request, Response
from backend.utils.pma_server import get_pma_manager
import httpx
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print(f"--- {settings.PROJECT_NAME} is starting up ---")
    
    # Start PMA PHP Server in a separate thread to avoid blocking lifespan
    import threading
    pma = get_pma_manager()
    if pma:
        threading.Thread(target=pma.start, daemon=True).start()

    # Start SSL expiry checker (initial + daily)
    from backend.utils.ssl_expiry_checker import start_ssl_checker
    threading.Thread(target=start_ssl_checker, daemon=True).start()

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

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
