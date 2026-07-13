from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from paperlens.api.health import router as health_router
from paperlens.api.papers import router as papers_router
from paperlens.api.tasks import router as tasks_router
from paperlens.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="PaperLens",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(papers_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")

    return app


app = create_app()
