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
    ExportReport,
    Paper,
    ReviewResult,
    User,
)
from paperlens.services.auth_service import create_session_for_user
import paperlens.services.export_service as export_service
from paperlens.services.embedding_client import EmbeddingClient, get_embedding_client
from paperlens.services.llm_client import LLMClient, get_llm_client
from paperlens.services.password_service import hash_password
from paperlens.services.export_service import compute_source_hash
from paperlens.utils.storage import LocalStorage
from tests.db_helpers import (
    db_available,
    ensure_test_database,
    get_test_db_url,
    is_test_db_required,
    run_alembic_migrations,
    truncate_test_tables,
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
        password_hash=hash_password("P62Test123!"),
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
        user = _add_user(db, "p62-owner@example.com")
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


def _create_parsed_paper(db, user_id: str, title: str = "P62 Export Paper") -> str:
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


def _create_review_task(db, paper_id: str, user_id: str) -> str:
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


def _setup_full_paper(db, user_id: str) -> str:
    paper_id = _create_parsed_paper(db, user_id)
    review_task_id = _create_review_task(db, paper_id, user_id)
    _create_review_result(db, review_task_id, paper_id, "SOUNDNESS", 4, "Good methodology")
    _create_review_result(db, review_task_id, paper_id, "OVERALL", 5, overall_verdict="ACCEPT")
    return paper_id


@requires_db
class TestThreeFormatCreateExport:
    async def test_create_pdf_export_201(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["report_type"] == "PDF"
        assert data["language"] == "zh"
        assert data["duplicate"] is False

    async def test_create_docx_export_201(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "DOCX", "language": "en"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["report_type"] == "DOCX"
        assert data["language"] == "en"
        assert data["duplicate"] is False

    async def test_create_markdown_export_201(self, db_client):
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
        assert data["report_type"] == "MARKDOWN"

    async def test_same_format_same_source_returns_200(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp1 = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )
        assert resp1.status_code == 201

        resp2 = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["duplicate"] is True
        assert resp2.json()["id"] == resp1.json()["id"]

    async def test_different_format_creates_separate_export(self, db_client):
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

        resp2 = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )
        assert resp2.status_code == 201
        assert resp2.json()["id"] != resp1.json()["id"]

    async def test_different_language_creates_separate_export(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp1 = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )
        assert resp1.status_code == 201

        resp2 = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "en"},
        )
        assert resp2.status_code == 201
        assert resp2.json()["id"] != resp1.json()["id"]


@requires_db
class TestListExports:
    async def test_list_exports_empty(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.get(f"/api/v1/papers/{paper_id}/exports")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_list_exports_with_items(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "MARKDOWN", "language": "zh"},
        )
        await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )

        resp = await db_client.get(f"/api/v1/papers/{paper_id}/exports")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    async def test_list_exports_pagination(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        for fmt in ["MARKDOWN", "PDF", "DOCX"]:
            await db_client.post(
                f"/api/v1/papers/{paper_id}/exports",
                json={"report_type": fmt, "language": "zh"},
            )

        resp = await db_client.get(
            f"/api/v1/papers/{paper_id}/exports",
            params={"page": 1, "page_size": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_list_exports_other_user_404(self, db_client):
        db = SessionLocal()
        try:
            other_user = _add_user(db, "p62-list-other@example.com")
            paper_id = _create_parsed_paper(db, other_user.id)
            db.commit()
        finally:
            db.close()

        resp = await db_client.get(f"/api/v1/papers/{paper_id}/exports")
        assert resp.status_code == 404

    async def test_list_exports_unauthenticated_401(self, db_client):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as anon_client:
            resp = await anon_client.get(f"/api/v1/papers/{str(uuid.uuid4())}/exports")
            assert resp.status_code == 401


@requires_db
class TestDownloadThreeFormats:
    async def test_download_pdf_mime_type(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
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
                key = f"export-reports/{report.id}/report.pdf"
                import tempfile, os
                tmp = os.path.join(tempfile.gettempdir(), f"test_export_{report.id}.pdf")
                with open(tmp, "wb") as f:
                    f.write(b"%PDF-1.4 fake pdf content")
                storage.save(key, tmp)
                os.unlink(tmp)
                read_back = storage.read_path(key)
                with open(read_back, "rb") as f:
                    stored = f.read()
                from paperlens.services.export_service import compute_content_hash
                report.storage_key = key
                report.content_hash = compute_content_hash(stored)
                report.file_size = len(stored)
                db2.commit()
        finally:
            db2.close()

        resp2 = await db_client.get(f"/api/v1/exports/{export_id}/download")
        assert resp2.status_code == 200
        assert resp2.headers["content-type"] == "application/pdf"
        assert "attachment" in resp2.headers.get("content-disposition", "")
        assert ".pdf" in resp2.headers.get("content-disposition", "")

    async def test_download_docx_mime_type(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "DOCX", "language": "en"},
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
                key = f"export-reports/{report.id}/report.docx"
                import tempfile, os, zipfile
                tmp = os.path.join(tempfile.gettempdir(), f"test_export_{report.id}.docx")
                with zipfile.ZipFile(tmp, "w") as zf:
                    zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')
                storage.save(key, tmp)
                os.unlink(tmp)
                read_back = storage.read_path(key)
                with open(read_back, "rb") as f:
                    stored = f.read()
                from paperlens.services.export_service import compute_content_hash
                report.storage_key = key
                report.content_hash = compute_content_hash(stored)
                report.file_size = len(stored)
                db2.commit()
        finally:
            db2.close()

        resp2 = await db_client.get(f"/api/v1/exports/{export_id}/download")
        assert resp2.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in resp2.headers["content-type"]
        assert ".docx" in resp2.headers.get("content-disposition", "")

    async def test_download_markdown_mime_type(self, db_client):
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
                read_back = storage.read_path(key)
                with open(read_back, "rb") as f:
                    stored = f.read()
                from paperlens.services.export_service import compute_content_hash
                report.storage_key = key
                report.content_hash = compute_content_hash(stored)
                report.file_size = len(stored)
                db2.commit()
        finally:
            db2.close()

        resp2 = await db_client.get(f"/api/v1/exports/{export_id}/download")
        assert resp2.status_code == 200
        assert "text/markdown" in resp2.headers["content-type"]
        assert ".md" in resp2.headers.get("content-disposition", "")

    async def test_safe_filename_contains_only_report_id(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )
        assert resp.status_code == 201
        export_id = resp.json()["id"]

        db2 = SessionLocal()
        try:
            report = db2.get(ExportReport, export_id)
            if report and report.status != ExportStatus.READY:
                report.status = ExportStatus.READY
                storage = LocalStorage(str(_storage_root(db_client)))
                key = f"export-reports/{report.id}/report.pdf"
                import tempfile, os
                tmp = os.path.join(tempfile.gettempdir(), f"test_export_{report.id}.pdf")
                with open(tmp, "wb") as f:
                    f.write(b"%PDF-1.4 fake pdf content")
                storage.save(key, tmp)
                os.unlink(tmp)
                read_back = storage.read_path(key)
                with open(read_back, "rb") as f:
                    stored = f.read()
                from paperlens.services.export_service import compute_content_hash
                report.storage_key = key
                report.content_hash = compute_content_hash(stored)
                report.file_size = len(stored)
                db2.commit()
        finally:
            db2.close()

        resp2 = await db_client.get(f"/api/v1/exports/{export_id}/download")
        assert resp2.status_code == 200
        cd = resp2.headers.get("content-disposition", "")
        safe_id = export_id.replace("-", "_")
        assert f"report_{safe_id}.pdf" in cd


@requires_db
class TestFailedRetryThreeFormats:
    async def test_failed_pdf_can_retry(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )
        assert resp.status_code == 201
        failed_id = resp.json()["id"]

        db2 = SessionLocal()
        try:
            report = db2.get(ExportReport, failed_id)
            report.status = ExportStatus.FAILED
            report.error_message = "报告生成失败，请稍后重试"
            report.storage_key = None
            report.content_hash = None
            report.file_size = None
            db2.commit()
        finally:
            db2.close()

        resp2 = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )
        assert resp2.status_code == 201
        assert resp2.json()["id"] != failed_id

    async def test_failed_docx_can_retry(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "DOCX", "language": "en"},
        )
        assert resp.status_code == 201
        failed_id = resp.json()["id"]

        db2 = SessionLocal()
        try:
            report = db2.get(ExportReport, failed_id)
            report.status = ExportStatus.FAILED
            report.error_message = "报告生成失败，请稍后重试"
            report.storage_key = None
            report.content_hash = None
            report.file_size = None
            db2.commit()
        finally:
            db2.close()

        resp2 = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "DOCX", "language": "en"},
        )
        assert resp2.status_code == 201
        assert resp2.json()["id"] != failed_id


@requires_db
class TestConcurrencyThreeFormats:
    async def test_concurrent_pdf_creates_one_row(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        barrier = threading.Barrier(2)
        outcomes: list[tuple[str, bool]] = []
        errors: list[Exception] = []

        def worker() -> None:
            worker_db = SessionLocal()
            try:
                barrier.wait(timeout=10)
                from paperlens.services.export_service import create_export
                report, duplicate, content = create_export(
                    paper_id=paper_id,
                    user_id=_user_id(db_client),
                    report_type="PDF",
                    language="zh",
                    include_metrics=False,
                    include_experiment_analysis=False,
                    db=worker_db,
                )
                outcomes.append((report.id, duplicate))
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

    async def test_concurrent_docx_creates_one_row(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        barrier = threading.Barrier(2)
        outcomes: list[tuple[str, bool]] = []
        errors: list[Exception] = []

        def worker() -> None:
            worker_db = SessionLocal()
            try:
                barrier.wait(timeout=10)
                from paperlens.services.export_service import create_export
                report, duplicate, content = create_export(
                    paper_id=paper_id,
                    user_id=_user_id(db_client),
                    report_type="DOCX",
                    language="en",
                    include_metrics=False,
                    include_experiment_analysis=False,
                    db=worker_db,
                )
                outcomes.append((report.id, duplicate))
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


@requires_db
class TestMigration012:
    async def test_012_migration_applied(self, db_client):
        from tests.db_helpers import verify_alembic_revision, get_test_db_url
        test_url = get_test_db_url()
        if test_url:
            verify_alembic_revision(test_url)

    async def test_pdf_docx_report_type_allowed(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        for fmt in ["PDF", "DOCX", "MARKDOWN"]:
            resp = await db_client.post(
                f"/api/v1/papers/{paper_id}/exports",
                json={"report_type": fmt, "language": "zh"},
            )
            assert resp.status_code == 201, f"report_type={fmt} should be accepted"
            assert resp.json()["report_type"] == fmt

    async def test_source_snapshot_nonnull_for_all_formats(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        for fmt in ["MARKDOWN", "PDF", "DOCX"]:
            resp = await db_client.post(
                f"/api/v1/papers/{paper_id}/exports",
                json={"report_type": fmt, "language": "zh"},
            )
            assert resp.status_code == 201
            export_id = resp.json()["id"]

            db2 = SessionLocal()
            try:
                report = db2.get(ExportReport, export_id)
                assert report is not None
                assert report.source_snapshot is not None, f"source_snapshot must be non-null for {fmt}"
                assert report.source_hash is not None, f"source_hash must be non-null for {fmt}"
            finally:
                db2.close()


@requires_db
class TestNoForbiddenFields:
    async def test_pdf_response_no_forbidden_fields(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )
        data = resp.json()
        for field in ["storage_key", "content_hash", "source_snapshot", "source_hash"]:
            assert field not in data, f"Forbidden field '{field}' in PDF response"

    async def test_docx_response_no_forbidden_fields(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "DOCX", "language": "en"},
        )
        data = resp.json()
        for field in ["storage_key", "content_hash", "source_snapshot", "source_hash"]:
            assert field not in data, f"Forbidden field '{field}' in DOCX response"

    async def test_list_response_no_forbidden_fields(self, db_client):
        db = SessionLocal()
        try:
            paper_id = _setup_full_paper(db, _user_id(db_client))
            db.commit()
        finally:
            db.close()

        await db_client.post(
            f"/api/v1/papers/{paper_id}/exports",
            json={"report_type": "PDF", "language": "zh"},
        )

        resp = await db_client.get(f"/api/v1/papers/{paper_id}/exports")
        data = resp.json()
        for item in data["items"]:
            for field in ["storage_key", "content_hash", "source_snapshot", "source_hash"]:
                assert field not in item, f"Forbidden field '{field}' in list item"