from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query
from pydantic import UUID4
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse, Response

from paperlens.core.database import get_db
from paperlens.core.deps import get_current_user_id
from paperlens.core.enums import AnchorType, MasteryStatus
from paperlens.schemas.library import (
    CreateHighlightRequest,
    HighlightListResponse,
    HighlightResponse,
    CreateBookmarkRequest,
    BookmarkListResponse,
    BookmarkResponse,
    CreateNoteRequest,
    NoteListResponse,
    NoteResponse,
    PatchNoteRequest,
    CreateKnowledgeCardRequest,
    KnowledgeCardListResponse,
    KnowledgeCardResponse,
    PatchKnowledgeCardRequest,
)
from paperlens.services.highlight_service import create_highlight, delete_highlight, list_highlights
from paperlens.services.bookmark_service import create_bookmark, delete_bookmark, list_bookmarks
from paperlens.services.note_service import create_note, delete_note, list_notes, patch_note
from paperlens.services.card_service import create_knowledge_card, delete_knowledge_card, list_knowledge_cards, patch_knowledge_card


router = APIRouter(tags=["personal-learning"])


@router.post(
    "/papers/{paper_id}/highlights",
    response_model=HighlightResponse,
    status_code=201,
)
def create_highlight_api(
    body: CreateHighlightRequest,
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    hl, duplicate = create_highlight(
        paper_id=str(paper_id),
        user_id=user_id,
        page_number=body.page_number,
        char_start=body.char_start,
        char_end=body.char_end,
        color=body.color,
        db=db,
    )
    resp = HighlightResponse(
        id=hl.id,
        paper_id=hl.paper_id,
        page_number=hl.page_number,
        char_start=hl.char_start,
        char_end=hl.char_end,
        quoted_text=hl.quoted_text,
        color=hl.color,
        created_at=hl.created_at,
        updated_at=hl.updated_at,
        duplicate=duplicate,
    )
    if duplicate:
        return JSONResponse(content=resp.model_dump(mode="json"), status_code=200)
    return resp


@router.get(
    "/papers/{paper_id}/highlights",
    response_model=HighlightListResponse,
)
def list_highlights_api(
    paper_id: UUID4 = Path(...),
    page_number: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = list_highlights(
        paper_id=str(paper_id),
        user_id=user_id,
        db=db,
        page_number=page_number,
        page=page,
        page_size=page_size,
    )
    return HighlightListResponse(
        items=[
            HighlightResponse(
                id=hl.id,
                paper_id=hl.paper_id,
                page_number=hl.page_number,
                char_start=hl.char_start,
                char_end=hl.char_end,
                quoted_text=hl.quoted_text,
                color=hl.color,
                created_at=hl.created_at,
                updated_at=hl.updated_at,
                duplicate=False,
            )
            for hl in result["items"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.delete("/highlights/{highlight_id}", status_code=204)
def delete_highlight_api(
    highlight_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    delete_highlight(str(highlight_id), user_id, db)
    return Response(status_code=204)


@router.post(
    "/papers/{paper_id}/bookmarks",
    response_model=BookmarkResponse,
    status_code=201,
)
def create_bookmark_api(
    body: CreateBookmarkRequest,
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    bm, duplicate = create_bookmark(
        paper_id=str(paper_id),
        user_id=user_id,
        page_number=body.page_number,
        label=body.label,
        db=db,
    )
    resp = BookmarkResponse(
        id=bm.id,
        paper_id=bm.paper_id,
        page_number=bm.page_number,
        label=bm.label,
        created_at=bm.created_at,
        duplicate=duplicate,
    )
    if duplicate:
        return JSONResponse(content=resp.model_dump(mode="json"), status_code=200)
    return resp


@router.get(
    "/papers/{paper_id}/bookmarks",
    response_model=BookmarkListResponse,
)
def list_bookmarks_api(
    paper_id: UUID4 = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = list_bookmarks(str(paper_id), user_id, db, page=page, page_size=page_size)
    return BookmarkListResponse(
        items=[
            BookmarkResponse(
                id=bm.id,
                paper_id=bm.paper_id,
                page_number=bm.page_number,
                label=bm.label,
                created_at=bm.created_at,
            )
            for bm in result["items"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark_api(
    bookmark_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    delete_bookmark(str(bookmark_id), user_id, db)
    return Response(status_code=204)


@router.post(
    "/papers/{paper_id}/notes",
    response_model=NoteResponse,
    status_code=201,
)
def create_note_api(
    body: CreateNoteRequest,
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    note = create_note(
        paper_id=str(paper_id),
        user_id=user_id,
        anchor_type=body.anchor_type,
        page_number=body.page_number,
        highlight_id=str(body.highlight_id) if body.highlight_id else None,
        content=body.content,
        db=db,
    )
    return NoteResponse(
        id=note.id,
        paper_id=note.paper_id,
        anchor_type=note.anchor_type,
        page_number=note.page_number,
        highlight_id=note.highlight_id,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.get(
    "/papers/{paper_id}/notes",
    response_model=NoteListResponse,
)
def list_notes_api(
    paper_id: UUID4 = Path(...),
    anchor_type: AnchorType | None = Query(None),
    page_number: int | None = Query(None, ge=1),
    highlight_id: UUID4 | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = list_notes(
        paper_id=str(paper_id),
        user_id=user_id,
        db=db,
        anchor_type=anchor_type,
        page_number=page_number,
        highlight_id=str(highlight_id) if highlight_id else None,
        page=page,
        page_size=page_size,
    )
    return NoteListResponse(
        items=[
            NoteResponse(
                id=n.id,
                paper_id=n.paper_id,
                anchor_type=n.anchor_type,
                page_number=n.page_number,
                highlight_id=n.highlight_id,
                content=n.content,
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
            for n in result["items"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.patch(
    "/notes/{note_id}",
    response_model=NoteResponse,
)
def patch_note_api(
    body: PatchNoteRequest,
    note_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    note = patch_note(str(note_id), user_id, body.content, db)
    return NoteResponse(
        id=note.id,
        paper_id=note.paper_id,
        anchor_type=note.anchor_type,
        page_number=note.page_number,
        highlight_id=note.highlight_id,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete("/notes/{note_id}", status_code=204)
def delete_note_api(
    note_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    delete_note(str(note_id), user_id, db)
    return Response(status_code=204)


@router.post(
    "/papers/{paper_id}/knowledge-cards",
    response_model=KnowledgeCardResponse,
    status_code=201,
)
def create_knowledge_card_api(
    body: CreateKnowledgeCardRequest,
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    card = create_knowledge_card(
        paper_id=str(paper_id),
        user_id=user_id,
        source_note_id=str(body.source_note_id) if body.source_note_id else None,
        source_highlight_id=str(body.source_highlight_id) if body.source_highlight_id else None,
        front=body.front,
        back=body.back,
        db=db,
    )
    return KnowledgeCardResponse(
        id=card.id,
        paper_id=card.paper_id,
        source_note_id=card.source_note_id,
        source_highlight_id=card.source_highlight_id,
        front=card.front,
        back=card.back,
        mastery_status=card.mastery_status,
        last_reviewed_at=card.last_reviewed_at,
        archived=card.archived,
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


@router.get(
    "/papers/{paper_id}/knowledge-cards",
    response_model=KnowledgeCardListResponse,
)
def list_knowledge_cards_api(
    paper_id: UUID4 = Path(...),
    mastery_status: MasteryStatus | None = Query(None),
    archived: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = list_knowledge_cards(
        paper_id=str(paper_id),
        user_id=user_id,
        db=db,
        mastery_status=mastery_status,
        archived=archived,
        page=page,
        page_size=page_size,
    )
    return KnowledgeCardListResponse(
        items=[
            KnowledgeCardResponse(
                id=c.id,
                paper_id=c.paper_id,
                source_note_id=c.source_note_id,
                source_highlight_id=c.source_highlight_id,
                front=c.front,
                back=c.back,
                mastery_status=c.mastery_status,
                last_reviewed_at=c.last_reviewed_at,
                archived=c.archived,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in result["items"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.patch(
    "/knowledge-cards/{card_id}",
    response_model=KnowledgeCardResponse,
)
def patch_knowledge_card_api(
    body: PatchKnowledgeCardRequest,
    card_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    card = patch_knowledge_card(
        card_id=str(card_id),
        user_id=user_id,
        front=body.front,
        back=body.back,
        mastery_status=body.mastery_status,
        archived=body.archived,
        provided_fields=set(body.model_fields_set),
        db=db,
    )
    return KnowledgeCardResponse(
        id=card.id,
        paper_id=card.paper_id,
        source_note_id=card.source_note_id,
        source_highlight_id=card.source_highlight_id,
        front=card.front,
        back=card.back,
        mastery_status=card.mastery_status,
        last_reviewed_at=card.last_reviewed_at,
        archived=card.archived,
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


@router.delete("/knowledge-cards/{card_id}", status_code=204)
def delete_knowledge_card_api(
    card_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    delete_knowledge_card(str(card_id), user_id, db)
    return Response(status_code=204)
