from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query
from pydantic import UUID4
from sqlalchemy.orm import Session, selectinload
from starlette.responses import JSONResponse

from paperlens.core.database import get_db
from paperlens.core.deps import get_current_user_id
from paperlens.core.enums import LearningStatus
from paperlens.core.errors import AppError
from paperlens.models.models import LearningCitation, LearningExplanation, Paper
from paperlens.schemas.learning import (
    CreateLearningExplanationRequest,
    LearningCitationItem,
    LearningExplanationListItem,
    LearningExplanationListResponse,
    LearningExplanationResponse,
)
from paperlens.services.learning_service import create_learning_explanation, run_learning_task


router = APIRouter(tags=["learning"])

_FAILED_MESSAGE = "学习解释生成失败，请稍后重试"


def _response(explanation: LearningExplanation, duplicate: bool) -> LearningExplanationResponse:
    citations = None
    if explanation.status == LearningStatus.SUCCEEDED:
        citations = [
            LearningCitationItem(
                evidence_id=c.evidence_id,
                sequence=c.sequence,
                page_number=c.evidence.page_number,
                evidence_type=c.evidence.evidence_type,
                quoted_text=c.evidence.quoted_text,
                char_start=c.evidence.char_start,
                char_end=c.evidence.char_end,
            )
            for c in sorted(explanation.citations, key=lambda item: item.sequence)
        ]

    return LearningExplanationResponse(
        id=explanation.id,
        paper_id=explanation.paper_id,
        mode=explanation.mode,
        scope_type=explanation.scope_type,
        output_language=explanation.output_language,
        section_id=explanation.section_id,
        page_number=explanation.page_number,
        evidence_id=explanation.evidence_id,
        selection_text=explanation.selection_text,
        selection_start=explanation.selection_start,
        selection_end=explanation.selection_end,
        status=explanation.status,
        duplicate=duplicate,
        answer=explanation.answer if explanation.status == LearningStatus.SUCCEEDED else None,
        key_points=explanation.key_points if explanation.status == LearningStatus.SUCCEEDED else None,
        terms=explanation.terms if explanation.status == LearningStatus.SUCCEEDED else None,
        error_message=_FAILED_MESSAGE if explanation.status == LearningStatus.FAILED else None,
        citations=citations,
        created_at=explanation.created_at,
        completed_at=explanation.completed_at,
    )


def _list_item(explanation: LearningExplanation) -> LearningExplanationListItem:
    return LearningExplanationListItem(
        id=explanation.id,
        paper_id=explanation.paper_id,
        mode=explanation.mode,
        scope_type=explanation.scope_type,
        output_language=explanation.output_language,
        section_id=explanation.section_id,
        page_number=explanation.page_number,
        evidence_id=explanation.evidence_id,
        selection_start=explanation.selection_start,
        selection_end=explanation.selection_end,
        status=explanation.status,
        error_message=_FAILED_MESSAGE if explanation.status == LearningStatus.FAILED else None,
        created_at=explanation.created_at,
        completed_at=explanation.completed_at,
    )


@router.post(
    "/papers/{paper_id}/learning-explanations",
    response_model=LearningExplanationResponse,
    status_code=201,
)
def create_learning_api(
    background_tasks: BackgroundTasks,
    body: CreateLearningExplanationRequest,
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    explanation, duplicate = create_learning_explanation(
        paper_id=str(paper_id),
        user_id=user_id,
        mode=body.mode,
        scope_type=body.scope_type,
        output_language=body.output_language,
        section_id=str(body.section_id) if body.section_id else None,
        page_number=body.page_number,
        evidence_id=str(body.evidence_id) if body.evidence_id else None,
        db=db,
        selection_text=body.selection_text,
        selection_start=body.selection_start,
        selection_end=body.selection_end,
    )

    response = _response(explanation, duplicate)
    if duplicate:
        return JSONResponse(content=response.model_dump(mode="json"), status_code=200)

    background_tasks.add_task(run_learning_task, explanation.id)
    return response


@router.get(
    "/learning-explanations/{explanation_id}",
    response_model=LearningExplanationResponse,
)
def get_learning_explanation_api(
    explanation_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    explanation = (
        db.query(LearningExplanation)
        .options(
            selectinload(LearningExplanation.citations).joinedload(LearningCitation.evidence)
        )
        .filter(LearningExplanation.id == str(explanation_id))
        .first()
    )
    if explanation is None or explanation.user_id != user_id:
        raise AppError("NOT_FOUND", "学习解释不存在", 404)

    return _response(explanation, False)


@router.delete("/learning-explanations/{explanation_id}", status_code=204)
def delete_learning_explanation_api(
    explanation_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    explanation = db.get(LearningExplanation, str(explanation_id))
    if explanation is None or explanation.user_id != user_id:
        raise AppError("NOT_FOUND", "学习解释不存在", 404)
    if explanation.status in (LearningStatus.PENDING, LearningStatus.RUNNING):
        raise AppError("TASK_RUNNING", "解释正在生成，暂时无法删除", 409)
    try:
        db.delete(explanation)
        db.commit()
    except Exception:
        db.rollback()
        raise AppError("DELETE_FAILED", "删除学习解释失败，请稍后重试", 500)


@router.get(
    "/papers/{paper_id}/learning-explanations",
    response_model=LearningExplanationListResponse,
)
def list_learning_explanations_api(
    paper_id: UUID4 = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    page_number: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    paper = db.get(Paper, str(paper_id))
    if paper is None or paper.user_id != user_id:
        raise AppError("NOT_FOUND", "论文不存在", 404)

    query = (
        db.query(LearningExplanation)
        .filter(
            LearningExplanation.paper_id == str(paper_id),
            LearningExplanation.user_id == user_id,
        )
        .order_by(LearningExplanation.created_at.desc(), LearningExplanation.id.desc())
    )
    if page_number is not None:
        query = query.filter(LearningExplanation.page_number == page_number)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return LearningExplanationListResponse(
        items=[_list_item(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
