from __future__ import annotations

import datetime
import uuid
from datetime import timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from paperlens.core.enums import (
    PaperStatus,
    TaskStatus,
    TaskType,
)
from paperlens.models.models import (
    AnalysisTask,
    Paper,
    User,
)
from paperlens.services.recovery_service import RecoveryService


def _make_user(db) -> str:
    uid = str(uuid.uuid4())
    email = f"recovery-{uid[:8]}@test.com"
    db.add(
        User(
            id=uid,
            email=email,
            email_normalized=email,
            display_name="Recovery User",
            role="USER",
            status="ACTIVE",
        )
    )
    db.flush()
    return uid


def _make_paper(db, user_id, status=PaperStatus.PROCESSING, storage_key="uploads/test.pdf") -> str:
    pid = str(uuid.uuid4())
    now = datetime.datetime.now(timezone.utc)
    db.add(Paper(
        id=pid,
        user_id=user_id,
        title="Recovery Test",
        filename="test.pdf",
        storage_key=storage_key,
        file_size=1,
        file_hash="0" * 64,
        status=status,
        created_at=now - timedelta(seconds=600),
        updated_at=now - timedelta(seconds=600),
    ))
    db.flush()
    return pid


def _make_task(db, user_id, paper_id, task_type=TaskType.REVIEW, status=TaskStatus.PENDING) -> str:
    tid = str(uuid.uuid4())
    now = datetime.datetime.now(timezone.utc)
    db.add(AnalysisTask(
        id=tid,
        user_id=user_id,
        paper_id=paper_id,
        task_type=task_type,
        status=status,
        progress=0,
        created_at=now - timedelta(seconds=600),
        started_at=now - timedelta(seconds=600) if status == TaskStatus.RUNNING else None,
    ))
    db.flush()
    return tid


@pytest.fixture
def recovery_service():
    return RecoveryService(stale_seconds=60, batch_size=50)


def test_stale_task_recovery_succeeds(db_session, recovery_service):
    user_id = _make_user(db_session)
    paper_id = _make_paper(db_session, user_id, status=PaperStatus.PARSED)
    task_id = _make_task(
        db_session,
        user_id,
        paper_id,
        TaskType.METRIC_EXTRACTION,
        TaskStatus.PENDING,
    )

    dispatches = recovery_service._scan_analysis_tasks(
        db_session,
        datetime.datetime.now(timezone.utc) - timedelta(seconds=60),
        {"tasks": 0, "failed": 0},
    )

    assert len(dispatches) >= 1
    func, args = dispatches[0]
    assert args[0] == task_id


def test_fresh_and_terminal_tasks_untouched(db_session, recovery_service):
    user_id = _make_user(db_session)
    paper_id = _make_paper(db_session, user_id, status=PaperStatus.PARSED)

    fresh_task_id = _make_task(db_session, user_id, paper_id, TaskType.REVIEW, TaskStatus.PENDING)
    db_session.query(AnalysisTask).filter(AnalysisTask.id == fresh_task_id).update(
        {"created_at": datetime.datetime.now(timezone.utc)}
    )
    db_session.flush()

    succeeded_task_id = _make_task(db_session, user_id, paper_id, TaskType.REVIEW, TaskStatus.SUCCEEDED)
    failed_task_id = _make_task(db_session, user_id, paper_id, TaskType.REVIEW, TaskStatus.FAILED)

    cutoff = datetime.datetime.now(timezone.utc) - timedelta(seconds=60)
    stats = {"tasks": 0, "failed": 0}
    dispatches = recovery_service._scan_analysis_tasks(db_session, cutoff, stats)

    dispatched_ids = [args[0] for _, args in dispatches]
    assert fresh_task_id not in dispatched_ids
    assert succeeded_task_id not in dispatched_ids
    assert failed_task_id not in dispatched_ids


def test_concurrent_mutex_and_missing_input_safe_failure(db_session, recovery_service):
    locked_session = MagicMock()
    locked_session.execute.return_value.scalar.return_value = False
    with patch(
        "paperlens.services.recovery_service.SessionLocal",
        return_value=locked_session,
    ):
        assert recovery_service.scan_and_recover() is False
    locked_session.rollback.assert_called_once()
    locked_session.close.assert_called_once()

    user_id = _make_user(db_session)
    paper_id = _make_paper(db_session, user_id, status=PaperStatus.PROCESSING, storage_key="")

    cutoff = datetime.datetime.now(timezone.utc) - timedelta(seconds=60)
    stats = {"papers": 0, "failed": 0}
    dispatches = recovery_service._scan_papers(db_session, cutoff, stats)

    assert len(dispatches) == 0
    assert stats["failed"] >= 1

    paper = db_session.get(Paper, paper_id)
    assert paper.status == PaperStatus.FAILED


@pytest.fixture
def db_session():
    from paperlens.core.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
