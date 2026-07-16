from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from paperlens.core.enums import MasteryStatus
from paperlens.core.errors import AppError
from paperlens.models.models import PaperHighlight, PaperKnowledgeCard, PaperNote
from paperlens.services.personal_learning_common import clean_user_text, commit_or_conflict, owned_paper


def create_knowledge_card(
    paper_id: str,
    user_id: str,
    source_note_id: str | None,
    source_highlight_id: str | None,
    front: str,
    back: str,
    db: Session,
) -> PaperKnowledgeCard:
    owned_paper(db, paper_id, user_id, require_parsed=True)
    if source_note_id is not None and source_highlight_id is not None:
        raise AppError("VALIDATION_ERROR", "知识卡最多只能选择一个来源", 422)
    if source_note_id is not None:
        note = db.query(PaperNote).filter(
            PaperNote.id == source_note_id,
            PaperNote.user_id == user_id,
            PaperNote.paper_id == paper_id,
        ).one_or_none()
        if note is None:
            raise AppError("NOT_FOUND", "来源笔记不存在", 404)
    if source_highlight_id is not None:
        highlight = db.query(PaperHighlight).filter(
            PaperHighlight.id == source_highlight_id,
            PaperHighlight.user_id == user_id,
            PaperHighlight.paper_id == paper_id,
        ).one_or_none()
        if highlight is None:
            raise AppError("NOT_FOUND", "来源高亮不存在", 404)
    card = PaperKnowledgeCard(
        id=str(uuid.uuid4()),
        user_id=user_id,
        paper_id=paper_id,
        source_note_id=source_note_id,
        source_highlight_id=source_highlight_id,
        front=clean_user_text(front, "知识卡正面", 2000),
        back=clean_user_text(back, "知识卡背面", 10000),
        mastery_status=MasteryStatus.NEW,
        archived=False,
    )
    db.add(card)
    commit_or_conflict(db, stage="create_knowledge_card", paper_id=paper_id)
    db.refresh(card)
    return card


def list_knowledge_cards(
    paper_id: str,
    user_id: str,
    db: Session,
    mastery_status: MasteryStatus | None = None,
    archived: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    owned_paper(db, paper_id, user_id)
    query = db.query(PaperKnowledgeCard).filter(
        PaperKnowledgeCard.user_id == user_id,
        PaperKnowledgeCard.paper_id == paper_id,
    )
    if mastery_status is not None:
        query = query.filter(PaperKnowledgeCard.mastery_status == mastery_status)
    if archived is not None:
        query = query.filter(PaperKnowledgeCard.archived == archived)
    total = query.order_by(None).count()
    items = (
        query.order_by(PaperKnowledgeCard.updated_at.desc(), PaperKnowledgeCard.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def patch_knowledge_card(
    card_id: str,
    user_id: str,
    front: str | None,
    back: str | None,
    mastery_status: MasteryStatus | None,
    archived: bool | None,
    provided_fields: set[str],
    db: Session,
) -> PaperKnowledgeCard:
    card = db.query(PaperKnowledgeCard).filter(
        PaperKnowledgeCard.id == card_id,
        PaperKnowledgeCard.user_id == user_id,
    ).one_or_none()
    if card is None:
        raise AppError("NOT_FOUND", "知识卡不存在", 404)
    if not provided_fields:
        raise AppError("VALIDATION_ERROR", "至少提供一个更新字段", 422)
    if "front" in provided_fields:
        card.front = clean_user_text(front, "知识卡正面", 2000)
    if "back" in provided_fields:
        card.back = clean_user_text(back, "知识卡背面", 10000)
    now = datetime.now(timezone.utc)
    if "mastery_status" in provided_fields and mastery_status != card.mastery_status:
        card.mastery_status = mastery_status
        card.last_reviewed_at = now
    if "archived" in provided_fields:
        card.archived = archived
    card.updated_at = now
    commit_or_conflict(db, stage="patch_knowledge_card", paper_id=card.paper_id)
    db.refresh(card)
    return card


def delete_knowledge_card(card_id: str, user_id: str, db: Session) -> None:
    card = db.query(PaperKnowledgeCard).filter(
        PaperKnowledgeCard.id == card_id,
        PaperKnowledgeCard.user_id == user_id,
    ).one_or_none()
    if card is None:
        raise AppError("NOT_FOUND", "知识卡不存在", 404)
    db.delete(card)
    commit_or_conflict(db, stage="delete_knowledge_card", paper_id=card.paper_id)
