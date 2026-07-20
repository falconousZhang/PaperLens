import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from paperlens.core.request_tracing import get_request_id

logger = logging.getLogger(__name__)


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details=None,
        headers: dict[str, str] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.headers = headers


def _error_response(
    code: str,
    message: str,
    status_code: int,
    details=None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    extra_headers = dict(headers) if headers else {}
    rid = get_request_id()
    if rid:
        extra_headers["X-Request-ID"] = rid
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
        headers=extra_headers if extra_headers else None,
    )


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return _error_response(exc.code, exc.message, exc.status_code, exc.details, exc.headers)


async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _error_response(
        str(exc.status_code),
        str(exc.detail),
        exc.status_code,
        None,
        exc.headers,
    )


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    details = _json_safe(exc.errors())
    messages = []
    for d in details:
        loc = ".".join(str(x) for x in d.get("loc", []))
        messages.append(f"{loc}: {d.get('msg', '')}")
    return _error_response("VALIDATION_ERROR", "; ".join(messages), 422, details)


async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.error("stage=unhandled_error error_type=%s", type(exc).__name__)
    return _error_response("INTERNAL_ERROR", "服务器内部错误", 500, None)
