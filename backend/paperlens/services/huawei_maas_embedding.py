import json
import logging
from typing import Any

import httpx
from pydantic import SecretStr

from paperlens.core.config import settings
from paperlens.services.embedding_client import (
    EmbeddingClient,
    EmbeddingError,
    validate_embeddings,
)

logger = logging.getLogger(__name__)


class HuaweiMaaSEmbeddingClient(EmbeddingClient):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | SecretStr | None = None,
        timeout_seconds: float | None = None,
        batch_size: int | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self._base_url = (base_url or settings.embedding_base_url).strip().rstrip("/")
        self._model = (model or settings.embedding_model).strip()
        self._api_key = self._coerce_api_key(api_key) if api_key is not None else self._resolve_api_key()
        self._timeout = settings.embedding_timeout_seconds if timeout_seconds is None else timeout_seconds
        self._batch_size = settings.embedding_batch_size if batch_size is None else batch_size
        self._transport = transport

        parsed_url = httpx.URL(self._base_url)
        if parsed_url.scheme != "https" or not parsed_url.host:
            raise EmbeddingError("embedding_base_url must be an absolute HTTPS URL")
        if not self._model:
            raise EmbeddingError("embedding_model must be non-empty")
        if isinstance(self._timeout, bool) or not isinstance(self._timeout, (int, float)) or self._timeout <= 0:
            raise EmbeddingError("timeout_seconds must be positive")
        if isinstance(self._batch_size, bool) or not isinstance(self._batch_size, int) or self._batch_size < 1:
            raise EmbeddingError("batch_size must be a positive integer")

    @staticmethod
    def _resolve_api_key() -> str:
        key = settings.embedding_api_key
        if not key:
            raise EmbeddingError(
                "embedding_api_key is required when provider is huawei_maas"
            )
        return HuaweiMaaSEmbeddingClient._coerce_api_key(key)

    @staticmethod
    def _coerce_api_key(key: str | SecretStr) -> str:
        value = key.get_secret_value() if isinstance(key, SecretStr) else key
        value = value.strip()
        if not value:
            raise EmbeddingError("embedding_api_key must be non-empty")
        return value

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise EmbeddingError("texts must be non-empty")
        for i, t in enumerate(texts):
            if not t or not t.strip():
                raise EmbeddingError(f"texts[{i}] must be non-empty")

        total = len(texts)
        all_vectors: list[list[float] | None] = [None] * total

        client_kwargs: dict[str, Any] = {
            "base_url": self._base_url,
            "timeout": self._timeout,
        }
        if self._transport is not None:
            client_kwargs["transport"] = self._transport

        with httpx.Client(**client_kwargs) as client:
            for batch_start in range(0, total, self._batch_size):
                batch_end = min(batch_start + self._batch_size, total)
                batch = texts[batch_start:batch_end]
                batch_vectors = self._embed_batch(client, batch)
                for j, vec in enumerate(batch_vectors):
                    all_vectors[batch_start + j] = vec

        result = []
        for i, v in enumerate(all_vectors):
            if v is None:
                raise EmbeddingError(f"missing vector at index {i}")
            result.append(v)

        validate_embeddings(result, total)
        return result

    def _embed_batch(self, client: httpx.Client, texts: list[str]) -> list[list[float]]:
        request_body = {
            "model": self._model,
            "input": texts,
            "encoding_format": "float",
        }

        try:
            response = client.post(
                "/embeddings",
                json=request_body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        except httpx.TimeoutException:
            raise EmbeddingError("embedding request timed out")
        except httpx.ConnectError:
            raise EmbeddingError("embedding service connection failed")
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"embedding request failed: {type(exc).__name__}")

        if response.status_code != 200:
            raise EmbeddingError(
                f"embedding service returned status {response.status_code}"
            )

        try:
            body = response.json()
        except (json.JSONDecodeError, ValueError):
            raise EmbeddingError("embedding service returned non-JSON response")

        if not isinstance(body, dict):
            raise EmbeddingError("embedding response must be a JSON object")

        data = body.get("data")
        if not isinstance(data, list):
            raise EmbeddingError("embedding response missing data array")

        if len(data) != len(texts):
            raise EmbeddingError(
                f"embedding response count mismatch: got {len(data)}, expected {len(texts)}"
            )

        indexed: dict[int, list[float]] = {}
        for item in data:
            if not isinstance(item, dict):
                raise EmbeddingError("embedding response item must be an object")
            idx = item.get("index")
            if isinstance(idx, bool) or not isinstance(idx, int):
                raise EmbeddingError("embedding response item missing valid index")
            if idx in indexed:
                raise EmbeddingError(f"embedding response duplicate index {idx}")
            if idx < 0 or idx >= len(texts):
                raise EmbeddingError(f"embedding response index out of range: {idx}")

            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                raise EmbeddingError(f"embedding response item {idx} missing embedding")

            vec: list[float] = []
            for v in embedding:
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise EmbeddingError(f"invalid vector value at index {idx}")
                if isinstance(v, float) and (v != v or abs(v) == float("inf")):
                    raise EmbeddingError(f"invalid vector value at index {idx}")
                vec.append(float(v))

            if not vec:
                raise EmbeddingError(f"empty vector at index {idx}")

            indexed[idx] = vec

        for i in range(len(texts)):
            if i not in indexed:
                raise EmbeddingError(f"embedding response missing index {i}")

        result = [indexed[i] for i in range(len(texts))]
        validate_embeddings(result, len(texts))
        return result
