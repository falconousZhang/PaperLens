import os
import pytest
from paperlens.utils.storage import LocalStorage, _sanitize_filename


def test_local_storage_save_and_read(tmp_path):
    storage = LocalStorage(root=str(tmp_path / "store"))
    key = storage.build_key("papers", "abc-123", "test.pdf")
    assert key == "papers/abc-123/source.pdf"

    src = tmp_path / "src.txt"
    src.write_text("hello")
    storage.save(key, str(src))

    read_back = storage.read_path(key)
    assert os.path.exists(read_back)


def test_local_storage_delete(tmp_path):
    storage = LocalStorage(root=str(tmp_path / "store"))
    key = "papers/xyz/source.pdf"
    src = tmp_path / "src.txt"
    src.write_text("hello")
    storage.save(key, str(src))
    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.read_path(key)


def test_local_storage_path_traversal_dotdot(tmp_path):
    storage = LocalStorage(root=str(tmp_path / "store"))
    with pytest.raises(ValueError, match="路径穿越"):
        storage._resolve("../../../etc/passwd")


def test_local_storage_path_traversal_dotdot_backslash(tmp_path):
    storage = LocalStorage(root=str(tmp_path / "store"))
    with pytest.raises(ValueError, match="路径穿越"):
        storage._resolve("..\\..\\store_evil\\file.pdf")


def test_local_storage_path_traversal_absolute(tmp_path):
    storage = LocalStorage(root=str(tmp_path / "store"))
    with pytest.raises(ValueError, match="路径穿越"):
        storage._resolve("/absolute/path/file.pdf")


def test_local_storage_path_traversal_sibling_prefix(tmp_path):
    storage = LocalStorage(root=str(tmp_path / "store"))
    with pytest.raises(ValueError, match="路径穿越"):
        storage._resolve("../store_evil/escaped.pdf")


def test_sanitize_filename_windows_path():
    assert _sanitize_filename("C:\\fake\\paper.pdf") == "paper.pdf"


def test_sanitize_filename_unix_path():
    assert _sanitize_filename("/tmp/secret/file.pdf") == "file.pdf"


def test_sanitize_filename_simple():
    assert _sanitize_filename("paper.pdf") == "paper.pdf"


def test_local_storage_read_nonexistent(tmp_path):
    storage = LocalStorage(root=str(tmp_path / "store"))
    with pytest.raises(FileNotFoundError):
        storage.read_path("nonexistent/file.pdf")


def test_build_key_ignores_user_filename(tmp_path):
    storage = LocalStorage(root=str(tmp_path / "store"))
    key = storage.build_key("papers", "uuid-123", "malicious../../../etc.pdf")
    assert key == "papers/uuid-123/source.pdf"


@pytest.mark.parametrize("filename", ["data.csv", "DATA.XLSX", "legacy.xls"])
def test_experiment_build_key_uses_internal_filename(tmp_path, filename):
    storage = LocalStorage(root=str(tmp_path / "store"))
    extension = filename.rsplit(".", 1)[-1].lower()
    key = storage.build_key("experiment-files", "uuid-456", filename)
    assert key == f"experiment-files/uuid-456/source.{extension}"
    assert filename not in key


def test_experiment_build_key_rejects_unconfirmed_extension(tmp_path):
    storage = LocalStorage(root=str(tmp_path / "store"))
    with pytest.raises(ValueError, match="unsupported"):
        storage.build_key("experiment-files", "uuid-456", "data.xlsm")
