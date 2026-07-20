from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from paperlens.core.config import settings
from paperlens.core.database import SessionLocal

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.app_version}


@router.get("/health/live")
async def liveness_check():
    return JSONResponse(
        status_code=200,
        content={"status": "alive", "version": settings.app_version},
    )


@router.get("/health/ready")
def readiness_check():
    db_ok = False
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_ok = True
        finally:
            db.close()
    except Exception:
        pass
    if db_ok:
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "version": settings.app_version,
                "checks": {"database": "ok"},
            },
        )
    return JSONResponse(
        status_code=503,
        content={
            "status": "not_ready",
            "version": settings.app_version,
            "checks": {"database": "error"},
        },
    )
