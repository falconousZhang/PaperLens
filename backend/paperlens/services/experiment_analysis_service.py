from __future__ import annotations

import copy
import datetime
import hashlib
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from paperlens.core.config import settings
from paperlens.core.database import SessionLocal
from paperlens.core.enums import ExperimentFileType, PaperStatus, TaskStatus, TaskType
from paperlens.core.errors import AppError
from paperlens.models.models import AnalysisTask, ExperimentFile, ExperimentResult, Paper, User
from paperlens.services.experiment_file_parser import ParseError, parse_experiment_file
from paperlens.services.experiment_statistics import StatisticsError, compute_summary_stats
from paperlens.utils.storage import get_storage

logger = logging.getLogger(__name__)

_SAFE_ERROR_MESSAGES = {
    "integrity": "实验文件完整性校验失败",
    "computation": "统计分析计算失败",
    "numeric_safety": "数值安全检查失败",
    "type": "文件类型不匹配",
    "storage": "文件存储读取失败",
    "unknown": "实验分析失败，请稍后重试",
}


@dataclass(frozen=True)
class _AnalysisInput:
    task_id: str
    user_id: str
    paper_id: str
    file_id: str
    storage_key: str
    file_hash: str
    file_type: ExperimentFileType
    row_count: int
    column_count: int
    columns_info: dict


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, StatisticsError):
        return _SAFE_ERROR_MESSAGES.get(exc.kind, _SAFE_ERROR_MESSAGES["unknown"])
    if isinstance(exc, ParseError):
        return _SAFE_ERROR_MESSAGES.get(exc.kind, _SAFE_ERROR_MESSAGES["integrity"])
    return _SAFE_ERROR_MESSAGES["unknown"]


def _compute_file_hash(source_path: str) -> str:
    digest = hashlib.sha256()
    with open(source_path, "rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_task_graph(
    task: AnalysisTask,
    exp_file: ExperimentFile | None,
    paper: Paper | None,
    user: User | None,
) -> None:
    if task.task_type != TaskType.EXPERIMENT_ANALYSIS or task.experiment_file_id is None:
        raise StatisticsError("task type or file link mismatch", "integrity")
    if exp_file is None or paper is None or user is None:
        raise StatisticsError("analysis object is missing", "integrity")
    if paper.status != PaperStatus.PARSED:
        raise StatisticsError("paper is not parsed", "integrity")
    if task.user_id != user.id or exp_file.user_id != user.id or paper.user_id != user.id:
        raise StatisticsError("analysis owner mismatch", "integrity")
    if task.paper_id != paper.id or exp_file.paper_id != paper.id:
        raise StatisticsError("analysis paper mismatch", "integrity")
    if task.experiment_file_id != exp_file.id:
        raise StatisticsError("analysis file mismatch", "integrity")


def _analysis_input(db: Session, task: AnalysisTask) -> _AnalysisInput:
    exp_file = db.get(ExperimentFile, task.experiment_file_id)
    paper = db.get(Paper, task.paper_id)
    user = db.get(User, task.user_id)
    _validate_task_graph(task, exp_file, paper, user)
    try:
        file_type = ExperimentFileType(exp_file.file_type)
    except ValueError as exc:
        raise StatisticsError("file type metadata mismatch", "type") from exc
    return _AnalysisInput(
        task_id=task.id,
        user_id=task.user_id,
        paper_id=task.paper_id,
        file_id=exp_file.id,
        storage_key=exp_file.storage_key,
        file_hash=exp_file.file_hash,
        file_type=file_type,
        row_count=exp_file.row_count,
        column_count=exp_file.column_count,
        columns_info=copy.deepcopy(exp_file.columns_info),
    )


def _find_existing_analysis(
    db: Session,
    file_id: str,
    user_id: str,
    paper_id: str,
) -> AnalysisTask | None:
    result = (
        db.query(ExperimentResult)
        .filter(ExperimentResult.file_id == file_id)
        .first()
    )
    if result is not None:
        task = db.get(AnalysisTask, result.task_id)
        if (
            task is not None
            and task.task_type == TaskType.EXPERIMENT_ANALYSIS
            and task.status == TaskStatus.SUCCEEDED
            and task.user_id == user_id
            and task.paper_id == paper_id
            and task.experiment_file_id == file_id
        ):
            return task
        raise AppError("ANALYSIS_STATE_INVALID", "实验分析状态异常", 409)
    return (
        db.query(AnalysisTask)
        .filter(
            AnalysisTask.task_type == TaskType.EXPERIMENT_ANALYSIS,
            AnalysisTask.experiment_file_id == file_id,
            AnalysisTask.paper_id == paper_id,
            AnalysisTask.user_id == user_id,
            AnalysisTask.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING]),
        )
        .order_by(AnalysisTask.created_at.asc(), AnalysisTask.id.asc())
        .first()
    )


def _numeric_column_count(exp_file: ExperimentFile) -> int:
    columns_info = exp_file.columns_info
    if not isinstance(columns_info, dict) or not isinstance(columns_info.get("columns"), list):
        raise AppError("EXPERIMENT_FILE_INVALID", "实验文件元数据异常", 409)
    count = 0
    for column in columns_info["columns"]:
        if not isinstance(column, dict) or column.get("dtype") not in {
            "integer",
            "float",
            "boolean",
            "datetime",
            "string",
            "empty",
        }:
            raise AppError("EXPERIMENT_FILE_INVALID", "实验文件元数据异常", 409)
        if column["dtype"] in {"integer", "float"}:
            count += 1
    if len(columns_info["columns"]) != exp_file.column_count:
        raise AppError("EXPERIMENT_FILE_INVALID", "实验文件元数据异常", 409)
    return count


def create_experiment_analysis(
    file_id: str,
    user_id: str,
    db: Session,
) -> tuple[AnalysisTask, bool]:
    exp_file = db.get(ExperimentFile, file_id)
    if exp_file is None or exp_file.user_id != user_id:
        raise AppError("NOT_FOUND", "实验文件不存在", 404)
    paper = db.get(Paper, exp_file.paper_id)
    if paper is None or paper.user_id != user_id:
        raise AppError("NOT_FOUND", "实验文件不存在", 404)
    if paper.status != PaperStatus.PARSED:
        raise AppError("PAPER_NOT_PARSED", "论文尚未解析完成，无法分析实验文件", 409)

    existing = _find_existing_analysis(db, file_id, user_id, paper.id)
    if existing is not None:
        return existing, True

    numeric_cells = exp_file.row_count * _numeric_column_count(exp_file)
    if numeric_cells > settings.max_experiment_analysis_numeric_cells:
        raise AppError("ANALYSIS_TOO_LARGE", "实验数据超过统计规模限制", 413)

    task = AnalysisTask(
        id=str(uuid.uuid4()),
        paper_id=paper.id,
        task_type=TaskType.EXPERIMENT_ANALYSIS,
        status=TaskStatus.PENDING,
        progress=0,
        user_id=user_id,
        experiment_file_id=file_id,
    )
    db.add(task)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        constraint_name = getattr(getattr(getattr(exc, "orig", None), "diag", None), "constraint_name", None)
        if isinstance(exc, IntegrityError) and constraint_name not in {
            None,
            "uq_active_experiment_task_per_user_file",
        }:
            raise
        winner = _find_existing_analysis(db, file_id, user_id, paper.id)
        if winner is not None:
            return winner, True
        raise
    try:
        db.refresh(task)
    except Exception:
        db.rollback()
        persisted = db.get(AnalysisTask, task.id)
        if persisted is None:
            raise
        task = persisted
    return task, False


def _claim_task(task_id: str) -> bool:
    db = SessionLocal()
    try:
        task = (
            db.query(AnalysisTask)
            .filter(AnalysisTask.id == task_id)
            .with_for_update()
            .one_or_none()
        )
        if task is None or task.status != TaskStatus.PENDING:
            db.rollback()
            return False
        if task.task_type != TaskType.EXPERIMENT_ANALYSIS or task.experiment_file_id is None:
            raise StatisticsError("task metadata mismatch", "integrity")
        task.status = TaskStatus.RUNNING
        task.progress = 10
        task.error_message = None
        task.started_at = datetime.datetime.now(datetime.timezone.utc)
        try:
            db.commit()
        except Exception:
            db.rollback()
            verification_db = SessionLocal()
            try:
                persisted = verification_db.get(AnalysisTask, task_id)
                if persisted is not None and persisted.status == TaskStatus.RUNNING:
                    return True
            finally:
                verification_db.close()
            raise
        return True
    finally:
        db.close()


def _load_input(task_id: str) -> _AnalysisInput:
    db = SessionLocal()
    try:
        task = db.get(AnalysisTask, task_id)
        if task is None or task.status != TaskStatus.RUNNING:
            raise StatisticsError("task state mismatch", "integrity")
        return _analysis_input(db, task)
    finally:
        db.close()


def _input_matches(exp_file: ExperimentFile, analysis_input: _AnalysisInput) -> bool:
    return (
        exp_file.id == analysis_input.file_id
        and exp_file.user_id == analysis_input.user_id
        and exp_file.paper_id == analysis_input.paper_id
        and exp_file.storage_key == analysis_input.storage_key
        and exp_file.file_hash == analysis_input.file_hash
        and exp_file.file_type == analysis_input.file_type.value
        and exp_file.row_count == analysis_input.row_count
        and exp_file.column_count == analysis_input.column_count
        and exp_file.columns_info == analysis_input.columns_info
    )


def _success_was_committed(task_id: str, file_id: str) -> bool:
    db = SessionLocal()
    try:
        task = db.get(AnalysisTask, task_id)
        result = (
            db.query(ExperimentResult)
            .filter(ExperimentResult.file_id == file_id)
            .one_or_none()
        )
        return (
            task is not None
            and task.status == TaskStatus.SUCCEEDED
            and task.progress == 100
            and result is not None
            and result.task_id == task_id
        )
    except Exception:
        return False
    finally:
        db.close()


def _persist_success(analysis_input: _AnalysisInput, summary_stats: dict) -> None:
    db = SessionLocal()
    try:
        task = (
            db.query(AnalysisTask)
            .filter(AnalysisTask.id == analysis_input.task_id)
            .with_for_update()
            .one_or_none()
        )
        if task is None or task.status != TaskStatus.RUNNING:
            raise StatisticsError("task state changed before persistence", "integrity")
        exp_file = db.get(ExperimentFile, analysis_input.file_id)
        paper = db.get(Paper, analysis_input.paper_id)
        user = db.get(User, analysis_input.user_id)
        _validate_task_graph(task, exp_file, paper, user)
        if not _input_matches(exp_file, analysis_input):
            raise StatisticsError("file metadata changed during analysis", "integrity")
        if db.query(ExperimentResult).filter(ExperimentResult.file_id == analysis_input.file_id).first() is not None:
            raise StatisticsError("experiment result already exists", "integrity")
        db.add(
            ExperimentResult(
                id=str(uuid.uuid4()),
                file_id=analysis_input.file_id,
                task_id=analysis_input.task_id,
                summary_stats=summary_stats,
                column_analysis=None,
                metric_comparisons=None,
            )
        )
        db.flush()
        task.status = TaskStatus.SUCCEEDED
        task.progress = 100
        task.completed_at = datetime.datetime.now(datetime.timezone.utc)
        task.error_message = None
        db.commit()
    except Exception:
        db.rollback()
        if _success_was_committed(analysis_input.task_id, analysis_input.file_id):
            return
        raise
    finally:
        db.close()


def _mark_task_failed(task_id: str, message: str) -> None:
    for _ in range(2):
        db = SessionLocal()
        try:
            task = (
                db.query(AnalysisTask)
                .filter(AnalysisTask.id == task_id)
                .with_for_update()
                .one_or_none()
            )
            if task is None or task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING}:
                db.rollback()
                return
            result = (
                db.query(ExperimentResult)
                .filter(ExperimentResult.task_id == task_id)
                .first()
            )
            if result is not None:
                db.rollback()
                return
            task.status = TaskStatus.FAILED
            task.progress = 100
            task.error_message = message
            task.completed_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            return
        except Exception:
            db.rollback()
        finally:
            db.close()
    logger.error("Experiment analysis failure state could not be persisted")


def run_experiment_analysis_task(task_id: str) -> None:
    try:
        if not _claim_task(task_id):
            return
        analysis_input = _load_input(task_id)
        try:
            with get_storage().materialize(analysis_input.storage_key) as source_path:
                actual_hash = _compute_file_hash(source_path)
                if actual_hash != analysis_input.file_hash:
                    raise StatisticsError("file hash mismatch", "integrity")
                try:
                    parse_result = parse_experiment_file(source_path, analysis_input.file_type)
                except ParseError as exc:
                    raise StatisticsError("file re-parse failed", "integrity") from exc
                if (
                    parse_result.file_type != analysis_input.file_type
                    or parse_result.row_count != analysis_input.row_count
                    or parse_result.column_count != analysis_input.column_count
                    or parse_result.columns_info != analysis_input.columns_info
                ):
                    raise StatisticsError("file structure mismatch", "integrity")
                summary_stats = compute_summary_stats(
                    source_path=source_path,
                    file_type=analysis_input.file_type,
                    row_count=analysis_input.row_count,
                    column_count=analysis_input.column_count,
                    columns_info=analysis_input.columns_info,
                )
                try:
                    if _compute_file_hash(source_path) != analysis_input.file_hash:
                        raise StatisticsError("file changed during analysis", "integrity")
                except StatisticsError:
                    raise
                except Exception as exc:
                    raise StatisticsError("storage re-read failed", "storage") from exc
        except StatisticsError:
            raise
        except Exception as exc:
            raise StatisticsError("storage read failed", "storage") from exc
        _persist_success(analysis_input, summary_stats)
    except Exception as exc:
        logger.error("Experiment analysis task failed (%s)", type(exc).__name__)
        _mark_task_failed(task_id, _safe_error_message(exc))
