import os
import pytest
import fitz

os.environ.setdefault(
    "PAPERLENS_JWT_SECRET",
    "paperlens-test-only-secret-never-use-outside-tests-2026",
)
os.environ["PAPERLENS_LLM_BACKEND"] = "mock"
os.environ["PAPERLENS_LLM_BASE_URL"] = "https://api.example.invalid/v2"
os.environ["PAPERLENS_LLM_MODEL"] = "offline-test-model"
os.environ.pop("PAPERLENS_LLM_API_KEY", None)
os.environ["PAPERLENS_EMBEDDING_PROVIDER"] = "mock"
os.environ["PAPERLENS_EMBEDDING_BASE_URL"] = "https://api.example.invalid/v1"
os.environ["PAPERLENS_EMBEDDING_MODEL"] = "offline-test-embedding"
os.environ.pop("PAPERLENS_EMBEDDING_API_KEY", None)

from tests.db_helpers import get_test_db_url, parse_db_name, assert_test_database

_test_db_url = get_test_db_url()
if _test_db_url:
    os.environ["PAPERLENS_DATABASE_URL"] = _test_db_url

assert_test_database()


def create_test_pdf(text: str, pages: int = 1, tmp_path: str | None = None) -> str:
    if tmp_path is None:
        tmp_path = pytest.ensuretemp("paperlens").strpath
    os.makedirs(tmp_path, exist_ok=True)
    path = os.path.join(tmp_path, "test.pdf")
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), text if pages == 1 else f"{text} - Page {i+1}")
    doc.save(path)
    doc.close()
    return path


def create_multipage_pdf(page_texts: list[str], tmp_path: str) -> str:
    os.makedirs(tmp_path, exist_ok=True)
    path = os.path.join(tmp_path, "multipage.pdf")
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()
    return path


def create_scanned_pdf(tmp_path: str) -> str:
    os.makedirs(tmp_path, exist_ok=True)
    path = os.path.join(tmp_path, "scanned.pdf")
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


def create_special_chars_pdf(tmp_path: str) -> str:
    os.makedirs(tmp_path, exist_ok=True)
    path = os.path.join(tmp_path, "special.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Text with  multiple   spaces\nand\ttabs\nand <angle> & ampersand")
    doc.save(path)
    doc.close()
    return path


def create_duplicate_prefix_pdf(tmp_path: str) -> str:
    os.makedirs(tmp_path, exist_ok=True)
    path = os.path.join(tmp_path, "dup_prefix.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Introduction to machine learning")
    page.insert_text((72, 120), "Introduction to deep learning")
    doc.save(path)
    doc.close()
    return path
