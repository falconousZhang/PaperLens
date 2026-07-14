import asyncio
import csv
import io
import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from paperlens.core.config import settings
from paperlens.core.database import SessionLocal, configure_engine, get_engine
from paperlens.core.enums import PaperStatus, UserRole, UserStatus
from paperlens.main import app
from paperlens.models.models import ExperimentFile, Paper, User
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
        raise RuntimeError("LLMClient must not be called during experiment file upload")


class _FakeEmbeddingClient(EmbeddingClient):
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("EmbeddingClient must not be called during experiment file upload")


def _add_user(db, email: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        email_normalized=email.casefold(),
        display_name=email.split("@", 1)[0],
        password_hash=hash_password("ExpFileTest123!"),
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
        user = _add_user(db, "expfile-owner@example.com")
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


def _storage_root(client: AsyncClient) -> Path:
    value = getattr(client, "_storage_root", None)
    assert value is not None
    return value


def _stored_experiment_objects(client: AsyncClient) -> list[Path]:
    root = _storage_root(client) / "experiment-files"
    return list(root.rglob("source.*")) if root.exists() else []


def _create_parsed_paper(db, user_id: str) -> str:
    paper_id = str(uuid.uuid4())
    db.add(
        Paper(
            id=paper_id,
            title="Experiment Test Paper",
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


@requires_db
class TestExperimentFileUpload:
    async def test_upload_csv_201(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        csv_content = _make_csv_bytes([["model", "accuracy"], ["bert", "0.89"], ["gpt", "0.92"]])
        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("experiment.csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_type"] == "CSV"
        assert data["row_count"] == 2
        assert data["column_count"] == 2
        assert data["duplicate"] is False
        assert "columns_info" in data

    async def test_upload_xlsx_201(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        xlsx_content = _make_xlsx_bytes([["model", "accuracy"], ["bert", 0.89], ["gpt", 0.92]])
        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("experiment.xlsx", xlsx_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_type"] == "XLSX"
        assert data["row_count"] == 2

    async def test_upload_duplicate_200(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        csv_content = _make_csv_bytes([["a", "b"], ["1", "2"]])
        resp1 = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert resp1.status_code == 201

        resp2 = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert resp2.status_code == 200
        assert resp2.json()["duplicate"] is True
        assert resp2.json()["id"] == resp1.json()["id"]

        db = SessionLocal()
        try:
            count = db.query(ExperimentFile).filter(ExperimentFile.paper_id == paper_id).count()
            assert count == 1
        finally:
            db.close()

    async def test_upload_no_token_401(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        csv_content = _make_csv_bytes([["a"], ["1"]])
        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("test.csv", csv_content, "text/csv")},
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401

    async def test_upload_paper_not_found_404(self, db_client: AsyncClient):
        csv_content = _make_csv_bytes([["a"], ["1"]])
        fake_paper_id = str(uuid.uuid4())
        resp = await db_client.post(
            f"/api/v1/papers/{fake_paper_id}/experiment-files/upload",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 404

    async def test_upload_paper_not_parsed_409(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = str(uuid.uuid4())
            db.add(
                Paper(
                    id=paper_id,
                    title="Unparsed Paper",
                    filename=f"{paper_id}.pdf",
                    storage_key=f"papers/{paper_id}/source.pdf",
                    file_size=1000,
                    file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                    status=PaperStatus.PROCESSING,
                    user_id=_user_id(db_client),
                )
            )
            db.flush()
            db.commit()
        finally:
            db.close()

        csv_content = _make_csv_bytes([["a"], ["1"]])
        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 409

    async def test_upload_wrong_extension_415(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 415

    async def test_upload_cross_user_paper_404(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            other_user = _add_user(db, "expfile-other@example.com")
            paper_id = str(uuid.uuid4())
            db.add(
                Paper(
                    id=paper_id,
                    title="Other User Paper",
                    filename=f"{paper_id}.pdf",
                    storage_key=f"papers/{paper_id}/source.pdf",
                    file_size=1000,
                    file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                    status=PaperStatus.PARSED,
                    user_id=other_user.id,
                )
            )
            db.flush()
            db.commit()
        finally:
            db.close()

        csv_content = _make_csv_bytes([["a"], ["1"]])
        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 404

    async def test_upload_admin_other_user_paper_404(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            admin = _add_user(db, "expfile-admin@example.com", role=UserRole.ADMIN)
            other_user = _add_user(db, "expfile-other2@example.com")
            paper_id = str(uuid.uuid4())
            db.add(
                Paper(
                    id=paper_id,
                    title="Other User Paper",
                    filename=f"{paper_id}.pdf",
                    storage_key=f"papers/{paper_id}/source.pdf",
                    file_size=1000,
                    file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                    status=PaperStatus.PARSED,
                    user_id=other_user.id,
                )
            )
            db.flush()
            admin_token, _ = create_session_for_user(db, admin)
            db.commit()
        finally:
            db.close()

        csv_content = _make_csv_bytes([["a"], ["1"]])
        resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("test.csv", csv_content, "text/csv")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


@requires_db
class TestExperimentFileList:
    async def test_list_experiment_files(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        csv_content = _make_csv_bytes([["a", "b"], ["1", "2"]])
        await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )

        resp = await db_client.get(f"/api/v1/papers/{paper_id}/experiment-files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["file_type"] == "CSV"

    async def test_list_pagination(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        for i in range(3):
            csv_content = _make_csv_bytes([[f"col{i}"], [str(i)]])
            await db_client.post(
                f"/api/v1/papers/{paper_id}/experiment-files/upload",
                files={"file": (f"test{i}.csv", csv_content, "text/csv")},
            )

        resp = await db_client.get(
            f"/api/v1/papers/{paper_id}/experiment-files",
            params={"page": 1, "page_size": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_list_no_token_401(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        resp = await db_client.get(
            f"/api/v1/papers/{paper_id}/experiment-files",
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401


@requires_db
class TestExperimentFileDetail:
    async def test_get_experiment_file_detail(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        csv_content = _make_csv_bytes([["model", "score"], ["bert", "0.89"]])
        upload_resp = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        file_id = upload_resp.json()["id"]

        resp = await db_client.get(f"/api/v1/experiment-files/{file_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == file_id
        assert data["file_type"] == "CSV"
        assert data["row_count"] == 1
        assert data["column_count"] == 2
        assert "columns_info" in data
        assert "file_hash" not in data

    async def test_get_nonexistent_file_404(self, db_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await db_client.get(f"/api/v1/experiment-files/{fake_id}")
        assert resp.status_code == 404

    async def test_get_cross_user_file_404(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            other_user = _add_user(db, "expfile-detail-other@example.com")
            paper_id = str(uuid.uuid4())
            db.add(
                Paper(
                    id=paper_id,
                    title="Other Paper",
                    filename=f"{paper_id}.pdf",
                    storage_key=f"papers/{paper_id}/source.pdf",
                    file_size=1000,
                    file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                    status=PaperStatus.PARSED,
                    user_id=other_user.id,
                )
            )
            db.flush()
            exp_file = ExperimentFile(
                id=str(uuid.uuid4()),
                paper_id=paper_id,
                filename="test.csv",
                storage_key=f"experiment-files/{uuid.uuid4()}/source.csv",
                file_size=100,
                file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                file_type="CSV",
                row_count=1,
                column_count=1,
                columns_info={"version": 1, "columns": [{"name": "a", "dtype": "string", "nullable": False, "null_count": 0}]},
                user_id=other_user.id,
            )
            db.add(exp_file)
            db.flush()
            db.commit()
            file_id = exp_file.id
        finally:
            db.close()

        resp = await db_client.get(f"/api/v1/experiment-files/{file_id}")
        assert resp.status_code == 404

    async def test_no_token_experiment_files_401(self, db_client: AsyncClient):
        resp = await db_client.get(
            f"/api/v1/experiment-files/{str(uuid.uuid4())}",
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401


@requires_db
class TestExperimentFileSecurityAndCompensation:
    async def test_real_size_limit_413(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        oversized = b"a" * (settings.max_experiment_file_size_mb * 1024 * 1024 + 1)
        response = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("large.csv", oversized, "text/csv")},
        )
        assert response.status_code == 413
        assert _stored_experiment_objects(db_client) == []

    async def test_magic_mismatch_415(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        response = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("fake.xlsx", b"a,b\n1,2\n", "application/octet-stream")},
        )
        assert response.status_code == 415
        assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"

    async def test_malformed_content_422_and_temp_cleanup(
        self,
        db_client: AsyncClient,
        monkeypatch,
    ):
        from paperlens.services import experiment_file_service

        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        staged_path = _storage_root(db_client) / "known-temp.csv"

        def controlled_mkstemp(prefix: str, suffix: str):
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            return os.open(staged_path, os.O_CREAT | os.O_EXCL | os.O_RDWR), str(staged_path)

        monkeypatch.setattr(experiment_file_service.tempfile, "mkstemp", controlled_mkstemp)
        response = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("bad.csv", b"a,b\n1\n", "text/csv")},
        )
        assert response.status_code == 422
        assert response.json()["error"]["message"] == "实验文件内容或结构无法解析"
        assert staged_path.exists() is False
        assert _stored_experiment_objects(db_client) == []

    async def test_temp_creation_failure_is_safe_500(
        self,
        db_client: AsyncClient,
        monkeypatch,
    ):
        from paperlens.services import experiment_file_service

        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()

        def fail_mkstemp(*args, **kwargs):
            raise OSError("private temp path")

        monkeypatch.setattr(experiment_file_service.tempfile, "mkstemp", fail_mkstemp)
        response = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("data.csv", b"a\n1\n", "text/csv")},
        )
        assert response.status_code == 500
        payload = str(response.json())
        assert "private temp path" not in payload
        assert _stored_experiment_objects(db_client) == []

    async def test_storage_failure_removes_partial_object(
        self,
        db_client: AsyncClient,
        monkeypatch,
    ):
        original_save = LocalStorage.save

        def fail_after_save(self, storage_key: str, src_path: str):
            original_save(self, storage_key, src_path)
            raise RuntimeError("storage private failure")

        monkeypatch.setattr(LocalStorage, "save", fail_after_save)
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        response = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("data.csv", b"a\n1\n", "text/csv")},
        )
        assert response.status_code == 500
        assert "storage private failure" not in str(response.json())
        assert _stored_experiment_objects(db_client) == []
        db = SessionLocal()
        try:
            assert db.query(ExperimentFile).filter_by(paper_id=paper_id).count() == 0
        finally:
            db.close()

    @pytest.mark.parametrize("failure_stage", ["flush", "commit"])
    async def test_database_failure_rolls_back_and_cleans_storage(
        self,
        db_client: AsyncClient,
        monkeypatch,
        failure_stage: str,
    ):
        from sqlalchemy.orm import Session as SqlAlchemySession

        original_flush = SqlAlchemySession.flush
        original_commit = SqlAlchemySession.commit

        def fail_flush(session, *args, **kwargs):
            if any(isinstance(item, ExperimentFile) for item in session.new):
                raise RuntimeError("flush private failure")
            return original_flush(session, *args, **kwargs)

        def fail_commit(session, *args, **kwargs):
            if any(isinstance(item, ExperimentFile) for item in session.identity_map.values()):
                raise RuntimeError("commit private failure")
            return original_commit(session, *args, **kwargs)

        monkeypatch.setattr(
            SqlAlchemySession,
            failure_stage,
            fail_flush if failure_stage == "flush" else fail_commit,
        )
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        response = await db_client.post(
            f"/api/v1/papers/{paper_id}/experiment-files/upload",
            files={"file": ("data.csv", b"a\n1\n", "text/csv")},
        )
        assert response.status_code == 500
        assert "private failure" not in str(response.json())
        assert _stored_experiment_objects(db_client) == []
        db = SessionLocal()
        try:
            assert db.query(ExperimentFile).filter_by(paper_id=paper_id).count() == 0
        finally:
            db.close()

    async def test_concurrent_duplicate_has_one_row_and_object(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            paper_id = _create_parsed_paper(db, _user_id(db_client))
        finally:
            db.close()
        content = _make_csv_bytes([["name", "score"], ["model", "0.9"]])

        async def upload_once():
            return await db_client.post(
                f"/api/v1/papers/{paper_id}/experiment-files/upload",
                files={"file": ("same.csv", content, "text/csv")},
            )

        first, second = await asyncio.gather(upload_once(), upload_once())
        assert sorted([first.status_code, second.status_code]) == [200, 201]
        assert first.json()["id"] == second.json()["id"]
        db = SessionLocal()
        try:
            assert db.query(ExperimentFile).filter_by(paper_id=paper_id).count() == 1
        finally:
            db.close()
        assert len(_stored_experiment_objects(db_client)) == 1

    async def test_list_cross_user_is_404(self, db_client: AsyncClient):
        db = SessionLocal()
        try:
            other = _add_user(db, "expfile-list-other@example.com")
            paper_id = _create_parsed_paper(db, other.id)
        finally:
            db.close()
        response = await db_client.get(f"/api/v1/papers/{paper_id}/experiment-files")
        assert response.status_code == 404

    async def test_settings_and_clients_remain_offline(self, db_client: AsyncClient):
        assert settings.llm_backend == "mock"
        assert settings.embedding_provider == "mock"
        assert settings.llm_api_key is None
        assert settings.embedding_api_key is None
