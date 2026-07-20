import logging
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from paperlens.core.config import settings
from paperlens.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_request_id_is_strict_and_logs_are_redacted(client: AsyncClient, caplog):
    caplog.set_level(logging.INFO, logger="paperlens.core.request_tracing")
    request_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"

    response = await client.get(
        "/api/v1/health?token=must-not-appear",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id

    secret_path = "11111111-1111-4111-8111-111111111111"
    response = await client.get(
        f"/api/v1/missing/{secret_path}?password=must-not-appear",
        headers={"X-Request-ID": "AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE"},
    )

    assert response.status_code == 404
    generated = response.headers["X-Request-ID"]
    assert generated != "AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE"
    assert uuid.UUID(generated).version == 4
    tracing_logs = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "paperlens.core.request_tracing"
    )
    assert "route=/api/v1/health" in tracing_logs
    assert "route=<unmatched>" in tracing_logs
    assert "must-not-appear" not in tracing_logs
    assert secret_path not in tracing_logs


@pytest.mark.asyncio
async def test_rate_limit_is_bounded_resets_and_exempts_health(client: AsyncClient, monkeypatch):
    import paperlens.core.rate_limit_middleware as middleware_module
    from paperlens.core.rate_limiter import RateLimiter, classify_scope

    current_time = [100.0]
    limiter = RateLimiter(
        window_seconds=60,
        max_keys=2,
        read_quota=1,
        write_quota=1,
        auth_quota=1,
        upload_quota=1,
        clock=lambda: current_time[0],
    )

    assert limiter.is_allowed("read:a", "read") is True
    assert limiter.is_allowed("read:a", "read") is False
    current_time[0] = 160.0
    assert limiter.is_allowed("read:a", "read") is True
    assert limiter.is_allowed("read:b", "read") is True
    assert limiter.is_allowed("read:c", "read") is True
    assert limiter.key_count == 2
    assert classify_scope(
        "POST",
        "/api/v1/papers/11111111-1111-4111-8111-111111111111/experiment-files/upload",
    ) == "upload"

    monkeypatch.setattr(middleware_module, "get_limiter", lambda: limiter)
    old_enabled = settings.rate_limit_enabled
    settings.rate_limit_enabled = True
    try:
        for _ in range(3):
            assert (await client.get("/api/v1/health/live")).status_code == 200

        current_time[0] = 220.0
        first = await client.get("/api/v1/not-found")
        limited = await client.get("/api/v1/not-found")
    finally:
        settings.rate_limit_enabled = old_enabled

    assert first.status_code == 404
    assert limited.status_code == 429
    assert limited.json() == {
        "error": {
            "code": "RATE_LIMITED",
            "message": "请求过于频繁，请稍后重试",
            "details": None,
        }
    }
    assert int(limited.headers["Retry-After"]) >= 1
    assert uuid.UUID(limited.headers["X-Request-ID"]).version == 4


@pytest.mark.asyncio
async def test_health_live_and_ready_are_safe(client: AsyncClient, monkeypatch):
    import paperlens.api.health as health_module

    ready = await client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {
        "status": "ready",
        "version": settings.app_version,
        "checks": {"database": "ok"},
    }

    def unavailable_session():
        raise RuntimeError("postgresql://credential-must-not-appear")

    monkeypatch.setattr(health_module, "SessionLocal", unavailable_session)

    live = await client.get("/api/v1/health/live")
    unavailable = await client.get("/api/v1/health/ready")

    assert live.status_code == 200
    assert live.json()["status"] == "alive"
    assert unavailable.status_code == 503
    assert unavailable.json() == {
        "status": "not_ready",
        "version": settings.app_version,
        "checks": {"database": "error"},
    }
    assert "credential-must-not-appear" not in unavailable.text
