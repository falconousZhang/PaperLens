import csv
import io
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

from paperlens.core.config import settings
from paperlens.core.database import SessionLocal, configure_engine, get_engine
from paperlens.core.enums import PaperStatus, TaskStatus, TaskType, UserRole, UserStatus
from paperlens.main import app
from paperlens.models.models import AnalysisTask, ExperimentFile, ExperimentResult, Paper, User
from paperlens.services.auth_service import create_session_for_user
from paperlens.services.embedding_client import EmbeddingClient, get_embedding_client
from paperlens.services.llm_client import LLMClient, get_llm_client
from paperlens.services.password_service import hash_password
from paperlens.utils.storage import LocalStorage
from tests.db_helpers import (
    db_available,
    ensure_test_database,
    get_test_db_url,
    is_test_db_required,
    run_alembic_migrations,
    truncate_test_tables,
    verify_no_test_residuals,
)

requires_db = pytest.mark.skipif(
    not db_available() and not is_test_db_required(),
    reason="需要 PAPERLENS_TEST_DATABASE_URL",
)
pytestmark = pytest.mark.asyncio


class _FakeLLMClient(LLMClient):
    def chat(self, messages: list[dict], **kwargs) -> dict:
        raise RuntimeError("LLMClient must not be called during experiment analysis")


class _FakeEmbeddingClient(EmbeddingClient):
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("EmbeddingClient must not be called during experiment analysis")


def _add_user(db, email: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        email_normalized=email.casefold(),
        display_name=email.split("@", 1)[0],
        password_hash=hash_password("ExpAnalysisTest123!"),
        role=role,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )
    db.add(user)
    db.flush()
    return user


def _make_csv_bytes(rows: list[list[str]], delimiter: str = ",") -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def _make_xlsx_bytes(rows: list[list]) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest_asyncio.fixture
async def db_client(tmp_path: Path, monkeypatch):
    test_url = get_test_db_url()
    if not test_url:
        if is_test_db_required():
            pytest.fail("PAPERLENS_REQUIRE_TEST_DB=true but PAPERLENS_TEST_DATABASE_URL is not set")
        pytest.skip("需要 PAPERLENS_TEST_DATABASE_URL")

    ensure_test_database()
    run_alembic_migrations(test_url)
    configure_engine(test_url)
    assert "paperlens_test" in str(get_engine().url)
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_root", str(storage_root))

    app.dependency_overrides[get_llm_client] = lambda: _FakeLLMClient()
    app.dependency_overrides[get_embedding_client] = lambda: _FakeEmbeddingClient()
    db = SessionLocal()
    try:
        user = _add_user(db, "expanalysis-owner@example.com")
        access_token, _ = create_session_for_user(db, user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {access_token}"},
        ) as client:
            client._test_user_id = user_id
            client._storage_root = storage_root
            yield client
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
        app.dependency_overrides.pop(get_embedding_client, None)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def _user_id(client: AsyncClient) -> str:
    value = getattr(client, "_test_user_id", None)
    assert value is not None
    return value


def _create_parsed_paper(db, user_id: str) -> str:
    paper_id = str(uuid.uuid4())
    db.add(
        Paper(
            id=paper_id,
            title="Analysis Test Paper",
            filename=f"{paper_id}.pdf",
            storage_key=f"papers/{paper_id}/source.pdf",
            file_size=1000,
            file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
            status=PaperStatus.PARSED,
            user_id=user_id,
        )
    )
    db.flush()
    db.commit()
    return paper_id


async def _upload_csv(client: AsyncClient, paper_id: str, rows: list[list[str]]) -> dict:
    csv_content = _make_csv_bytes(rows)
    resp = await client.post(
        f"/api/v1/papers/{paper_id}/experiment-files/upload",
        files={"file": ("data.csv", csv_content, "text/csv")},
    )
    assert resp.status_code in (200, 201)
    return resp.json()


@requires_db
class TestExperimentAnalysisCreate:
    async def test_create_analysis_201(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["accuracy", "loss"], ["0.9", "0.1"], ["0.88", "0.2"]],
        )
        file_id = file_data["id"]

        resp = await db_client.post(f"/api/v1/experiment-files/{file_id}/analysis")
        assert resp.status_code == 201
        data = resp.json()
        assert data["task_type"] == "EXPERIMENT_ANALYSIS"
        assert data["status"] == "PENDING"
        assert data["experiment_file_id"] == file_id
        assert data["duplicate"] is False

    async def test_create_analysis_idempotent_200(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["accuracy"], ["0.9"]],
        )
        file_id = file_data["id"]

        resp1 = await db_client.post(f"/api/v1/experiment-files/{file_id}/analysis")
        assert resp1.status_code == 201

        db2 = SessionLocal()
        try:
            task = db2.query(AnalysisTask).filter(
                AnalysisTask.experiment_file_id == file_id,
            ).first()
            if task:
                task.status = "SUCCEEDED"
                task.progress = 100
                db2.commit()
        finally:
            db2.close()

        resp2 = await db_client.post(f"/api/v1/experiment-files/{file_id}/analysis")
        assert resp2.status_code == 200
        assert resp2.json()["duplicate"] is True

    async def test_create_analysis_no_token_401(self, db_client: AsyncClient):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as anon_client:
            resp = await anon_client.post("/api/v1/experiment-files/nonexistent/analysis")
            assert resp.status_code == 401

    async def test_create_analysis_not_found_404(self, db_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await db_client.post(f"/api/v1/experiment-files/{fake_id}/analysis")
        assert resp.status_code == 404

    @pytest.mark.parametrize("other_role", [UserRole.USER, UserRole.ADMIN])
    async def test_create_analysis_cross_user_404(
        self, db_client: AsyncClient, other_role: UserRole
    ):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
            other_user = _add_user(
                db, f"other-analysis-{other_role.value.casefold()}@example.com", other_role
            )
            other_user_id = other_user.id
            db.commit()
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["x"], ["1.0"]],
        )
        file_id = file_data["id"]

        db2 = SessionLocal()
        try:
            other_user = db2.get(User, other_user_id)
            other_token, _ = create_session_for_user(db2, other_user)
            db2.commit()
        finally:
            db2.close()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {other_token}"},
        ) as other_client:
            resp = await other_client.post(f"/api/v1/experiment-files/{file_id}/analysis")
            assert resp.status_code == 404

    async def test_create_analysis_paper_not_parsed_409(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["x"], ["1.0"]],
        )
        file_id = file_data["id"]

        db3 = SessionLocal()
        try:
            paper = db3.get(Paper, paper_id)
            paper.status = PaperStatus.PROCESSING
            db3.commit()
        finally:
            db3.close()

        resp = await db_client.post(f"/api/v1/experiment-files/{file_id}/analysis")
        assert resp.status_code == 409


@requires_db
class TestExperimentResult:
    async def test_get_result_200(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["accuracy", "loss"], ["0.9", "0.1"], ["0.88", "0.2"], ["0.92", "0.15"]],
        )
        file_id = file_data["id"]

        db2 = SessionLocal()
        try:
            from paperlens.services.experiment_analysis_service import create_experiment_analysis
            task, dup = create_experiment_analysis(file_id, _user_id(db_client), db2)
            task_id = task.id
        finally:
            db2.close()

        from paperlens.services.experiment_analysis_service import run_experiment_analysis_task
        run_experiment_analysis_task(task_id)

        resp = await db_client.get(f"/api/v1/experiment-files/{file_id}/result")
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_id"] == file_id
        assert data["task_id"] == task_id
        assert "summary_stats" in data
        stats = data["summary_stats"]
        assert stats["version"] == 1
        assert stats["row_count"] == 3
        assert stats["column_count"] == 2
        assert len(stats["columns"]) == 2

        acc_col = stats["columns"][0]
        assert acc_col["name"] == "accuracy"
        assert acc_col["dtype"] == "float"
        assert acc_col["count"] == 3
        assert acc_col["stats"] is not None
        assert abs(acc_col["stats"]["mean"] - 0.9) < 1e-10

        loss_col = stats["columns"][1]
        assert loss_col["name"] == "loss"
        assert loss_col["stats"] is not None

    async def test_get_result_not_ready_404(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["x"], ["1.0"]],
        )
        file_id = file_data["id"]

        resp = await db_client.get(f"/api/v1/experiment-files/{file_id}/result")
        assert resp.status_code == 404

    async def test_get_result_no_token_401(self, db_client: AsyncClient):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as anon_client:
            resp = await anon_client.get("/api/v1/experiment-files/nonexistent/result")
            assert resp.status_code == 401

    @pytest.mark.parametrize("other_role", [UserRole.USER, UserRole.ADMIN])
    async def test_get_result_cross_user_404(
        self, db_client: AsyncClient, other_role: UserRole
    ):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
            other_user = _add_user(
                db, f"other-result-{other_role.value.casefold()}@example.com", other_role
            )
            other_user_id = other_user.id
            db.commit()
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["x"], ["1.0"]],
        )
        file_id = file_data["id"]

        db2 = SessionLocal()
        try:
            other_user = db2.get(User, other_user_id)
            other_token, _ = create_session_for_user(db2, other_user)
            db2.commit()
        finally:
            db2.close()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {other_token}"},
        ) as other_client:
            resp = await other_client.get(f"/api/v1/experiment-files/{file_id}/result")
            assert resp.status_code == 404

    async def test_result_with_mismatched_task_relation_is_hidden(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        file_data = await _upload_csv(db_client, paper_id, [["x"], ["1"]])
        db2 = SessionLocal()
        try:
            unrelated_task = AnalysisTask(
                id=str(uuid.uuid4()),
                paper_id=paper_id,
                task_type=TaskType.REVIEW,
                status=TaskStatus.SUCCEEDED,
                progress=100,
                user_id=_user_id(db_client),
            )
            db2.add(unrelated_task)
            db2.flush()
            db2.add(
                ExperimentResult(
                    id=str(uuid.uuid4()),
                    file_id=file_data["id"],
                    task_id=unrelated_task.id,
                    summary_stats={
                        "version": 1,
                        "row_count": 1,
                        "column_count": 1,
                        "columns": [
                            {
                                "name": "x",
                                "dtype": "integer",
                                "count": 1,
                                "null_count": 0,
                                "stats": {
                                    "mean": 1.0,
                                    "stddev": None,
                                    "min": 1.0,
                                    "max": 1.0,
                                    "median": 1.0,
                                },
                            }
                        ],
                    },
                )
            )
            db2.commit()
        finally:
            db2.close()
        resp = await db_client.get(
            f"/api/v1/experiment-files/{file_data['id']}/result"
        )
        assert resp.status_code == 404


@requires_db
class TestExperimentAnalysisIntegrity:
    async def test_hash_mismatch_task_fails(self, db_client: AsyncClient, monkeypatch):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["x"], ["1.0"]],
        )
        file_id = file_data["id"]

        db2 = SessionLocal()
        try:
            from paperlens.services.experiment_analysis_service import create_experiment_analysis
            task, dup = create_experiment_analysis(file_id, _user_id(db_client), db2)
            task_id = task.id
        finally:
            db2.close()

        import paperlens.services.experiment_analysis_service as _eam
        original_compute = _eam._compute_file_hash

        def _fake_compute(source_path: str) -> str:
            return "0" * 64

        monkeypatch.setattr(_eam, "_compute_file_hash", _fake_compute)

        from paperlens.services.experiment_analysis_service import run_experiment_analysis_task
        run_experiment_analysis_task(task_id)

        db3 = SessionLocal()
        try:
            task = db3.get(AnalysisTask, task_id)
            assert task is not None
            assert task.status == "FAILED"
            result_count = db3.query(ExperimentResult).filter(
                ExperimentResult.task_id == task_id
            ).count()
            assert result_count == 0
        finally:
            db3.close()

    async def test_successful_analysis_creates_single_result(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["accuracy"], ["0.9"], ["0.88"], ["0.92"]],
        )
        file_id = file_data["id"]

        db2 = SessionLocal()
        try:
            from paperlens.services.experiment_analysis_service import create_experiment_analysis
            task, dup = create_experiment_analysis(file_id, _user_id(db_client), db2)
            task_id = task.id
        finally:
            db2.close()

        from paperlens.services.experiment_analysis_service import run_experiment_analysis_task
        run_experiment_analysis_task(task_id)

        db3 = SessionLocal()
        try:
            task = db3.get(AnalysisTask, task_id)
            assert task.status == "SUCCEEDED"
            assert task.progress == 100
            results = db3.query(ExperimentResult).filter(
                ExperimentResult.file_id == file_id
            ).all()
            assert len(results) == 1
            assert results[0].summary_stats is not None
            assert results[0].summary_stats["version"] == 1
            assert results[0].column_analysis is None
            assert results[0].metric_comparisons is None
        finally:
            db3.close()

    async def test_full_columns_info_mismatch_task_fails(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        file_data = await _upload_csv(db_client, paper_id, [["x"], ["1.0"], [""]])
        file_id = file_data["id"]
        db2 = SessionLocal()
        try:
            from paperlens.services.experiment_analysis_service import create_experiment_analysis

            task, _ = create_experiment_analysis(file_id, _user_id(db_client), db2)
            task_id = task.id
            exp_file = db2.get(ExperimentFile, file_id)
            columns_info = dict(exp_file.columns_info)
            columns_info["columns"] = [dict(exp_file.columns_info["columns"][0])]
            columns_info["columns"][0]["nullable"] = False
            columns_info["columns"][0]["null_count"] = 0
            exp_file.columns_info = columns_info
            db2.commit()
        finally:
            db2.close()

        from paperlens.services.experiment_analysis_service import run_experiment_analysis_task

        run_experiment_analysis_task(task_id)
        db3 = SessionLocal()
        try:
            task = db3.get(AnalysisTask, task_id)
            assert task.status == "FAILED"
            assert task.error_message == "实验文件完整性校验失败"
            assert db3.query(ExperimentResult).filter(ExperimentResult.file_id == file_id).count() == 0
        finally:
            db3.close()

    async def test_missing_storage_marks_task_failed(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        file_data = await _upload_csv(db_client, paper_id, [["x"], ["1.0"]])
        file_id = file_data["id"]
        db2 = SessionLocal()
        try:
            from paperlens.services.experiment_analysis_service import create_experiment_analysis

            task, _ = create_experiment_analysis(file_id, _user_id(db_client), db2)
            task_id = task.id
            exp_file = db2.get(ExperimentFile, file_id)
            source_path = Path(getattr(db_client, "_storage_root")) / exp_file.storage_key
        finally:
            db2.close()
        source_path.unlink()

        from paperlens.services.experiment_analysis_service import run_experiment_analysis_task

        run_experiment_analysis_task(task_id)
        db3 = SessionLocal()
        try:
            task = db3.get(AnalysisTask, task_id)
            assert task.status == "FAILED"
            assert task.error_message == "文件存储读取失败"
            assert db3.query(ExperimentResult).filter(ExperimentResult.task_id == task_id).count() == 0
        finally:
            db3.close()


@requires_db
class TestExperimentAnalysisConcurrency:
    async def test_concurrent_analysis_one_task_one_result(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["x"], ["1.0"]],
        )
        file_id = file_data["id"]

        resp1 = await db_client.post(f"/api/v1/experiment-files/{file_id}/analysis")
        resp2 = await db_client.post(f"/api/v1/experiment-files/{file_id}/analysis")

        assert resp1.status_code in (200, 201)
        assert resp2.status_code == 200

        db2 = SessionLocal()
        try:
            tasks = db2.query(AnalysisTask).filter(
                AnalysisTask.experiment_file_id == file_id,
            ).all()
            assert len(tasks) == 1
        finally:
            db2.close()

    async def test_true_concurrent_creation_returns_winner(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        file_data = await _upload_csv(db_client, paper_id, [["x"], ["1.0"]])
        file_id = file_data["id"]
        barrier = threading.Barrier(2)

        def _create():
            from paperlens.services.experiment_analysis_service import create_experiment_analysis

            session = SessionLocal()
            try:
                barrier.wait(timeout=5)
                task, duplicate = create_experiment_analysis(file_id, _user_id(db_client), session)
                return task.id, duplicate
            finally:
                session.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: _create(), range(2)))
        assert len({task_id for task_id, _ in outcomes}) == 1
        assert sorted(duplicate for _, duplicate in outcomes) == [False, True]
        db2 = SessionLocal()
        try:
            assert db2.query(AnalysisTask).filter(
                AnalysisTask.experiment_file_id == file_id
            ).count() == 1
        finally:
            db2.close()


@requires_db
class TestExperimentAnalysisTransactions:
    async def _prepared_task(self, db_client: AsyncClient) -> tuple[str, str]:
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        file_data = await _upload_csv(db_client, paper_id, [["x"], ["1.0"], ["2.0"]])
        db2 = SessionLocal()
        try:
            from paperlens.services.experiment_analysis_service import create_experiment_analysis

            task, _ = create_experiment_analysis(file_data["id"], _user_id(db_client), db2)
            return file_data["id"], task.id
        finally:
            db2.close()

    async def test_result_flush_failure_is_atomic(self, db_client: AsyncClient, monkeypatch):
        file_id, task_id = await self._prepared_task(db_client)
        original_flush = Session.flush

        def _flush(session, *args, **kwargs):
            if any(isinstance(item, ExperimentResult) for item in session.new):
                raise RuntimeError("injected result flush failure")
            return original_flush(session, *args, **kwargs)

        monkeypatch.setattr(Session, "flush", _flush)
        from paperlens.services.experiment_analysis_service import run_experiment_analysis_task

        run_experiment_analysis_task(task_id)
        db = SessionLocal()
        try:
            assert db.get(AnalysisTask, task_id).status == "FAILED"
            assert db.query(ExperimentResult).filter(ExperimentResult.file_id == file_id).count() == 0
        finally:
            db.close()

    async def test_success_commit_failure_rolls_back_result(self, db_client: AsyncClient, monkeypatch):
        file_id, task_id = await self._prepared_task(db_client)
        original_commit = Session.commit

        def _commit(session):
            if any(
                isinstance(item, AnalysisTask) and item.status == "SUCCEEDED"
                for item in session.dirty
            ):
                raise RuntimeError("injected success commit failure")
            return original_commit(session)

        monkeypatch.setattr(Session, "commit", _commit)
        from paperlens.services.experiment_analysis_service import run_experiment_analysis_task

        run_experiment_analysis_task(task_id)
        db = SessionLocal()
        try:
            assert db.get(AnalysisTask, task_id).status == "FAILED"
            assert db.query(ExperimentResult).filter(ExperimentResult.file_id == file_id).count() == 0
        finally:
            db.close()

    async def test_commit_unknown_requery_preserves_success(self, db_client: AsyncClient, monkeypatch):
        file_id, task_id = await self._prepared_task(db_client)
        original_commit = Session.commit
        injected = False

        def _commit(session):
            nonlocal injected
            is_success = any(
                isinstance(item, AnalysisTask) and item.status == "SUCCEEDED"
                for item in session.dirty
            )
            if is_success and not injected:
                injected = True
                original_commit(session)
                raise RuntimeError("injected unknown commit outcome")
            return original_commit(session)

        monkeypatch.setattr(Session, "commit", _commit)
        from paperlens.services.experiment_analysis_service import run_experiment_analysis_task

        run_experiment_analysis_task(task_id)
        db = SessionLocal()
        try:
            assert db.get(AnalysisTask, task_id).status == "SUCCEEDED"
            results = db.query(ExperimentResult).filter(ExperimentResult.file_id == file_id).all()
            assert len(results) == 1
            assert results[0].task_id == task_id
        finally:
            db.close()

    async def test_claim_commit_unknown_continues_safely(self, db_client: AsyncClient, monkeypatch):
        file_id, task_id = await self._prepared_task(db_client)
        original_commit = Session.commit
        injected = False

        def _commit(session):
            nonlocal injected
            is_claim = any(
                isinstance(item, AnalysisTask) and item.status == "RUNNING"
                for item in session.dirty
            )
            if is_claim and not injected:
                injected = True
                original_commit(session)
                raise RuntimeError("injected unknown claim commit outcome")
            return original_commit(session)

        monkeypatch.setattr(Session, "commit", _commit)
        from paperlens.services.experiment_analysis_service import run_experiment_analysis_task

        run_experiment_analysis_task(task_id)
        db = SessionLocal()
        try:
            assert injected is True
            assert db.get(AnalysisTask, task_id).status == "SUCCEEDED"
            assert db.query(ExperimentResult).filter(ExperimentResult.file_id == file_id).count() == 1
        finally:
            db.close()

    async def test_failed_status_commit_is_retried(self, db_client: AsyncClient, monkeypatch):
        file_id, task_id = await self._prepared_task(db_client)
        original_commit = Session.commit
        failures = 0

        def _commit(session):
            nonlocal failures
            is_failure = any(
                isinstance(item, AnalysisTask) and item.status == "FAILED"
                for item in session.dirty
            )
            if is_failure and failures == 0:
                failures += 1
                raise RuntimeError("injected failed-state commit failure")
            return original_commit(session)

        monkeypatch.setattr(Session, "commit", _commit)
        import paperlens.services.experiment_analysis_service as analysis_service

        monkeypatch.setattr(analysis_service, "_compute_file_hash", lambda _path: "0" * 64)
        analysis_service.run_experiment_analysis_task(task_id)
        db = SessionLocal()
        try:
            assert failures == 1
            assert db.get(AnalysisTask, task_id).status == "FAILED"
            assert db.query(ExperimentResult).filter(ExperimentResult.file_id == file_id).count() == 0
        finally:
            db.close()


@requires_db
class TestExperimentAnalysisNumericCellsLimit:
    async def test_too_large_413(self, db_client: AsyncClient, monkeypatch):
        monkeypatch.setattr(settings, "max_experiment_analysis_numeric_cells", 1)

        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        file_data = await _upload_csv(
            db_client, paper_id,
            [["x", "y"], ["1.0", "2.0"]],
        )
        file_id = file_data["id"]

        resp = await db_client.post(f"/api/v1/experiment-files/{file_id}/analysis")
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "ANALYSIS_TOO_LARGE"
        assert "2" not in resp.json()["error"]["message"]
        db2 = SessionLocal()
        try:
            assert db2.query(AnalysisTask).filter(
                AnalysisTask.experiment_file_id == file_id
            ).count() == 0
        finally:
            db2.close()
