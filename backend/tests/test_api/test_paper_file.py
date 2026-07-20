import uuid
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest
from fastapi.responses import FileResponse

from paperlens.api import papers as papers_api
from paperlens.models.models import Paper, PaperPage
from paperlens.utils.storage import LocalStorage


class _PaperDb:
    def __init__(self, paper, page=None):
        self.paper = paper
        self.page = page
        self.deleted = None
        self.committed = False

    def get(self, model, paper_id):
        assert model is Paper
        assert paper_id == self.paper.id
        return self.paper

    def delete(self, paper):
        self.deleted = paper

    def commit(self):
        self.committed = True

    def rollback(self):
        self.committed = False

    def query(self, model):
        assert model is PaperPage
        return self

    def filter(self, *args):
        return self

    def first(self):
        return self.page


def test_owner_can_open_original_pdf_inline(tmp_path, monkeypatch):
    paper_id = str(uuid.uuid4())
    source = tmp_path / "source.pdf"
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "original layout")
        document.set_toc([[1, "Original Introduction", 1]])
        document.save(source)
    storage = LocalStorage(str(tmp_path / "storage"))
    storage_key = storage.build_key("papers", paper_id, "论文.pdf")
    storage.save(storage_key, str(source))
    paper = SimpleNamespace(
        id=paper_id,
        user_id="user-1",
        filename="论文.pdf",
        storage_key=storage_key,
    )
    monkeypatch.setattr(papers_api, "get_storage", lambda: storage)

    response = papers_api.get_paper_file(uuid.UUID(paper_id), _PaperDb(paper), "user-1")

    assert isinstance(response, FileResponse)
    assert response.media_type == "application/pdf"
    assert Path(response.path).read_bytes() == source.read_bytes()
    assert response.headers["content-disposition"].startswith("inline;")
    papers_api._remove_materialized_file(response.path)

    page_row = SimpleNamespace(normalized_text_content="original layout")
    db = _PaperDb(paper, page_row)
    image_response = papers_api.get_paper_page_image(uuid.UUID(paper_id), 1, db, "user-1")
    assert image_response.media_type == "image/png"
    assert image_response.body.startswith(b"\x89PNG\r\n\x1a\n")

    text_layer = papers_api.get_paper_page_text_layer(uuid.UUID(paper_id), 1, db, "user-1")
    assert text_layer.page_number == 1
    assert [word.text for word in text_layer.words] == ["original", "layout"]
    assert [(word.char_start, word.char_end) for word in text_layer.words] == [(0, 8), (9, 15)]

    outline_response = papers_api.get_paper_outline(uuid.UUID(paper_id), _PaperDb(paper), "user-1")
    assert [item.model_dump() for item in outline_response.items] == [
        {"title": "Original Introduction", "level": 1, "page_number": 1}
    ]


def test_owner_can_delete_paper_and_storage_object(tmp_path, monkeypatch):
    paper_id = str(uuid.uuid4())
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-delete-test")
    storage = LocalStorage(str(tmp_path / "storage"))
    storage_key = storage.build_key("papers", paper_id, "source.pdf")
    storage.save(storage_key, str(source))
    paper = SimpleNamespace(id=paper_id, user_id="user-1", storage_key=storage_key)
    db = _PaperDb(paper)
    monkeypatch.setattr(papers_api, "get_storage", lambda: storage)

    response = papers_api.delete_paper(uuid.UUID(paper_id), db, "user-1")

    assert response.status_code == 204
    assert db.deleted is paper
    assert db.committed is True
    with pytest.raises(FileNotFoundError):
        with storage.materialize(storage_key):
            pass
