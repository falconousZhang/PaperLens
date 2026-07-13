from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import UUID4
from sqlalchemy.orm import Session

from paperlens.core.config import settings
from paperlens.core.database import get_db
from paperlens.core.enums import (
    PaperStatus,
    ReviewDimension,
    TaskType,
    VerificationStatus,
)
from paperlens.core.errors import AppError
from paperlens.models.models import (
    AnalysisTask,
    Evidence,
    FindingEvidence,
    Paper,
    ReviewFinding,
    ReviewResult,
)
from paperlens.schemas.task import (
    FindingResponse,
    ReviewListResponse,
    ReviewResultResponse,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskDetailResponse,
    TaskListResponse,
)
from paperlens.services.review_service import run_review_task
from paperlens.services.llm_client import LLMClient, get_llm_client

router = APIRouter(tags=["tasks"])


def _get_user_id() -> str:
    return settings.demo_user_id


@router.post("/papers/{paper_id}/tasks", response_model=TaskCreateResponse, status_code=201)
def create_task(
    paper_id: UUID4,
    body: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
):
    user_id = _get_user_id()
    paper_id_str = str(paper_id)

    if body.task_type != TaskType.REVIEW:
        raise AppError("TASK_TYPE_NOT_SUPPORTED", f"当前仅支持 REVIEW 任务类型", 422)

    paper = db.get(Paper, paper_id_str)
    if not paper:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    if paper.user_id != user_id:
        raise AppError("FORBIDDEN", "无权访问该论文", 403)
    if paper.status != PaperStatus.PARSED:
        raise AppError("PAPER_NOT_READY", "论文尚未解析完成，无法创建审阅任务", 409)

    evidence_count = db.query(Evidence).filter(Evidence.paper_id == paper_id_str).count()
    if evidence_count == 0:
        raise AppError("NO_EVIDENCE", "论文暂无提取的 Evidence，无法创建审阅任务", 409)

    options = body.options
    dimensions = options.dimensions if options else [ReviewDimension.OVERALL]
    language = options.language if options else "zh"

    task = AnalysisTask(
        paper_id=paper_id_str,
        task_type=TaskType.REVIEW,
        status="PENDING",
        progress=0,
        user_id=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    task_options = {
        "dimensions": [d.value for d in dimensions],
        "language": language,
    }

    background_tasks.add_task(run_review_task, task.id, task_options, llm_client)

    return TaskCreateResponse(
        id=task.id,
        paper_id=task.paper_id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        created_at=task.created_at,
    )


@router.get("/papers/{paper_id}/tasks", response_model=TaskListResponse)
def list_tasks(paper_id: UUID4, db: Session = Depends(get_db)):
    user_id = _get_user_id()
    paper_id_str = str(paper_id)

    paper = db.get(Paper, paper_id_str)
    if not paper:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    if paper.user_id != user_id:
        raise AppError("FORBIDDEN", "无权访问该论文", 403)

    tasks = (
        db.query(AnalysisTask)
        .filter(AnalysisTask.paper_id == paper_id_str, AnalysisTask.user_id == user_id)
        .order_by(AnalysisTask.created_at.desc(), AnalysisTask.id.desc())
        .all()
    )

    return TaskListResponse(
        items=[
            TaskDetailResponse(
                id=t.id,
                paper_id=t.paper_id,
                task_type=t.task_type,
                status=t.status,
                progress=t.progress,
                error_message=t.error_message,
                started_at=t.started_at,
                completed_at=t.completed_at,
                created_at=t.created_at,
            )
            for t in tasks
        ]
    )


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: UUID4, db: Session = Depends(get_db)):
    user_id = _get_user_id()

    task = db.get(AnalysisTask, str(task_id))
    if not task:
        raise AppError("NOT_FOUND", "任务不存在", 404)
    if task.user_id != user_id:
        raise AppError("NOT_FOUND", "任务不存在", 404)

    return TaskDetailResponse(
        id=task.id,
        paper_id=task.paper_id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        error_message=task.error_message,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
    )


@router.get("/papers/{paper_id}/reviews", response_model=ReviewListResponse)
def list_reviews(paper_id: UUID4, db: Session = Depends(get_db)):
    user_id = _get_user_id()
    paper_id_str = str(paper_id)

    paper = db.get(Paper, paper_id_str)
    if not paper:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    if paper.user_id != user_id:
        raise AppError("FORBIDDEN", "无权访问该论文", 403)

    reviews = (
        db.query(ReviewResult)
        .join(AnalysisTask, ReviewResult.task_id == AnalysisTask.id)
        .filter(
            ReviewResult.paper_id == paper_id_str,
            AnalysisTask.user_id == user_id,
        )
        .order_by(ReviewResult.created_at.asc(), ReviewResult.id.asc())
        .all()
    )

    result = []
    for r in reviews:
        findings = (
            db.query(ReviewFinding)
            .filter(
                ReviewFinding.review_id == r.id,
                ReviewFinding.verification_status == VerificationStatus.VERIFIED,
            )
            .order_by(ReviewFinding.sequence.asc(), ReviewFinding.id.asc())
            .all()
        )

        finding_responses = []
        for f in findings:
            fe_rows = (
                db.query(FindingEvidence.evidence_id)
                .join(Evidence, FindingEvidence.evidence_id == Evidence.id)
                .filter(FindingEvidence.finding_id == f.id)
                .filter(Evidence.paper_id == paper_id_str)
                .order_by(FindingEvidence.evidence_id.asc())
                .all()
            )
            evidence_ids = [str(fe[0]) for fe in fe_rows]

            finding_responses.append(
                FindingResponse(
                    id=f.id,
                    finding_type=f.finding_type,
                    content=f.content,
                    confidence=f.confidence,
                    verification_status=f.verification_status,
                    sequence=f.sequence,
                    evidence_ids=evidence_ids,
                )
            )

        result.append(
            ReviewResultResponse(
                id=r.id,
                task_id=r.task_id,
                dimension=r.dimension,
                rating=r.rating,
                summary=r.summary,
                overall_verdict=r.overall_verdict,
                created_at=r.created_at,
                findings=finding_responses,
            )
        )

    return ReviewListResponse(reviews=result)
