from __future__ import annotations

import logging
import uuid

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from paperlens.core.errors import AppError
from paperlens.models.models import PaperBookmark
from paperlens.services.personal_learning_common import clean_user_text, commit_or_conflict, owned_page, owned_paper


logger = logging.getLogger(__name__)


def create_bookmark(
    paper_id: str,
    user_id: str,
    page_number: int,
    label: str | None,
    db: Session,
) -> tuple[PaperBookmark, bool]:
    paper = owned_paper(db, paper_id, user_id, require_parsed=True)
    owned_page(db, paper, page_number)
    cleaned_label = clean_user_text(label, "书签标签", 100) if label is not None else None
    bookmark = PaperBookmark(
        id=str(uuid.uuid4()),
        user_id=user_id,
        paper_id=paper_id,
        page_number=page_number,
        label=cleaned_label,
    )
    db.add(bookmark)
    try:
        db.commit()
        db.refresh(bookmark)
        return bookmark, False
    except IntegrityError:
        db.rollback()
        existing = db.query(PaperBookmark).filter(
            PaperBookmark.user_id == user_id,
            PaperBookmark.paper_id == paper_id,
            PaperBookmark.page_number == page_number,
        ).one_or_none()
        if existing is not None:
            return existing, True
        logger.error("personal_learning_write_failed stage=create_bookmark paper_id=%s error_type=IntegrityError", paper_id)
        raise AppError("WRITE_CONFLICT", "书签保存冲突，请重试", 409) from None
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("personal_learning_write_failed stage=create_bookmark paper_id=%s error_type=%s", paper_id, type(exc).__name__)
        raise AppError("WRITE_CONFLICT", "书签保存冲突，请重试", 409) from None


def list_bookmarks(paper_id: str, user_id: str, db: Session, page: int = 1, page_size: int = 20) -> dict:
    owned_paper(db, paper_id, user_id)
    query = db.query(PaperBookmark).filter(PaperBookmark.user_id == user_id, PaperBookmark.paper_id == paper_id)
    total = query.order_by(None).count()
    items = (
        query.order_by(PaperBookmark.page_number.asc(), PaperBookmark.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def delete_bookmark(bookmark_id: str, user_id: str, db: Session) -> None:
    bookmark = db.query(PaperBookmark).filter(PaperBookmark.id == bookmark_id, PaperBookmark.user_id == user_id).one_or_none()
    if bookmark is None:
        raise AppError("NOT_FOUND", "书签不存在", 404)
    db.delete(bookmark)
    commit_or_conflict(db, stage="delete_bookmark", paper_id=bookmark.paper_id)
