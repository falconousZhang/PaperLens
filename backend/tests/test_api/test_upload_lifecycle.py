import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks

from paperlens.api.papers import upload_paper
from paperlens.core.config import settings
from paperlens.core.errors import AppError


PDF_BYTES = b"%PDF-1.4\nPaperLens lifecycle test"


def _upload_file(filename: str = "paper.pdf", side_effect=None) -> AsyncMock:
    upload = AsyncMock()
    upload.filename = filename
    upload.read = AsyncMock(side_effect=side_effect or [PDF_BYTES, b""])
    upload.close = AsyncMock()
    return upload


def _db_session() -> MagicMock:
    db = MagicMock()

    def refresh(paper):
        paper.created_at = datetime.datetime(2026, 7, 13, tzinfo=datetime.timezone.utc)

    db.refresh.side_effect = refresh
    return db


def _storage() -> MagicMock:
    storage = MagicMock()
    storage.build_key.return_value = "papers/test-id/source.pdf"
    return storage


@pytest.fixture
def tracked_tempfiles(tmp_path):
    import tempfile

    original = tempfile.NamedTemporaryFile
    handles = []

    def create(*args, **kwargs):
        kwargs["dir"] = tmp_path
        handle = original(*args, **kwargs)
        handles.append(handle)
        return handle

    return create, handles


def _assert_tempfiles_released(handles, *, paths_exist: bool):
    assert handles
    for handle in handles:
        assert handle.closed
        assert Path(handle.name).exists() is paths_exist


@pytest.mark.asyncio
async def test_non_pdf_extension_closes_upload_once():
    upload = _upload_file(filename="paper.txt")

    with pytest.raises(AppError) as exc_info:
        await upload_paper(upload, BackgroundTasks(), _db_session())

    assert exc_info.value.code == "INVALID_FILE_TYPE"
    upload.read.assert_not_called()
    upload.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_invalid_pdf_magic_closes_and_removes_temp(tracked_tempfiles):
    create_temp, handles = tracked_tempfiles
    upload = _upload_file(side_effect=[b"not a pdf", b""])

    with patch("paperlens.api.papers.tempfile.NamedTemporaryFile", side_effect=create_temp):
        with pytest.raises(AppError) as exc_info:
            await upload_paper(upload, BackgroundTasks(), _db_session())

    assert exc_info.value.code == "INVALID_FILE_TYPE"
    upload.close.assert_awaited_once_with()
    _assert_tempfiles_released(handles, paths_exist=False)


@pytest.mark.asyncio
async def test_oversized_upload_closes_and_removes_temp(tracked_tempfiles):
    create_temp, handles = tracked_tempfiles
    upload = _upload_file()

    with patch.object(settings, "max_pdf_size_mb", 0), \
         patch("paperlens.api.papers.tempfile.NamedTemporaryFile", side_effect=create_temp):
        with pytest.raises(AppError) as exc_info:
            await upload_paper(upload, BackgroundTasks(), _db_session())

    assert exc_info.value.code == "FILE_TOO_LARGE"
    upload.close.assert_awaited_once_with()
    _assert_tempfiles_released(handles, paths_exist=False)


@pytest.mark.asyncio
async def test_read_failure_closes_handle_upload_and_removes_temp(tracked_tempfiles):
    create_temp, handles = tracked_tempfiles
    upload = _upload_file(side_effect=OSError("read failed"))

    with patch("paperlens.api.papers.tempfile.NamedTemporaryFile", side_effect=create_temp):
        with pytest.raises(AppError) as exc_info:
            await upload_paper(upload, BackgroundTasks(), _db_session())

    assert exc_info.value.code == "UPLOAD_FAILED"
    upload.close.assert_awaited_once_with()
    _assert_tempfiles_released(handles, paths_exist=False)


@pytest.mark.asyncio
async def test_hash_failure_closes_upload_and_removes_temp(tracked_tempfiles):
    create_temp, handles = tracked_tempfiles
    upload = _upload_file()

    with patch("paperlens.api.papers.tempfile.NamedTemporaryFile", side_effect=create_temp), \
         patch("paperlens.api.papers.compute_file_hash", side_effect=RuntimeError("hash failed")):
        with pytest.raises(AppError) as exc_info:
            await upload_paper(upload, BackgroundTasks(), _db_session())

    assert exc_info.value.code == "UPLOAD_FAILED"
    upload.close.assert_awaited_once_with()
    _assert_tempfiles_released(handles, paths_exist=False)


@pytest.mark.asyncio
async def test_storage_save_failure_attempts_delete_and_releases_resources(tracked_tempfiles):
    create_temp, handles = tracked_tempfiles
    upload = _upload_file()
    storage = _storage()
    storage.save.side_effect = RuntimeError("save failed")

    with patch("paperlens.api.papers.tempfile.NamedTemporaryFile", side_effect=create_temp), \
         patch("paperlens.api.papers.get_storage", return_value=storage):
        with pytest.raises(AppError) as exc_info:
            await upload_paper(upload, BackgroundTasks(), _db_session())

    assert exc_info.value.code == "UPLOAD_FAILED"
    storage.delete.assert_called_once_with("papers/test-id/source.pdf")
    upload.close.assert_awaited_once_with()
    _assert_tempfiles_released(handles, paths_exist=False)


@pytest.mark.asyncio
async def test_paper_construction_failure_rolls_back_storage(tracked_tempfiles):
    create_temp, handles = tracked_tempfiles
    upload = _upload_file()
    storage = _storage()
    db = _db_session()

    with patch("paperlens.api.papers.tempfile.NamedTemporaryFile", side_effect=create_temp), \
         patch("paperlens.api.papers.get_storage", return_value=storage), \
         patch("paperlens.api.papers.Paper", side_effect=RuntimeError("paper construction failed")):
        with pytest.raises(AppError) as exc_info:
            await upload_paper(upload, BackgroundTasks(), db)

    assert exc_info.value.code == "UPLOAD_FAILED"
    db.add.assert_not_called()
    storage.delete.assert_called_once_with("papers/test-id/source.pdf")
    upload.close.assert_awaited_once_with()
    _assert_tempfiles_released(handles, paths_exist=False)


@pytest.mark.asyncio
async def test_commit_failure_rolls_back_storage_and_temp(tracked_tempfiles):
    create_temp, handles = tracked_tempfiles
    upload = _upload_file()
    storage = _storage()
    db = _db_session()
    db.commit.side_effect = RuntimeError("commit failed")

    with patch("paperlens.api.papers.tempfile.NamedTemporaryFile", side_effect=create_temp), \
         patch("paperlens.api.papers.get_storage", return_value=storage):
        with pytest.raises(AppError) as exc_info:
            await upload_paper(upload, BackgroundTasks(), db)

    assert exc_info.value.code == "UPLOAD_FAILED"
    db.rollback.assert_called_once_with()
    storage.delete.assert_called_once_with("papers/test-id/source.pdf")
    upload.close.assert_awaited_once_with()
    _assert_tempfiles_released(handles, paths_exist=False)


@pytest.mark.asyncio
async def test_background_registration_failure_rolls_back_storage_and_temp(tracked_tempfiles):
    create_temp, handles = tracked_tempfiles
    upload = _upload_file()
    storage = _storage()
    db = _db_session()
    tasks = BackgroundTasks()
    tasks.add_task = MagicMock(side_effect=RuntimeError("task registration failed"))

    with patch("paperlens.api.papers.tempfile.NamedTemporaryFile", side_effect=create_temp), \
         patch("paperlens.api.papers.get_storage", return_value=storage):
        with pytest.raises(AppError) as exc_info:
            await upload_paper(upload, tasks, db)

    assert exc_info.value.code == "UPLOAD_FAILED"
    db.commit.assert_not_called()
    db.rollback.assert_called_once_with()
    storage.delete.assert_called_once_with("papers/test-id/source.pdf")
    upload.close.assert_awaited_once_with()
    _assert_tempfiles_released(handles, paths_exist=False)


@pytest.mark.asyncio
async def test_success_transfers_temp_and_storage_ownership(tracked_tempfiles):
    create_temp, handles = tracked_tempfiles
    upload = _upload_file()
    storage = _storage()
    db = _db_session()
    tasks = BackgroundTasks()

    with patch("paperlens.api.papers.tempfile.NamedTemporaryFile", side_effect=create_temp), \
         patch("paperlens.api.papers.get_storage", return_value=storage):
        response = await upload_paper(upload, tasks, db)

    assert response.status == "PROCESSING"
    db.flush.assert_called_once_with()
    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()
    storage.delete.assert_not_called()
    assert len(tasks.tasks) == 1
    upload.close.assert_awaited_once_with()
    _assert_tempfiles_released(handles, paths_exist=True)
