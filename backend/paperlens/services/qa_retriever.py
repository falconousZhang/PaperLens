from __future__ import annotations

import re

from paperlens.core.config import settings
from paperlens.services.embedding_client import (
    EmbeddingClient,
    cosine_similarity,
    get_embedding_client,
    validate_embeddings,
)


_NUMBER_RANGE = re.compile(r"(?<!\d)(\d{1,4})\s*(?:-|–|—|~|～|到|至)\s*(\d{1,4})(?!\d)")
_NUMBER = re.compile(r"(?<!\d)(\d{1,4})(?!\d)")
_FIGURE_TERM = re.compile(r"\bfig(?:ure)?s?\.?\b|图(?:片|表)?", re.IGNORECASE)
_TABLE_TERM = re.compile(r"\btables?\b|表格|表(?=\s*(?:第\s*)?\d)", re.IGNORECASE)
_PAGE_PATTERNS = (
    re.compile(r"(?:第\s*)?(\d{1,4})\s*页"),
    re.compile(r"\bpages?\s*(\d{1,4})\b", re.IGNORECASE),
)


def _safe_page_number(row: dict) -> int:
    try:
        return int(row.get("page_number") or 0)
    except (TypeError, ValueError):
        return 0


def _expand_ranges(text: str) -> set[int]:
    numbers: set[int] = set()
    for match in _NUMBER_RANGE.finditer(text):
        start, end = int(match.group(1)), int(match.group(2))
        if start > end:
            start, end = end, start
        if end - start <= 50:
            numbers.update(range(start, end + 1))
    return numbers


def _referenced_numbers(question: str, kind: str) -> set[int]:
    term = _FIGURE_TERM if kind == "figure" else _TABLE_TERM
    if term.search(question) is None:
        return set()

    numbers = _expand_ranges(question)
    if kind == "figure":
        patterns = (
            re.compile(r"(?:\bfig(?:ure)?s?\.?|图(?:片|表)?)\s*(?:编号|序号|第|no\.?|nos\.?)?\s*(\d{1,4})", re.IGNORECASE),
            re.compile(r"(\d{1,4})\s*号?\s*(?:的)?\s*(?:图|图片|图表)"),
        )
    else:
        patterns = (
            re.compile(r"(?:\btables?|表格|表)\s*(?:编号|序号|第|no\.?|nos\.?)?\s*(\d{1,4})", re.IGNORECASE),
            re.compile(r"(\d{1,4})\s*号?\s*(?:的)?\s*(?:表|表格)"),
        )
    for pattern in patterns:
        numbers.update(int(match.group(1)) for match in pattern.finditer(question))

    for match in term.finditer(question):
        nearby = question[match.end() : match.end() + 60]
        nearby = re.split(r"[.;!?。！？\n]", nearby, maxsplit=1)[0]
        numbers.update(int(value) for value in _NUMBER.findall(nearby))
    return numbers


def _referenced_pages(question: str) -> set[int]:
    pages: set[int] = set()
    for pattern in _PAGE_PATTERNS:
        pages.update(int(match.group(1)) for match in pattern.finditer(question))
    return pages


def _reference_hits(text: str, numbers: set[int], kind: str) -> int:
    if not numbers:
        return 0
    term = _FIGURE_TERM if kind == "figure" else _TABLE_TERM
    hits: set[int] = set()
    for fragment in re.split(r"[.;!?。！？\n]", text):
        if term.search(fragment) is None:
            continue
        fragment_numbers = {int(value) for value in _NUMBER.findall(fragment)}
        hits.update(numbers.intersection(fragment_numbers))
    return len(hits)


def _context_value(text: str) -> float:
    lowered = text.lower()
    score = min(len(text) / 300, 4.0)
    markers = (
        "results indicate",
        "results show",
        "we find",
        "we observe",
        "demonstrate",
        "illustrate",
        "suggest",
        "conclusion",
        "结果表明",
        "结果显示",
        "说明",
        "表明",
        "结论",
    )
    score += sum(1.5 for marker in markers if marker in lowered)
    score += min(len(_FIGURE_TERM.findall(text)) + len(_TABLE_TERM.findall(text)), 6) * 0.5
    score += min(len(re.findall(r"[.;。；]", text)), 4) * 0.25
    return score


def retrieve_evidence(
    question: str,
    evidence_rows: list[dict],
    embedding_client: EmbeddingClient | None = None,
    current_page: int | None = None,
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
        {
            "score": cosine_similarity(query_vector, evidence_vector),
            "row": row,
            "text": text,
        }
        for evidence_vector, row, text in zip(
            vectors[1:], valid, evidence_texts, strict=True
        )
    ]
    scored.sort(
        key=lambda item: (
            -item["score"],
            _safe_page_number(item["row"]),
            item["row"].get("created_at_iso", ""),
            str(item["row"]["id"]),
        )
    )

    top_k = settings.qa_evidence_top_k
    figure_numbers = _referenced_numbers(normalized_question, "figure")
    table_numbers = _referenced_numbers(normalized_question, "table")
    selected: list[dict] = []
    selected_ids: set[str] = set()

    anchored = []
    for item in scored:
        hits = _reference_hits(item["text"], figure_numbers, "figure")
        hits += _reference_hits(item["text"], table_numbers, "table")
        if hits:
            anchored.append((hits, item))
    anchored.sort(
        key=lambda pair: (
            -pair[0],
            0 if current_page is not None and _safe_page_number(pair[1]["row"]) == current_page else 1,
            -_context_value(pair[1]["text"]),
            -pair[1]["score"],
            _safe_page_number(pair[1]["row"]),
            str(pair[1]["row"]["id"]),
        )
    )

    def add(item: dict) -> None:
        row_id = str(item["row"]["id"])
        if row_id not in selected_ids and len(selected) < top_k:
            selected.append(item["row"])
            selected_ids.add(row_id)

    for _, item in anchored:
        add(item)

    pages = _referenced_pages(normalized_question)
    if current_page is not None:
        pages.add(current_page)
    page_target = min(top_k, max(3, top_k // 2))
    if pages and len(selected) < page_target:
        page_candidates = [
            item for item in scored if _safe_page_number(item["row"]) in pages
        ]
        page_candidates.sort(
            key=lambda item: (
                -_context_value(item["text"]),
                -item["score"],
                _safe_page_number(item["row"]),
                str(item["row"]["id"]),
            )
        )
        for item in page_candidates:
            add(item)
            if len(selected) >= page_target:
                break

    for item in scored:
        add(item)
    return selected
