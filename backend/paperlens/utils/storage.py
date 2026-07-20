from __future__ import annotations

import logging
import os
import re
import shutil
import ssl
import tempfile
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Generator

from paperlens.core.config import settings

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    def save(self, storage_key: str, src_path: str) -> None: ...

    @abstractmethod
    def delete(self, storage_key: str) -> None: ...

    @abstractmethod
    def build_key(self, namespace: str, file_id: str, filename: str) -> str: ...

    @abstractmethod
    @contextmanager
    def materialize(self, storage_key: str) -> Generator[str, None, None]: ...

    def read_path(self, storage_key: str) -> str:
        raise NotImplementedError("该存储后端不提供持久本地路径")

    def close(self) -> None:
        pass


def _sanitize_filename(filename: str) -> str:
    basename = os.path.basename(filename.replace("\\", "/"))
    return basename


def _experiment_storage_key(namespace: str, file_id: str, filename: str) -> str:
    extension = os.path.splitext(filename)[1].casefold()
    allowed = {".csv": "csv", ".xlsx": "xlsx", ".xls": "xls"}
    if extension not in allowed:
        raise ValueError("unsupported experiment file extension")
    return f"{namespace}/{file_id}/source.{allowed[extension]}"


_FORBIDDEN_KEY_PATTERN = re.compile(r"[\x00-\x1f\x7f]")


def _validate_storage_key(key: str) -> None:
    if not isinstance(key, str) or not key or key != key.strip():
        raise ValueError("路径穿越检测：存储 key 无效")
    if key.startswith("/"):
        raise ValueError("路径穿越检测：存储 key 无效")
    if "\\" in key:
        raise ValueError("路径穿越检测：存储 key 无效")
    segments = key.split("/")
    if any(not seg or seg in (".", "..") for seg in segments):
        raise ValueError("路径穿越检测：存储 key 无效")
    if _FORBIDDEN_KEY_PATTERN.search(key):
        raise ValueError("路径穿越检测：存储 key 无效")
    if len(key) > 1024:
        raise ValueError("路径穿越检测：存储 key 无效")


def _build_storage_key(namespace: str, file_id: str, filename: str) -> str:
    if namespace == "papers":
        key = f"{namespace}/{file_id}/source.pdf"
    elif namespace == "experiment-files":
        key = _experiment_storage_key(namespace, file_id, filename)
    else:
        key = f"{namespace}/{file_id}/{_sanitize_filename(filename)}"
    _validate_storage_key(key)
    return key


class LocalStorage(StorageBackend):

    def __init__(self, root: str | None = None):
        self._root = Path(root or settings.storage_root).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, storage_key: str) -> Path:
        _validate_storage_key(storage_key)
        normalized = str(PurePosixPath(storage_key))
        resolved = (self._root / normalized).resolve()
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise ValueError("存储路径无效")
        if resolved == self._root:
            raise ValueError("存储路径无效")
        return resolved

    def build_key(self, namespace: str, file_id: str, filename: str) -> str:
        return _build_storage_key(namespace, file_id, filename)

    def save(self, storage_key: str, src_path: str) -> None:
        target = self._resolve(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src_path, target)
        except Exception:
            if target.exists():
                target.unlink()
            raise

    def read_path(self, storage_key: str) -> str:
        target = self._resolve(storage_key)
        if not target.exists():
            raise FileNotFoundError("文件不存在")
        return str(target)

    @contextmanager
    def materialize(self, storage_key: str) -> Generator[str, None, None]:
        yield self.read_path(storage_key)

    def delete(self, storage_key: str) -> None:
        target = self._resolve(storage_key)
        if target.exists():
            target.unlink()


class OBSStorage(StorageBackend):

    def __init__(self, client=None, config=None) -> None:
        self._config = config or settings
        if self._config.obs_prefix:
            _validate_storage_key(self._config.obs_prefix)
        self._client = client or self._create_client()
        self._bucket = self._config.obs_bucket
        self._prefix = self._config.obs_prefix
        self._sse_mode = self._config.obs_sse_mode
        self._kms_key_id = self._config.obs_kms_key_id
        self._tmp_dir = self._config.obs_download_tmp_dir or None

    def _create_client(self):
        from obs import ObsClient

        ca_bundle = self._config.obs_ca_bundle or ssl.get_default_verify_paths().cafile
        if not ca_bundle or not Path(ca_bundle).is_file():
            raise OSError("OBS CA 证书不可用")
        kwargs = {
            "server": self._config.obs_endpoint,
            "long_conn_mode": True,
            "timeout": self._config.obs_timeout_seconds,
            "max_retry_count": 3,
            "max_redirect_count": 3,
            "ssl_verify": ca_bundle,
        }
        if self._config.obs_credential_mode == "ENV":
            kwargs.update(
                access_key_id=self._config.obs_access_key_id.get_secret_value(),
                secret_access_key=self._config.obs_secret_access_key.get_secret_value(),
                security_token=(
                    self._config.obs_security_token.get_secret_value()
                    if self._config.obs_security_token
                    else None
                ),
            )
        else:
            kwargs["security_provider_policy"] = "ECS"
        return ObsClient(**kwargs)

    def _object_key(self, storage_key: str) -> str:
        _validate_storage_key(storage_key)
        if self._prefix:
            return f"{self._prefix}/{storage_key}"
        return storage_key

    def _put_headers(self):
        from obs import HeadPermission, PutObjectHeader, SseKmsHeader

        headers = PutObjectHeader()
        headers.acl = HeadPermission.PRIVATE
        headers.sseHeader = SseKmsHeader(
            encryption="kms" if self._sse_mode == "KMS" else "AES256",
            key=self._kms_key_id if self._sse_mode == "KMS" else None,
        )
        return headers

    def build_key(self, namespace: str, file_id: str, filename: str) -> str:
        return _build_storage_key(namespace, file_id, filename)

    def save(self, storage_key: str, src_path: str) -> None:
        obj_key = self._object_key(storage_key)
        src = Path(src_path)
        if not src.is_file() or src.is_symlink():
            raise ValueError("source path is not a regular file")
        try:
            resp = self._client.putFile(
                self._bucket,
                obj_key,
                file_path=str(src),
                headers=self._put_headers(),
            )
        except Exception as exc:
            logger.error("stage=obs_save_failed error_type=%s", type(exc).__name__)
            raise _storage_error() from exc
        status = getattr(resp, "status", 0)
        if not isinstance(status, int) or not 200 <= status < 300:
            logger.error("stage=obs_save_failed status_class=non_2xx")
            raise _storage_error()

    @contextmanager
    def materialize(self, storage_key: str) -> Generator[str, None, None]:
        obj_key = self._object_key(storage_key)
        try:
            tmp_dir = Path(self._tmp_dir or tempfile.gettempdir()).resolve()
            tmp_dir.mkdir(parents=True, exist_ok=True)
            handle = tempfile.NamedTemporaryFile(dir=tmp_dir, prefix="paperlens_obs_", delete=False)
            tmp_path = handle.name
            handle.close()
            os.chmod(tmp_path, 0o600)
        except Exception as exc:
            logger.error("stage=obs_tempfile_failed error_type=%s", type(exc).__name__)
            raise _storage_error() from exc
        try:
            try:
                resp = self._client.getFile(self._bucket, obj_key, downloadPath=tmp_path)
            except Exception as exc:
                logger.error("stage=obs_download_failed error_type=%s", type(exc).__name__)
                raise _storage_error() from exc
            status = getattr(resp, "status", 0)
            if not isinstance(status, int) or not 200 <= status < 300:
                logger.error("stage=obs_download_failed status_class=non_2xx")
                raise _storage_error()
            if not Path(tmp_path).is_file():
                raise _storage_error()
            yield tmp_path
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def delete(self, storage_key: str) -> None:
        obj_key = self._object_key(storage_key)
        try:
            resp = self._client.deleteObject(self._bucket, obj_key)
        except Exception as exc:
            logger.error("stage=obs_delete_failed error_type=%s", type(exc).__name__)
            raise _storage_error() from exc
        status = getattr(resp, "status", 0)
        if not isinstance(status, int) or not 200 <= status < 300:
            logger.error("stage=obs_delete_failed status_class=non_2xx")
            raise _storage_error()

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass


def _storage_error() -> OSError:
    return OSError("存储操作失败")


_storage_instance: StorageBackend | None = None
_storage_lock = threading.RLock()


def get_storage() -> StorageBackend:
    global _storage_instance
    with _storage_lock:
        if _storage_instance is None:
            if settings.storage_backend == "local":
                _storage_instance = LocalStorage()
            elif settings.storage_backend == "obs":
                _storage_instance = OBSStorage()
            else:
                raise ValueError("未知的存储后端")
        return _storage_instance


def close_storage() -> None:
    global _storage_instance
    with _storage_lock:
        instance = _storage_instance
        _storage_instance = None
    if instance is not None:
        instance.close()
