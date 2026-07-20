from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from paperlens.core.config import settings
from paperlens.core.rate_limiter import classify_scope, get_limiter, parse_trusted_cidrs, resolve_client_ip
from paperlens.core.request_tracing import get_request_id

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._trusted_cidrs = parse_trusted_cidrs(settings.trusted_proxy_cidrs)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not settings.rate_limit_enabled:
            request.state.rate_scope = "disabled"
            return await call_next(request)

        scope = classify_scope(request.method, request.url.path)
        request.state.rate_scope = scope

        if scope == "exempt":
            return await call_next(request)

        client_host = request.client.host if request.client else "0.0.0.0"
        forwarded = request.headers.get("x-forwarded-for")
        client_ip = resolve_client_ip(client_host, forwarded, self._trusted_cidrs)
        key = f"{scope}:{client_ip}"

        limiter = get_limiter()
        if not limiter.is_allowed(key, scope):
            retry_after = limiter.retry_after(key)
            rid = get_request_id()
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "请求过于频繁，请稍后重试",
                        "details": None,
                    }
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-Request-ID": rid,
                },
            )

        return await call_next(request)
