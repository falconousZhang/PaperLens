from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from paperlens.core.enums import AnchorType
from paperlens.core.errors import AppError
from paperlens.models.models import PaperHighlight, PaperKnowledgeCard, PaperNote
from paperlens.services.personal_learning_common import clean_user_text, commit_or_conflict, owned_page, owned_paper


def create_note(
    paper_id: str,
    user_id: str,
    anchor_type: AnchorType,
    page_number: int | None,
    highlight_id: str | None,
    content: str,
    db: Session,
) -> PaperNote:
    paper = owned_paper(db, paper_id, user_id, require_parsed=True)
    if anchor_type == AnchorType.PAPER:
        if page_number is not None or highlight_id is not None:
            raise AppError("VALIDATION_ERROR", "论文级笔记不能设置页面或高亮", 422)
    elif anchor_type == AnchorType.PAGE:
        if page_number is None or highlight_id is not None:
            raise AppError("VALIDATION_ERROR", "页面级笔记锚点无效", 422)
        owned_page(db, paper, page_number)
    elif anchor_type == AnchorType.HIGHLIGHT:
        if page_number is not None or highlight_id is None:
            raise AppError("VALIDATION_ERROR", "高亮级笔记锚点无效", 422)
        highlight = db.query(PaperHighlight).filter(
            PaperHighlight.id == highlight_id,
            PaperHighlight.user_id == user_id,
            PaperHighlight.paper_id == paper_id,
        ).one_or_none()
        if highlight is None:
            raise AppError("NOT_FOUND", "高亮不存在", 404)
    cleaned = clean_user_text(content, "笔记内容", 20000)
    note = PaperNote(
        id=str(uuid.uuid4()),
        user_id=user_id,
        paper_id=paper_id,
        anchor_type=anchor_type,
        page_number=page_number,
        highlight_id=highlight_id,
        content=cleaned,
    )
    db.add(note)
    commit_or_conflict(db, stage="create_note", paper_id=paper_id)
    db.refresh(note)
    return note


def list_notes(
    paper_id: str,
    user_id: str,
    db: Session,
    anchor_type: AnchorType | None = None,
    page_number: int | None = None,
    highlight_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    owned_paper(db, paper_id, user_id)
    query = db.query(PaperNote).filter(PaperNote.user_id == user_id, PaperNote.paper_id == paper_id)
    if anchor_type is not None:
        query = query.filter(PaperNote.anchor_type == anchor_type)
    if page_number is not None:
        query = query.filter(PaperNote.page_number == page_number)
    if highlight_id is not None:
        query = query.filter(PaperNote.highlight_id == highlight_id)
    total = query.order_by(None).count()
    items = (
        query.order_by(PaperNote.created_at.desc(), PaperNote.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def patch_note(note_id: str, user_id: str, content: str, db: Session) -> PaperNote:
    note = db.query(PaperNote).filter(PaperNote.id == note_id, PaperNote.user_id == user_id).one_or_none()
    if note is None:
        raise AppError("NOT_FOUND", "笔记不存在", 404)
    note.content = clean_user_text(content, "笔记内容", 20000)
    note.updated_at = datetime.now(timezone.utc)
    commit_or_conflict(db, stage="patch_note", paper_id=note.paper_id)
    db.refresh(note)
    return note


def delete_note(note_id: str, user_id: str, db: Session) -> None:
    note = db.query(PaperNote).filter(PaperNote.id == note_id, PaperNote.user_id == user_id).one_or_none()
    if note is None:
        raise AppError("NOT_FOUND", "笔记不存在", 404)
    card_ref = db.query(PaperKnowledgeCard.id).filter(
        PaperKnowledgeCard.user_id == user_id,
        PaperKnowledgeCard.paper_id == note.paper_id,
        PaperKnowledgeCard.source_note_id == note_id,
    ).first()
    if card_ref:
        raise AppError("REFERENCED", "笔记已被知识卡引用，无法删除", 409)
    db.delete(note)
    commit_or_conflict(db, stage="delete_note", paper_id=note.paper_id)
