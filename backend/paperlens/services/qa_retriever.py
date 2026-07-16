from __future__ import annotations

from paperlens.core.config import settings
from paperlens.services.embedding_client import (
    EmbeddingClient,
    cosine_similarity,
    get_embedding_client,
    validate_embeddings,
)


def retrieve_evidence(
    question: str,
    evidence_rows: list[dict],
    embedding_client: EmbeddingClient | None = None,
) -> list[dict]:
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("question must not be blank")

    valid = [
        row
        for row in evidence_rows
        if isinstance(row.get("quoted_text"), str) and row["quoted_text"].strip()
    ]
    if not valid:
        return []

    evidence_texts = [
        row["quoted_text"].strip()[: settings.qa_evidence_max_chars]
        for row in valid
    ]
    client = embedding_client or get_embedding_client()
    vectors = client.embed([normalized_question, *evidence_texts])
    validate_embeddings(vectors, len(evidence_texts) + 1)
    query_vector = vectors[0]

    scored = [
        (cosine_similarity(query_vector, evidence_vector), row)
        for evidence_vector, row in zip(vectors[1:], valid, strict=True)
    ]
    scored.sort(
        key=lambda item: (
            -item[0],
            int(item[1]["page_number"]),
            item[1].get("created_at_iso", ""),
            str(item[1]["id"]),
        )
    )
    return [row for _, row in scored[: settings.qa_evidence_top_k]]
