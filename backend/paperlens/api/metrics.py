from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import UUID4
from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import Session

from paperlens.core.database import get_db
from paperlens.core.deps import get_current_user_id
from paperlens.core.enums import CheckpointType, TaskType
from paperlens.core.errors import AppError
from paperlens.models.models import (
    AnalysisTask,
    Evidence,
    MetricRecord,
    Paper,
    PaperTable,
)
from paperlens.schemas.metric import (
    MetricListQuery,
    MetricListResponse,
    MetricRecordResponse,
)

router = APIRouter(tags=["metrics"])


def _check_paper_owner(paper: Paper | None, user_id: str) -> Paper:
    if paper is None:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    if paper.user_id != user_id:
        raise AppError("FORBIDDEN", "无权访问该论文", 403)
    return paper


def _valid_source_filter(paper_id: Any):
    return or_(
        and_(
            MetricRecord.table_id.is_not(None),
            MetricRecord.evidence_id.is_(None),
            MetricRecord.row_index.is_not(None),
            MetricRecord.row_index >= 0,
            exists().where(
                PaperTable.id == MetricRecord.table_id,
                PaperTable.paper_id == paper_id,
            ),
        ),
        and_(
            MetricRecord.table_id.is_(None),
            MetricRecord.evidence_id.is_not(None),
            MetricRecord.row_index.is_(None),
            exists().where(
                Evidence.id == MetricRecord.evidence_id,
                Evidence.paper_id == paper_id,
            ),
        ),
    )


def _to_response(record: MetricRecord) -> MetricRecordResponse:
    return MetricRecordResponse(
        id=record.id,
        paper_id=record.paper_id,
        task_id=record.task_id,
        model_name=record.model_name,
        dataset_name=record.dataset_name,
        metric_name=record.metric_name,
        metric_value=record.metric_value,
        checkpoint_type=CheckpointType(record.checkpoint_type),
        checkpoint_source=record.checkpoint_source,
        evidence_id=record.evidence_id,
        table_id=record.table_id,
        row_index=record.row_index,
        raw_text=record.raw_text,
        created_at=record.created_at,
    )


@router.get("/papers/{paper_id}/metrics", response_model=MetricListResponse)
def list_metrics(
    paper_id: UUID4,
    filters: Annotated[MetricListQuery, Query()],
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    paper_id_str = str(paper_id)
    _check_paper_owner(db.get(Paper, paper_id_str), user_id)

    query = (
        db.query(MetricRecord)
        .join(AnalysisTask, AnalysisTask.id == MetricRecord.task_id)
        .filter(
            MetricRecord.paper_id == paper_id_str,
            MetricRecord.user_id == user_id,
            AnalysisTask.paper_id == paper_id_str,
            AnalysisTask.user_id == user_id,
            AnalysisTask.task_type == TaskType.METRIC_EXTRACTION,
            MetricRecord.checkpoint_type.is_not(None),
            MetricRecord.raw_text.is_not(None),
            func.length(func.btrim(MetricRecord.raw_text)) > 0,
            _valid_source_filter(paper_id_str),
        )
    )

    if filters.task_id is not None:
        query = query.filter(MetricRecord.task_id == str(filters.task_id))
    if filters.metric_name is not None:
        query = query.filter(MetricRecord.metric_name == filters.metric_name)
    if filters.dataset_name is not None:
        query = query.filter(MetricRecord.dataset_name == filters.dataset_name)
    if filters.checkpoint_type is not None:
        query = query.filter(MetricRecord.checkpoint_type == filters.checkpoint_type)

    total = query.count()
    records = (
        query.order_by(
            MetricRecord.metric_name.asc(),
            MetricRecord.model_name.asc().nulls_last(),
            MetricRecord.dataset_name.asc().nulls_last(),
            MetricRecord.metric_value.asc(),
            MetricRecord.created_at.asc(),
            MetricRecord.id.asc(),
        )
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
        .all()
    )
    return MetricListResponse(
        items=[_to_response(record) for record in records],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@router.get("/metrics/{metric_id}", response_model=MetricRecordResponse)
def get_metric(
    metric_id: UUID4,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    record = (
        db.query(MetricRecord)
        .join(Paper, Paper.id == MetricRecord.paper_id)
        .join(AnalysisTask, AnalysisTask.id == MetricRecord.task_id)
        .filter(
            MetricRecord.id == str(metric_id),
            MetricRecord.user_id == user_id,
            Paper.user_id == user_id,
            AnalysisTask.user_id == user_id,
            AnalysisTask.paper_id == MetricRecord.paper_id,
            AnalysisTask.task_type == TaskType.METRIC_EXTRACTION,
            MetricRecord.checkpoint_type.is_not(None),
            MetricRecord.raw_text.is_not(None),
            func.length(func.btrim(MetricRecord.raw_text)) > 0,
            _valid_source_filter(MetricRecord.paper_id),
        )
        .one_or_none()
    )
    if record is None:
        raise AppError("NOT_FOUND", "指标记录不存在", 404)
    return _to_response(record)
