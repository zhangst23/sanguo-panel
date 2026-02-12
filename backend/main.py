import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.api.v1 import auth, system, site, service, cache, ssl, image, database, assets, cdn, ultimate

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
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

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(system.router, prefix=f"{settings.API_V1_STR}/system", tags=["system"])
app.include_router(site.router, prefix=f"{settings.API_V1_STR}/sites", tags=["sites"])
app.include_router(service.router, prefix=f"{settings.API_V1_STR}/services", tags=["services"])
app.include_router(cache.router, prefix=f"{settings.API_V1_STR}/cache", tags=["cache"])
app.include_router(ssl.router, prefix=f"{settings.API_V1_STR}/ssl", tags=["ssl"])
app.include_router(image.router, prefix=f"{settings.API_V1_STR}/images", tags=["images"])
app.include_router(database.router, prefix=f"{settings.API_V1_STR}/database", tags=["database"])
app.include_router(assets.router, prefix=f"{settings.API_V1_STR}/assets", tags=["assets"])
app.include_router(cdn.router, prefix=f"{settings.API_V1_STR}/cdn", tags=["cdn"])
app.include_router(ultimate.router, prefix=f"{settings.API_V1_STR}/ultimate", tags=["ultimate"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
