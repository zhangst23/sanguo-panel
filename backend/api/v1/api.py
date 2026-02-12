from fastapi import APIRouter
from backend.api.v1 import auth, system, site, service

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(site.router, prefix="/sites", tags=["sites"])
api_router.include_router(service.router, prefix="/services", tags=["services"])
