from __future__ import annotations

import logging
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath

from paperlens.core.config import settings

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    def save(self, storage_key: str, src_path: str) -> None: ...

    @abstractmethod
    def read_path(self, storage_key: str) -> str: ...

    @abstractmethod
    def delete(self, storage_key: str) -> None: ...

    @abstractmethod
    def build_key(self, namespace: str, file_id: str, filename: str) -> str: ...


def _sanitize_filename(filename: str) -> str:
    basename = os.path.basename(filename.replace("\\", "/"))
    return basename


class LocalStorage(StorageBackend):

    def __init__(self, root: str | None = None):
        self._root = Path(root or settings.storage_root).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, storage_key: str) -> Path:
        normalized = storage_key.replace("\\", "/")
        normalized = str(PurePosixPath(normalized))
        resolved = (self._root / normalized).resolve()
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise ValueError(f"路径穿越检测: {storage_key}")
        if resolved == self._root:
            raise ValueError(f"路径穿越检测: {storage_key}")
        return resolved

    def build_key(self, namespace: str, file_id: str, filename: str) -> str:
        return f"{namespace}/{file_id}/source.pdf"

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
            raise FileNotFoundError(f"文件不存在: {storage_key}")
        return str(target)

    def delete(self, storage_key: str) -> None:
        target = self._resolve(storage_key)
        if target.exists():
            target.unlink()


class OBSStorage(StorageBackend):

    def save(self, storage_key: str, src_path: str) -> None:
        raise NotImplementedError("OBS 存储尚未实现")

    def read_path(self, storage_key: str) -> str:
        raise NotImplementedError("OBS 存储尚未实现")

    def delete(self, storage_key: str) -> None:
        raise NotImplementedError("OBS 存储尚未实现")

    def build_key(self, namespace: str, file_id: str, filename: str) -> str:
        return f"{namespace}/{file_id}/source.pdf"


def get_storage() -> StorageBackend:
    if settings.storage_backend == "local":
        return LocalStorage()
    elif settings.storage_backend == "obs":
        return OBSStorage()
    else:
        raise ValueError(f"未知的存储后端: {settings.storage_backend}")
