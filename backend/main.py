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
        return Response(content="phpMyAdmin not installed", status_code=404)
    
    url = f"http://{pma.host}:{pma.port}/{path}"
    if request.query_params:
        url += f"?{request.query_params}"

    async with httpx.AsyncClient() as client:
        # Forward the request to the PHP server
        content = await request.body()
        headers = dict(request.headers)
        # Remove host header to avoid issues with PHP built-in server
        if "host" in headers:
            del headers["host"]
            
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
            return Response(content=f"PMA Proxy Error: {str(e)}", status_code=502)

        # Return the response from the PHP server
        response = Response(
            content=rp_resp.content,
            status_code=rp_resp.status_code,
            headers=dict(rp_resp.headers)
        )
        return response

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
