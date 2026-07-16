import datetime
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from paperlens.core.database import SessionLocal
from paperlens.core.enums import PaperStatus, UserRole, UserStatus
from paperlens.main import app
from paperlens.models.models import (
    Evidence,
    Paper,
    PaperBookmark,
    PaperHighlight,
    PaperKnowledgeCard,
    PaperLibraryEntry,
    PaperNote,
    PaperPage,
    User,
)
from paperlens.services.auth_service import create_session_for_user
from paperlens.services.password_service import hash_password
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


def _add_user(db, email: str) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        email_normalized=email.casefold(),
        display_name=email.split("@", 1)[0],
        password_hash=hash_password("LibTest123!"),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )
    db.add(user)
    db.flush()
    return user


def _add_parsed_paper(db, user_id: str, title: str = "Lib Test Paper", page_count: int = 3) -> Paper:
    paper = Paper(
        id=str(uuid.uuid4()),
        title=title,
        filename="test.pdf",
        storage_key="test-key",
        file_size=1024,
        file_hash="d" * 64,
        page_count=page_count,
        status=PaperStatus.PARSED,
        user_id=user_id,
    )
    db.add(paper)
    db.flush()
    return paper


def _add_page(db, paper_id: str, page_number: int = 1, text: str = "Hello world this is test content for highlights.") -> PaperPage:
    page = PaperPage(
        id=str(uuid.uuid4()),
        paper_id=paper_id,
        page_number=page_number,
        text_content=text,
        normalized_text_content=text,
    )
    db.add(page)
    db.flush()
    return page


def _make_token(user_id: str) -> str:
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        token, _ = create_session_for_user(db, user)
        db.commit()
        return token
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _setup_db():
    test_url = get_test_db_url()
    if not test_url:
        if is_test_db_required():
            pytest.skip("PAPERLENS_REQUIRE_TEST_DB=true but no test DB URL")
        yield
        return
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    yield
    truncate_test_tables(test_url)
    verify_no_test_residuals(test_url)


@requires_db
async def test_library_list_defaults():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-default@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/library/papers", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["reading_status"] == "TO_READ"
    assert item["favorite"] is False
    assert item["progress_percent"] == 0


@requires_db
async def test_patch_library_entry():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-patch@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/papers/{paper_id}/library-entry",
            json={"reading_status": "READING", "favorite": True, "collection_name": "ML Papers"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reading_status"] == "READING"
    assert data["favorite"] is True
    assert data["collection_name"] == "ML Papers"


@requires_db
async def test_patch_reading_progress():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-progress@example.com")
        paper = _add_parsed_paper(db, user.id, page_count=10)
        _add_page(db, paper.id, page_number=5)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/papers/{paper_id}/reading-progress",
            json={"page_number": 5},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reading_status"] == "READING"
    assert data["last_page"] == 5
    assert data["furthest_page"] == 5
    assert data["progress_percent"] == 50


@requires_db
async def test_create_highlight():
    db = SessionLocal()
    try:
        user = _add_user(db, "hl-create@example.com")
        paper = _add_parsed_paper(db, user.id)
        from paperlens.models.models import PaperPage
        page = PaperPage(
            id=str(uuid.uuid4()),
            paper_id=paper.id,
            page_number=1,
            text_content="This is a test sentence for highlighting.",
            normalized_text_content="This is a test sentence for highlighting.",
        )
        db.add(page)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/highlights",
            json={"page_number": 1, "char_start": 0, "char_end": 4, "color": "YELLOW"},
            headers=_auth(token),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["quoted_text"] == "This"
    assert data["color"] == "YELLOW"


@requires_db
async def test_list_highlights():
    db = SessionLocal()
    try:
        user = _add_user(db, "hl-list@example.com")
        paper = _add_parsed_paper(db, user.id)
        from paperlens.models.models import PaperPage
        page = PaperPage(
            id=str(uuid.uuid4()),
            paper_id=paper.id,
            page_number=1,
            text_content="Hello world",
            normalized_text_content="Hello world",
        )
        db.add(page)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            f"/api/v1/papers/{paper_id}/highlights",
            json={"page_number": 1, "char_start": 0, "char_end": 5, "color": "GREEN"},
            headers=_auth(token),
        )
        resp = await client.get(
            f"/api/v1/papers/{paper_id}/highlights",
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


@requires_db
async def test_delete_highlight():
    db = SessionLocal()
    try:
        user = _add_user(db, "hl-del@example.com")
        paper = _add_parsed_paper(db, user.id)
        from paperlens.models.models import PaperPage
        page = PaperPage(
            id=str(uuid.uuid4()),
            paper_id=paper.id,
            page_number=1,
            text_content="Test text",
            normalized_text_content="Test text",
        )
        db.add(page)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            f"/api/v1/papers/{paper_id}/highlights",
            json={"page_number": 1, "char_start": 0, "char_end": 4, "color": "YELLOW"},
            headers=_auth(token),
        )
        hl_id = create_resp.json()["id"]
        resp = await client.delete(
            f"/api/v1/highlights/{hl_id}",
            headers=_auth(token),
        )
    assert resp.status_code == 204


@requires_db
async def test_create_bookmark():
    db = SessionLocal()
    try:
        user = _add_user(db, "bm-create@example.com")
        paper = _add_parsed_paper(db, user.id)
        _add_page(db, paper.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/bookmarks",
            json={"page_number": 1, "label": "Important"},
            headers=_auth(token),
        )
    assert resp.status_code == 201
    assert resp.json()["label"] == "Important"


@requires_db
async def test_bookmark_duplicate():
    db = SessionLocal()
    try:
        user = _add_user(db, "bm-dup@example.com")
        paper = _add_parsed_paper(db, user.id)
        _add_page(db, paper.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp1 = await client.post(
            f"/api/v1/papers/{paper_id}/bookmarks",
            json={"page_number": 1},
            headers=_auth(token),
        )
        resp2 = await client.post(
            f"/api/v1/papers/{paper_id}/bookmarks",
            json={"page_number": 1},
            headers=_auth(token),
        )
    assert resp1.status_code == 201
    assert resp2.status_code == 200
    assert resp2.json()["duplicate"] is True


@requires_db
async def test_create_note():
    db = SessionLocal()
    try:
        user = _add_user(db, "note-create@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/notes",
            json={"anchor_type": "PAPER", "content": "This paper is about transformers."},
            headers=_auth(token),
        )
    assert resp.status_code == 201
    assert resp.json()["content"] == "This paper is about transformers."


@requires_db
async def test_create_knowledge_card():
    db = SessionLocal()
    try:
        user = _add_user(db, "card-create@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/knowledge-cards",
            json={"front": "What is attention?", "back": "A mechanism to weight input importance."},
            headers=_auth(token),
        )
    assert resp.status_code == 201
    assert resp.json()["front"] == "What is attention?"
    assert resp.json()["mastery_status"] == "NEW"


@requires_db
async def test_patch_knowledge_card_mastery():
    db = SessionLocal()
    try:
        user = _add_user(db, "card-mastery@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            f"/api/v1/papers/{paper_id}/knowledge-cards",
            json={"front": "Q", "back": "A"},
            headers=_auth(token),
        )
        card_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/knowledge-cards/{card_id}",
            json={"mastery_status": "LEARNING"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["mastery_status"] == "LEARNING"
    assert resp.json()["last_reviewed_at"] is not None


@requires_db
async def test_highlight_referenced_delete_409():
    db = SessionLocal()
    try:
        user = _add_user(db, "hl-ref@example.com")
        paper = _add_parsed_paper(db, user.id)
        from paperlens.models.models import PaperPage
        page = PaperPage(
            id=str(uuid.uuid4()),
            paper_id=paper.id,
            page_number=1,
            text_content="Referenced highlight text",
            normalized_text_content="Referenced highlight text",
        )
        db.add(page)
        db.flush()
        hl = PaperHighlight(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=1,
            char_start=0,
            char_end=10,
            quoted_text="Referenced",
            source_hash="a" * 64,
            color="YELLOW",
        )
        db.add(hl)
        db.flush()
        note = PaperNote(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            anchor_type="HIGHLIGHT",
            highlight_id=hl.id,
            content="A note about this highlight",
        )
        db.add(note)
        db.commit()
        token = _make_token(user.id)
        hl_id = hl.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            f"/api/v1/highlights/{hl_id}",
            headers=_auth(token),
        )
    assert resp.status_code == 409


@requires_db
async def test_note_referenced_delete_409():
    db = SessionLocal()
    try:
        user = _add_user(db, "note-ref@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        note = PaperNote(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            anchor_type="PAPER",
            content="A referenced note",
        )
        db.add(note)
        db.flush()
        card = PaperKnowledgeCard(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            source_note_id=note.id,
            front="Q",
            back="A",
            mastery_status="NEW",
            archived=False,
        )
        db.add(card)
        db.commit()
        token = _make_token(user.id)
        note_id = note.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            f"/api/v1/notes/{note_id}",
            headers=_auth(token),
        )
    assert resp.status_code == 409


@requires_db
async def test_library_filter_by_reading_status():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-filter@example.com")
        p1 = _add_parsed_paper(db, user.id, title="Paper A")
        p2 = _add_parsed_paper(db, user.id, title="Paper B")
        entry = PaperLibraryEntry(
            user_id=user.id,
            paper_id=p1.id,
            reading_status="COMPLETED",
            favorite=True,
            completed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        db.add(entry)
        db.commit()
        token = _make_token(user.id)
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/library/papers",
            params={"reading_status": "COMPLETED"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Paper A"


@requires_db
async def test_library_filter_by_favorite():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-fav@example.com")
        p1 = _add_parsed_paper(db, user.id, title="Fav Paper")
        p2 = _add_parsed_paper(db, user.id, title="NonFav Paper")
        entry = PaperLibraryEntry(
            user_id=user.id,
            paper_id=p1.id,
            reading_status="TO_READ",
            favorite=True,
        )
        db.add(entry)
        db.commit()
        token = _make_token(user.id)
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/library/papers",
            params={"favorite": "true"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["favorite"] is True


@requires_db
async def test_library_keyword_search():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-kw@example.com")
        _add_parsed_paper(db, user.id, title="Attention Is All You Need")
        _add_parsed_paper(db, user.id, title="BERT Pre-training")
        db.commit()
        token = _make_token(user.id)
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/library/papers",
            params={"keyword": "Attention"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["title"] == "Attention Is All You Need"


@requires_db
async def test_library_counts():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-counts@example.com")
        paper = _add_parsed_paper(db, user.id)
        _add_page(db, paper.id)
        db.flush()
        hl = PaperHighlight(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=1,
            char_start=0,
            char_end=5,
            quoted_text="Hello",
            source_hash="b" * 64,
            color="YELLOW",
        )
        db.add(hl)
        bm = PaperBookmark(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=1,
        )
        db.add(bm)
        note = PaperNote(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            anchor_type="PAPER",
            content="A note",
        )
        db.add(note)
        card = PaperKnowledgeCard(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            front="Q",
            back="A",
            mastery_status="NEW",
            archived=False,
        )
        db.add(card)
        db.commit()
        token = _make_token(user.id)
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/library/papers", headers=_auth(token))
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["highlight_count"] == 1
    assert item["bookmark_count"] == 1
    assert item["note_count"] == 1
    assert item["card_count"] == 1


@requires_db
async def test_patch_library_entry_completed_sets_date():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-comp@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/papers/{paper_id}/library-entry",
            json={"reading_status": "COMPLETED"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reading_status"] == "COMPLETED"
    assert data["completed_at"] is not None


@requires_db
async def test_patch_library_entry_uncompleted_clears_date():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-uncomp@example.com")
        paper = _add_parsed_paper(db, user.id)
        entry = PaperLibraryEntry(
            user_id=user.id,
            paper_id=paper.id,
            reading_status="COMPLETED",
            favorite=False,
            completed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        db.add(entry)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/papers/{paper_id}/library-entry",
            json={"reading_status": "READING"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is None


@requires_db
async def test_patch_library_entry_blank_collection_to_null():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-blank@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/papers/{paper_id}/library-entry",
            json={"collection_name": "   "},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["collection_name"] is None


@requires_db
async def test_reading_progress_to_read_to_reading():
    db = SessionLocal()
    try:
        user = _add_user(db, "rp-auto@example.com")
        paper = _add_parsed_paper(db, user.id, page_count=10)
        _add_page(db, paper.id, page_number=3)
        entry = PaperLibraryEntry(
            user_id=user.id,
            paper_id=paper.id,
            reading_status="TO_READ",
            favorite=False,
        )
        db.add(entry)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/papers/{paper_id}/reading-progress",
            json={"page_number": 3},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["reading_status"] == "READING"
    assert resp.json()["last_page"] == 3
    assert resp.json()["furthest_page"] == 3


@requires_db
async def test_reading_progress_completed_not_overwritten():
    db = SessionLocal()
    try:
        user = _add_user(db, "rp-comp@example.com")
        paper = _add_parsed_paper(db, user.id, page_count=10)
        _add_page(db, paper.id, page_number=5)
        entry = PaperLibraryEntry(
            user_id=user.id,
            paper_id=paper.id,
            reading_status="COMPLETED",
            favorite=False,
            completed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        db.add(entry)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/papers/{paper_id}/reading-progress",
            json={"page_number": 5},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["reading_status"] == "COMPLETED"


@requires_db
async def test_reading_progress_page_out_of_range():
    db = SessionLocal()
    try:
        user = _add_user(db, "rp-range@example.com")
        paper = _add_parsed_paper(db, user.id, page_count=5)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/papers/{paper_id}/reading-progress",
            json={"page_number": 10},
            headers=_auth(token),
        )
    assert resp.status_code == 422


@requires_db
async def test_reading_progress_unparsed_paper():
    db = SessionLocal()
    try:
        user = _add_user(db, "rp-unparsed@example.com")
        paper = Paper(
            id=str(uuid.uuid4()),
            title="Unparsed",
            filename="test.pdf",
            storage_key="test-key",
            file_size=1024,
            file_hash="d" * 64,
            page_count=5,
            status=PaperStatus.UPLOADING,
            user_id=user.id,
        )
        db.add(paper)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/papers/{paper_id}/reading-progress",
            json={"page_number": 2},
            headers=_auth(token),
        )
    assert resp.status_code == 409


@requires_db
async def test_highlight_char_out_of_range():
    db = SessionLocal()
    try:
        user = _add_user(db, "hl-range@example.com")
        paper = _add_parsed_paper(db, user.id)
        _add_page(db, paper.id, text="Short")
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/highlights",
            json={"page_number": 1, "char_start": 0, "char_end": 100, "color": "YELLOW"},
            headers=_auth(token),
        )
    assert resp.status_code == 422


@requires_db
async def test_highlight_whitespace_only():
    db = SessionLocal()
    try:
        user = _add_user(db, "hl-ws@example.com")
        paper = _add_parsed_paper(db, user.id)
        _add_page(db, paper.id, text="   space   more")
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/highlights",
            json={"page_number": 1, "char_start": 0, "char_end": 3, "color": "YELLOW"},
            headers=_auth(token),
        )
    assert resp.status_code == 422


@requires_db
async def test_highlight_duplicate_same_range():
    db = SessionLocal()
    try:
        user = _add_user(db, "hl-dup@example.com")
        paper = _add_parsed_paper(db, user.id)
        _add_page(db, paper.id, text="Duplicate highlight text here")
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp1 = await client.post(
            f"/api/v1/papers/{paper_id}/highlights",
            json={"page_number": 1, "char_start": 0, "char_end": 9, "color": "YELLOW"},
            headers=_auth(token),
        )
        resp2 = await client.post(
            f"/api/v1/papers/{paper_id}/highlights",
            json={"page_number": 1, "char_start": 0, "char_end": 9, "color": "GREEN"},
            headers=_auth(token),
        )
    assert resp1.status_code == 201
    assert resp2.status_code == 200


@requires_db
async def test_highlight_server_derived_quoted_text():
    db = SessionLocal()
    try:
        user = _add_user(db, "hl-derive@example.com")
        paper = _add_parsed_paper(db, user.id)
        _add_page(db, paper.id, text="The quick brown fox jumps over the lazy dog")
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/highlights",
            json={"page_number": 1, "char_start": 4, "char_end": 15, "color": "YELLOW"},
            headers=_auth(token),
        )
    assert resp.status_code == 201
    assert resp.json()["quoted_text"] == "quick brown"


@requires_db
async def test_highlight_page_not_found():
    db = SessionLocal()
    try:
        user = _add_user(db, "hl-nopage@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/highlights",
            json={"page_number": 2, "char_start": 0, "char_end": 5, "color": "YELLOW"},
            headers=_auth(token),
        )
    assert resp.status_code == 404


@requires_db
async def test_list_highlights_filter_by_page():
    db = SessionLocal()
    try:
        user = _add_user(db, "hl-filter@example.com")
        paper = _add_parsed_paper(db, user.id, page_count=3)
        _add_page(db, paper.id, page_number=1, text="Page one content")
        _add_page(db, paper.id, page_number=2, text="Page two content")
        db.flush()
        hl1 = PaperHighlight(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=1,
            char_start=0,
            char_end=4,
            quoted_text="Page",
            source_hash="c" * 64,
            color="YELLOW",
        )
        hl2 = PaperHighlight(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=2,
            char_start=0,
            char_end=4,
            quoted_text="Page",
            source_hash="d" * 64,
            color="GREEN",
        )
        db.add(hl1)
        db.add(hl2)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/papers/{paper_id}/highlights",
            params={"page_number": 1},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["page_number"] == 1


@requires_db
async def test_bookmark_page_out_of_range():
    db = SessionLocal()
    try:
        user = _add_user(db, "bm-range@example.com")
        paper = _add_parsed_paper(db, user.id, page_count=5)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/bookmarks",
            json={"page_number": 10},
            headers=_auth(token),
        )
    assert resp.status_code == 422


@requires_db
async def test_list_bookmarks():
    db = SessionLocal()
    try:
        user = _add_user(db, "bm-list@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        bm1 = PaperBookmark(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=1,
            label="Intro",
        )
        bm2 = PaperBookmark(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=3,
        )
        db.add(bm1)
        db.add(bm2)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/papers/{paper_id}/bookmarks",
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


@requires_db
async def test_delete_bookmark():
    db = SessionLocal()
    try:
        user = _add_user(db, "bm-del@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        bm = PaperBookmark(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=1,
        )
        db.add(bm)
        db.commit()
        token = _make_token(user.id)
        bm_id = bm.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            f"/api/v1/bookmarks/{bm_id}",
            headers=_auth(token),
        )
    assert resp.status_code == 204


@requires_db
async def test_note_page_anchor_requires_page_number():
    db = SessionLocal()
    try:
        user = _add_user(db, "note-page@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/notes",
            json={"anchor_type": "PAGE", "content": "Missing page number"},
            headers=_auth(token),
        )
    assert resp.status_code == 422


@requires_db
async def test_note_highlight_anchor():
    db = SessionLocal()
    try:
        user = _add_user(db, "note-hl@example.com")
        paper = _add_parsed_paper(db, user.id)
        _add_page(db, paper.id, text="Highlight anchor text")
        db.flush()
        hl = PaperHighlight(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=1,
            char_start=0,
            char_end=9,
            quoted_text="Highlight",
            source_hash="e" * 64,
            color="YELLOW",
        )
        db.add(hl)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
        hl_id = hl.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/notes",
            json={"anchor_type": "HIGHLIGHT", "highlight_id": hl_id, "content": "Note on highlight"},
            headers=_auth(token),
        )
    assert resp.status_code == 201
    assert resp.json()["anchor_type"] == "HIGHLIGHT"
    assert resp.json()["highlight_id"] == hl_id


@requires_db
async def test_note_paper_anchor_rejects_page_number():
    db = SessionLocal()
    try:
        user = _add_user(db, "note-reject@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/notes",
            json={"anchor_type": "PAPER", "page_number": 1, "content": "Invalid combo"},
            headers=_auth(token),
        )
    assert resp.status_code == 422


@requires_db
async def test_patch_note():
    db = SessionLocal()
    try:
        user = _add_user(db, "note-patch@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        note = PaperNote(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            anchor_type="PAPER",
            content="Original content",
        )
        db.add(note)
        db.commit()
        token = _make_token(user.id)
        note_id = note.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/notes/{note_id}",
            json={"content": "Updated content"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Updated content"


@requires_db
async def test_list_notes_filter():
    db = SessionLocal()
    try:
        user = _add_user(db, "note-list@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        n1 = PaperNote(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            anchor_type="PAPER",
            content="Paper note",
        )
        n2 = PaperNote(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            anchor_type="PAGE",
            page_number=1,
            content="Page note",
        )
        db.add(n1)
        db.add(n2)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/papers/{paper_id}/notes",
            params={"anchor_type": "PAGE"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["anchor_type"] == "PAGE"


@requires_db
async def test_card_source_exclusive_both():
    db = SessionLocal()
    try:
        user = _add_user(db, "card-exc@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        note = PaperNote(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            anchor_type="PAPER",
            content="Source note",
        )
        db.add(note)
        _add_page(db, paper.id, text="Source highlight text")
        db.flush()
        hl = PaperHighlight(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=1,
            char_start=0,
            char_end=6,
            quoted_text="Source",
            source_hash="f" * 64,
            color="YELLOW",
        )
        db.add(hl)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
        note_id = note.id
        hl_id = hl.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/knowledge-cards",
            json={"source_note_id": note_id, "source_highlight_id": hl_id, "front": "Q", "back": "A"},
            headers=_auth(token),
        )
    assert resp.status_code == 422


@requires_db
async def test_card_from_note():
    db = SessionLocal()
    try:
        user = _add_user(db, "card-note@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        note = PaperNote(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            anchor_type="PAPER",
            content="Source note for card",
        )
        db.add(note)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
        note_id = note.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/knowledge-cards",
            json={"source_note_id": note_id, "front": "Key concept", "back": "Explanation"},
            headers=_auth(token),
        )
    assert resp.status_code == 201
    assert resp.json()["source_note_id"] == note_id


@requires_db
async def test_card_from_highlight():
    db = SessionLocal()
    try:
        user = _add_user(db, "card-hl@example.com")
        paper = _add_parsed_paper(db, user.id)
        _add_page(db, paper.id, text="Important definition here")
        db.flush()
        hl = PaperHighlight(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            page_number=1,
            char_start=0,
            char_end=10,
            quoted_text="Important",
            source_hash="a0" * 32,
            color="YELLOW",
        )
        db.add(hl)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
        hl_id = hl.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/knowledge-cards",
            json={"source_highlight_id": hl_id, "front": "Definition", "back": "Meaning"},
            headers=_auth(token),
        )
    assert resp.status_code == 201
    assert resp.json()["source_highlight_id"] == hl_id


@requires_db
async def test_card_mastery_updates_last_reviewed():
    db = SessionLocal()
    try:
        user = _add_user(db, "card-review@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        card = PaperKnowledgeCard(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            front="Q",
            back="A",
            mastery_status="NEW",
            archived=False,
        )
        db.add(card)
        db.commit()
        token = _make_token(user.id)
        card_id = card.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/knowledge-cards/{card_id}",
            json={"mastery_status": "MASTERED"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["mastery_status"] == "MASTERED"
    assert resp.json()["last_reviewed_at"] is not None


@requires_db
async def test_card_archive():
    db = SessionLocal()
    try:
        user = _add_user(db, "card-arch@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        card = PaperKnowledgeCard(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            front="Q",
            back="A",
            mastery_status="NEW",
            archived=False,
        )
        db.add(card)
        db.commit()
        token = _make_token(user.id)
        card_id = card.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/knowledge-cards/{card_id}",
            json={"archived": True},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["archived"] is True


@requires_db
async def test_list_cards_filter_mastery():
    db = SessionLocal()
    try:
        user = _add_user(db, "card-filter@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        c1 = PaperKnowledgeCard(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            front="Q1",
            back="A1",
            mastery_status="NEW",
            archived=False,
        )
        c2 = PaperKnowledgeCard(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            front="Q2",
            back="A2",
            mastery_status="MASTERED",
            archived=False,
        )
        db.add(c1)
        db.add(c2)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/papers/{paper_id}/knowledge-cards",
            params={"mastery_status": "MASTERED"},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["mastery_status"] == "MASTERED"


@requires_db
async def test_delete_knowledge_card():
    db = SessionLocal()
    try:
        user = _add_user(db, "card-del@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.flush()
        card = PaperKnowledgeCard(
            id=str(uuid.uuid4()),
            user_id=user.id,
            paper_id=paper.id,
            front="Q",
            back="A",
            mastery_status="NEW",
            archived=False,
        )
        db.add(card)
        db.commit()
        token = _make_token(user.id)
        card_id = card.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            f"/api/v1/knowledge-cards/{card_id}",
            headers=_auth(token),
        )
    assert resp.status_code == 204


@requires_db
async def test_other_user_cannot_see_highlights():
    db = SessionLocal()
    try:
        user1 = _add_user(db, "hl-owner@example.com")
        user2 = _add_user(db, "hl-other@example.com")
        paper = _add_parsed_paper(db, user1.id)
        _add_page(db, paper.id, text="Private highlight text")
        db.flush()
        hl = PaperHighlight(
            id=str(uuid.uuid4()),
            user_id=user1.id,
            paper_id=paper.id,
            page_number=1,
            char_start=0,
            char_end=7,
            quoted_text="Private",
            source_hash="b0" * 32,
            color="YELLOW",
        )
        db.add(hl)
        db.commit()
        token2 = _make_token(user2.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/papers/{paper_id}/highlights",
            headers=_auth(token2),
        )
    assert resp.status_code == 404


@requires_db
async def test_other_user_cannot_delete_highlight():
    db = SessionLocal()
    try:
        user1 = _add_user(db, "hl-owner2@example.com")
        user2 = _add_user(db, "hl-del-other@example.com")
        paper = _add_parsed_paper(db, user1.id)
        _add_page(db, paper.id, text="Protected text")
        db.flush()
        hl = PaperHighlight(
            id=str(uuid.uuid4()),
            user_id=user1.id,
            paper_id=paper.id,
            page_number=1,
            char_start=0,
            char_end=9,
            quoted_text="Protected",
            source_hash="c0" * 32,
            color="YELLOW",
        )
        db.add(hl)
        db.commit()
        token2 = _make_token(user2.id)
        hl_id = hl.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            f"/api/v1/highlights/{hl_id}",
            headers=_auth(token2),
        )
    assert resp.status_code == 404


@requires_db
async def test_reading_progress_furthest_page_tracks():
    db = SessionLocal()
    try:
        user = _add_user(db, "rp-furthest@example.com")
        paper = _add_parsed_paper(db, user.id, page_count=10)
        _add_page(db, paper.id, page_number=7)
        _add_page(db, paper.id, page_number=3)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.patch(
            f"/api/v1/papers/{paper_id}/reading-progress",
            json={"page_number": 7},
            headers=_auth(token),
        )
        resp = await client.patch(
            f"/api/v1/papers/{paper_id}/reading-progress",
            json={"page_number": 3},
            headers=_auth(token),
        )
    assert resp.status_code == 200
    assert resp.json()["last_page"] == 3
    assert resp.json()["furthest_page"] == 7


@requires_db
async def test_library_paper_not_found():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-nf@example.com")
        db.commit()
        token = _make_token(user.id)
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        fake_id = str(uuid.uuid4())
        resp = await client.patch(
            f"/api/v1/papers/{fake_id}/library-entry",
            json={"reading_status": "READING"},
            headers=_auth(token),
        )
    assert resp.status_code == 404


@requires_db
async def test_library_default_filters_include_entryless_papers_without_writing():
    db = SessionLocal()
    try:
        user = _add_user(db, "lib-default-filters@example.com")
        paper = _add_parsed_paper(db, user.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/library/papers?reading_status=TO_READ&favorite=false",
            headers=_auth(token),
        )
    assert response.status_code == 200
    assert [item["paper_id"] for item in response.json()["items"]] == [paper_id]
    db = SessionLocal()
    try:
        assert db.query(PaperLibraryEntry).count() == 0
    finally:
        db.close()


@requires_db
async def test_personal_learning_patch_schemas_are_strict_and_hide_owner_fields():
    db = SessionLocal()
    try:
        user = _add_user(db, "strict-schema@example.com")
        paper = _add_parsed_paper(db, user.id)
        _add_page(db, paper.id)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        empty = await client.patch(f"/api/v1/papers/{paper_id}/library-entry", json={}, headers=_auth(token))
        null_status = await client.patch(f"/api/v1/papers/{paper_id}/library-entry", json={"reading_status": None}, headers=_auth(token))
        extra = await client.patch(f"/api/v1/papers/{paper_id}/library-entry", json={"favorite": True, "owner": "x"}, headers=_auth(token))
        valid = await client.patch(f"/api/v1/papers/{paper_id}/library-entry", json={"collection_name": "  Study  "}, headers=_auth(token))
        progress = await client.patch(f"/api/v1/papers/{paper_id}/reading-progress", json={"page_number": 1}, headers=_auth(token))
    assert empty.status_code == 422
    assert null_status.status_code == 422
    assert extra.status_code == 422
    assert valid.status_code == 200
    assert valid.json()["collection_name"] == "Study"
    assert "user_id" not in valid.json()
    assert "user_id" not in progress.json()


@requires_db
async def test_all_personal_learning_lists_hide_cross_owner_paper():
    db = SessionLocal()
    try:
        owner = _add_user(db, "list-owner@example.com")
        other = _add_user(db, "list-other@example.com")
        paper = _add_parsed_paper(db, owner.id)
        db.commit()
        token = _make_token(other.id)
        paper_id = paper.id
    finally:
        db.close()
    paths = (
        f"/api/v1/papers/{paper_id}/highlights",
        f"/api/v1/papers/{paper_id}/bookmarks",
        f"/api/v1/papers/{paper_id}/notes",
        f"/api/v1/papers/{paper_id}/knowledge-cards",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        responses = [await client.get(path, headers=_auth(token)) for path in paths]
    assert [response.status_code for response in responses] == [404, 404, 404, 404]


@requires_db
async def test_card_creation_requires_owned_parsed_paper_before_writing():
    db = SessionLocal()
    try:
        owner = _add_user(db, "card-paper-owner@example.com")
        other = _add_user(db, "card-paper-other@example.com")
        paper = _add_parsed_paper(db, owner.id)
        db.commit()
        token = _make_token(other.id)
        paper_id = paper.id
    finally:
        db.close()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/papers/{paper_id}/knowledge-cards",
            json={"front": "private", "back": "private"},
            headers=_auth(token),
        )
    assert response.status_code == 404
    db = SessionLocal()
    try:
        assert db.query(PaperKnowledgeCard).count() == 0
    finally:
        db.close()


@requires_db
async def test_bookmark_list_has_real_pagination():
    db = SessionLocal()
    try:
        user = _add_user(db, "bookmark-pages@example.com")
        paper = _add_parsed_paper(db, user.id, page_count=3)
        for page_number in range(1, 4):
            _add_page(db, paper.id, page_number=page_number, text=f"page {page_number}")
            db.add(PaperBookmark(id=str(uuid.uuid4()), user_id=user.id, paper_id=paper.id, page_number=page_number))
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
    finally:
        db.close()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/papers/{paper_id}/bookmarks?page=2&page_size=2", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["page"] == 2
    assert [item["page_number"] for item in response.json()["items"]] == [3]


@requires_db
async def test_empty_card_patch_control_char_and_invalid_filters_are_rejected():
    db = SessionLocal()
    try:
        user = _add_user(db, "strict-card@example.com")
        paper = _add_parsed_paper(db, user.id)
        card = PaperKnowledgeCard(
            id=str(uuid.uuid4()), user_id=user.id, paper_id=paper.id,
            front="front", back="back", mastery_status="NEW", archived=False,
        )
        db.add(card)
        db.commit()
        token = _make_token(user.id)
        paper_id = paper.id
        card_id = card.id
    finally:
        db.close()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        empty = await client.patch(f"/api/v1/knowledge-cards/{card_id}", json={}, headers=_auth(token))
        control = await client.patch(f"/api/v1/knowledge-cards/{card_id}", json={"front": "bad\u0000text"}, headers=_auth(token))
        invalid_filter = await client.get(f"/api/v1/papers/{paper_id}/knowledge-cards?mastery_status=REVIEWING", headers=_auth(token))
    assert empty.status_code == 422
    assert control.status_code == 422
    assert invalid_filter.status_code == 422


@requires_db
async def test_same_mastery_status_does_not_advance_review_time():
    db = SessionLocal()
    try:
        user = _add_user(db, "same-mastery@example.com")
        paper = _add_parsed_paper(db, user.id)
        reviewed_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        card = PaperKnowledgeCard(
            id=str(uuid.uuid4()), user_id=user.id, paper_id=paper.id,
            front="front", back="back", mastery_status="LEARNING", last_reviewed_at=reviewed_at, archived=False,
        )
        db.add(card)
        db.commit()
        token = _make_token(user.id)
        card_id = card.id
    finally:
        db.close()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/knowledge-cards/{card_id}",
            json={"mastery_status": "LEARNING"},
            headers=_auth(token),
        )
    assert response.status_code == 200
    assert response.json()["last_reviewed_at"] == "2026-01-01T00:00:00Z"
