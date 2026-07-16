from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query
from pydantic import UUID4
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from paperlens.core.database import get_db
from paperlens.core.deps import get_current_user_id
from paperlens.core.enums import QATurnStatus
from paperlens.models.models import PaperQAConversation, PaperQATurn
from paperlens.schemas.qa import (
    CreateQAConversationRequest,
    CreateQATurnRequest,
    QACitationItem,
    QAConversationListItem,
    QAConversationListResponse,
    QAConversationResponse,
    QATurnResponse,
)
from paperlens.services.qa_service import (
    create_qa_conversation,
    create_qa_turn,
    get_qa_conversation,
    get_qa_turn,
    list_qa_conversations,
    run_qa_turn,
)


router = APIRouter(tags=["qa"])

_FAILED_MESSAGE = "论文问答生成失败，请稍后重试"


def _turn_response(turn: PaperQATurn, duplicate: bool = False) -> QATurnResponse:
    citations = None
    if turn.status == QATurnStatus.SUCCEEDED:
        citations = [
            QACitationItem(
                evidence_id=citation.evidence_id,
                sequence=citation.sequence,
                page_number=citation.evidence.page_number,
                evidence_type=citation.evidence.evidence_type,
                quoted_text=citation.evidence.quoted_text,
                char_start=citation.evidence.char_start,
                char_end=citation.evidence.char_end,
            )
            for citation in sorted(turn.citations, key=lambda item: item.sequence)
        ]
    return QATurnResponse(
        id=turn.id,
        conversation_id=turn.conversation_id,
        sequence=turn.sequence,
        question=turn.question,
        output_language=turn.output_language,
        status=turn.status,
        duplicate=duplicate,
        answer=turn.answer if turn.status == QATurnStatus.SUCCEEDED else None,
        grounded=turn.grounded if turn.status == QATurnStatus.SUCCEEDED else None,
        error_message=_FAILED_MESSAGE if turn.status == QATurnStatus.FAILED else None,
        citations=citations,
        created_at=turn.created_at,
        completed_at=turn.completed_at,
    )


def _conversation_response(
    conversation: PaperQAConversation,
    turns: list[PaperQATurn] | None = None,
    total: int = 0,
    page: int = 1,
    page_size: int = 20,
) -> QAConversationResponse:
    return QAConversationResponse(
        id=conversation.id,
        paper_id=conversation.paper_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        turns=[_turn_response(turn) for turn in turns] if turns is not None else None,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/papers/{paper_id}/qa-conversations",
    response_model=QAConversationResponse,
    status_code=201,
)
def create_conversation_api(
    body: CreateQAConversationRequest,
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    del body
    conversation = create_qa_conversation(
        paper_id=str(paper_id),
        user_id=user_id,
        db=db,
    )
    return _conversation_response(conversation)


@router.get(
    "/papers/{paper_id}/qa-conversations",
    response_model=QAConversationListResponse,
)
def list_conversations_api(
    paper_id: UUID4 = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    rows, total = list_qa_conversations(
        paper_id=str(paper_id),
        user_id=user_id,
        page=page,
        page_size=page_size,
        db=db,
    )
    return QAConversationListResponse(
        items=[
            QAConversationListItem(
                id=row["conversation"].id,
                paper_id=row["conversation"].paper_id,
                created_at=row["conversation"].created_at,
                updated_at=row["conversation"].updated_at,
                turn_count=row["turn_count"],
                last_question_preview=row["last_question_preview"],
                last_status=row["last_status"],
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/qa-conversations/{conversation_id}",
    response_model=QAConversationResponse,
)
def get_conversation_api(
    conversation_id: UUID4 = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    conversation, turns, total = get_qa_conversation(
        conversation_id=str(conversation_id),
        user_id=user_id,
        page=page,
        page_size=page_size,
        db=db,
    )
    return _conversation_response(
        conversation,
        turns=turns,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/qa-conversations/{conversation_id}/turns",
    response_model=QATurnResponse,
    status_code=201,
)
def create_turn_api(
    background_tasks: BackgroundTasks,
    body: CreateQATurnRequest,
    conversation_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    turn, duplicate = create_qa_turn(
        conversation_id=str(conversation_id),
        user_id=user_id,
        question=body.question,
        output_language=body.output_language,
        client_request_id=str(body.client_request_id),
        db=db,
    )
    response = _turn_response(turn, duplicate)
    if duplicate:
        return JSONResponse(content=response.model_dump(mode="json"), status_code=200)
    background_tasks.add_task(run_qa_turn, turn.id)
    return response


@router.get(
    "/qa-turns/{turn_id}",
    response_model=QATurnResponse,
)
def get_turn_api(
    turn_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    turn = get_qa_turn(
        turn_id=str(turn_id),
        user_id=user_id,
        db=db,
    )
    return _turn_response(turn)
