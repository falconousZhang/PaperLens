import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from paperlens.core.database import SessionLocal
from paperlens.core.enums import PaperStatus, QATurnStatus, UserRole, UserStatus
from paperlens.main import app
from paperlens.models.models import (
    Evidence,
    Paper,
    PaperQAConversation,
    PaperQATurn,
    User,
)
from paperlens.services.auth_service import create_session_for_user
from paperlens.services.password_service import hash_password
from paperlens.services import qa_service
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
        password_hash=hash_password("QATest123!"),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )
    db.add(user)
    db.flush()
    return user


def _add_parsed_paper(db, user_id: str, title: str = "QA Test Paper") -> Paper:
    paper = Paper(
        id=str(uuid.uuid4()),
        title=title,
        filename="test.pdf",
        storage_key="test-key",
        file_size=1024,
        file_hash="b" * 64,
        page_count=2,
        status=PaperStatus.PARSED,
        user_id=user_id,
    )
    db.add(paper)
    db.flush()
    return paper


def _add_evidence(db, paper_id: str, page_number: int = 1, text: str = "Evidence text for QA") -> Evidence:
    evidence = Evidence(
        id=str(uuid.uuid4()),
        paper_id=paper_id,
        quoted_text=text,
        page_number=page_number,
        evidence_type="TEXT",
    )
    db.add(evidence)
    db.flush()
    return evidence


def _make_token(user_id: str) -> str:
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        token, _ = create_session_for_user(db, user)
        db.commit()
        return token
    finally:
        db.close()


class _QATestContext:
    def __init__(self):
        self.user_id: str = ""
        self.paper_id: str = ""
        self.evidence_id: str = ""
        self.token: str = ""


def _setup_qa_context(email: str = "qa-test@example.com") -> _QATestContext:
    ctx = _QATestContext()
    db = SessionLocal()
    try:
        user = _add_user(db, email)
        paper = _add_parsed_paper(db, user.id)
        evidence = _add_evidence(db, paper.id, text="The model achieves 95% accuracy on the benchmark dataset.")
        ctx.user_id = user.id
        ctx.paper_id = paper.id
        ctx.evidence_id = evidence.id
        db.commit()
        ctx.token = _make_token(user.id)
    finally:
        db.close()
    return ctx


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
async def test_create_qa_conversation():
    ctx = _setup_qa_context()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{ctx.paper_id}/qa-conversations",
            json={},
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["paper_id"] == ctx.paper_id
    assert data["turns"] is None


@requires_db
async def test_create_conversation_rejects_client_fields():
    ctx = _setup_qa_context("qa-conv-extra@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{ctx.paper_id}/qa-conversations",
            json={"title": "client supplied title"},
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 422


@requires_db
async def test_create_conversation_paper_not_found():
    ctx = _setup_qa_context()
    fake_paper_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{fake_paper_id}/qa-conversations",
            json={},
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 404


@requires_db
async def test_create_conversation_paper_not_parsed():
    db = SessionLocal()
    paper_id = ""
    token = ""
    try:
        user = _add_user(db, "qa-unparsed@example.com")
        paper = Paper(
            id=str(uuid.uuid4()),
            title="Unparsed",
            filename="test.pdf",
            storage_key="key",
            file_size=1024,
            file_hash="c" * 64,
            status=PaperStatus.PROCESSING,
            user_id=user.id,
        )
        db.add(paper)
        db.commit()
        paper_id = paper.id
        token = _make_token(user.id)
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/papers/{paper_id}/qa-conversations",
            json={},
            headers=_auth(token),
        )
    assert resp.status_code == 409


@requires_db
async def test_list_qa_conversations():
    ctx = _setup_qa_context("qa-list@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            f"/api/v1/papers/{ctx.paper_id}/qa-conversations",
            json={},
            headers=_auth(ctx.token),
        )
        await client.post(
            f"/api/v1/papers/{ctx.paper_id}/qa-conversations",
            json={},
            headers=_auth(ctx.token),
        )
        resp = await client.get(
            f"/api/v1/papers/{ctx.paper_id}/qa-conversations",
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all(item["turn_count"] == 0 for item in data["items"])


@requires_db
async def test_get_qa_conversation():
    ctx = _setup_qa_context("qa-get-conv@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            f"/api/v1/papers/{ctx.paper_id}/qa-conversations",
            json={},
            headers=_auth(ctx.token),
        )
        conv_id = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/qa-conversations/{conv_id}",
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 200
    assert resp.json()["turns"] == []
    assert resp.json()["total"] == 0


@requires_db
async def test_get_conversation_turn_pagination_and_safe_fields():
    ctx = _setup_qa_context("qa-pagination@example.com")
    db = SessionLocal()
    try:
        conversation = PaperQAConversation(
            id=str(uuid.uuid4()),
            paper_id=ctx.paper_id,
            user_id=ctx.user_id,
        )
        db.add(conversation)
        db.flush()
        now = datetime.now(timezone.utc)
        for sequence in range(1, 22):
            db.add(
                PaperQATurn(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation.id,
                    user_id=ctx.user_id,
                    paper_id=ctx.paper_id,
                    sequence=sequence,
                    question=f"question {sequence}",
                    output_language="zh",
                    client_request_id=str(uuid.uuid4()),
                    status=QATurnStatus.FAILED,
                    error_message="论文问答生成失败，请稍后重试",
                    started_at=now,
                    completed_at=now,
                )
            )
        db.commit()
        conversation_id = conversation.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/qa-conversations/{conversation_id}?page=2&page_size=20",
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 21
    assert data["page"] == 2
    assert [turn["sequence"] for turn in data["turns"]] == [21]
    assert "client_request_id" not in data["turns"][0]
    assert "context_hash" not in data["turns"][0]


@requires_db
async def test_get_conversation_not_found():
    ctx = _setup_qa_context("qa-get-nf@example.com")
    fake_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/qa-conversations/{fake_id}",
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 404


@requires_db
async def test_create_qa_turn():
    ctx = _setup_qa_context("qa-turn@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_conv = await client.post(
            f"/api/v1/papers/{ctx.paper_id}/qa-conversations",
            json={},
            headers=_auth(ctx.token),
        )
        conv_id = create_conv.json()["id"]
        client_req_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/qa-conversations/{conv_id}/turns",
            json={
                "question": "What accuracy does the model achieve?",
                "output_language": "zh",
                "client_request_id": client_req_id,
            },
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["question"] == "What accuracy does the model achieve?"
    assert data["sequence"] == 1
    assert data["status"] in ("PENDING", "RUNNING", "SUCCEEDED")
    assert data["duplicate"] is False


@requires_db
async def test_create_turn_rejects_blank_question():
    ctx = _setup_qa_context("qa-blank@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        conversation = await client.post(
            f"/api/v1/papers/{ctx.paper_id}/qa-conversations",
            json={},
            headers=_auth(ctx.token),
        )
        resp = await client.post(
            f"/api/v1/qa-conversations/{conversation.json()['id']}/turns",
            json={
                "question": "   ",
                "output_language": "zh",
                "client_request_id": str(uuid.uuid4()),
            },
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 422


@requires_db
async def test_create_turn_rejects_paper_without_evidence_before_insert():
    db = SessionLocal()
    try:
        user = _add_user(db, "qa-create-no-evidence@example.com")
        paper = _add_parsed_paper(db, user.id, title="No evidence")
        db.commit()
        paper_id = paper.id
        user_id = user.id
        token = _make_token(user.id)
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        conversation = await client.post(
            f"/api/v1/papers/{paper_id}/qa-conversations",
            json={},
            headers=_auth(token),
        )
        conversation_id = conversation.json()["id"]
        resp = await client.post(
            f"/api/v1/qa-conversations/{conversation_id}/turns",
            json={
                "question": "What does this paper say?",
                "output_language": "en",
                "client_request_id": str(uuid.uuid4()),
            },
            headers=_auth(token),
        )
    assert resp.status_code == 409
    db = SessionLocal()
    try:
        assert db.query(PaperQATurn).filter(
            PaperQATurn.conversation_id == conversation_id,
            PaperQATurn.user_id == user_id,
        ).count() == 0
    finally:
        db.close()


@requires_db
async def test_create_turn_duplicate_client_request_id():
    ctx = _setup_qa_context("qa-dup@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_conv = await client.post(
            f"/api/v1/papers/{ctx.paper_id}/qa-conversations",
            json={},
            headers=_auth(ctx.token),
        )
        conv_id = create_conv.json()["id"]
        client_req_id = str(uuid.uuid4())
        body = {
            "question": "What is the method?",
            "output_language": "en",
            "client_request_id": client_req_id,
        }
        resp1 = await client.post(
            f"/api/v1/qa-conversations/{conv_id}/turns",
            json=body,
            headers=_auth(ctx.token),
        )
        resp2 = await client.post(
            f"/api/v1/qa-conversations/{conv_id}/turns",
            json=body,
            headers=_auth(ctx.token),
        )
    assert resp1.status_code == 201
    assert resp2.status_code == 200
    assert resp2.json()["duplicate"] is True
    assert resp2.json()["id"] == resp1.json()["id"]


@requires_db
async def test_create_turn_conversation_not_found():
    ctx = _setup_qa_context("qa-turn-nf@example.com")
    fake_conv_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/qa-conversations/{fake_conv_id}/turns",
            json={
                "question": "Test question?",
                "output_language": "zh",
                "client_request_id": str(uuid.uuid4()),
            },
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 404


@requires_db
async def test_get_qa_turn():
    ctx = _setup_qa_context("qa-get-turn@example.com")
    db = SessionLocal()
    try:
        conv = PaperQAConversation(
            id=str(uuid.uuid4()),
            paper_id=ctx.paper_id,
            user_id=ctx.user_id,
        )
        db.add(conv)
        db.flush()
        turn = PaperQATurn(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            user_id=ctx.user_id,
            paper_id=ctx.paper_id,
            sequence=1,
            question="Test question",
            output_language="zh",
            client_request_id=str(uuid.uuid4()),
            status=QATurnStatus.PENDING,
        )
        db.add(turn)
        db.commit()
        turn_id = turn.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/qa-turns/{turn_id}",
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 200
    assert resp.json()["question"] == "Test question"


@requires_db
async def test_get_turn_not_found():
    ctx = _setup_qa_context("qa-get-turn-nf@example.com")
    fake_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/qa-turns/{fake_id}",
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 404


@requires_db
async def test_turn_ownership_isolation():
    ctx1 = _setup_qa_context("qa-owner1@example.com")
    ctx2 = _setup_qa_context("qa-owner2@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_conv = await client.post(
            f"/api/v1/papers/{ctx1.paper_id}/qa-conversations",
            json={},
            headers=_auth(ctx1.token),
        )
        conv_id = create_conv.json()["id"]
        resp = await client.get(
            f"/api/v1/qa-conversations/{conv_id}",
            headers=_auth(ctx2.token),
        )
    assert resp.status_code == 404


@requires_db
async def test_run_qa_turn_succeeds():
    ctx = _setup_qa_context("qa-run@example.com")
    db = SessionLocal()
    try:
        conv = PaperQAConversation(
            id=str(uuid.uuid4()),
            paper_id=ctx.paper_id,
            user_id=ctx.user_id,
        )
        db.add(conv)
        db.flush()
        turn = PaperQATurn(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            user_id=ctx.user_id,
            paper_id=ctx.paper_id,
            sequence=1,
            question="What is the accuracy?",
            output_language="zh",
            client_request_id=str(uuid.uuid4()),
            status=QATurnStatus.PENDING,
        )
        db.add(turn)
        db.commit()
        turn_id = turn.id
    finally:
        db.close()

    from paperlens.services.llm_client import MockLLMClient
    qa_service.run_qa_turn(turn_id, llm_client=MockLLMClient())

    db = SessionLocal()
    try:
        updated = db.get(PaperQATurn, turn_id)
        assert updated.status == QATurnStatus.SUCCEEDED
        assert updated.answer is not None
        assert updated.grounded is not None
    finally:
        db.close()


@requires_db
async def test_run_qa_turn_rejects_changed_evidence_before_persistence():
    ctx = _setup_qa_context("qa-source-change@example.com")
    db = SessionLocal()
    try:
        conversation = PaperQAConversation(
            id=str(uuid.uuid4()),
            paper_id=ctx.paper_id,
            user_id=ctx.user_id,
        )
        db.add(conversation)
        db.flush()
        turn = PaperQATurn(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            user_id=ctx.user_id,
            paper_id=ctx.paper_id,
            sequence=1,
            question="What is the accuracy?",
            output_language="en",
            client_request_id=str(uuid.uuid4()),
            status=QATurnStatus.PENDING,
        )
        db.add(turn)
        db.commit()
        turn_id = turn.id
    finally:
        db.close()

    class MutatingLLM:
        def chat(self, messages, **kwargs):
            del messages, kwargs
            mutation_db = SessionLocal()
            try:
                evidence_row = mutation_db.get(Evidence, ctx.evidence_id)
                evidence_row.quoted_text = "Evidence changed after model inference started."
                mutation_db.commit()
            finally:
                mutation_db.close()
            return {
                "content": '{"answer":"The accuracy is 95%.","grounded":true,"evidence_refs":["E1"]}'
            }

    from paperlens.services.embedding_client import MockEmbeddingClient

    qa_service.run_qa_turn(
        turn_id,
        llm_client=MutatingLLM(),
        embedding_client=MockEmbeddingClient(),
    )
    db = SessionLocal()
    try:
        updated = db.get(PaperQATurn, turn_id)
        assert updated.status == QATurnStatus.FAILED
        assert updated.context_hash is None
        assert updated.answer is None
        assert updated.error_message == "论文问答生成失败，请稍后重试"
    finally:
        db.close()


@requires_db
async def test_run_qa_turn_no_evidence():
    db = SessionLocal()
    turn_id = ""
    try:
        user = _add_user(db, "qa-no-ev@example.com")
        paper = _add_parsed_paper(db, user.id, title="No Evidence Paper")
        conv = PaperQAConversation(
            id=str(uuid.uuid4()),
            paper_id=paper.id,
            user_id=user.id,
        )
        db.add(conv)
        db.flush()
        turn = PaperQATurn(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            user_id=user.id,
            paper_id=paper.id,
            sequence=1,
            question="Any evidence?",
            output_language="zh",
            client_request_id=str(uuid.uuid4()),
            status=QATurnStatus.PENDING,
        )
        db.add(turn)
        db.commit()
        turn_id = turn.id
    finally:
        db.close()

    from paperlens.services.llm_client import MockLLMClient
    qa_service.run_qa_turn(turn_id, llm_client=MockLLMClient())

    db = SessionLocal()
    try:
        updated = db.get(PaperQATurn, turn_id)
        assert updated.status == QATurnStatus.FAILED
    finally:
        db.close()


@requires_db
async def test_concurrent_turn_creation_rejected():
    ctx = _setup_qa_context("qa-concurrent@example.com")
    db = SessionLocal()
    conv_id = ""
    try:
        conv = PaperQAConversation(
            id=str(uuid.uuid4()),
            paper_id=ctx.paper_id,
            user_id=ctx.user_id,
        )
        db.add(conv)
        db.flush()
        active_turn = PaperQATurn(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            user_id=ctx.user_id,
            paper_id=ctx.paper_id,
            sequence=1,
            question="Active question",
            output_language="zh",
            client_request_id=str(uuid.uuid4()),
            status=QATurnStatus.RUNNING,
            started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        db.add(active_turn)
        db.commit()
        conv_id = conv.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/qa-conversations/{conv_id}/turns",
            json={
                "question": "Second question",
                "output_language": "zh",
                "client_request_id": str(uuid.uuid4()),
            },
            headers=_auth(ctx.token),
        )
    assert resp.status_code == 409
