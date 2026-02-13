from fastapi import APIRouter
from backend.api.v1 import (
    auth, system, site, service, cache, ssl, 
    image, database, assets, cdn, ultimate, tasks,
    litespeed, php
)

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(site.router, prefix="/sites", tags=["sites"])
api_router.include_router(service.router, prefix="/services", tags=["services"])
api_router.include_router(litespeed.router, prefix="/litespeed", tags=["litespeed"])
api_router.include_router(php.router, prefix="/php", tags=["php"])
api_router.include_router(cache.router, prefix="/cache", tags=["cache"])
api_router.include_router(ssl.router, prefix="/ssl", tags=["ssl"])
api_router.include_router(image.router, prefix="/image", tags=["image"])
api_router.include_router(database.router, prefix="/database", tags=["database"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(cdn.router, prefix="/cdn", tags=["cdn"])
api_router.include_router(ultimate.router, prefix="/ultimate", tags=["ultimate"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
