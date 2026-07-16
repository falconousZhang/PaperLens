from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, Path, Query, UploadFile
from pydantic import UUID4, ValidationError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from paperlens.core.database import get_db
from paperlens.core.deps import get_current_user_id
from paperlens.core.errors import AppError
from paperlens.core.enums import TaskStatus, TaskType
from paperlens.models.models import AnalysisTask, ExperimentFile, ExperimentResult, Paper
from paperlens.schemas.experiment_file import (
    ComparisonItem,
    ExperimentAnalysisTaskResponse,
    ExperimentFileDetail,
    ExperimentFileListItem,
    ExperimentFileListResponse,
    ExperimentFileUploadResponse,
    ExperimentResultResponse,
    PostComparisonsRequest,
    PostComparisonsResponse,
    SummaryStatsResponse,
)
from paperlens.services.experiment_analysis_service import (
    create_experiment_analysis,
    run_experiment_analysis_task,
)
from paperlens.services.experiment_comparison_service import create_comparisons
from paperlens.services.experiment_file_service import (
    cleanup_temp_file,
    stage_upload_to_temp,
    upload_experiment_file,
    validate_upload_filename,
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["experiment-files"])


def _check_paper_owner(paper: Paper | None, user_id: str) -> Paper:
    if paper is None or paper.user_id != user_id:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    return paper


@router.post(
    "/papers/{paper_id}/experiment-files/upload",
    response_model=ExperimentFileUploadResponse,
    status_code=201,
)
async def upload_experiment_file_api(
    paper_id: UUID4 = Path(...),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    if file is None:
        raise AppError("VALIDATION_ERROR", "缺少上传文件", 422)
    temp_path: str | None = None
    try:
        filename, file_type = validate_upload_filename(file.filename or "")
        temp_path, _ = await stage_upload_to_temp(file, file_type)
        record, duplicate = await run_in_threadpool(
            upload_experiment_file,
            source_path=temp_path,
            filename=filename,
            file_type=file_type,
            paper_id=str(paper_id),
            user_id=user_id,
            db=db,
        )
        response = ExperimentFileUploadResponse(
            **record.__dict__,
            duplicate=duplicate,
        )
        if duplicate:
            return JSONResponse(
                content=response.model_dump(mode="json"),
                status_code=200,
            )
        return response
    finally:
        try:
            await file.close()
        except Exception as exc:
            logger.warning(
                "experiment upload close failed error_type=%s",
                type(exc).__name__,
            )
        cleanup_temp_file(temp_path)


@router.get(
    "/papers/{paper_id}/experiment-files",
    response_model=ExperimentFileListResponse,
)
def list_experiment_files(
    paper_id: UUID4 = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    paper = db.get(Paper, str(paper_id))
    _check_paper_owner(paper, user_id)
    query = db.query(ExperimentFile).filter(
        ExperimentFile.paper_id == str(paper_id),
        ExperimentFile.user_id == user_id,
    )
    total = query.count()
    items = (
        query.order_by(ExperimentFile.created_at.desc(), ExperimentFile.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ExperimentFileListResponse(
        items=[
            ExperimentFileListItem(
                id=item.id,
                paper_id=item.paper_id,
                filename=item.filename,
                file_type=item.file_type,
                file_size=item.file_size,
                row_count=item.row_count,
                column_count=item.column_count,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/experiment-files/{file_id}",
    response_model=ExperimentFileDetail,
)
def get_experiment_file(
    file_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    exp_file = db.get(ExperimentFile, str(file_id))
    if exp_file is None or exp_file.user_id != user_id:
        raise AppError("NOT_FOUND", "实验文件不存在", 404)
    return ExperimentFileDetail(
        id=exp_file.id,
        paper_id=exp_file.paper_id,
        filename=exp_file.filename,
        file_type=exp_file.file_type,
        file_size=exp_file.file_size,
        row_count=exp_file.row_count,
        column_count=exp_file.column_count,
        columns_info=exp_file.columns_info,
        created_at=exp_file.created_at,
    )


@router.post(
    "/experiment-files/{file_id}/analysis",
    response_model=ExperimentAnalysisTaskResponse,
    status_code=201,
)
def create_experiment_analysis_api(
    background_tasks: BackgroundTasks,
    file_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    task, duplicate = create_experiment_analysis(
        file_id=str(file_id),
        user_id=user_id,
        db=db,
    )
    if not duplicate:
        background_tasks.add_task(run_experiment_analysis_task, task.id)
    response = ExperimentAnalysisTaskResponse(
        id=task.id,
        paper_id=task.paper_id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        experiment_file_id=task.experiment_file_id,
        created_at=task.created_at,
        duplicate=duplicate,
    )
    if duplicate:
        return JSONResponse(
            content=response.model_dump(mode="json"),
            status_code=200,
        )
    return response


@router.get(
    "/experiment-files/{file_id}/result",
    response_model=ExperimentResultResponse,
)
def get_experiment_result(
    file_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    exp_file = db.get(ExperimentFile, str(file_id))
    if exp_file is None or exp_file.user_id != user_id:
        raise AppError("NOT_FOUND", "实验文件不存在", 404)
    paper = db.get(Paper, exp_file.paper_id)
    if paper is None or paper.user_id != user_id:
        raise AppError("NOT_FOUND", "实验文件不存在", 404)
    row = (
        db.query(ExperimentResult)
        .join(AnalysisTask, AnalysisTask.id == ExperimentResult.task_id)
        .filter(
            ExperimentResult.file_id == str(file_id),
            AnalysisTask.task_type == TaskType.EXPERIMENT_ANALYSIS,
            AnalysisTask.status == TaskStatus.SUCCEEDED,
            AnalysisTask.experiment_file_id == str(file_id),
            AnalysisTask.paper_id == exp_file.paper_id,
            AnalysisTask.user_id == user_id,
        )
        .first()
    )
    if row is None:
        raise AppError("RESULT_NOT_READY", "实验分析结果尚未就绪", 404)
    try:
        comparisons = None
        if row.metric_comparisons is not None:
            comparisons = [ComparisonItem(**item) for item in row.metric_comparisons]
        return ExperimentResultResponse(
            id=row.id,
            file_id=row.file_id,
            task_id=row.task_id,
            summary_stats=SummaryStatsResponse(**row.summary_stats),
            metric_comparisons=comparisons,
            created_at=row.created_at,
        )
    except ValidationError as exc:
        logger.error("Stored experiment result failed response validation")
        raise AppError("ANALYSIS_STATE_INVALID", "实验分析状态异常", 409) from exc


@router.post(
    "/experiment-files/{file_id}/comparisons",
    response_model=PostComparisonsResponse,
    status_code=201,
)
def create_comparisons_api(
    body: PostComparisonsRequest,
    file_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    outcome = create_comparisons(
        file_id=str(file_id),
        metric_task_id=str(body.metric_task_id),
        user_id=user_id,
        db=db,
    )
    try:
        response = PostComparisonsResponse(
            file_id=outcome.file_id,
            experiment_result_id=outcome.experiment_result_id,
            metric_task_id=outcome.metric_task_id,
            comparisons=[ComparisonItem.model_validate(item) for item in outcome.comparisons],
            duplicate=outcome.duplicate,
        )
    except ValidationError as exc:
        logger.error("Stored experiment comparison failed response validation")
        raise AppError("COMPARISON_STATE_INVALID", "交叉验证结果异常", 409) from exc
    if outcome.duplicate:
        return JSONResponse(
            content=response.model_dump(mode="json"),
            status_code=200,
        )
    return response
