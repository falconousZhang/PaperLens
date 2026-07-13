import os
import logging
import uuid
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from paperlens.main import app
from tests.db_helpers import (
    get_test_db_url,
    db_available,
    ensure_test_database,
    run_alembic_migrations,
    verify_alembic_revision,
    truncate_test_tables,
    verify_no_test_residuals,
    count_papers_in_db,
    get_dev_db_url,
    wait_for_paper_status,
    is_test_db_required,
)


requires_db = pytest.mark.skipif(
    not db_available() and not is_test_db_required(),
    reason="需要 PAPERLENS_TEST_DATABASE_URL 且 PostgreSQL 可连接",
)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def db_client():
    test_url = get_test_db_url()
    if not test_url:
        if is_test_db_required():
            pytest.fail("PAPERLENS_REQUIRE_TEST_DB=true but PAPERLENS_TEST_DATABASE_URL is not set")
        pytest.skip("需要 PAPERLENS_TEST_DATABASE_URL")

    ensure_test_database()
    run_alembic_migrations(test_url)
    verify_alembic_revision(test_url)

    from paperlens.core.database import configure_engine, get_engine
    configure_engine(test_url)
    actual_url = str(get_engine().url)
    assert "paperlens_test" in actual_url, (
        f"Engine URL must point to paperlens_test, got: {actual_url}"
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


@pytest_asyncio.fixture
def dev_db_count():
    dev_url = get_dev_db_url()
    if not dev_url:
        return None
    try:
        return count_papers_in_db(dev_url)
    except Exception:
        return None


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_upload_non_pdf_returns_415(client: AsyncClient, tmp_path):
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("not a pdf")
    with open(str(txt_path), "rb") as f:
        resp = await client.post("/api/v1/papers/upload", files={"file": ("test.txt", f, "text/plain")})
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_fake_extension_rejected(client: AsyncClient, tmp_path):
    txt_path = tmp_path / "fake.pdf"
    txt_path.write_text("not really a pdf content here")
    with open(str(txt_path), "rb") as f:
        resp = await client.post("/api/v1/papers/upload", files={"file": ("fake.pdf", f, "application/pdf")})
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_oversized_file_rejected(client: AsyncClient, tmp_path):
    from paperlens.core.config import settings
    old = settings.max_pdf_size_mb
    settings.max_pdf_size_mb = 0
    try:
        from tests.conftest import create_test_pdf
        pdf_path = create_test_pdf("hello", tmp_path=str(tmp_path))
        with open(pdf_path, "rb") as f:
            resp = await client.post("/api/v1/papers/upload", files={"file": ("test.pdf", f, "application/pdf")})
        assert resp.status_code == 413
    finally:
        settings.max_pdf_size_mb = old


@pytest.mark.asyncio
async def test_invalid_uuid_returns_422(client: AsyncClient):
    resp = await client.get("/api/v1/papers/not-a-uuid")
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["details"] is not None


@pytest.mark.asyncio
async def test_invalid_uuid_evidence_returns_422(client: AsyncClient):
    resp = await client.get("/api/v1/evidences/not-a-uuid")
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_error_response_has_details_field(client: AsyncClient):
    resp = await client.get("/api/v1/papers/not-a-uuid")
    assert resp.status_code == 422
    data = resp.json()
    assert "details" in data["error"]


@requires_db
@pytest.mark.asyncio
async def test_upload_valid_pdf(db_client: AsyncClient, tmp_path):
    from tests.conftest import create_test_pdf
    pdf_path = create_test_pdf("This is a test paper about machine learning and deep neural networks.", tmp_path=str(tmp_path))
    with open(pdf_path, "rb") as f:
        resp = await db_client.post("/api/v1/papers/upload", files={"file": ("test.pdf", f, "application/pdf")})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "PROCESSING"
    assert data["filename"] == "test.pdf"


@requires_db
@pytest.mark.asyncio
async def test_path_traversal_filename_sanitized(db_client: AsyncClient, tmp_path):
    from tests.conftest import create_test_pdf
    from paperlens.core.database import SessionLocal
    from paperlens.models.models import Paper

    pdf_path = create_test_pdf("hello", tmp_path=str(tmp_path))
    with open(pdf_path, "rb") as f:
        resp = await db_client.post("/api/v1/papers/upload", files={"file": ("../../../etc/passwd.pdf", f, "application/pdf")})
    assert resp.status_code == 201
    data = resp.json()
    paper_id = data["id"]
    assert data["filename"] == "passwd.pdf"

    db = SessionLocal()
    try:
        paper = db.get(Paper, paper_id)
        assert paper is not None
        assert paper.filename == "passwd.pdf"
        assert paper.storage_key == f"papers/{paper_id}/source.pdf"
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
async def test_paper_detail_has_error_message(db_client: AsyncClient, tmp_path):
    from tests.conftest import create_test_pdf
    pdf_path = create_test_pdf("Test paper for detail.", tmp_path=str(tmp_path))
    with open(pdf_path, "rb") as f:
        upload_resp = await db_client.post("/api/v1/papers/upload", files={"file": ("detail_test.pdf", f, "application/pdf")})
    assert upload_resp.status_code == 201
    paper_id = upload_resp.json()["id"]

    detail_resp = await db_client.get(f"/api/v1/papers/{paper_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert "error_message" in detail


@requires_db
@pytest.mark.asyncio
async def test_evidence_detail_fields_strict(db_client: AsyncClient, tmp_path):
    from tests.conftest import create_test_pdf
    from paperlens.core.database import SessionLocal
    from paperlens.models.models import Paper, Evidence as EvidenceModel

    pdf_path = create_test_pdf("Testing evidence detail endpoint with real database.", tmp_path=str(tmp_path))
    with open(pdf_path, "rb") as f:
        upload_resp = await db_client.post("/api/v1/papers/upload", files={"file": ("ev_test.pdf", f, "application/pdf")})
    assert upload_resp.status_code == 201
    paper_id = upload_resp.json()["id"]

    status = wait_for_paper_status(paper_id)
    assert status == "PARSED", f"Paper parsing failed or timed out: {status}"

    db = SessionLocal()
    try:
        db_evidence = db.query(EvidenceModel).filter(EvidenceModel.paper_id == paper_id).first()
        assert db_evidence is not None
        ev_id = db_evidence.id
        expected_quoted = db_evidence.quoted_text
        expected_page = db_evidence.page_number
        expected_bbox_x0 = db_evidence.bbox_x0
        expected_bbox_y0 = db_evidence.bbox_y0
        expected_bbox_x1 = db_evidence.bbox_x1
        expected_bbox_y1 = db_evidence.bbox_y1
        expected_char_start = db_evidence.char_start
        expected_char_end = db_evidence.char_end
        expected_evidence_type = db_evidence.evidence_type
        expected_section_id = db_evidence.section_id
        expected_chunk_id = db_evidence.chunk_id
    finally:
        db.close()

    detail_resp = await db_client.get(f"/api/v1/evidences/{ev_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == ev_id
    assert detail["quoted_text"] == expected_quoted
    assert detail["page_number"] == expected_page
    assert detail["bbox_x0"] == expected_bbox_x0
    assert detail["bbox_y0"] == expected_bbox_y0
    assert detail["bbox_x1"] == expected_bbox_x1
    assert detail["bbox_y1"] == expected_bbox_y1
    assert detail["char_start"] == expected_char_start
    assert detail["char_end"] == expected_char_end
    assert detail["evidence_type"] == expected_evidence_type
    assert detail["section_id"] == expected_section_id
    assert detail["chunk_id"] == expected_chunk_id


@requires_db
@pytest.mark.asyncio
async def test_evidence_nullable_fields(db_client: AsyncClient):
    from paperlens.core.database import SessionLocal
    from paperlens.core.enums import EvidenceType, PaperStatus
    from paperlens.models.models import Evidence as EvidenceModel, Paper

    paper_id = str(uuid.uuid4())
    evidence_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(Paper(
            id=paper_id,
            title="nullable evidence",
            filename="nullable.pdf",
            storage_key=f"papers/{paper_id}/source.pdf",
            file_size=123,
            file_hash="0" * 64,
            status=PaperStatus.PARSED,
            user_id="demo-user",
        ))
        db.add(EvidenceModel(
            id=evidence_id,
            paper_id=paper_id,
            section_id=None,
            chunk_id=None,
            quoted_text="deterministic nullable evidence",
            page_number=1,
            bbox_x0=None,
            bbox_y0=None,
            bbox_x1=None,
            bbox_y1=None,
            char_start=None,
            char_end=None,
            evidence_type=EvidenceType.TEXT,
        ))
        db.commit()
    finally:
        db.close()

    detail_resp = await db_client.get(f"/api/v1/evidences/{evidence_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == evidence_id
    assert detail["quoted_text"] == "deterministic nullable evidence"
    assert detail["page_number"] == 1
    assert detail["bbox_x0"] is None
    assert detail["bbox_y0"] is None
    assert detail["bbox_x1"] is None
    assert detail["bbox_y1"] is None
    assert detail["char_start"] is None
    assert detail["char_end"] is None
    assert detail["section_id"] is None
    assert detail["chunk_id"] is None
    assert detail["evidence_type"] == "TEXT"


@requires_db
@pytest.mark.asyncio
async def test_evidence_not_found_returns_404(db_client: AsyncClient):
    fake_uuid = str(uuid.uuid4())
    resp = await db_client.get(f"/api/v1/evidences/{fake_uuid}")
    assert resp.status_code == 404


@requires_db
@pytest.mark.asyncio
async def test_page_has_normalized_text_content(db_client: AsyncClient, tmp_path):
    from tests.conftest import create_test_pdf

    pdf_path = create_test_pdf("Testing normalized text content field.", tmp_path=str(tmp_path))
    with open(pdf_path, "rb") as f:
        upload_resp = await db_client.post("/api/v1/papers/upload", files={"file": ("norm_test.pdf", f, "application/pdf")})
    assert upload_resp.status_code == 201
    paper_id = upload_resp.json()["id"]

    status = wait_for_paper_status(paper_id)
    assert status == "PARSED"

    page_resp = await db_client.get(f"/api/v1/papers/{paper_id}/pages/1")
    assert page_resp.status_code == 200
    page_data = page_resp.json()
    assert "normalized_text_content" in page_data
    assert page_data["normalized_text_content"] is not None


@requires_db
@pytest.mark.asyncio
async def test_invalid_status_filter_returns_422(db_client: AsyncClient):
    resp = await db_client.get("/api/v1/papers", params={"status": "INVALID_STATUS"})
    assert resp.status_code == 422


@requires_db
@pytest.mark.asyncio
async def test_dev_db_not_polluted(db_client: AsyncClient, tmp_path, dev_db_count):
    if dev_db_count is None:
        pytest.skip("Cannot connect to dev database")

    from tests.conftest import create_test_pdf

    pdf_path = create_test_pdf("Isolation test.", tmp_path=str(tmp_path))
    with open(pdf_path, "rb") as f:
        resp = await db_client.post("/api/v1/papers/upload", files={"file": ("iso_test.pdf", f, "application/pdf")})
    assert resp.status_code == 201

    wait_for_paper_status(resp.json()["id"])

    dev_url = get_dev_db_url()
    after_count = count_papers_in_db(dev_url)
    assert after_count == dev_db_count, (
        f"Dev database was polluted! Before: {dev_db_count}, After: {after_count}"
    )


@requires_db
@pytest.mark.asyncio
async def test_error_message_is_safe(db_client: AsyncClient, tmp_path):
    from paperlens.core.database import SessionLocal
    from paperlens.models.models import Paper
    from paperlens.core.config import settings

    old = settings.max_page_count
    settings.max_page_count = 0
    try:
        from tests.conftest import create_test_pdf
        pdf_path = create_test_pdf("Force failure.", tmp_path=str(tmp_path))
        with open(pdf_path, "rb") as f:
            resp = await db_client.post("/api/v1/papers/upload", files={"file": ("fail_test.pdf", f, "application/pdf")})
        assert resp.status_code == 201
        paper_id = resp.json()["id"]

        status = wait_for_paper_status(paper_id)
        assert status == "FAILED"

        db = SessionLocal()
        try:
            paper = db.get(Paper, paper_id)
            assert paper is not None
            assert paper.error_message is not None
            unsafe_patterns = [
                "/tmp/", "C:\\", "Traceback", "File ", "SELECT ",
                "postgresql://", "psycopg2", "sqlalchemy",
            ]
            for pattern in unsafe_patterns:
                assert pattern not in paper.error_message, (
                    f"Unsafe pattern '{pattern}' found in error_message: {paper.error_message}"
                )
        finally:
            db.close()

        detail = await db_client.get(f"/api/v1/papers/{paper_id}")
        assert detail.status_code == 200
        error_msg = detail.json().get("error_message", "")
        for pattern in unsafe_patterns:
            assert pattern not in error_msg, (
                f"Unsafe pattern '{pattern}' found in API error_message: {error_msg}"
            )
    finally:
        settings.max_page_count = old


@requires_db
@pytest.mark.asyncio
async def test_error_message_safe_with_injected_exception(db_client: AsyncClient, tmp_path):
    from paperlens.core.database import SessionLocal
    from paperlens.models.models import Paper
    from unittest.mock import patch

    injected_messages = [
        "/tmp/private/source.pdf",
        "C:\\secret\\source.pdf",
        "postgresql://user:password@host/db",
        "SELECT * FROM secret_table",
        "Traceback (most recent call last)",
    ]

    from tests.conftest import create_test_pdf
    pdf_path = create_test_pdf("Injected error test.", tmp_path=str(tmp_path))
    with open(pdf_path, "rb") as f:
        upload_resp = await db_client.post("/api/v1/papers/upload", files={"file": ("inject_test.pdf", f, "application/pdf")})
    assert upload_resp.status_code == 201
    paper_id = upload_resp.json()["id"]

    from paperlens.api.papers import _process_paper
    with patch("paperlens.api.papers.parse_pdf", side_effect=Exception("/tmp/private/source.pdf\nTraceback (most recent call last)\nSELECT * FROM secret_table")):
        _process_paper(paper_id, pdf_path)

    db = SessionLocal()
    try:
        paper = db.get(Paper, paper_id)
        assert paper is not None
        assert paper.error_message is not None
        for pattern in ["/tmp/", "Traceback", "SELECT ", "secret"]:
            assert pattern not in paper.error_message, (
                f"Injected pattern '{pattern}' leaked into error_message: {paper.error_message}"
            )
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
async def test_table_savepoint_degradation(db_client: AsyncClient, tmp_path, caplog):
    from paperlens.core.database import SessionLocal, get_engine
    from paperlens.core.enums import PaperStatus
    from paperlens.models.models import Paper, PaperPage, PaperSection, PaperChunk, PaperTable, Evidence

    test_url = get_test_db_url()
    assert test_url is not None
    actual_url = str(get_engine().url)
    assert "paperlens_test" in actual_url, f"Engine must point to test DB, got: {actual_url}"

    db = SessionLocal()
    try:
        paper_id = str(uuid.uuid4())
        paper = Paper(
            id=paper_id,
            title="table_test",
            filename="table_test.pdf",
            storage_key=f"papers/{paper_id}/source.pdf",
            file_size=100,
            file_hash="abc123",
            status=PaperStatus.PROCESSING,
            user_id="demo-user",
        )
        db.add(paper)
        db.commit()

        fake_result = {
            "pages": [{"page_number": 1, "text_content": "Test", "normalized_text_content": "Test", "width": 612, "height": 792}],
            "sections": [{"section_type": "OTHER", "title": "", "level": 1, "sequence": 1, "start_page": 1, "end_page": 1, "text_content": "Test"}],
            "chunks": [{"section_sequence": 1, "chunk_index": 0, "content": "Test", "char_count": 4, "page_numbers": [1]}],
            "tables": [
                {"page_number": 1, "table_index": 1, "caption": None, "bbox_x0": 72, "bbox_y0": 72, "bbox_x1": 200, "bbox_y1": 200, "structured_data": {"rows": [["a"]]}, "raw_text": "a"},
                {"page_number": 0, "table_index": 2, "caption": None, "bbox_x0": 72, "bbox_y0": 72, "bbox_x1": 200, "bbox_y1": 200, "structured_data": {"rows": [["b"]]}, "raw_text": "b"},
            ],
            "evidences": [{"quoted_text": "Test", "page_number": 1, "bbox_x0": 72, "bbox_y0": 72, "bbox_x1": 200, "bbox_y1": 100, "char_start": 0, "char_end": 4, "evidence_type": "TEXT", "chunk_index": 0}],
        }

        pdf_path = tmp_path / "fake_table_test.pdf"
        pdf_path.write_bytes(b"%PDF-fake")
        from paperlens.api.papers import _process_paper

        caplog.set_level(logging.WARNING, logger="paperlens.api.papers")
        with patch("paperlens.api.papers.parse_pdf", return_value=fake_result):
            _process_paper(paper_id, str(pdf_path))

        db.expire_all()
        paper = db.get(Paper, paper_id)
        assert paper is not None
        assert paper.status == "PARSED", f"Expected PARSED, got {paper.status}: {paper.error_message}"

        pages = db.query(PaperPage).filter(PaperPage.paper_id == paper_id).all()
        assert len(pages) == 1

        sections = db.query(PaperSection).filter(PaperSection.paper_id == paper_id).all()
        assert len(sections) == 1

        chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == paper_id).all()
        assert len(chunks) == 1

        tables = db.query(PaperTable).filter(PaperTable.paper_id == paper_id).all()
        assert len(tables) == 1
        assert tables[0].page_number == 1
        assert tables[0].table_index == 1
        assert tables[0].raw_text == "a"
        assert db.query(PaperTable).filter(
            PaperTable.paper_id == paper_id,
            PaperTable.page_number == 0,
        ).count() == 0

        evidences = db.query(Evidence).filter(Evidence.paper_id == paper_id).all()
        assert len(evidences) == 1
        assert not pdf_path.exists()
        assert any(
            paper_id in record.message and "page=0" in record.message and "table_idx=2" in record.message
            for record in caplog.records
        )
    finally:
        db.close()


def test_cleanup_rejects_non_test_database():
    with pytest.raises(AssertionError, match="Refusing to truncate"):
        truncate_test_tables("postgresql+psycopg2://user:pass@localhost:5432/paperlens")


def test_cleanup_connect_failure_propagates():
    test_url = "postgresql+psycopg2://user:pass@localhost:5432/paperlens_test"
    with patch("psycopg2.connect", side_effect=RuntimeError("connect failed")):
        with pytest.raises(RuntimeError, match="connect failed"):
            truncate_test_tables(test_url)


def test_cleanup_truncate_failure_propagates():
    test_url = "postgresql+psycopg2://user:pass@localhost:5432/paperlens_test"
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.execute.side_effect = RuntimeError("truncate failed")
    with patch("psycopg2.connect", return_value=connection):
        with pytest.raises(RuntimeError, match="truncate failed"):
            truncate_test_tables(test_url)
    cursor.close.assert_called_once_with()
    connection.close.assert_called_once_with()


def test_cleanup_residual_failure_names_table():
    test_url = "postgresql+psycopg2://user:pass@localhost:5432/paperlens_test"
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.fetchone.return_value = (1,)
    with patch("psycopg2.connect", return_value=connection):
        with pytest.raises(AssertionError, match=r"paperlens_test\.finding_evidences: 1 rows"):
            verify_no_test_residuals(test_url)
    cursor.execute.assert_called_once_with('SELECT count(*) FROM "finding_evidences"')
    cursor.close.assert_called_once_with()
    connection.close.assert_called_once_with()
