import logging
import math

from paperlens.core.config import settings
from paperlens.core.enums import ReviewDimension
from paperlens.models.models import Evidence
from paperlens.services.embedding_client import (
    EmbeddingClient,
    EmbeddingError,
    cosine_similarity,
)

logger = logging.getLogger(__name__)

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
    if top_k is None:
        top_k = settings.review_evidence_top_k

    rows = (
        db.query(Evidence.id, Evidence.quoted_text, Evidence.page_number, Evidence.created_at, Evidence.id)
        .filter(Evidence.paper_id == paper_id)
        .order_by(Evidence.page_number.asc(), Evidence.created_at.asc(), Evidence.id.asc())
        .all()
    )

    if not rows:
        return {d: [] for d in dimensions}

    evidence_data = []
    for r in rows:
        evidence_data.append({
            "id": str(r[0]),
            "text": r[1] or "",
            "page_number": r[2],
            "created_at": r[3],
            "raw_id": r[4],
        })

    evidence_texts = [e["text"] for e in evidence_data]
    evidence_vectors = embedding_client.embed(evidence_texts)

    query_texts = [
        build_dimension_query(paper_title, d, language) for d in dimensions
    ]
    query_vectors = embedding_client.embed(query_texts)

    results: dict[ReviewDimension, list[tuple[str, str]]] = {}

    for dim_idx, dimension in enumerate(dimensions):
        query_vec = query_vectors[dim_idx]
        scored = []
        for ev_idx, ev in enumerate(evidence_data):
            ev_vec = evidence_vectors[ev_idx]
            sim = cosine_similarity(query_vec, ev_vec)
            scored.append((sim, ev["page_number"], ev["created_at"], ev["raw_id"], ev["id"], ev["text"]))

        scored.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))

        top_items = scored[:top_k]
        results[dimension] = [(item[4], item[5]) for item in top_items]

    return results