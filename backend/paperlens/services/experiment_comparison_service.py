from __future__ import annotations

import datetime
import math
import unicodedata
from collections import Counter
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy.orm import Session, defer

from paperlens.core.config import settings
from paperlens.core.database import SessionLocal
from paperlens.core.enums import CheckpointType, TaskStatus, TaskType
from paperlens.core.errors import AppError
from paperlens.models.models import (
    AnalysisTask,
    Evidence,
    ExperimentFile,
    ExperimentResult,
    MetricRecord,
    Paper,
    PaperTable,
    User,
)
from paperlens.schemas.experiment_file import ComparisonItem, SummaryStatsResponse


@dataclass(frozen=True)
class ComparisonOutcome:
    file_id: str
    experiment_result_id: str
    metric_task_id: str
    comparisons: list[dict]
    duplicate: bool


_CHECKPOINT_STAT_MAP: dict[CheckpointType, tuple[str, str]] = {
    CheckpointType.MEAN: ("mean", "MEAN"),
    CheckpointType.MAX: ("max", "MAX"),
}


def normalize_comparison_key(raw_name: str) -> str | None:
    if not isinstance(raw_name, str):
        return None
    normalized = unicodedata.normalize("NFKC", raw_name).casefold()
    value = "".join(char for char in normalized if char.isalnum())
    return value or None


def _finite_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AppError("COMPARISON_INPUT_INVALID", f"{field_name} 数值无效", 409)
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise AppError("COMPARISON_INPUT_INVALID", f"{field_name} 数值无效", 409) from exc
    if not math.isfinite(number):
        raise AppError("COMPARISON_INPUT_INVALID", f"{field_name} 数值无效", 409)
    return number


def _resolve_experiment_value(
    summary_stats: dict,
    normalized_metric_name: str,
    checkpoint_type: CheckpointType,
) -> tuple[str | None, str | None, float | None, str | None]:
    mapping = _CHECKPOINT_STAT_MAP.get(checkpoint_type)
    if mapping is None:
        return None, None, None, "UNSUPPORTED_CHECKPOINT"
    stat_key, statistic = mapping
    columns = summary_stats.get("columns")
    if not isinstance(columns, list):
        raise AppError("COMPARISON_STATE_INVALID", "实验统计结果异常", 409)
    matching = [
        column
        for column in columns
        if isinstance(column, dict)
        and column.get("dtype") in {"integer", "float"}
        and isinstance(column.get("name"), str)
        and normalize_comparison_key(column["name"]) == normalized_metric_name
    ]
    if not matching:
        return None, None, None, "NO_EXPERIMENT_COLUMN"
    if len(matching) > 1:
        return None, None, None, "AMBIGUOUS_EXPERIMENT_COLUMN"
    column = matching[0]
    stats = column.get("stats")
    if not isinstance(stats, dict) or stat_key not in stats:
        raise AppError("COMPARISON_STATE_INVALID", "实验统计结果异常", 409)
    value = _finite_number(stats[stat_key], "实验统计")
    return column["name"], statistic, value, None


def _unverifiable_item(metric_record: MetricRecord, reason: str) -> dict:
    return {
        "metric_record_id": metric_record.id,
        "metric_task_id": metric_record.task_id,
        "metric_name": metric_record.metric_name,
        "checkpoint_type": metric_record.checkpoint_type,
        "column_name": None,
        "statistic": None,
        "paper_value": _finite_number(metric_record.metric_value, "论文指标"),
        "experiment_value": None,
        "diff": None,
        "absolute_diff": None,
        "relative_diff": None,
        "allowed_diff": None,
        "status": "UNVERIFIABLE",
        "reason": reason,
    }


def _compute_comparison(
    metric_record: MetricRecord,
    summary_stats: dict,
    abs_tolerance: float,
    rel_tolerance: float,
    ambiguous_paper_metric: bool = False,
) -> dict:
    paper_value = _finite_number(metric_record.metric_value, "论文指标")
    absolute_tolerance = _finite_number(abs_tolerance, "绝对容差")
    relative_tolerance = _finite_number(rel_tolerance, "相对容差")
    normalized_name = normalize_comparison_key(metric_record.metric_name)
    if normalized_name is None:
        return _unverifiable_item(metric_record, "EMPTY_NORMALIZED_NAME")
    if ambiguous_paper_metric:
        return _unverifiable_item(metric_record, "AMBIGUOUS_PAPER_METRIC")
    try:
        checkpoint_type = CheckpointType(metric_record.checkpoint_type)
    except ValueError as exc:
        raise AppError("COMPARISON_STATE_INVALID", "论文指标状态异常", 409) from exc
    column_name, statistic, experiment_value, reason = _resolve_experiment_value(
        summary_stats,
        normalized_name,
        checkpoint_type,
    )
    if reason is not None:
        return _unverifiable_item(metric_record, reason)
    diff = _finite_number(experiment_value - paper_value, "差值")
    absolute_diff = _finite_number(abs(diff), "绝对差值")
    relative_diff = None
    if paper_value != 0:
        relative_diff = _finite_number(absolute_diff / abs(paper_value), "相对差值")
    allowed_diff = _finite_number(
        max(absolute_tolerance, abs(paper_value) * relative_tolerance),
        "允许差值",
    )
    status = "MATCH" if absolute_diff <= allowed_diff else "MISMATCH"
    return {
        "metric_record_id": metric_record.id,
        "metric_task_id": metric_record.task_id,
        "metric_name": metric_record.metric_name,
        "checkpoint_type": checkpoint_type,
        "column_name": column_name,
        "statistic": statistic,
        "paper_value": paper_value,
        "experiment_value": experiment_value,
        "diff": diff,
        "absolute_diff": absolute_diff,
        "relative_diff": relative_diff,
        "allowed_diff": allowed_diff,
        "status": status,
        "reason": None,
    }


def _validate_metric_task(
    metric_task_id: str,
    user_id: str,
    paper_id: str,
    db: Session,
) -> AnalysisTask:
    task = db.get(AnalysisTask, metric_task_id)
    if task is None or task.user_id != user_id:
        raise AppError("NOT_FOUND", "指标任务不存在", 404)
    if task.task_type != TaskType.METRIC_EXTRACTION:
        raise AppError("TASK_TYPE_MISMATCH", "任务类型不匹配", 409)
    if task.status != TaskStatus.SUCCEEDED:
        raise AppError("TASK_NOT_SUCCEEDED", "指标任务未完成", 409)
    if task.paper_id != paper_id:
        raise AppError("PAPER_MISMATCH", "指标任务与论文不匹配", 409)
    return task


def _validate_analysis_graph(
    result: ExperimentResult,
    exp_file: ExperimentFile,
    paper: Paper,
    user_id: str,
    db: Session,
) -> None:
    task = db.get(AnalysisTask, result.task_id)
    if (
        result.file_id != exp_file.id
        or task is None
        or task.task_type != TaskType.EXPERIMENT_ANALYSIS
        or task.status != TaskStatus.SUCCEEDED
        or task.experiment_file_id != exp_file.id
        or task.paper_id != paper.id
        or task.user_id != user_id
    ):
        raise AppError("COMPARISON_STATE_INVALID", "实验分析状态异常", 409)


def _validate_metric_sources(records: list[MetricRecord], paper_id: str, user_id: str, db: Session) -> None:
    for record in records:
        if record.paper_id != paper_id or record.user_id != user_id:
            raise AppError("METRIC_STATE_INVALID", "论文指标状态异常", 409)
        if (record.table_id is None) == (record.evidence_id is None):
            raise AppError("METRIC_STATE_INVALID", "论文指标状态异常", 409)
    table_ids = {record.table_id for record in records if record.table_id is not None}
    evidence_ids = {record.evidence_id for record in records if record.evidence_id is not None}
    if table_ids:
        tables = db.query(PaperTable.id, PaperTable.paper_id).filter(PaperTable.id.in_(table_ids)).all()
        if {table.id for table in tables} != table_ids or any(table.paper_id != paper_id for table in tables):
            raise AppError("METRIC_STATE_INVALID", "论文指标来源异常", 409)
    if evidence_ids:
        evidences = db.query(Evidence.id, Evidence.paper_id).filter(Evidence.id.in_(evidence_ids)).all()
        if {evidence.id for evidence in evidences} != evidence_ids or any(
            evidence.paper_id != paper_id for evidence in evidences
        ):
            raise AppError("METRIC_STATE_INVALID", "论文指标来源异常", 409)


def _load_metric_records(metric_task_id: str, paper_id: str, user_id: str, db: Session) -> list[MetricRecord]:
    records = (
        db.query(MetricRecord)
        .options(defer(MetricRecord.raw_text))
        .filter(MetricRecord.task_id == metric_task_id)
        .all()
    )
    if not records:
        raise AppError("NO_METRICS", "指标任务没有可比较记录", 409)
    _validate_metric_sources(records, paper_id, user_id, db)
    return records


def _validated_summary(value: object) -> dict:
    try:
        return SummaryStatsResponse.model_validate(value).model_dump(mode="python")
    except ValidationError as exc:
        raise AppError("COMPARISON_STATE_INVALID", "实验统计结果异常", 409) from exc


def _validated_comparisons(value: object) -> tuple[str, list[dict]]:
    if not isinstance(value, list) or not value:
        raise AppError("COMPARISON_STATE_INVALID", "交叉验证结果异常", 409)
    try:
        items = [ComparisonItem.model_validate(item) for item in value]
    except ValidationError as exc:
        raise AppError("COMPARISON_STATE_INVALID", "交叉验证结果异常", 409) from exc
    task_ids = {str(item.metric_task_id) for item in items}
    if len(task_ids) != 1:
        raise AppError("COMPARISON_STATE_INVALID", "交叉验证结果异常", 409)
    return task_ids.pop(), [item.model_dump(mode="json") for item in items]


def _build_comparisons(records: list[MetricRecord], summary_stats: dict) -> list[dict]:
    normalized_names = [normalize_comparison_key(record.metric_name) for record in records]
    counts = Counter(name for name in normalized_names if name is not None)
    try:
        ordered = sorted(
            zip(records, normalized_names),
            key=lambda pair: (
                pair[1] or "",
                pair[0].created_at if isinstance(pair[0].created_at, datetime.datetime) else datetime.datetime.min,
                pair[0].id,
            ),
        )
    except TypeError as exc:
        raise AppError("METRIC_STATE_INVALID", "论文指标状态异常", 409) from exc
    comparisons = [
        _compute_comparison(
            record,
            summary_stats,
            settings.experiment_comparison_absolute_tolerance,
            settings.experiment_comparison_relative_tolerance,
            ambiguous_paper_metric=normalized_name is not None and counts[normalized_name] > 1,
        )
        for record, normalized_name in ordered
    ]
    try:
        return [ComparisonItem.model_validate(item).model_dump(mode="json") for item in comparisons]
    except ValidationError as exc:
        raise AppError("COMPARISON_STATE_INVALID", "交叉验证结果异常", 409) from exc


def _outcome(
    result: ExperimentResult,
    metric_task_id: str,
    comparisons: list[dict],
    duplicate: bool,
) -> ComparisonOutcome:
    return ComparisonOutcome(
        file_id=result.file_id,
        experiment_result_id=result.id,
        metric_task_id=metric_task_id,
        comparisons=comparisons,
        duplicate=duplicate,
    )


def _recover_committed_outcome(
    file_id: str,
    metric_task_id: str,
    user_id: str,
) -> ComparisonOutcome | None:
    recovery_db = SessionLocal()
    try:
        exp_file = recovery_db.get(ExperimentFile, file_id)
        if exp_file is None or exp_file.user_id != user_id:
            return None
        paper = recovery_db.get(Paper, exp_file.paper_id)
        if paper is None or paper.user_id != user_id:
            return None
        result = recovery_db.query(ExperimentResult).filter(ExperimentResult.file_id == file_id).one_or_none()
        if result is None:
            return None
        _validate_analysis_graph(result, exp_file, paper, user_id, recovery_db)
        if result.metric_comparisons is None:
            return None
        stored_task_id, comparisons = _validated_comparisons(result.metric_comparisons)
        if stored_task_id != metric_task_id:
            raise AppError("COMPARISON_ALREADY_EXISTS", "交叉验证结果已存在", 409)
        return _outcome(result, metric_task_id, comparisons, False)
    finally:
        recovery_db.close()


def create_comparisons(
    file_id: str,
    metric_task_id: str,
    user_id: str,
    db: Session,
) -> ComparisonOutcome:
    user = db.get(User, user_id)
    exp_file = db.get(ExperimentFile, file_id)
    if user is None or exp_file is None or exp_file.user_id != user_id:
        raise AppError("NOT_FOUND", "实验文件不存在", 404)
    paper = db.get(Paper, exp_file.paper_id)
    if paper is None or paper.user_id != user_id:
        raise AppError("NOT_FOUND", "实验文件不存在", 404)
    result = (
        db.query(ExperimentResult)
        .filter(ExperimentResult.file_id == file_id)
        .with_for_update()
        .execution_options(populate_existing=True)
        .one_or_none()
    )
    if result is None:
        raise AppError("RESULT_NOT_READY", "实验分析结果尚未就绪", 404)
    _validate_analysis_graph(result, exp_file, paper, user_id, db)
    _validate_metric_task(metric_task_id, user_id, paper.id, db)
    if result.metric_comparisons is not None:
        stored_task_id, comparisons = _validated_comparisons(result.metric_comparisons)
        if stored_task_id == metric_task_id:
            return _outcome(result, metric_task_id, comparisons, True)
        raise AppError("COMPARISON_ALREADY_EXISTS", "交叉验证结果已存在", 409)
    summary_stats = _validated_summary(result.summary_stats)
    metric_records = _load_metric_records(metric_task_id, paper.id, user_id, db)
    comparisons = _build_comparisons(metric_records, summary_stats)
    result.metric_comparisons = comparisons
    try:
        db.flush()
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        recovered = _recover_committed_outcome(file_id, metric_task_id, user_id)
        if recovered is not None:
            return recovered
        raise
    return _outcome(result, metric_task_id, comparisons, False)
