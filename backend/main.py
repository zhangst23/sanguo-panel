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

    async with httpx.AsyncClient() as client:
        # Forward the request to the PHP server
        content = await request.body()
        
        # Prepare headers: forward all except 'host'
        headers = {}
        for k, v in request.headers.items():
            if k.lower() != 'host':
                headers[k] = v
                
        try:
            rp_resp = await client.request(
                method=request.method,
                url=url,
                content=content,
                headers=headers,
                follow_redirects=False,
                timeout=30.0
            )
        except Exception as e:
            # Check if it's a connection error (server not running)
            error_detail = str(e)
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
        
        # Forward headers from the PHP response to the browser
        # Use raw headers to preserve multiple Set-Cookie headers
        exclude_headers = ["content-length", "content-encoding", "transfer-encoding", "connection"]
        for name, value in rp_resp.headers.raw:
            name_str = name.decode("latin-1").lower()
            if name_str not in exclude_headers:
                header_value = value.decode("latin-1")
                # Rewrite Location header to be relative to the proxy or absolute for the browser
                if name_str == "location":
                    if header_value.startswith("http://127.0.0.1") or header_value.startswith(f"http://{pma.host}"):
                        # Convert absolute PHP URL back to relative/proxy URL
                        import urllib.parse
                        parsed = urllib.parse.urlparse(header_value)
                        path = parsed.path
                        # IMPORTANT: Prefix with /phpmyadmin because the browser needs to hit the proxy
                        if not path.startswith("/phpmyadmin"):
                            path = "/phpmyadmin" + (path if path.startswith("/") else "/" + path)
                        
                        header_value = path
                        if parsed.query:
                            header_value += f"?{parsed.query}"
                
                # print(f"Response header: {name_str}: {header_value}")
                response.headers.append(name_str, header_value)
                
        return response

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
