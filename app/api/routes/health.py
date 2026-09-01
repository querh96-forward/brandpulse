from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.app_env,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/info")
async def project_info() -> dict[str, str]:
    settings = get_settings()

    return {
        "project": "BrandPulse",
        "version": "0.1.0",
        "environment": settings.app_env,
    }
