import logging
from dataclasses import dataclass
from datetime import datetime

from paperlens.core.config import settings
from paperlens.core.enums import ReviewDimension
from paperlens.models.models import Evidence
from paperlens.services.embedding_client import (
    EmbeddingClient,
    EmbeddingError,
    cosine_similarity,
    validate_embeddings,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvidenceCandidate:
    id: str
    text: str
    page_number: int
    created_at: datetime

_DIMENSION_QUERIES: dict[ReviewDimension, dict[str, str]] = {
    ReviewDimension.SOUNDNESS: {
        "en": "methodology soundness reliability validity rigorous experimental setup",
        "zh": "方法论可靠性 有效性 严谨性 实验设置 验证",
    },
    ReviewDimension.NOVELTY: {
        "en": "novelty innovation originality new contribution related work",
        "zh": "新颖性 创新性 原创性 贡献 相关工作",
    },
    ReviewDimension.CLARITY: {
        "en": "clarity writing presentation readability explanation organization",
        "zh": "清晰度 写作 表达 可读性 解释 组织",
    },
    ReviewDimension.COMPLETENESS: {
        "en": "completeness thoroughness detail comprehensive coverage related work",
        "zh": "完整性 全面性 细节 覆盖 相关工作",
    },
    ReviewDimension.REPRODUCIBILITY: {
        "en": "reproducibility implementation details experimental setup parameters code",
        "zh": "可复现性 实现细节 实验设置 参数 代码",
    },
    ReviewDimension.SIGNIFICANCE: {
        "en": "significance importance impact meaningful contribution practical",
        "zh": "重要性 影响 意义 贡献 实用性",
    },
    ReviewDimension.OVERALL: {
        "en": "overall assessment recommendation strengths weaknesses quality",
        "zh": "总体评估 推荐 优势 劣势 质量",
    },
}


def build_dimension_query(
    paper_title: str,
    dimension: ReviewDimension,
    language: str,
) -> str:
    dim_info = _DIMENSION_QUERIES.get(dimension, _DIMENSION_QUERIES[ReviewDimension.OVERALL])
    lang_key = "zh" if language == "zh" else "en"
    dimension_terms = dim_info.get(lang_key, dim_info["en"])
    return f"{paper_title} {dimension.value} {dimension_terms}"


def retrieve_evidence_by_dimension(
    paper_id: str,
    dimensions: list[ReviewDimension],
    language: str,
    paper_title: str,
    db,
    embedding_client: EmbeddingClient,
    top_k: int | None = None,
) -> dict[ReviewDimension, list[tuple[str, str]]]:
    evidence_candidates = load_evidence_candidates(paper_id, db)
    return rank_evidence_by_dimension(
        evidence_candidates,
        dimensions,
        language,
        paper_title,
        embedding_client,
        top_k,
    )


def load_evidence_candidates(paper_id: str, db) -> list[EvidenceCandidate]:
    rows = (
        db.query(Evidence.id, Evidence.quoted_text, Evidence.page_number, Evidence.created_at)
        .filter(Evidence.paper_id == paper_id)
        .order_by(Evidence.page_number.asc(), Evidence.created_at.asc(), Evidence.id.asc())
        .all()
    )
    return [
        EvidenceCandidate(
            id=str(row[0]),
            text=row[1] or "",
            page_number=row[2],
            created_at=row[3],
        )
        for row in rows
    ]


def rank_evidence_by_dimension(
    evidence_candidates: list[EvidenceCandidate],
    dimensions: list[ReviewDimension],
    language: str,
    paper_title: str,
    embedding_client: EmbeddingClient,
    top_k: int | None = None,
) -> dict[ReviewDimension, list[tuple[str, str]]]:
    if top_k is None:
        top_k = settings.review_evidence_top_k
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise EmbeddingError("top_k must be a positive integer")
    if not dimensions:
        raise EmbeddingError("dimensions must be non-empty")
    if not evidence_candidates:
        return {d: [] for d in dimensions}

    evidence_texts = [candidate.text for candidate in evidence_candidates]
    evidence_vectors = embedding_client.embed(evidence_texts)
    validate_embeddings(evidence_vectors, len(evidence_texts))

    query_texts = [
        build_dimension_query(paper_title, d, language) for d in dimensions
    ]
    query_vectors = embedding_client.embed(query_texts)
    validate_embeddings(query_vectors, len(query_texts))

    results: dict[ReviewDimension, list[tuple[str, str]]] = {}

    for dim_idx, dimension in enumerate(dimensions):
        query_vec = query_vectors[dim_idx]
        scored = []
        for ev_idx, candidate in enumerate(evidence_candidates):
            ev_vec = evidence_vectors[ev_idx]
            sim = cosine_similarity(query_vec, ev_vec)
            scored.append(
                (
                    sim,
                    candidate.page_number,
                    candidate.created_at,
                    candidate.id,
                    candidate.text,
                )
            )

        scored.sort(key=lambda item: (-item[0], item[1], item[2], item[3]))

        top_items = scored[:top_k]
        results[dimension] = [(item[3], item[4]) for item in top_items]

    return results
