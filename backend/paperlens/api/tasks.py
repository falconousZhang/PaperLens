from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from paperlens.core.database import get_db
from paperlens.core.deps import get_current_user_id
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
    Paper,
    ReviewFinding,
    ReviewResult,
)
from paperlens.schemas.task import (
    FindingResponse,
    ReviewListResponse,
    ReviewResultResponse,
    TaskCreateRequest,
    MetricTaskCreateRequest,
    ReviewTaskCreateRequest,
    TaskCreateResponse,
    TaskDetailResponse,
    TaskListResponse,
)
from paperlens.services.review_service import run_review_task
from paperlens.services.metric_service import (
    extract_metrics_from_paper,
    run_metric_extraction_task,
)
from paperlens.services.llm_client import LLMClient, get_llm_client
from paperlens.services.embedding_client import EmbeddingClient, get_embedding_client

router = APIRouter(tags=["tasks"])


@router.post("/papers/{paper_id}/tasks", response_model=TaskCreateResponse, status_code=201)
def create_task(
    paper_id: UUID4,
    body: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
    user_id: str = Depends(get_current_user_id),
):

    paper_id_str = str(paper_id)

    if body.task_type == TaskType.REVIEW:
        return _create_review_task(paper_id_str, body, background_tasks, db, llm_client, embedding_client, user_id)
    elif body.task_type == TaskType.METRIC_EXTRACTION:
        return _create_metric_task(paper_id_str, body, background_tasks, db, user_id)
    else:
        raise AppError("TASK_TYPE_NOT_SUPPORTED", f"不支持的任务类型: {body.task_type}", 422)


def _create_review_task(
    paper_id_str: str,
    body: ReviewTaskCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session,
    llm_client: LLMClient,
    embedding_client: EmbeddingClient,
    user_id: str,
):
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

    background_tasks.add_task(run_review_task, task.id, task_options, llm_client, embedding_client)

    return TaskCreateResponse(
        id=task.id,
        paper_id=task.paper_id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        created_at=task.created_at,
    )


def _create_metric_task(
    paper_id_str: str,
    body: MetricTaskCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session,
    user_id: str,
):
    paper = db.get(Paper, paper_id_str)
    if not paper:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    if paper.user_id != user_id:
        raise AppError("FORBIDDEN", "无权访问该论文", 403)
    if paper.status != PaperStatus.PARSED:
        raise AppError("PAPER_NOT_READY", "论文尚未解析完成，无法创建指标提取任务", 409)

    active = (
        db.query(AnalysisTask)
        .filter(
            AnalysisTask.paper_id == paper_id_str,
            AnalysisTask.task_type == TaskType.METRIC_EXTRACTION,
            AnalysisTask.user_id == user_id,
            AnalysisTask.status.in_(["PENDING", "RUNNING"]),
        )
        .first()
    )
    if active:
        raise AppError("TASK_ALREADY_RUNNING", "该论文已有进行中的指标提取任务", 409)

    if not extract_metrics_from_paper(paper_id_str, db):
        raise AppError("NO_CANDIDATES", "论文中没有可验证的指标候选，无法创建指标提取任务", 409)

    task = AnalysisTask(
        paper_id=paper_id_str,
        task_type=TaskType.METRIC_EXTRACTION,
        status="PENDING",
        progress=0,
        user_id=user_id,
    )
    db.add(task)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint_name = getattr(getattr(exc, "orig", None), "diag", None)
        if getattr(constraint_name, "constraint_name", None) == "uq_active_metric_task_per_user_paper":
            raise AppError("TASK_ALREADY_RUNNING", "该论文已有进行中的指标提取任务", 409) from exc
        raise
    db.refresh(task)

    background_tasks.add_task(run_metric_extraction_task, task.id)

    return TaskCreateResponse(
        id=task.id,
        paper_id=task.paper_id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        created_at=task.created_at,
    )


@router.get("/papers/{paper_id}/tasks", response_model=TaskListResponse)
def list_tasks(paper_id: UUID4, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):

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
        .limit(200)
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
                experiment_file_id=t.experiment_file_id,
                error_message=t.error_message,
                started_at=t.started_at,
                completed_at=t.completed_at,
                created_at=t.created_at,
            )
            for t in tasks
        ]
    )


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: UUID4, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):

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
        experiment_file_id=task.experiment_file_id,
        error_message=task.error_message,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
    )


@router.get("/papers/{paper_id}/reviews", response_model=ReviewListResponse)
def list_reviews(paper_id: UUID4, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):

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
        .options(
            selectinload(ReviewResult.findings.and_(
                ReviewFinding.verification_status == VerificationStatus.VERIFIED,
            )).selectinload(
                ReviewFinding.evidences.and_(Evidence.paper_id == paper_id_str),
            ),
        )
        .order_by(ReviewResult.created_at.asc(), ReviewResult.id.asc())
        .all()
    )

    result = []
    for r in reviews:
        finding_responses = []
        for f in sorted(r.findings, key=lambda f: (f.sequence, f.id)):
            evidence_ids = sorted(
                [str(e.id) for e in f.evidences if e.paper_id == paper_id_str]
            )
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
