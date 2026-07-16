from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, case, false, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, aliased

from paperlens.core.enums import ReadingStatus
from paperlens.core.errors import AppError
from paperlens.models.models import Paper, PaperBookmark, PaperHighlight, PaperKnowledgeCard, PaperLibraryEntry, PaperNote
from paperlens.services.personal_learning_common import commit_or_conflict, owned_page, owned_paper


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _count_for(model, user_id: str):
    return (
        select(func.count())
        .select_from(model)
        .where(model.user_id == user_id, model.paper_id == Paper.id)
        .correlate(Paper)
        .scalar_subquery()
    )


def list_library_papers(
    user_id: str,
    db: Session,
    page: int = 1,
    page_size: int = 20,
    reading_status: ReadingStatus | None = None,
    favorite: bool | None = None,
    collection_name: str | None = None,
    keyword: str | None = None,
) -> dict:
    entry = aliased(PaperLibraryEntry)
    highlight_count = _count_for(PaperHighlight, user_id).label("highlight_count")
    bookmark_count = _count_for(PaperBookmark, user_id).label("bookmark_count")
    note_count = _count_for(PaperNote, user_id).label("note_count")
    card_count = _count_for(PaperKnowledgeCard, user_id).label("card_count")
    query = (
        db.query(Paper, entry, highlight_count, bookmark_count, note_count, card_count)
        .outerjoin(entry, and_(entry.paper_id == Paper.id, entry.user_id == user_id))
        .filter(Paper.user_id == user_id)
    )
    if keyword is not None and keyword.strip():
        pattern = _contains_pattern(keyword.strip())
        query = query.filter(Paper.title.ilike(pattern, escape="\\") | Paper.filename.ilike(pattern, escape="\\"))
    if reading_status is not None:
        query = query.filter(func.coalesce(entry.reading_status, ReadingStatus.TO_READ) == reading_status)
    if favorite is not None:
        query = query.filter(func.coalesce(entry.favorite, false()) == favorite)
    if collection_name is not None:
        query = query.filter(entry.collection_name == collection_name.strip())
    total = query.order_by(None).count()
    rows = (
        query.order_by(
            func.coalesce(entry.favorite, false()).desc(),
            entry.last_read_at.desc().nullslast(),
            Paper.created_at.desc(),
            Paper.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for paper, library_entry, highlights, bookmarks, notes, cards in rows:
        furthest_page = library_entry.furthest_page if library_entry else None
        page_count = paper.page_count or 0
        progress_percent = min(100, furthest_page * 100 // page_count) if furthest_page and page_count else 0
        items.append(
            {
                "paper_id": paper.id,
                "title": paper.title,
                "filename": paper.filename,
                "page_count": paper.page_count,
                "status": paper.status,
                "created_at": paper.created_at,
                "reading_status": library_entry.reading_status if library_entry else ReadingStatus.TO_READ,
                "favorite": library_entry.favorite if library_entry else False,
                "collection_name": library_entry.collection_name if library_entry else None,
                "last_page": library_entry.last_page if library_entry else None,
                "furthest_page": furthest_page,
                "progress_percent": progress_percent,
                "last_read_at": library_entry.last_read_at if library_entry else None,
                "completed_at": library_entry.completed_at if library_entry else None,
                "updated_at": library_entry.updated_at if library_entry else paper.created_at,
                "highlight_count": highlights,
                "bookmark_count": bookmarks,
                "note_count": notes,
                "card_count": cards,
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def patch_library_entry(
    paper_id: str,
    user_id: str,
    reading_status: ReadingStatus | None,
    favorite: bool | None,
    collection_name: str | None,
    provided_fields: set[str],
    db: Session,
) -> PaperLibraryEntry:
    owned_paper(db, paper_id, user_id)
    if not provided_fields:
        raise AppError("VALIDATION_ERROR", "至少提供一个更新字段", 422)
    now = datetime.now(timezone.utc)
    insert_stmt = (
        pg_insert(PaperLibraryEntry)
        .values(
            user_id=user_id,
            paper_id=paper_id,
            reading_status=ReadingStatus.TO_READ,
            favorite=False,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "paper_id"])
    )
    db.execute(insert_stmt)
    entry = (
        db.query(PaperLibraryEntry)
        .filter(PaperLibraryEntry.user_id == user_id, PaperLibraryEntry.paper_id == paper_id)
        .with_for_update()
        .one()
    )
    if "reading_status" in provided_fields:
        entry.reading_status = reading_status
        entry.completed_at = now if reading_status == ReadingStatus.COMPLETED else None
    if "favorite" in provided_fields:
        entry.favorite = favorite
    if "collection_name" in provided_fields:
        entry.collection_name = collection_name.strip() if collection_name is not None else None
    entry.updated_at = now
    commit_or_conflict(db, stage="patch_library_entry", paper_id=paper_id)
    db.refresh(entry)
    return entry


def patch_reading_progress(paper_id: str, user_id: str, page_number: int, db: Session) -> PaperLibraryEntry:
    paper = owned_paper(db, paper_id, user_id, require_parsed=True)
    owned_page(db, paper, page_number)
    now = datetime.now(timezone.utc)
    table = PaperLibraryEntry.__table__
    stmt = pg_insert(table).values(
        user_id=user_id,
        paper_id=paper_id,
        reading_status=ReadingStatus.READING,
        favorite=False,
        last_page=page_number,
        furthest_page=page_number,
        last_read_at=now,
        created_at=now,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[table.c.user_id, table.c.paper_id],
        set_={
            "last_page": page_number,
            "furthest_page": func.greatest(func.coalesce(table.c.furthest_page, page_number), page_number),
            "last_read_at": now,
            "reading_status": case(
                (table.c.reading_status == ReadingStatus.TO_READ, ReadingStatus.READING),
                else_=table.c.reading_status,
            ),
            "updated_at": now,
        },
    )
    db.execute(stmt)
    commit_or_conflict(db, stage="patch_reading_progress", paper_id=paper_id)
    return db.query(PaperLibraryEntry).filter(PaperLibraryEntry.user_id == user_id, PaperLibraryEntry.paper_id == paper_id).one()
