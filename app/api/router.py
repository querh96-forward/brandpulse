from fastapi import APIRouter

from app.api.routes.analysis_jobs import router as analysis_jobs_router
from app.api.routes.articles import router as articles_router
from app.api.routes.brands import router as brands_router
from app.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(brands_router)
api_router.include_router(articles_router)
api_router.include_router(analysis_jobs_router)
