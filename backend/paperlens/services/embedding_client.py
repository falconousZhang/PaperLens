import hashlib
import math
from abc import ABC, abstractmethod


class EmbeddingError(Exception):
    pass


class EmbeddingClient(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


_MOCK_VOCAB = {
    "method": 0, "approach": 0, "technique": 0, "algorithm": 0,
    "result": 1, "experiment": 1, "evaluation": 1, "performance": 1,
    "novel": 2, "new": 2, "innovative": 2, "original": 2, "contribution": 2,
    "clear": 3, "writing": 3, "presentation": 3, "readable": 3, "explain": 3,
    "complete": 4, "comprehensive": 4, "thorough": 4, "detail": 4,
    "reproduce": 5, "implementation": 5, "setup": 5, "code": 5, "parameter": 5,
    "significant": 6, "important": 6, "impact": 6, "meaningful": 6,
    "soundness": 0, "reliability": 0, "validity": 0, "rigorous": 0,
    "novelty": 2, "innovation": 2,
    "clarity": 3, "understand": 3,
    "completeness": 4,
    "reproducibility": 5, "replicate": 5,
    "significance": 6,
    "overall": 7, "general": 7, "summary": 7, "recommend": 7,
    "weakness": 8, "limitation": 8, "issue": 8, "problem": 8,
    "strength": 9, "advantage": 9, "benefit": 9, "good": 9,
}

_MOCK_DIM = 10


def _stable_hash_token(token: str) -> float:
    h = hashlib.sha256(token.encode("utf-8")).digest()
    raw = int.from_bytes(h[:8], "big")
    normalized = (raw % 10000) / 10000.0
    return 0.1 + normalized * 0.8


class MockEmbeddingClient(EmbeddingClient):
    def __init__(self, dim: int = _MOCK_DIM):
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise EmbeddingError("texts must be non-empty")
        for i, t in enumerate(texts):
            if not t or not t.strip():
                raise EmbeddingError(f"texts[{i}] must be non-empty")

        result = []
        for text in texts:
            vec = self._make_vector(text.strip().lower())
            result.append(vec)
        return result

    def _make_vector(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        tokens = text.split()
        if not tokens:
            vec[0] = 1.0
            return self._normalize(vec)

        for token in tokens:
            if token in _MOCK_VOCAB:
                idx = _MOCK_VOCAB[token] % self._dim
                vec[idx] += 1.0
            else:
                h = hashlib.sha256(token.encode("utf-8")).digest()
                idx = int.from_bytes(h[:2], "big") % self._dim
                weight = _stable_hash_token(token)
                vec[idx] += weight

        if all(v == 0.0 for v in vec):
            vec[0] = 1.0

        return self._normalize(vec)

    @staticmethod
    def _normalize(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            raise EmbeddingError("zero-norm vector produced")
        return [v / norm for v in vec]


def validate_embeddings(vectors: list[list[float]], expected_count: int) -> None:
    if len(vectors) != expected_count:
        raise EmbeddingError(
            f"embedding count mismatch: got {len(vectors)}, expected {expected_count}"
        )

    if not vectors:
        return

    dim = len(vectors[0])
    for i, vec in enumerate(vectors):
        if len(vec) != dim:
            raise EmbeddingError(
                f"vector {i} dimension mismatch: got {len(vec)}, expected {dim}"
            )
        if not vec:
            raise EmbeddingError(f"vector {i} is empty")
        for j, v in enumerate(vec):
            if isinstance(v, bool):
                raise EmbeddingError(f"vector {i}[{j}] is boolean")
            if not isinstance(v, (int, float)):
                raise EmbeddingError(f"vector {i}[{j}] is not a number")
            if math.isnan(v):
                raise EmbeddingError(f"vector {i}[{j}] is NaN")
            if math.isinf(v):
                raise EmbeddingError(f"vector {i}[{j}] is Infinity")

        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            raise EmbeddingError(f"vector {i} has zero norm")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise EmbeddingError("vector dimension mismatch in cosine_similarity")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        raise EmbeddingError("zero-norm vector in cosine_similarity")
    sim = dot / (norm_a * norm_b)
    if math.isnan(sim) or math.isinf(sim):
        raise EmbeddingError("invalid cosine similarity result")
    return sim