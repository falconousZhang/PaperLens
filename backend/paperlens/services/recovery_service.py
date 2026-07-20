from __future__ import annotations

import datetime
import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, timezone
from typing import Any

from sqlalchemy import or_, text

from paperlens.core.config import settings
from paperlens.core.database import SessionLocal
from paperlens.core.enums import (
    ExportStatus,
    LearningStatus,
    PaperStatus,
    QATurnStatus,
    TaskStatus,
    TaskType,
)
from paperlens.models.models import (
    AnalysisTask,
    ExportReport,
    LearningExplanation,
    Paper,
    PaperQATurn,
)

logger = logging.getLogger(__name__)

_RECOVERY_LOCK_KEY = 0x5245434F56455259
_PAPER_FAILED_MESSAGE = "论文解析失败，请稍后重试或重新上传"
_REVIEW_FAILED_MESSAGE = "审阅生成失败，请稍后重试"
_EXPORT_FAILED_MESSAGE = "报告生成失败，请稍后重试"

Dispatch = tuple[Callable[..., None], tuple[Any, ...]]

_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def get_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=settings.recovery_max_workers,
                thread_name_prefix="recovery",
            )
        return _executor


def shutdown_executor() -> None:
    global _executor
    with _executor_lock:
        executor = _executor
        _executor = None
    if executor is not None:
        executor.shutdown(wait=True, cancel_futures=True)


def run_recovery(submitter: Callable[..., None] | None = None) -> bool:
    service = RecoveryService(
        stale_seconds=settings.recovery_stale_seconds,
        batch_size=settings.recovery_batch_size,
    )
    return service.scan_and_recover(submitter)


class RecoveryService:
    def __init__(self, stale_seconds: int, batch_size: int) -> None:
        if stale_seconds < 1 or stale_seconds > 86400:
            raise ValueError("invalid recovery stale threshold")
        if batch_size < 1 or batch_size > 1000:
            raise ValueError("invalid recovery batch size")
        self.stale_seconds = stale_seconds
        self.batch_size = batch_size

    def scan_and_recover(self, submitter: Callable[..., None] | None = None) -> bool:
        db = SessionLocal()
        dispatches: list[Dispatch] = []
        stats = {
            "papers": 0,
            "tasks": 0,
            "learning": 0,
            "qa": 0,
            "exports": 0,
            "failed": 0,
        }
        try:
            acquired = bool(
                db.execute(
                    text("SELECT pg_try_advisory_xact_lock(:key)"),
                    {"key": _RECOVERY_LOCK_KEY},
                ).scalar()
            )
            if not acquired:
                db.rollback()
                logger.info("stage=recovery_skipped action=lock_busy")
                return False

            cutoff = datetime.datetime.now(timezone.utc) - timedelta(
                seconds=self.stale_seconds
            )
            dispatches.extend(self._scan_papers(db, cutoff, stats))
            dispatches.extend(self._scan_analysis_tasks(db, cutoff, stats))
            dispatches.extend(self._scan_learning(db, cutoff, stats))
            dispatches.extend(self._scan_qa(db, cutoff, stats))
            dispatches.extend(self._scan_exports(db, cutoff, stats))
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error(
                "stage=recovery_failed error_type=%s",
                type(exc).__name__,
                exc_info=True,
            )
            return False
        finally:
            db.close()

        for func, args in dispatches:
            try:
                if submitter is not None:
                    submitter(func, args)
                else:
                    get_executor().submit(func, *args)
            except Exception:
                logger.error(
                    "stage=recovery_submit_failed error_type=executor_rejected"
                )

        logger.info(
            "stage=recovery_complete papers=%d tasks=%d learning=%d qa=%d exports=%d failed=%d",
            stats["papers"],
            stats["tasks"],
            stats["learning"],
            stats["qa"],
            stats["exports"],
            stats["failed"],
        )
        return True

    def _scan_papers(self, db, cutoff, stats) -> list[Dispatch]:
        rows = (
            db.query(Paper)
            .filter(
                Paper.status == PaperStatus.PROCESSING,
                Paper.updated_at < cutoff,
            )
            .order_by(Paper.created_at, Paper.id)
            .limit(self.batch_size)
            .with_for_update(skip_locked=True)
            .all()
        )
        now = datetime.datetime.now(timezone.utc)
        for paper in rows:
            paper.status = PaperStatus.FAILED
            paper.error_message = _PAPER_FAILED_MESSAGE
            paper.updated_at = now
            stats["failed"] += 1
            logger.info(
                "stage=recovery entity_type=paper entity_id=%s action=failed",
                paper.id,
            )
        return []

    def _scan_analysis_tasks(self, db, cutoff, stats) -> list[Dispatch]:
        dispatches: list[Dispatch] = []
        pending = (
            db.query(AnalysisTask)
            .filter(
                AnalysisTask.status == TaskStatus.PENDING,
                AnalysisTask.created_at < cutoff,
            )
            .order_by(AnalysisTask.created_at, AnalysisTask.id)
            .limit(self.batch_size)
            .with_for_update(skip_locked=True)
            .all()
        )
        for task in pending:
            dispatch = self._pending_analysis_dispatch(task)
            if dispatch is None:
                self._fail_unrecoverable_analysis(task)
                stats["failed"] += 1
                continue
            dispatches.append(dispatch)
            stats["tasks"] += 1
            logger.info(
                "stage=recovery entity_type=analysis_task entity_id=%s task_type=%s action=redispatch",
                task.id,
                task.task_type,
            )

        running = (
            db.query(AnalysisTask)
            .filter(
                AnalysisTask.status == TaskStatus.RUNNING,
                or_(
                    AnalysisTask.started_at.is_(None),
                    AnalysisTask.started_at < cutoff,
                ),
            )
            .order_by(AnalysisTask.created_at, AnalysisTask.id)
            .limit(self.batch_size)
            .with_for_update(skip_locked=True)
            .all()
        )
        now = datetime.datetime.now(timezone.utc)
        for task in running:
            if self._analysis_task_has_results(db, task):
                task.status = TaskStatus.SUCCEEDED
                task.progress = 100
                task.error_message = None
                task.completed_at = now
                stats["tasks"] += 1
                logger.info(
                    "stage=recovery entity_type=analysis_task entity_id=%s task_type=%s action=set_succeeded",
                    task.id,
                    task.task_type,
                )
                continue

            dispatch = self._pending_analysis_dispatch(task)
            if dispatch is None:
                self._fail_unrecoverable_analysis(task)
                stats["failed"] += 1
                continue
            task.status = TaskStatus.PENDING
            task.progress = 0
            task.error_message = None
            task.started_at = None
            task.completed_at = None
            dispatches.append(dispatch)
            stats["tasks"] += 1
            logger.info(
                "stage=recovery entity_type=analysis_task entity_id=%s task_type=%s action=reset_and_redispatch",
                task.id,
                task.task_type,
            )
        return dispatches

    def _scan_learning(self, db, cutoff, stats) -> list[Dispatch]:
        dispatches: list[Dispatch] = []
        pending = (
            db.query(LearningExplanation)
            .filter(
                LearningExplanation.status == LearningStatus.PENDING,
                LearningExplanation.created_at < cutoff,
            )
            .order_by(LearningExplanation.created_at, LearningExplanation.id)
            .limit(self.batch_size)
            .with_for_update(skip_locked=True)
            .all()
        )
        for explanation in pending:
            dispatches.append((_recover_learning, (explanation.id,)))
            stats["learning"] += 1
            logger.info(
                "stage=recovery entity_type=learning_explanation entity_id=%s action=redispatch",
                explanation.id,
            )

        running = (
            db.query(LearningExplanation)
            .filter(
                LearningExplanation.status == LearningStatus.RUNNING,
                or_(
                    LearningExplanation.started_at.is_(None),
                    LearningExplanation.started_at < cutoff,
                ),
            )
            .order_by(LearningExplanation.created_at, LearningExplanation.id)
            .limit(self.batch_size)
            .with_for_update(skip_locked=True)
            .all()
        )
        for explanation in running:
            explanation.status = LearningStatus.PENDING
            explanation.answer = None
            explanation.key_points = None
            explanation.terms = None
            explanation.error_message = None
            explanation.started_at = None
            explanation.completed_at = None
            dispatches.append((_recover_learning, (explanation.id,)))
            stats["learning"] += 1
            logger.info(
                "stage=recovery entity_type=learning_explanation entity_id=%s action=reset_and_redispatch",
                explanation.id,
            )
        return dispatches

    def _scan_qa(self, db, cutoff, stats) -> list[Dispatch]:
        dispatches: list[Dispatch] = []
        pending = (
            db.query(PaperQATurn)
            .filter(
                PaperQATurn.status == QATurnStatus.PENDING,
                PaperQATurn.created_at < cutoff,
            )
            .order_by(PaperQATurn.created_at, PaperQATurn.id)
            .limit(self.batch_size)
            .with_for_update(skip_locked=True)
            .all()
        )
        for turn in pending:
            dispatches.append((_recover_qa_turn, (turn.id,)))
            stats["qa"] += 1
            logger.info(
                "stage=recovery entity_type=qa_turn entity_id=%s action=redispatch",
                turn.id,
            )

        running = (
            db.query(PaperQATurn)
            .filter(
                PaperQATurn.status == QATurnStatus.RUNNING,
                or_(
                    PaperQATurn.started_at.is_(None),
                    PaperQATurn.started_at < cutoff,
                ),
            )
            .order_by(PaperQATurn.created_at, PaperQATurn.id)
            .limit(self.batch_size)
            .with_for_update(skip_locked=True)
            .all()
        )
        for turn in running:
            turn.status = QATurnStatus.PENDING
            turn.answer = None
            turn.grounded = None
            turn.context_hash = None
            turn.error_message = None
            turn.started_at = None
            turn.completed_at = None
            dispatches.append((_recover_qa_turn, (turn.id,)))
            stats["qa"] += 1
            logger.info(
                "stage=recovery entity_type=qa_turn entity_id=%s action=reset_and_redispatch",
                turn.id,
            )
        return dispatches

    def _scan_exports(self, db, cutoff, stats) -> list[Dispatch]:
        reports = (
            db.query(ExportReport)
            .filter(
                ExportReport.status.in_(
                    [ExportStatus.PENDING, ExportStatus.GENERATING]
                ),
                ExportReport.created_at < cutoff,
            )
            .order_by(ExportReport.created_at, ExportReport.id)
            .limit(self.batch_size)
            .with_for_update(skip_locked=True)
            .all()
        )
        now = datetime.datetime.now(timezone.utc)
        for report in reports:
            report.status = ExportStatus.FAILED
            report.storage_key = None
            report.file_size = None
            report.error_message = _EXPORT_FAILED_MESSAGE
            report.completed_at = now
            stats["exports"] += 1
            stats["failed"] += 1
            logger.info(
                "stage=recovery entity_type=export_report entity_id=%s action=failed",
                report.id,
            )
        return []

    def _pending_analysis_dispatch(self, task: AnalysisTask) -> Dispatch | None:
        if task.task_type == TaskType.METRIC_EXTRACTION:
            return (_recover_metric_task, (task.id,))
        if task.task_type == TaskType.EXPERIMENT_ANALYSIS:
            return (_recover_experiment_task, (task.id,))
        return None

    def _fail_unrecoverable_analysis(self, task: AnalysisTask) -> None:
        task.status = TaskStatus.FAILED
        task.progress = 100
        task.error_message = _REVIEW_FAILED_MESSAGE
        task.completed_at = datetime.datetime.now(timezone.utc)
        logger.info(
            "stage=recovery entity_type=analysis_task entity_id=%s task_type=%s action=failed",
            task.id,
            task.task_type,
        )

    def _analysis_task_has_results(self, db, task: AnalysisTask) -> bool:
        if task.task_type == TaskType.REVIEW:
            from paperlens.models.models import ReviewResult

            return (
                db.query(ReviewResult.id)
                .filter(ReviewResult.task_id == task.id)
                .first()
                is not None
            )
        if task.task_type == TaskType.METRIC_EXTRACTION:
            from paperlens.models.models import MetricRecord

            return (
                db.query(MetricRecord.id)
                .filter(MetricRecord.task_id == task.id)
                .first()
                is not None
            )
        if task.task_type == TaskType.EXPERIMENT_ANALYSIS:
            from paperlens.models.models import ExperimentResult

            return (
                db.query(ExperimentResult.id)
                .filter(ExperimentResult.task_id == task.id)
                .first()
                is not None
            )
        return False


def _recover_metric_task(task_id: str) -> None:
    from paperlens.services.metric_service import run_metric_extraction_task

    try:
        run_metric_extraction_task(task_id)
    except Exception as exc:
        logger.error(
            "stage=metric_recovery_failed entity_type=analysis_task entity_id=%s error_type=%s",
            task_id,
            type(exc).__name__,
            exc_info=True,
        )


def _recover_experiment_task(task_id: str) -> None:
    from paperlens.services.experiment_analysis_service import (
        run_experiment_analysis_task,
    )

    try:
        run_experiment_analysis_task(task_id)
    except Exception as exc:
        logger.error(
            "stage=experiment_recovery_failed entity_type=analysis_task entity_id=%s error_type=%s",
            task_id,
            type(exc).__name__,
            exc_info=True,
        )


def _recover_learning(explanation_id: str) -> None:
    from paperlens.services.learning_service import run_learning_task

    try:
        run_learning_task(explanation_id)
    except Exception as exc:
        logger.error(
            "stage=learning_recovery_failed entity_type=learning_explanation entity_id=%s error_type=%s",
            explanation_id,
            type(exc).__name__,
            exc_info=True,
        )


def _recover_qa_turn(turn_id: str) -> None:
    from paperlens.services.qa_service import run_qa_turn

    try:
        run_qa_turn(turn_id)
    except Exception as exc:
        logger.error(
            "stage=qa_recovery_failed entity_type=qa_turn entity_id=%s error_type=%s",
            turn_id,
            type(exc).__name__,
            exc_info=True,
        )
