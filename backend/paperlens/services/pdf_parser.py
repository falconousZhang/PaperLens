from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid

from paperlens.core.enums import PaperStatus, SectionType, EvidenceType
from paperlens.core.config import settings
from paperlens.models.models import (
    Paper,
    PaperPage,
    PaperSection,
    PaperChunk,
    PaperTable,
    Evidence,
)
from paperlens.utils.storage import get_storage

import fitz
import pdfplumber

logger = logging.getLogger(__name__)

_SECTION_PATTERNS: list[tuple[str, list[str]]] = [
    (SectionType.ABSTRACT, ["abstract"]),
    (SectionType.INTRODUCTION, ["introduction", "1 introduction", "1. introduction"]),
    (SectionType.METHOD, ["method", "methodology", "approach", "proposed method", "2 method", "3 method"]),
    (SectionType.EXPERIMENT, ["experiment", "experimental", "experimental setup", "experimental results"]),
    (SectionType.RESULT, ["result", "results", "evaluation"]),
    (SectionType.DISCUSSION, ["discussion", "analysis"]),
    (SectionType.CONCLUSION, ["conclusion", "conclusions", "concluding remarks", "summary"]),
    (SectionType.REFERENCES, ["reference", "references", "bibliography"]),
    (SectionType.APPENDIX, ["appendix", "appendices", "supplementary"]),
]


def _detect_section_type(title: str) -> str:
    lower = title.strip().lower()
    for section_type, patterns in _SECTION_PATTERNS:
        for pattern in patterns:
            if lower == pattern or lower.startswith(pattern + " ") or lower.startswith(pattern + ":"):
                return section_type
    return SectionType.OTHER


def compute_file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def check_pdf_magic(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except Exception:
        return False


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_pdf(paper_id: str, pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    max_pages = settings.max_page_count

    try:
        if len(doc) > max_pages:
            raise ValueError(f"页数超出限制: {len(doc)} > {max_pages}")

        total_chars = 0
        for page in doc:
            total_chars += len(page.get_text().strip())
        if total_chars < len(doc) * 10:
            raise ValueError("OCR_NOT_SUPPORTED")

        pages_data = []
        for page_idx, page in enumerate(doc):
            text = page.get_text()
            normalized = _normalize_whitespace(text)
            pages_data.append({
                "page_number": page_idx + 1,
                "text_content": text,
                "normalized_text_content": normalized,
                "width": page.rect.width,
                "height": page.rect.height,
            })

        sections_data = _detect_sections(doc, pages_data)
        chunks_data = _chunk_text(sections_data, pages_data)
        tables_data = _extract_tables(pdf_path, pages_data)
        evidences_data = _generate_evidences(doc, pages_data, chunks_data, sections_data)

        return {
            "pages": pages_data,
            "sections": sections_data,
            "chunks": chunks_data,
            "tables": tables_data,
            "evidences": evidences_data,
        }
    finally:
        doc.close()


def _detect_sections(doc: fitz.Document, pages_data: list[dict]) -> list[dict]:
    sections = []
    seq = 0
    current_section = None

    for page_data in pages_data:
        page_num = page_data["page_number"]
        text = page_data["text_content"]
        lines = text.split("\n")

        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) > 200:
                continue
            if len(stripped) < 100 and stripped[0].isupper() and not stripped.endswith("."):
                detected = _detect_section_type(stripped)
                if detected != SectionType.OTHER or stripped[0].isdigit():
                    if current_section:
                        sections.append(current_section)
                    seq += 1
                    current_section = {
                        "section_type": detected,
                        "title": stripped,
                        "level": 1,
                        "sequence": seq,
                        "start_page": page_num,
                        "end_page": page_num,
                        "text_content": "",
                    }
                    continue
            if current_section:
                current_section["text_content"] += stripped + "\n"
                current_section["end_page"] = page_num

    if current_section:
        sections.append(current_section)

    if not sections:
        all_text = "\n".join(p["text_content"] or "" for p in pages_data)
        sections.append({
            "section_type": SectionType.OTHER,
            "title": "",
            "level": 1,
            "sequence": 1,
            "start_page": 1,
            "end_page": len(pages_data),
            "text_content": all_text,
        })

    return sections


def _chunk_text(sections_data: list[dict], pages_data: list[dict]) -> list[dict]:
    max_chars = settings.chunk_max_chars
    overlap = settings.chunk_overlap_chars
    chunks = []
    chunk_index = 0

    for section in sections_data:
        text = section.get("text_content", "")
        if not text.strip():
            continue

        start = 0
        while start < len(text):
            end = start + max_chars
            chunk_text = text[start:end]
            if not chunk_text.strip():
                start = end - overlap
                continue

            start_page = section.get("start_page", 1)
            end_page = section.get("end_page", start_page)
            page_numbers = list(range(start_page, end_page + 1))

            chunks.append({
                "section_sequence": section.get("sequence"),
                "chunk_index": chunk_index,
                "content": chunk_text,
                "char_count": len(chunk_text),
                "page_numbers": page_numbers,
            })
            chunk_index += 1
            start = end - overlap if end < len(text) else end

    return chunks


def _extract_tables(pdf_path: str, pages_data: list[dict]) -> list[dict]:
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1
                try:
                    page_tables = page.find_tables()
                    for table_idx, table in enumerate(page_tables):
                        if not table or not table.extract():
                            continue
                        raw_rows = []
                        for row in table.extract():
                            raw_rows.append([str(cell) if cell else "" for cell in row])
                        raw_text = "\n".join("\t".join(row) for row in raw_rows)
                        bbox = table.bbox if hasattr(table, "bbox") else None
                        tables.append({
                            "page_number": page_num,
                            "table_index": table_idx + 1,
                            "caption": None,
                            "bbox_x0": bbox[0] if bbox else None,
                            "bbox_y0": bbox[1] if bbox else None,
                            "bbox_x1": bbox[2] if bbox else None,
                            "bbox_y1": bbox[3] if bbox else None,
                            "structured_data": {"rows": raw_rows},
                            "raw_text": raw_text,
                        })
                except Exception:
                    logger.warning("Table extraction failed on page %d", page_num, exc_info=True)
    except Exception:
        logger.warning("Failed to open PDF for table extraction: %s", pdf_path, exc_info=True)
    return tables


def _generate_evidences(
    doc: fitz.Document,
    pages_data: list[dict],
    chunks_data: list[dict],
    sections_data: list[dict],
) -> list[dict]:
    evidences = []
    chunk_by_page: dict[int, list[dict]] = {}
    for chunk in chunks_data:
        for pn in chunk.get("page_numbers", []):
            chunk_by_page.setdefault(pn, []).append(chunk)

    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        normalized_page = pages_data[page_idx]["normalized_text_content"] or ""
        page_width = page.rect.width
        page_height = page.rect.height

        blocks = page.get_text("blocks")
        search_offset = 0
        for block in blocks:
            bbox_x0, bbox_y0, bbox_x1, bbox_y1, block_text, block_no, block_type = block
            if block_type != 0:
                continue
            block_text = block_text.strip()
            if not block_text or len(block_text) < 10:
                continue

            normalized_block = _normalize_whitespace(block_text)
            char_start = normalized_page.find(normalized_block, search_offset)
            char_end = None
            if char_start >= 0:
                char_end = char_start + len(normalized_block)
                if char_end > len(normalized_page):
                    char_end = len(normalized_page)
                search_offset = char_end
            else:
                logger.warning(
                    "Evidence block not found in normalized page text, paper_id=%s page=%d block_start=%.0f",
                    pages_data[page_idx].get("paper_id", "unknown"),
                    page_num,
                    bbox_x0,
                )

            if bbox_x1 > page_width:
                bbox_x1 = page_width
            if bbox_y1 > page_height:
                bbox_y1 = page_height

            matched_chunk = None
            for chunk in chunk_by_page.get(page_num, []):
                chunk_norm = _normalize_whitespace(chunk["content"])
                if normalized_block in chunk_norm or chunk_norm[:80] in normalized_block:
                    matched_chunk = chunk
                    break

            evidences.append({
                "quoted_text": normalized_block,
                "page_number": page_num,
                "bbox_x0": bbox_x0,
                "bbox_y0": bbox_y0,
                "bbox_x1": bbox_x1,
                "bbox_y1": bbox_y1,
                "char_start": char_start if char_start >= 0 else None,
                "char_end": char_end,
                "evidence_type": EvidenceType.TEXT,
                "chunk_index": matched_chunk["chunk_index"] if matched_chunk else None,
            })

    return evidences
