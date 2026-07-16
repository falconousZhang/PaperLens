import uuid
import threading
import datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pathlib import Path

from paperlens.core.config import settings
from paperlens.core.database import SessionLocal, configure_engine, get_engine
from paperlens.core.enums import (
    CheckpointType,
    ExportStatus,
    PaperStatus,
    TaskStatus,
    TaskType,
    UserRole,
    UserStatus,
)
from paperlens.main import app
from paperlens.models.models import (
    AnalysisTask,
    Evidence,
    ExperimentFile,
    ExperimentResult,
    ExportReport,
    MetricRecord,
    Paper,
    ReviewFinding,
    ReviewResult,
    User,
)
from paperlens.services.auth_service import create_session_for_user
import paperlens.services.export_service as export_service
from paperlens.services.embedding_client import EmbeddingClient, get_embedding_client
from paperlens.services.llm_client import LLMClient, get_llm_client
from paperlens.services.password_service import hash_password
from paperlens.services.export_service import compute_source_hash, create_export, run_export_task
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
        raise RuntimeError("LLMClient must not be called during export")


class _FakeEmbeddingClient(EmbeddingClient):
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("EmbeddingClient must not be called during export")


def _add_user(db, email: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        email_normalized=email.casefold(),
        display_name=email.split("@", 1)[0],
        password_hash=hash_password("ExportTest123!"),
        role=role,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )
    db.add(user)
    db.flush()
    return user


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
        user = _add_user(db, "export-owner@example.com")
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



def _user_id(client: AsyncClient) -> str:
    value = getattr(client, "_test_user_id", None)
    assert value is not None
    return value


def _storage_root(client: AsyncClient) -> Path:
    value = getattr(client, "_storage_root", None)
    assert value is not None
    return value


def _create_parsed_paper(db, user_id: str, title: str = "Export Test Paper") -> str:
    paper_id = str(uuid.uuid4())
    db.add(
        Paper(
            id=paper_id,
            title=title,
            filename=f"{paper_id}.pdf",
            storage_key=f"papers/{paper_id}/source.pdf",
            file_size=1000,
            file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
            status=PaperStatus.PARSED,
            user_id=user_id,
        )
    )
    db.flush()
    return paper_id


def _create_review_task(db, paper_id: str, user_id: str) -> tuple[str, str]:
    task_id = str(uuid.uuid4())
    db.add(
        AnalysisTask(
            id=task_id,
            paper_id=paper_id,
            task_type=TaskType.REVIEW,
            status=TaskStatus.SUCCEEDED,
            progress=100,
            user_id=user_id,
        )
    )
    db.flush()
    return task_id


def _create_review_result(db, task_id: str, paper_id: str, dimension: str = "SOUNDNESS", rating: int = 4, summary: str = "Good", overall_verdict: str | None = None) -> str:
    rr_id = str(uuid.uuid4())
    db.add(
        ReviewResult(
            id=rr_id,
            task_id=task_id,
            paper_id=paper_id,
            dimension=dimension,
            rating=rating,
            summary=summary,
            overall_verdict=overall_verdict,
        )
    )
    db.flush()
    return rr_id


def _create_metric_task(db, paper_id: str, user_id: str) -> str:
    task_id = str(uuid.uuid4())
    db.add(
        AnalysisTask(
            id=task_id,
            paper_id=paper_id,
            task_type=TaskType.METRIC_EXTRACTION,
            status=TaskStatus.SUCCEEDED,
            progress=100,
            user_id=user_id,
        )
    )
    db.flush()
    return task_id


def _create_metric_record(db, task_id: str, paper_id: str, user_id: str, model_name: str = "BERT", metric_name: str = "Accuracy", metric_value: float = 92.5, checkpoint_type: str = "BEST") -> str:
    mr_id = str(uuid.uuid4())
    db.add(
        MetricRecord(
            id=mr_id,
            paper_id=paper_id,
            task_id=task_id,
            user_id=user_id,
            model_name=model_name,
            dataset_name="SQuAD",
            metric_name=metric_name,
            metric_value=metric_value,
            checkpoint_type=checkpoint_type,
        )
    )
    db.flush()
    return mr_id


def _create_experiment_file(db, paper_id: str, user_id: str, filename: str = "exp.csv") -> str:
    ef_id = str(uuid.uuid4())
    db.add(
        ExperimentFile(
            id=ef_id,
            paper_id=paper_id,
            user_id=user_id,
            filename=filename,
            file_type="CSV",
            storage_key=f"experiment-files/{ef_id}/source.csv",
            file_size=5000,
            file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
            row_count=1,
            column_count=1,
            columns_info={
                "version": 1,
                "encoding": "utf-8",
                "delimiter": ",",
                "sheet_name": None,
                "columns": [
                    {"name": "value", "dtype": "string", "nullable": False, "null_count": 0}
                ],
            },
        )
    )
    db.flush()
    return ef_id


def _create_experiment_task(db, paper_id: str, user_id: str, ef_id: str) -> str:
    task_id = str(uuid.uuid4())
    db.add(
        AnalysisTask(
            id=task_id,
            paper_id=paper_id,
            task_type=TaskType.EXPERIMENT_ANALYSIS,
            status=TaskStatus.SUCCEEDED,
            progress=100,
            user_id=user_id,
            experiment_file_id=ef_id,
        )
    )
    db.flush()
    return task_id


def _create_experiment_result(db, task_id: str, ef_id: str, summary_stats: dict | None = None, metric_comparisons: list | None = None) -> str:
    er_id = str(uuid.uuid4())
    db.add(
        ExperimentResult(
            id=er_id,
            file_id=ef_id,
            task_id=task_id,
            summary_stats=summary_stats or {
                "version": 1,
                "row_count": 1,
                "column_count": 1,
                "columns": [
                    {
                        "name": "value",
                        "dtype": "string",
                        "count": 1,
                        "null_count": 0,
                        "stats": None,
                    }
                ],
            },
            metric_comparisons=metric_comparisons,
        )
    )
    db.flush()
    return er_id


def _setup_full_paper(db, user_id: str) -> str:
    paper_id = _create_parsed_paper(db, user_id)
    review_task_id = _create_review_task(db, paper_id, user_id)
    _create_review_result(db, review_task_id, paper_id, "SOUNDNESS", 4, "Good methodology")
    _create_review_result(db, review_task_id, paper_id, "OVERALL", 5, overall_verdict="ACCEPT")
    return paper_id


@requires_db
class TestCreateExport:
    async def test_create_export_201(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] in ("PENDING", "GENERATING", "READY")
        assert data["report_type"] == "MARKDOWN"
        assert data["language"] == "zh"
        assert data["duplicate"] is False

    async def test_create_export_en(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "en"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["language"] == "en"

    async def test_duplicate_returns_200(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp1 = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        assert resp1.status_code == 201

        db2 = SessionLocal()
        try:
            report = db2.query(ExportReport).filter(ExportReport.paper_id == paper_id).first()
            if report and report.status in (ExportStatus.PENDING, ExportStatus.GENERATING):
                report.status = ExportStatus.READY
                report.storage_key = f"export-reports/{report.id}/report.md"
                report.content_hash = "a" * 64
                report.file_size = 100
                db2.commit()
        finally:
            db2.close()

        resp2 = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["duplicate"] is True

    async def test_paper_not_found_404(self, db_client):
        fake_id = str(uuid.uuid4())
        resp = await db_client.post(
            f"/api/v1/papers/{fake_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        assert resp.status_code == 404

    async def test_paper_not_parsed_409(self, db_client):
        db = SessionLocal()
        try:
            paper_id = str(uuid.uuid4())
            db.add(
                Paper(
                    id=paper_id,
                    title="Unparsed",
                    filename="test.pdf",
                    storage_key=f"papers/{paper_id}/source.pdf",
                    file_size=1000,
                    file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                    status=PaperStatus.UPLOADING,
                    user_id=_user_id(db_client),
                )
            )
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        assert resp.status_code == 409

    async def test_review_not_ready_409(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        assert resp.status_code == 409

    async def test_unauthenticated_401(self, db_client):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as anon_client:
            resp = await anon_client.post(
                f"/api/v1/papers/{str(uuid.uuid4())}/exports",
                json={"report_type": "MARKDOWN", "language": "zh"},
            )
            assert resp.status_code == 401

    async def test_other_users_paper_404(self, db_client):
        db = SessionLocal()
        try:
            other_user = _add_user(db, "export-other@example.com")
            paper_id = _create_parsed_paper(db, other_user.id)
            review_task_id = _create_review_task(db, paper_id, other_user.id)
            _create_review_result(db, review_task_id, paper_id)
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        assert resp.status_code == 404


@requires_db
class TestGetExport:
    async def test_get_export(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        assert resp.status_code == 201
        export_id = resp.json()["id"]

        resp2 = await db_client.get(f"/api/v1/exports/{export_id}")
        assert resp2.status_code == 200
        assert resp2.json()["id"] == export_id

    async def test_get_export_not_found(self, db_client):
        fake_id = str(uuid.uuid4())
        resp = await db_client.get(f"/api/v1/exports/{fake_id}")
        assert resp.status_code == 404

    async def test_get_export_other_user_404(self, db_client):
        db = SessionLocal()
        try:
            other_user = _add_user(db, "export-get-other2@example.com")
            other_user_id = other_user.id
            paper_id = _setup_full_paper(db, other_user_id)
            db.commit()
        finally:
            db.close()

        db2 = SessionLocal()
        try:
            source_snapshot = {"review_task_id": "fake"}
            report = ExportReport(
                paper_id=paper_id,
                report_type="MARKDOWN",
                language="zh",
                include_metrics=True,
                include_experiment_analysis=True,
                source_snapshot=source_snapshot,
                source_hash=compute_source_hash(source_snapshot),
                status=ExportStatus.READY,
                user_id=other_user_id,
                storage_key="export-reports/fake/report.md",
                content_hash="a" * 64,
                file_size=100,
                completed_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db2.add(report)
            db2.commit()
            export_id = report.id
        finally:
            db2.close()

        resp = await db_client.get(f"/api/v1/exports/{export_id}")
        assert resp.status_code == 404


@requires_db
class TestDownloadExport:
    async def test_download_ready_report(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        assert resp.status_code == 201
        export_id = resp.json()["id"]

        db2 = SessionLocal()
        try:
            report = db2.get(ExportReport, export_id)
            if report and report.status == ExportStatus.READY:
                pass
            else:
                report.status = ExportStatus.READY
                storage = LocalStorage(str(_storage_root(db_client)))
                key = f"export-reports/{report.id}/report.md"
                import tempfile, os
                tmp = os.path.join(tempfile.gettempdir(), f"test_export_{report.id}.md")
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write("# Test Report\n")
                storage.save(key, tmp)
                os.unlink(tmp)

                from paperlens.services.export_service import compute_content_hash
                read_back = storage.read_path(key)
                with open(read_back, "rb") as f:
                    stored = f.read()
                report.storage_key = key
                report.content_hash = compute_content_hash(stored)
                report.file_size = len(stored)
                db2.commit()
        finally:
            db2.close()

        resp2 = await db_client.get(f"/api/v1/exports/{export_id}/download")
        assert resp2.status_code == 200
        assert resp2.headers["content-type"] == "text/markdown; charset=utf-8"
        assert resp2.headers["x-content-type-options"] == "nosniff"
        assert "attachment" in resp2.headers.get("content-disposition", "")

    async def test_download_not_ready_409(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
            report, duplicate, content = create_export(
                paper_id=paper_id,
                user_id=_user_id(db_client),
                report_type="MARKDOWN",
                language="zh",
                include_metrics=False,
                include_experiment_analysis=False,
                db=db,
            )
            assert duplicate is False
            assert content is not None
            export_id = report.id
        finally:
            db.close()

        resp2 = await db_client.get(f"/api/v1/exports/{export_id}/download")
        assert resp2.status_code == 409

    async def test_download_not_found(self, db_client):
        resp = await db_client.get(f"/api/v1/exports/{str(uuid.uuid4())}/download")
        assert resp.status_code == 404


@requires_db
class TestExportReportIntegrity:
    async def test_no_forbidden_fields_in_response(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        data = resp.json()
        forbidden = ["storage_key", "content_hash", "source_snapshot"]
        for field in forbidden:
            assert field not in data, f"Forbidden field '{field}' in response"

    async def test_ready_report_has_file_size(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        export_id = resp.json()["id"]

        db2 = SessionLocal()
        try:
            report = db2.get(ExportReport, export_id)
            assert report is not None
            assert report.status == ExportStatus.READY
            assert report.file_size is not None
            assert report.content_hash is not None
            assert report.storage_key is not None
        finally:
            db2.close()


@requires_db
class TestExportSourceAndConcurrency:
    async def test_new_review_source_creates_new_export(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        first = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={
                "report_type": "MARKDOWN",
                "language": "zh",
                "include_metrics": False,
                "include_experiment_analysis": False,
            },
        )
        assert first.status_code == 201

        db = SessionLocal()
        try:
            task_id = _create_review_task(db, paper_id, _user_id(db_client))
            task = db.get(AnalysisTask, task_id)
            task.completed_at = datetime.datetime.now(datetime.timezone.utc)
            _create_review_result(db, task_id, paper_id, summary="New source content")
            db.commit()
        finally:
            db.close()

        second = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={
                "report_type": "MARKDOWN",
                "language": "zh",
                "include_metrics": False,
                "include_experiment_analysis": False,
            },
        )
        assert second.status_code == 201
        assert second.json()["id"] != first.json()["id"]

    async def test_review_result_paper_tamper_is_fixed_409(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            other_paper_id = _create_parsed_paper(db, _user_id(db_client), "Other")
            result = db.query(ReviewResult).filter(ReviewResult.paper_id == paper_id).first()
            result.paper_id = other_paper_id
            db.commit()
        finally:
            db.close()

        response = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={
                "report_type": "MARKDOWN",
                "include_metrics": False,
                "include_experiment_analysis": False,
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EXPORT_SOURCE_INVALID"

    async def test_cross_paper_evidence_tamper_is_fixed_409(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            other_paper_id = _create_parsed_paper(db, _user_id(db_client), "Other")
            review = db.query(ReviewResult).filter(ReviewResult.paper_id == paper_id).first()
            finding = ReviewFinding(
                review_id=review.id,
                finding_type="WEAKNESS",
                content="Tampered evidence",
                confidence=0.5,
                verification_status="UNVERIFIED",
                sequence=0,
            )
            finding.evidences.append(
                Evidence(
                    paper_id=other_paper_id,
                    quoted_text="Wrong paper quote",
                    page_number=1,
                    evidence_type="TEXT",
                )
            )
            db.add(finding)
            db.commit()
        finally:
            db.close()

        response = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={
                "report_type": "MARKDOWN",
                "include_metrics": False,
                "include_experiment_analysis": False,
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EXPORT_SOURCE_INVALID"

    async def test_cross_paper_metric_source_is_fixed_409(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            other_paper_id = _create_parsed_paper(db, _user_id(db_client), "Other")
            task_id = _create_metric_task(db, paper_id, _user_id(db_client))
            evidence = Evidence(
                paper_id=other_paper_id,
                quoted_text="Wrong metric source",
                page_number=1,
                evidence_type="TEXT",
            )
            db.add(evidence)
            db.flush()
            db.add(
                MetricRecord(
                    paper_id=paper_id,
                    task_id=task_id,
                    user_id=_user_id(db_client),
                    model_name="Model",
                    dataset_name="Dataset",
                    metric_name="Accuracy",
                    metric_value=0.9,
                    checkpoint_type="BEST",
                    evidence_id=evidence.id,
                )
            )
            db.commit()
        finally:
            db.close()

        response = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={
                "report_type": "MARKDOWN",
                "include_metrics": True,
                "include_experiment_analysis": False,
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EXPORT_SOURCE_INVALID"

    async def test_cross_paper_experiment_link_is_fixed_409(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            other_paper_id = _create_parsed_paper(db, _user_id(db_client), "Other")
            file_id = _create_experiment_file(db, other_paper_id, _user_id(db_client))
            task_id = _create_experiment_task(db, paper_id, _user_id(db_client), file_id)
            _create_experiment_result(db, task_id, file_id)
            db.commit()
        finally:
            db.close()

        response = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={
                "report_type": "MARKDOWN",
                "include_metrics": False,
                "include_experiment_analysis": True,
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EXPORT_SOURCE_INVALID"

    async def test_evidence_page_and_quote_are_downloaded(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            review = db.query(ReviewResult).filter(ReviewResult.paper_id == paper_id).first()
            evidence = Evidence(
                paper_id=paper_id,
                quoted_text="A stable evidence quote",
                page_number=6,
                evidence_type="TEXT",
            )
            finding = ReviewFinding(
                review_id=review.id,
                finding_type="STRENGTH",
                content="Evidence-backed finding",
                confidence=0.9,
                verification_status="VERIFIED",
                sequence=0,
            )
            finding.evidences.append(evidence)
            db.add(finding)
            db.commit()
        finally:
            db.close()

        created = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={
                "report_type": "MARKDOWN",
                "language": "en",
                "include_metrics": False,
                "include_experiment_analysis": False,
            },
        )
        assert created.status_code == 201
        downloaded = await db_client.get(
            f"/api/v1/exports/{created.json()['id']}/download"
        )
        assert downloaded.status_code == 200
        assert "**Evidence Page 6**: A stable evidence quote" in downloaded.text

    async def test_two_threads_create_one_source_row(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        barrier = threading.Barrier(2)
        outcomes: list[tuple[str, bool, bytes | None]] = []
        errors: list[Exception] = []

        def worker() -> None:
            worker_db = SessionLocal()
            try:
                barrier.wait(timeout=10)
                report, duplicate, content = create_export(
                    paper_id=paper_id,
                    user_id=_user_id(db_client),
                    report_type="MARKDOWN",
                    language="zh",
                    include_metrics=False,
                    include_experiment_analysis=False,
                    db=worker_db,
                )
                outcomes.append((report.id, duplicate, content))
            except Exception as exc:
                errors.append(exc)
            finally:
                worker_db.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        assert errors == []
        assert len(outcomes) == 2
        assert len({item[0] for item in outcomes}) == 1
        assert sorted(item[1] for item in outcomes) == [False, True]
        assert sum(item[2] is not None for item in outcomes) == 1

        db = SessionLocal()
        try:
            reports = db.query(ExportReport).filter(ExportReport.paper_id == paper_id).all()
            assert len(reports) == 1
        finally:
            db.close()

    async def test_two_background_workers_write_one_object(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
            report, duplicate, content = create_export(
                paper_id=paper_id,
                user_id=_user_id(db_client),
                report_type="MARKDOWN",
                language="zh",
                include_metrics=False,
                include_experiment_analysis=False,
                db=db,
            )
            assert duplicate is False
            assert content is not None
            report_id = report.id
        finally:
            db.close()

        workers = [
            threading.Thread(target=run_export_task, args=(report_id, content))
            for _ in range(2)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=20)

        db = SessionLocal()
        try:
            report = db.get(ExportReport, report_id)
            assert report.status == ExportStatus.READY
            assert report.file_size == len(content)
            assert report.content_hash is not None
        finally:
            db.close()
        files = list(_storage_root(db_client).glob("export-reports/*/report.md"))
        assert len(files) == 1

    async def test_partial_storage_failure_cleans_and_failed_can_retry(
        self,
        db_client,
        monkeypatch,
    ):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        storage_root = _storage_root(db_client)

        class PartialFailureStorage(LocalStorage):
            def save(self, storage_key: str, src_path: str) -> None:
                super().save(storage_key, src_path)
                raise OSError("injected storage failure")

        monkeypatch.setattr(
            export_service,
            "get_storage",
            lambda: PartialFailureStorage(str(storage_root)),
        )
        failed = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={
                "report_type": "MARKDOWN",
                "include_metrics": False,
                "include_experiment_analysis": False,
            },
        )
        assert failed.status_code == 201
        failed_id = failed.json()["id"]
        status = await db_client.get(f"/api/v1/exports/{failed_id}")
        assert status.json()["status"] == "FAILED"
        assert status.json()["error_message"] == "报告生成失败，请稍后重试"
        assert list(storage_root.glob("export-reports/*/report.md")) == []

        monkeypatch.setattr(
            export_service,
            "get_storage",
            lambda: LocalStorage(str(storage_root)),
        )
        retried = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={
                "report_type": "MARKDOWN",
                "include_metrics": False,
                "include_experiment_analysis": False,
            },
        )
        assert retried.status_code == 201
        assert retried.json()["id"] != failed_id
        retry_status = await db_client.get(f"/api/v1/exports/{retried.json()['id']}")
        assert retry_status.json()["status"] == "READY"
        assert len(list(storage_root.glob("export-reports/*/report.md"))) == 1
