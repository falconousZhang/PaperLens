from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Path, Query, UploadFile
from pydantic import UUID4
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from paperlens.core.database import get_db
from paperlens.core.deps import get_current_user_id
from paperlens.core.errors import AppError
from paperlens.models.models import ExperimentFile, Paper
from paperlens.schemas.experiment_file import (
    ExperimentFileDetail,
    ExperimentFileListItem,
    ExperimentFileListResponse,
    ExperimentFileUploadResponse,
)
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
