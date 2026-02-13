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
    
    # Start PMA PHP Server
    pma = get_pma_manager()
    if pma:
        pma.start()
        
    yield
    # Shutdown logic
    print(f"--- {settings.PROJECT_NAME} is shutting down ---")
    if pma:
        pma.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
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
        
        # Forward headers correctly (avoiding dict collapse for multiple Set-Cookie)
        for name, value in rp_resp.headers.items():
            name_lower = name.lower()
            if name_lower in ["content-length", "content-encoding", "transfer-encoding", "connection"]:
                continue
            
            header_value = value
            if name_lower == "set-cookie":
                print(f"--- PMA Proxy: PHP setting cookie: {header_value}")

            if name_lower == "location":
                import urllib.parse
                parsed = urllib.parse.urlparse(header_value)
                
                if not parsed.netloc or \
                   parsed.netloc == f"{pma.host}:{pma.port}" or \
                   parsed.netloc == "127.0.0.1" or \
                   parsed.netloc == "localhost":
                    
                    path = parsed.path
                    if not path.startswith("/phpmyadmin"):
                        path = "/phpmyadmin" + (path if path.startswith("/") else "/" + path)
                    
                    header_value = path
                    if parsed.query:
                        header_value += f"?{parsed.query}"
                    if parsed.fragment:
                        header_value += f"#{parsed.fragment}"
            
            # Use append to preserve multiple headers like Set-Cookie
            response.headers.append(name, header_value)
            
        return response

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
