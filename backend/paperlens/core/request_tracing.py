from __future__ import annotations

import contextvars
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)

def _is_valid_uuid4(value: str) -> bool:
    if len(value) != 36:
        return False
    try:
        parsed = uuid.UUID(value)
        return parsed.version == 4 and str(parsed) == value
    except (ValueError, AttributeError):
        return False


def get_request_id() -> str:
    return request_id_ctx.get()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        inbound = request.headers.get("x-request-id", "")
        rid = inbound if _is_valid_uuid4(inbound) else str(uuid.uuid4())
        token = request_id_ctx.set(rid)
        start = time.monotonic()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                logger.error(
                    "stage=request_failed request_id=%s error_type=%s",
                    rid,
                    type(exc).__name__,
                )
                response = JSONResponse(
                    status_code=500,
                    content={
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "服务器内部错误",
                            "details": None,
                        }
                    },
                )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            route = request.scope.get("route")
            route_template = getattr(route, "path", "<unmatched>")
            rate_scope = getattr(request.state, "rate_scope", "unclassified")
            logger.info(
                "request_id=%s method=%s route=%s status=%d duration_ms=%d rate_scope=%s",
                rid,
                request.method,
                route_template,
                response.status_code,
                elapsed_ms,
                rate_scope,
            )
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_ctx.reset(token)
