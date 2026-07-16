from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from pydantic import UUID4
from sqlalchemy.orm import Session

from paperlens.core.database import get_db
from paperlens.core.deps import get_current_user_id
from paperlens.core.enums import ReadingStatus
from paperlens.models.models import PaperLibraryEntry
from paperlens.schemas.library import (
    LibraryPaperItem,
    LibraryPaperListResponse,
    LibraryEntryResponse,
    PatchLibraryEntryRequest,
    PatchReadingProgressRequest,
    ReadingProgressResponse,
)
from paperlens.services.library_service import (
    list_library_papers,
    patch_library_entry,
    patch_reading_progress,
)


router = APIRouter(tags=["library"])


def _progress_percent(entry: PaperLibraryEntry | None, page_count: int | None) -> int:
    if entry is None or not entry.furthest_page or not page_count:
        return 0
    return min(100, entry.furthest_page * 100 // page_count)


@router.get(
    "/library/papers",
    response_model=LibraryPaperListResponse,
)
def list_library_papers_api(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    reading_status: ReadingStatus | None = Query(None),
    favorite: bool | None = Query(None),
    collection_name: str | None = Query(None, max_length=100),
    keyword: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = list_library_papers(
        user_id=user_id,
        db=db,
        page=page,
        page_size=page_size,
        reading_status=reading_status,
        favorite=favorite,
        collection_name=collection_name,
        keyword=keyword,
    )
    items = [
        LibraryPaperItem(
            paper_id=item["paper_id"],
            title=item["title"],
            filename=item["filename"],
            page_count=item["page_count"],
            status=item["status"],
            created_at=item["created_at"],
            reading_status=item["reading_status"],
            favorite=item["favorite"],
            collection_name=item["collection_name"],
            last_page=item["last_page"],
            furthest_page=item["furthest_page"],
            progress_percent=item["progress_percent"],
            last_read_at=item["last_read_at"],
            completed_at=item["completed_at"],
            updated_at=item["updated_at"],
            highlight_count=item["highlight_count"],
            bookmark_count=item["bookmark_count"],
            note_count=item["note_count"],
            card_count=item["card_count"],
        )
        for item in result["items"]
    ]
    return LibraryPaperListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.patch(
    "/papers/{paper_id}/library-entry",
    response_model=LibraryEntryResponse,
)
def patch_library_entry_api(
    body: PatchLibraryEntryRequest,
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    entry = patch_library_entry(
        paper_id=str(paper_id),
        user_id=user_id,
        reading_status=body.reading_status,
        favorite=body.favorite,
        collection_name=body.collection_name,
        provided_fields=set(body.model_fields_set),
        db=db,
    )
    return LibraryEntryResponse(
        paper_id=entry.paper_id,
        reading_status=entry.reading_status,
        favorite=entry.favorite,
        collection_name=entry.collection_name,
        last_page=entry.last_page,
        furthest_page=entry.furthest_page,
        last_read_at=entry.last_read_at,
        completed_at=entry.completed_at,
        updated_at=entry.updated_at,
    )


@router.patch(
    "/papers/{paper_id}/reading-progress",
    response_model=ReadingProgressResponse,
)
def patch_reading_progress_api(
    body: PatchReadingProgressRequest,
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    entry = patch_reading_progress(
        paper_id=str(paper_id),
        user_id=user_id,
        page_number=body.page_number,
        db=db,
    )
    from paperlens.models.models import Paper
    paper = db.get(Paper, str(paper_id))
    pp = _progress_percent(entry, paper.page_count if paper else None)
    return ReadingProgressResponse(
        paper_id=entry.paper_id,
        reading_status=entry.reading_status,
        last_page=entry.last_page,
        furthest_page=entry.furthest_page,
        progress_percent=pp,
        last_read_at=entry.last_read_at,
        updated_at=entry.updated_at,
    )
