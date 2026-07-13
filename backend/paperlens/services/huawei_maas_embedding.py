import json
import logging
from typing import Any

import httpx

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
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        batch_size: int | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self._base_url = (base_url or settings.embedding_base_url).rstrip("/")
        self._model = model or settings.embedding_model
        self._api_key = api_key or self._resolve_api_key()
        self._timeout = timeout_seconds or settings.embedding_timeout_seconds
        self._batch_size = batch_size or settings.embedding_batch_size
        self._transport = transport

    @staticmethod
    def _resolve_api_key() -> str:
        key = settings.embedding_api_key
        if not key:
            raise EmbeddingError(
                "embedding_api_key is required when provider is huawei_maas"
            )
        return key

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise EmbeddingError("texts must be non-empty")
        for i, t in enumerate(texts):
            if not t or not t.strip():
                raise EmbeddingError(f"texts[{i}] must be non-empty")

        total = len(texts)
        all_vectors: list[list[float] | None] = [None] * total

        for batch_start in range(0, total, self._batch_size):
            batch_end = min(batch_start + self._batch_size, total)
            batch = texts[batch_start:batch_end]
            batch_vectors = self._embed_batch(batch)
            for j, vec in enumerate(batch_vectors):
                all_vectors[batch_start + j] = vec

        result = []
        for i, v in enumerate(all_vectors):
            if v is None:
                raise EmbeddingError(f"missing vector at index {i}")
            result.append(v)

        validate_embeddings(result, total)
        return result

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        request_body = {
            "model": self._model,
            "input": texts,
            "encoding_format": "float",
        }

        try:
            client_kwargs: dict[str, Any] = {
                "base_url": self._base_url,
                "timeout": self._timeout,
            }
            if self._transport is not None:
                client_kwargs["transport"] = self._transport

            with httpx.Client(**client_kwargs) as client:
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

        data = body.get("data")
        if not isinstance(data, list):
            raise EmbeddingError("embedding response missing data array")

        if len(data) != len(texts):
            raise EmbeddingError(
                f"embedding response count mismatch: got {len(data)}, expected {len(texts)}"
            )

        indexed: dict[int, list[float]] = {}
        for item in data:
            idx = item.get("index")
            if not isinstance(idx, int):
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

        dim = len(indexed[0])
        for i in range(1, len(texts)):
            if len(indexed[i]) != dim:
                raise EmbeddingError("embedding dimension mismatch across items")

        return [indexed[i] for i in range(len(texts))]