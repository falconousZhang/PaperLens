from __future__ import annotations

import ipaddress
import math
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from paperlens.core.config import settings

@dataclass
class _Bucket:
    remaining: int
    expires_at: float


class RateLimiter:
    def __init__(
        self,
        window_seconds: int,
        max_keys: int,
        read_quota: int,
        write_quota: int,
        auth_quota: int,
        upload_quota: int,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if isinstance(window_seconds, bool) or not isinstance(window_seconds, int) or window_seconds < 1:
            raise ValueError("rate_limit_window_seconds must be >= 1")
        if isinstance(max_keys, bool) or not isinstance(max_keys, int) or max_keys < 1:
            raise ValueError("rate_limit_max_keys must be >= 1")
        quotas = {
            "read": read_quota,
            "write": write_quota,
            "auth": auth_quota,
            "upload": upload_quota,
        }
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in quotas.values()):
            raise ValueError("rate limit quotas must be positive integers")
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self.quotas = quotas
        self._clock = clock or time.monotonic
        self._store: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str, scope: str) -> bool:
        quota = self.quotas.get(scope)
        if quota is None:
            return True
        now = self._clock()
        with self._lock:
            bucket = self._store.get(key)
            if bucket is None or bucket.expires_at <= now:
                self._evict_if_needed(now)
                self._store[key] = _Bucket(remaining=quota - 1, expires_at=now + self.window_seconds)
                return True
            if bucket.remaining <= 0:
                return False
            bucket.remaining -= 1
            return True

    def _evict_if_needed(self, now: float) -> None:
        expired = [key for key, bucket in self._store.items() if bucket.expires_at <= now]
        for k in expired:
            del self._store[k]
        if len(self._store) < self.max_keys:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k].expires_at)
        del self._store[oldest_key]

    def retry_after(self, key: str) -> int:
        with self._lock:
            bucket = self._store.get(key)
            if bucket is None:
                return self.window_seconds
            remaining = math.ceil(bucket.expires_at - self._clock())
            return max(1, remaining)

    @property
    def key_count(self) -> int:
        with self._lock:
            return len(self._store)


_EXPERIMENT_UPLOAD = re.compile(
    r"^/api/v1/papers/[^/]+/experiment-files/upload$"
)


def classify_scope(method: str, path: str) -> str:
    if path == "/api/v1/health" or path.startswith("/api/v1/health/"):
        return "exempt"
    auth_paths = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
    }
    if method == "POST" and path in auth_paths:
        return "auth"
    if method == "POST" and (
        path == "/api/v1/papers/upload" or _EXPERIMENT_UPLOAD.fullmatch(path)
    ):
        return "upload"
    if method in ("GET", "HEAD"):
        return "read"
    return "write"


def resolve_client_ip(
    request_ip: str,
    forwarded_for: str | None,
    trusted_cidrs: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> str:
    if not trusted_cidrs:
        return request_ip
    try:
        peer = ipaddress.ip_address(request_ip)
    except ValueError:
        return request_ip
    if not any(peer in cidr for cidr in trusted_cidrs):
        return str(peer)
    if not forwarded_for or len(forwarded_for) > 512:
        return str(peer)
    parts = [part.strip() for part in forwarded_for.split(",")]
    if not parts or any(not part for part in parts):
        return str(peer)
    try:
        forwarded = [ipaddress.ip_address(part) for part in parts]
    except ValueError:
        return str(peer)
    for address in reversed([*forwarded, peer]):
        if any(address in cidr for cidr in trusted_cidrs):
            continue
        return str(address)
    return str(forwarded[0])


def parse_trusted_cidrs(raw: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    if not raw.strip():
        return []
    result = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(ipaddress.ip_network(part, strict=False))
        except ValueError as exc:
            raise ValueError("invalid PAPERLENS_TRUSTED_PROXY_CIDRS") from exc
    return result


_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(
            window_seconds=settings.rate_limit_window_seconds,
            max_keys=settings.rate_limit_max_keys,
            read_quota=settings.rate_limit_read_quota,
            write_quota=settings.rate_limit_write_quota,
            auth_quota=settings.rate_limit_auth_quota,
            upload_quota=settings.rate_limit_upload_quota,
        )
    return _limiter
