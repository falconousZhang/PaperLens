from fastapi import APIRouter

from paperlens.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.app_version}