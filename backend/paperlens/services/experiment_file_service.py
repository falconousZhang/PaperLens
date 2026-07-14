from __future__ import annotations

import datetime
import hashlib
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from paperlens.core.config import settings
from paperlens.core.enums import ExperimentFileType, PaperStatus
from paperlens.core.errors import AppError
from paperlens.models.models import ExperimentFile, Paper
from paperlens.services.experiment_file_parser import (
    ParseError,
    parse_experiment_file,
    validate_container,
    validate_filename_and_type,
)
from paperlens.utils.storage import StorageBackend, get_storage


logger = logging.getLogger(__name__)
_UPLOAD_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class ExperimentFileRecord:
    id: str
    paper_id: str
    filename: str
    file_type: ExperimentFileType
    file_size: int
    row_count: int
    column_count: int
    columns_info: dict
    created_at: datetime.datetime


def validate_upload_filename(filename: str) -> tuple[str, ExperimentFileType]:
    try:
        return validate_filename_and_type(filename)
    except ParseError as exc:
        raise AppError(
            "INVALID_FILE_TYPE",
            "仅支持有效的 CSV、XLSX 或 XLS 文件",
            415,
        ) from exc


async def stage_upload_to_temp(
    upload: UploadFile,
    file_type: ExperimentFileType,
) -> tuple[str, int]:
    max_bytes = settings.max_experiment_file_size_mb * 1024 * 1024
    suffix = f".{file_type.value.casefold()}"
    path: str | None = None
    size = 0
    try:
        descriptor, path = tempfile.mkstemp(prefix="paperlens-experiment-", suffix=suffix)
        with os.fdopen(descriptor, "wb") as target:
            while True:
                chunk = await upload.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise AppError(
                        "FILE_TOO_LARGE",
                        f"实验文件超过 {settings.max_experiment_file_size_mb}MB 限制",
                        413,
                    )
                target.write(chunk)
        if size == 0:
            raise AppError("INVALID_FILE_TYPE", "实验文件不能为空", 415)
        return path, size
    except AppError:
        cleanup_temp_file(path)
        raise
    except Exception as exc:
        cleanup_temp_file(path)
        raise AppError("UPLOAD_FAILED", "上传失败，请稍后重试", 500) from exc
    except BaseException:
        cleanup_temp_file(path)
        raise


def cleanup_temp_file(path: str | None) -> None:
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except Exception as exc:
        logger.warning(
            "experiment temp cleanup failed error_type=%s",
            type(exc).__name__,
        )


def compute_file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(_UPLOAD_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _to_record(exp_file: ExperimentFile) -> ExperimentFileRecord:
    return ExperimentFileRecord(
        id=exp_file.id,
        paper_id=exp_file.paper_id,
        filename=exp_file.filename,
        file_type=ExperimentFileType(exp_file.file_type),
        file_size=exp_file.file_size,
        row_count=exp_file.row_count,
        column_count=exp_file.column_count,
        columns_info=exp_file.columns_info,
        created_at=exp_file.created_at,
    )


def _find_duplicate(
    db: Session,
    user_id: str,
    paper_id: str,
    file_hash: str,
) -> ExperimentFile | None:
    return (
        db.query(ExperimentFile)
        .filter(
            ExperimentFile.user_id == user_id,
            ExperimentFile.paper_id == paper_id,
            ExperimentFile.file_hash == file_hash,
        )
        .first()
    )


def _rollback(db: Session) -> None:
    try:
        db.rollback()
    except Exception as exc:
        logger.warning(
            "experiment upload rollback failed error_type=%s",
            type(exc).__name__,
        )


def _delete_unowned_object(storage: StorageBackend, storage_key: str) -> None:
    try:
        storage.delete(storage_key)
    except Exception as exc:
        logger.warning(
            "experiment object cleanup failed object_key=%s error_type=%s",
            storage_key,
            type(exc).__name__,
        )


def _map_parse_error(exc: ParseError) -> AppError:
    if exc.kind == "type":
        return AppError(
            "INVALID_FILE_TYPE",
            "文件类型或内容与扩展名不匹配",
            415,
        )
    if exc.kind == "size":
        return AppError(
            "FILE_TOO_LARGE",
            "实验文件内容超过安全解析限制",
            413,
        )
    return AppError(
        "UNPARSABLE_CONTENT",
        "实验文件内容或结构无法解析",
        422,
    )


def upload_experiment_file(
    source_path: str,
    filename: str,
    file_type: ExperimentFileType,
    paper_id: str,
    user_id: str,
    db: Session,
    storage: StorageBackend | None = None,
) -> tuple[ExperimentFileRecord, bool]:
    storage = storage or get_storage()
    paper = db.get(Paper, paper_id)
    if paper is None or paper.user_id != user_id:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    if paper.status != PaperStatus.PARSED:
        raise AppError("PAPER_NOT_PARSED", "论文尚未解析完成，无法上传实验文件", 409)

    try:
        path = validate_container(source_path, file_type)
        file_hash = compute_file_hash(path)
        parse_result = parse_experiment_file(path, file_type)
        file_size = path.stat().st_size
    except ParseError as exc:
        raise _map_parse_error(exc) from exc
    except OSError as exc:
        raise AppError("UPLOAD_FAILED", "上传失败，请稍后重试", 500) from exc

    existing = _find_duplicate(db, user_id, paper_id, file_hash)
    if existing is not None:
        return _to_record(existing), True

    file_id = str(uuid.uuid4())
    storage_key = storage.build_key("experiment-files", file_id, filename)
    save_attempted = False
    try:
        save_attempted = True
        storage.save(storage_key, str(path))
        exp_file = ExperimentFile(
            id=file_id,
            paper_id=paper_id,
            filename=filename,
            storage_key=storage_key,
            file_size=file_size,
            file_hash=file_hash,
            file_type=parse_result.file_type.value,
            row_count=parse_result.row_count,
            column_count=parse_result.column_count,
            columns_info=parse_result.columns_info,
            user_id=user_id,
        )
        db.add(exp_file)
        db.flush()
        db.refresh(exp_file)
        record = _to_record(exp_file)
        db.commit()
        return record, False
    except IntegrityError as exc:
        _rollback(db)
        if save_attempted:
            _delete_unowned_object(storage, storage_key)
        try:
            winner = _find_duplicate(db, user_id, paper_id, file_hash)
        except Exception:
            _rollback(db)
            winner = None
        if winner is not None:
            return _to_record(winner), True
        logger.warning(
            "experiment upload integrity failure error_type=%s",
            type(exc).__name__,
        )
        raise AppError("UPLOAD_FAILED", "上传失败，请稍后重试", 500) from exc
    except AppError:
        _rollback(db)
        if save_attempted:
            _delete_unowned_object(storage, storage_key)
        raise
    except Exception as exc:
        _rollback(db)
        committed = None
        try:
            committed = _find_duplicate(db, user_id, paper_id, file_hash)
        except Exception:
            _rollback(db)
        if committed is not None and committed.id == file_id:
            return _to_record(committed), False
        if save_attempted:
            _delete_unowned_object(storage, storage_key)
        logger.warning(
            "experiment upload failed error_type=%s",
            type(exc).__name__,
        )
        raise AppError("UPLOAD_FAILED", "上传失败，请稍后重试", 500) from exc
