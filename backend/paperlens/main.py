import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from paperlens.api.auth import router as auth_router
from paperlens.api.admin import router as admin_router
from paperlens.api.experiment_files import router as experiment_files_router
from paperlens.api.exports import router as exports_router
from paperlens.api.health import router as health_router
from paperlens.api.learning import router as learning_router
from paperlens.api.metrics import router as metrics_router
from paperlens.api.papers import router as papers_router
from paperlens.api.qa import router as qa_router
from paperlens.api.library import router as library_router
from paperlens.api.personal_learning import router as personal_learning_router
from paperlens.api.tasks import router as tasks_router
from paperlens.core.config import settings
from paperlens.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.recovery_enabled:
        try:
            from paperlens.services.recovery_service import get_executor, run_recovery

            executor = get_executor()
            run_recovery(lambda func, args: executor.submit(func, *args))
        except Exception as exc:
            logger.error("stage=startup_recovery_failed error_type=%s", type(exc).__name__)
    yield
    from paperlens.services.recovery_service import shutdown_executor
    from paperlens.utils.storage import close_storage

    shutdown_executor()
    close_storage()


def create_app() -> FastAPI:
    app = FastAPI(
        title="PaperLens",
        version="0.1.0",
        docs_url="/api/docs" if settings.docs_enabled else None,
        redoc_url="/api/redoc" if settings.docs_enabled else None,
        openapi_url="/api/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    from paperlens.core.request_tracing import RequestTracingMiddleware
    from paperlens.core.rate_limit_middleware import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestTracingMiddleware)

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(papers_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(metrics_router, prefix="/api/v1")
    app.include_router(experiment_files_router, prefix="/api/v1")
    app.include_router(exports_router, prefix="/api/v1")
    app.include_router(learning_router, prefix="/api/v1")
    app.include_router(qa_router, prefix="/api/v1")
    app.include_router(library_router, prefix="/api/v1")
    app.include_router(personal_learning_router, prefix="/api/v1")

    return app


app = create_app()
