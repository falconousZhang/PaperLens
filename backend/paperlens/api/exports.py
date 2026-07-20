from __future__ import annotations

import logging
import hmac

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Response
from pydantic import UUID4
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from paperlens.core.database import get_db
from paperlens.core.deps import get_current_user_id
from paperlens.core.errors import AppError
from paperlens.core.enums import ExportStatus
from paperlens.models.models import ExportReport, Paper
from paperlens.schemas.export import (
    CreateExportRequest,
    ExportReportResponse,
    ExportListItem,
    ExportListResponse,
)
from paperlens.services.export_service import compute_content_hash, create_export, run_export_task
from paperlens.utils.storage import get_storage


logger = logging.getLogger(__name__)
router = APIRouter(tags=["exports"])

_MIME_TYPES = {
    "MARKDOWN": "text/markdown; charset=utf-8",
    "PDF": "application/pdf",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_EXTENSIONS = {"MARKDOWN": ".md", "PDF": ".pdf", "DOCX": ".docx"}
_PUBLIC_FAILED_MESSAGE = "报告生成失败，请稍后重试"


def _response(report: ExportReport, duplicate: bool) -> ExportReportResponse:
    return ExportReportResponse(
        id=report.id,
        paper_id=report.paper_id,
        report_type=report.report_type,
        language=report.language,
        include_metrics=report.include_metrics,
        include_experiment_analysis=report.include_experiment_analysis,
        status=report.status,
        file_size=report.file_size,
        error_message=_PUBLIC_FAILED_MESSAGE if report.status == ExportStatus.FAILED else None,
        created_at=report.created_at,
        completed_at=report.completed_at,
        duplicate=duplicate,
    )


def _list_item(report: ExportReport) -> ExportListItem:
    return ExportListItem(
        id=report.id,
        paper_id=report.paper_id,
        report_type=report.report_type,
        language=report.language,
        include_metrics=report.include_metrics,
        include_experiment_analysis=report.include_experiment_analysis,
        status=report.status,
        file_size=report.file_size,
        error_message=_PUBLIC_FAILED_MESSAGE if report.status == ExportStatus.FAILED else None,
        created_at=report.created_at,
        completed_at=report.completed_at,
    )


@router.post(
    "/papers/{paper_id}/exports",
    response_model=ExportReportResponse,
    status_code=201,
)
def create_export_api(
    background_tasks: BackgroundTasks,
    body: CreateExportRequest,
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    report, duplicate, content = create_export(
        paper_id=str(paper_id),
        user_id=user_id,
        report_type=body.report_type,
        language=body.language,
        include_metrics=body.include_metrics,
        include_experiment_analysis=body.include_experiment_analysis,
        db=db,
    )
    response = _response(report, duplicate)
    if duplicate:
        return JSONResponse(
            content=response.model_dump(mode="json"),
            status_code=200,
        )
    if content is not None:
        background_tasks.add_task(run_export_task, report.id, content)
    return response


@router.get(
    "/papers/{paper_id}/exports",
    response_model=ExportListResponse,
)
def list_exports_api(
    paper_id: UUID4 = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    paper = db.get(Paper, str(paper_id))
    if paper is None or paper.user_id != user_id:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    query = (
        db.query(ExportReport)
        .filter(
            ExportReport.paper_id == str(paper_id),
            ExportReport.user_id == user_id,
        )
        .order_by(ExportReport.created_at.desc(), ExportReport.id.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return ExportListResponse(
        items=[_list_item(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/exports/{export_id}",
    response_model=ExportReportResponse,
)
def get_export_api(
    export_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    report = db.get(ExportReport, str(export_id))
    if report is None or report.user_id != user_id:
        raise AppError("NOT_FOUND", "报告不存在", 404)
    return _response(report, False)


@router.get(
    "/exports/{export_id}/download",
)
def download_export_api(
    export_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    report = db.get(ExportReport, str(export_id))
    if report is None or report.user_id != user_id:
        raise AppError("NOT_FOUND", "报告不存在", 404)
    if report.status != ExportStatus.READY:
        raise AppError("EXPORT_NOT_READY", "报告尚未就绪", 409)

    if (
        not report.storage_key
        or not report.content_hash
        or report.file_size is None
        or report.file_size < 0
    ):
        raise AppError("EXPORT_NOT_READY", "报告文件损坏", 409)

    try:
        storage = get_storage()
        with storage.materialize(report.storage_key) as local_path:
            with open(local_path, "rb") as f:
                content = f.read()
    except (FileNotFoundError, OSError, ValueError, NotImplementedError):
        raise AppError("EXPORT_NOT_READY", "报告文件缺失", 409)

    actual_hash = compute_content_hash(content)
    if not hmac.compare_digest(actual_hash, report.content_hash) or len(content) != report.file_size:
        raise AppError("EXPORT_NOT_READY", "报告文件损坏", 409)

    safe_name = report.id.replace("-", "_")
    ext = _EXTENSIONS.get(report.report_type, ".md")
    filename = f"report_{safe_name}{ext}"
    mime = _MIME_TYPES.get(report.report_type, "application/octet-stream")

    return Response(
        content=content,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{filename}',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
