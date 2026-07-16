from __future__ import annotations

import hashlib
import json
import logging
import uuid

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from paperlens.core.config import settings
from paperlens.core.errors import AppError
from paperlens.models.models import PaperHighlight, PaperKnowledgeCard, PaperNote
from paperlens.services.personal_learning_common import commit_or_conflict, owned_page, owned_paper


logger = logging.getLogger(__name__)


def _compute_source_hash(paper_id: str, page_number: int, page_text_hash: str, char_start: int, char_end: int, quoted_text: str) -> str:
    canonical = json.dumps(
        {
            "paper_id": paper_id,
            "page": page_number,
            "page_hash": page_text_hash,
            "range": [char_start, char_end],
            "quoted": quoted_text,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def create_highlight(
    paper_id: str,
    user_id: str,
    page_number: int,
    char_start: int,
    char_end: int,
    color: str,
    db: Session,
) -> tuple[PaperHighlight, bool]:
    paper = owned_paper(db, paper_id, user_id, require_parsed=True)
    page = owned_page(db, paper, page_number)
    if char_start < 0 or char_end <= char_start:
        raise AppError("VALIDATION_ERROR", "高亮区间无效", 422)
    text = page.normalized_text_content if page.normalized_text_content else page.text_content
    if not text:
        raise AppError("PAGE_TEXT_UNAVAILABLE", "当前页面没有可高亮文本", 409)
    if char_end > len(text):
        raise AppError("VALIDATION_ERROR", "选区超出页面文本范围", 422)
    selected = text[char_start:char_end]
    if not selected.strip():
        raise AppError("VALIDATION_ERROR", "选区不能为空白", 422)
    if len(selected) > settings.highlight_max_chars:
        raise AppError("VALIDATION_ERROR", "选区超过长度限制", 422)
    page_text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    highlight = PaperHighlight(
        id=str(uuid.uuid4()),
        user_id=user_id,
        paper_id=paper_id,
        page_number=page_number,
        char_start=char_start,
        char_end=char_end,
        quoted_text=selected,
        source_hash=_compute_source_hash(paper_id, page_number, page_text_hash, char_start, char_end, selected),
        color=color,
    )
    db.add(highlight)
    try:
        db.commit()
        db.refresh(highlight)
        return highlight, False
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(PaperHighlight)
            .filter(
                PaperHighlight.user_id == user_id,
                PaperHighlight.paper_id == paper_id,
                PaperHighlight.page_number == page_number,
                PaperHighlight.char_start == char_start,
                PaperHighlight.char_end == char_end,
            )
            .one_or_none()
        )
        if existing is not None:
            return existing, True
        logger.error("personal_learning_write_failed stage=create_highlight paper_id=%s error_type=IntegrityError", paper_id)
        raise AppError("WRITE_CONFLICT", "高亮保存冲突，请重试", 409) from None
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("personal_learning_write_failed stage=create_highlight paper_id=%s error_type=%s", paper_id, type(exc).__name__)
        raise AppError("WRITE_CONFLICT", "高亮保存冲突，请重试", 409) from None


def list_highlights(
    paper_id: str,
    user_id: str,
    db: Session,
    page_number: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    owned_paper(db, paper_id, user_id)
    query = db.query(PaperHighlight).filter(PaperHighlight.user_id == user_id, PaperHighlight.paper_id == paper_id)
    if page_number is not None:
        query = query.filter(PaperHighlight.page_number == page_number)
    total = query.order_by(None).count()
    items = (
        query.order_by(PaperHighlight.page_number.asc(), PaperHighlight.char_start.asc(), PaperHighlight.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def delete_highlight(highlight_id: str, user_id: str, db: Session) -> None:
    highlight = db.query(PaperHighlight).filter(PaperHighlight.id == highlight_id, PaperHighlight.user_id == user_id).one_or_none()
    if highlight is None:
        raise AppError("NOT_FOUND", "高亮不存在", 404)
    note_ref = db.query(PaperNote.id).filter(
        PaperNote.user_id == user_id,
        PaperNote.paper_id == highlight.paper_id,
        PaperNote.highlight_id == highlight_id,
    ).first()
    card_ref = db.query(PaperKnowledgeCard.id).filter(
        PaperKnowledgeCard.user_id == user_id,
        PaperKnowledgeCard.paper_id == highlight.paper_id,
        PaperKnowledgeCard.source_highlight_id == highlight_id,
    ).first()
    if note_ref or card_ref:
        raise AppError("REFERENCED", "高亮已被学习记录引用，无法删除", 409)
    db.delete(highlight)
    commit_or_conflict(db, stage="delete_highlight", paper_id=highlight.paper_id)
