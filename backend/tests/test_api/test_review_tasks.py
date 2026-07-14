import json
import uuid
import datetime
import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport, AsyncClient

from paperlens.main import app
from paperlens.core.database import configure_engine, get_engine, SessionLocal
from paperlens.core.enums import PaperStatus, EvidenceType, ReviewDimension, UserRole, UserStatus
from paperlens.models.models import (
    AnalysisTask,
    AuthSession,
    Evidence,
    FindingEvidence,
    Paper,
    ReviewFinding,
    ReviewResult,
    User,
)
from paperlens.services.password_service import hash_password
from paperlens.services.auth_service import create_session_for_user
from paperlens.services.llm_client import LLMClient, get_llm_client
from paperlens.services.huawei_maas_llm import HuaweiMaaSLLMClient
import paperlens.services.review_service as review_service_module
from paperlens.services.review_service import select_evidence_candidates
from paperlens.services.embedding_client import (
    EmbeddingClient,
    EmbeddingError,
    MockEmbeddingClient,
    get_embedding_client,
)
from tests.db_helpers import (
    db_available,
    ensure_test_database,
    get_test_db_url,
    is_test_db_required,
    run_alembic_migrations,
    truncate_test_tables,
    verify_no_test_residuals,
    wait_for_paper_status,
)

requires_db = pytest.mark.skipif(
    not db_available() and not is_test_db_required(),
    reason="需要 PAPERLENS_TEST_DATABASE_URL 且 PostgreSQL 可连接",
)


class FakeLLMClient(LLMClient):
    def __init__(self, outputs: list[dict] | None = None):
        self._outputs = outputs
        self.call_count = 0

    def chat(self, messages: list[dict], **kwargs) -> dict:
        self.call_count += 1
        dimension = kwargs.get("dimension", "OVERALL")
        evidence_aliases = kwargs.get("evidence_aliases", [])

        if self._outputs and len(self._outputs) >= self.call_count:
            return {"role": "assistant", "content": json.dumps(self._outputs[self.call_count - 1])}

        overall_verdict = "WEAK_ACCEPT" if dimension == "OVERALL" else None
        findings = []
        if evidence_aliases:
            findings.append({
                "finding_type": "STRENGTH",
                "content": f"Fake finding for {dimension}",
                "confidence": 0.85,
                "evidence_refs": [evidence_aliases[0]],
            })

        return {
            "role": "assistant",
            "content": json.dumps({
                "dimension": dimension,
                "rating": 4,
                "summary": f"Fake summary for {dimension}",
                "overall_verdict": overall_verdict,
                "findings": findings,
            }),
        }


class FakeUnknownAliasLLM(LLMClient):
    def chat(self, messages: list[dict], **kwargs) -> dict:
        return {
            "role": "assistant",
            "content": json.dumps({
                "dimension": "OVERALL",
                "rating": 3,
                "summary": "Fake with unknown alias",
                "overall_verdict": "BORDERLINE",
                "findings": [
                    {"finding_type": "WEAKNESS", "content": "Unknown ref", "confidence": 0.5, "evidence_refs": ["E99"]},
                ],
            }),
        }


class FakeBadJsonLLM(LLMClient):
    def chat(self, messages: list[dict], **kwargs) -> dict:
        return {"role": "assistant", "content": "this is not json"}


class FakeSecondDimensionBadLLM(FakeLLMClient):
    def chat(self, messages: list[dict], **kwargs) -> dict:
        if self.call_count == 0:
            return super().chat(messages, **kwargs)
        self.call_count += 1
        return {"role": "assistant", "content": "secret-second-dimension is not json"}


class FakeFailingEmbeddingClient(EmbeddingClient):
    def __init__(self, fail_on_call: int):
        self.fail_on_call = fail_on_call
        self.call_count = 0
        self.delegate = MockEmbeddingClient()

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        if self.call_count == self.fail_on_call:
            raise EmbeddingError("secret-embedding-failure")
        return self.delegate.embed(texts)


class HuaweiReviewTransport(httpx.BaseTransport):
    def __init__(
        self,
        fail_on_call: int | None = None,
        session_holder: dict | None = None,
        wrap_json_fence: bool = False,
    ):
        self.fail_on_call = fail_on_call
        self.session_holder = session_holder
        self.wrap_json_fence = wrap_json_fence
        self.call_count = 0
        self.transaction_states: list[bool] = []
        self.urls: list[str] = []
        self.authorization_headers: list[str] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.call_count += 1
        self.urls.append(str(request.url))
        self.authorization_headers.append(request.headers.get("authorization", ""))

        if self.session_holder is not None:
            session = self.session_holder.get("session")
            assert session is not None
            self.transaction_states.append(session.in_transaction())

        if self.call_count == self.fail_on_call:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "secret-upstream-partial-response",
                            },
                            "finish_reason": "length",
                        }
                    ]
                },
                request=request,
            )

        body = json.loads(request.content)
        user_content = body["messages"][-1]["content"]
        dimension = next(
            (
                candidate.value
                for candidate in ReviewDimension
                if f"on the {candidate.value} dimension" in user_content
            ),
            None,
        )
        assert dimension is not None
        review_output = {
            "dimension": dimension,
            "rating": 4,
            "summary": f"Huawei transport summary for {dimension}",
            "overall_verdict": "WEAK_ACCEPT" if dimension == "OVERALL" else None,
            "findings": [
                {
                    "finding_type": "STRENGTH",
                    "content": f"Huawei transport finding for {dimension}",
                    "confidence": 0.9,
                    "evidence_refs": ["E1"],
                }
            ],
        }
        response_content = json.dumps(review_output)
        if self.wrap_json_fence:
            response_content = f"```json\n{response_content}\n```"

        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_content,
                        },
                        "finish_reason": "stop",
                    }
                ]
            },
            request=request,
        )


@pytest_asyncio.fixture
async def db_client():
    test_url = get_test_db_url()
    if not test_url:
        if is_test_db_required():
            pytest.fail("PAPERLENS_REQUIRE_TEST_DB=true but PAPERLENS_TEST_DATABASE_URL is not set")
        pytest.skip("需要 PAPERLENS_TEST_DATABASE_URL")

    ensure_test_database()
    run_alembic_migrations(test_url)
    configure_engine(test_url)
    actual_url = str(get_engine().url)
    assert "paperlens_test" in actual_url, f"Engine must point to test DB, got: {actual_url}"

    default_llm = FakeLLMClient()
    default_emb = MockEmbeddingClient()
    app.dependency_overrides[get_llm_client] = lambda: default_llm
    app.dependency_overrides[get_embedding_client] = lambda: default_emb

    db = SessionLocal()
    test_user_id = None
    access_token = None
    try:
        test_user = User(
            id=str(uuid.uuid4()),
            email="test-review@example.com",
            email_normalized="test-review@example.com",
            display_name="Test Review User",
            password_hash=hash_password("TestReviewPass123!@#"),
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            failed_login_count=0,
        )
        db.add(test_user)
        db.flush()
        test_user_id = test_user.id
        access_token, _ = create_session_for_user(db, test_user)
        db.commit()
    finally:
        db.close()

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": f"Bearer {access_token}"},
        ) as c:
            c._test_user_id = test_user_id
            yield c
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
        app.dependency_overrides.pop(get_embedding_client, None)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def _get_test_user_id(client: AsyncClient) -> str:
    return getattr(client, "_test_user_id", "demo-user")


def _create_parsed_paper_with_evidence(db, user_id=None, evidence_count=2):
    if user_id is None:
        user_id = "demo-user"
    paper_id = str(uuid.uuid4())
    paper = Paper(
        id=paper_id,
        title="Test Paper",
        filename="test.pdf",
        storage_key=f"papers/{paper_id}/source.pdf",
        file_size=1000,
        file_hash="a" * 64,
        status=PaperStatus.PARSED,
        user_id=user_id,
    )
    db.add(paper)

    for i in range(evidence_count):
        ev = Evidence(
            id=str(uuid.uuid4()),
            paper_id=paper_id,
            quoted_text=f"Evidence text {i+1}",
            page_number=1,
            evidence_type=EvidenceType.TEXT,
        )
        db.add(ev)

    db.commit()
    return paper_id


@requires_db
@pytest.mark.asyncio
async def test_create_review_task_success(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client))
    finally:
        db.close()

    resp = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "REVIEW"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["progress"] == 0
    assert data["task_type"] == "REVIEW"

    task_id = data["id"]
    import time
    deadline = time.time() + 15
    while time.time() < deadline:
        task_resp = await db_client.get(f"/api/v1/tasks/{task_id}")
        task_data = task_resp.json()
        if task_data["status"] in ("SUCCEEDED", "FAILED"):
            break
        time.sleep(0.5)

    assert task_data["status"] == "SUCCEEDED"
    assert task_data["progress"] == 100


@requires_db
@pytest.mark.asyncio
async def test_get_reviews_returns_verified_findings(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client))
    finally:
        db.close()

    task_resp = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "REVIEW"})
    task_id = task_resp.json()["id"]

    import time
    deadline = time.time() + 15
    while time.time() < deadline:
        r = await db_client.get(f"/api/v1/tasks/{task_id}")
        if r.json()["status"] in ("SUCCEEDED", "FAILED"):
            break
        time.sleep(0.5)

    reviews_resp = await db_client.get(f"/api/v1/papers/{paper_id}/reviews")
    assert reviews_resp.status_code == 200
    reviews = reviews_resp.json()["reviews"]
    assert len(reviews) >= 1
    for rev in reviews:
        assert rev["dimension"] == "OVERALL"
        assert rev["rating"] is not None
        for f in rev["findings"]:
            assert f["verification_status"] == "VERIFIED"
            assert len(f["evidence_ids"]) > 0


@requires_db
@pytest.mark.asyncio
async def test_multi_dimension_review(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client), evidence_count=3)
    finally:
        db.close()

    resp = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks",
        json={"task_type": "REVIEW", "options": {"dimensions": ["SOUNDNESS", "OVERALL"], "language": "en"}},
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    import time
    deadline = time.time() + 15
    while time.time() < deadline:
        r = await db_client.get(f"/api/v1/tasks/{task_id}")
        if r.json()["status"] in ("SUCCEEDED", "FAILED"):
            break
        time.sleep(0.5)

    reviews_resp = await db_client.get(f"/api/v1/papers/{paper_id}/reviews")
    reviews = reviews_resp.json()["reviews"]
    dimensions = [r["dimension"] for r in reviews]
    assert "SOUNDNESS" in dimensions
    assert "OVERALL" in dimensions

    for r in reviews:
        if r["dimension"] == "OVERALL":
            assert r["overall_verdict"] is not None
        else:
            assert r["overall_verdict"] is None


@requires_db
@pytest.mark.asyncio
@pytest.mark.parametrize("wrap_json_fence", [False, True])
async def test_huawei_maas_review_success_is_strict_bound_and_transaction_free(
    db_client: AsyncClient,
    monkeypatch,
    wrap_json_fence: bool,
):
    session_holder: dict = {}
    original_session_factory = review_service_module.SessionLocal

    def tracking_session_factory():
        session = original_session_factory()
        session_holder["session"] = session
        return session

    monkeypatch.setattr(review_service_module, "SessionLocal", tracking_session_factory)
    transport = HuaweiReviewTransport(
        session_holder=session_holder,
        wrap_json_fence=wrap_json_fence,
    )
    huawei_client = HuaweiMaaSLLMClient(
        base_url="https://mock.test/v2",
        model="glm-5.2",
        api_key="sentinel-huawei-review-key",
        transport=transport,
    )
    app.dependency_overrides[get_llm_client] = lambda: huawei_client

    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client), evidence_count=2)
    finally:
        db.close()

    response = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks",
        json={
            "task_type": "REVIEW",
            "options": {"dimensions": ["SOUNDNESS", "OVERALL"], "language": "zh"},
        },
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    task_response = await db_client.get(f"/api/v1/tasks/{task_id}")
    assert task_response.json()["status"] == "SUCCEEDED"
    assert transport.call_count == 2
    assert transport.transaction_states == [False, False]
    assert transport.urls == [
        "https://mock.test/v2/chat/completions",
        "https://mock.test/v2/chat/completions",
    ]
    assert transport.authorization_headers == [
        "Bearer sentinel-huawei-review-key",
        "Bearer sentinel-huawei-review-key",
    ]

    db = SessionLocal()
    try:
        assert db.query(ReviewResult).filter(ReviewResult.task_id == task_id).count() == 2
        assert (
            db.query(ReviewFinding)
            .join(ReviewResult)
            .filter(ReviewResult.task_id == task_id)
            .count()
            == 2
        )
        assert (
            db.query(FindingEvidence)
            .join(ReviewFinding)
            .join(ReviewResult)
            .filter(ReviewResult.task_id == task_id)
            .count()
            == 2
        )
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
@pytest.mark.parametrize("fail_on_call", [1, 2])
async def test_huawei_maas_failure_rolls_back_entire_result_batch(
    db_client: AsyncClient,
    monkeypatch,
    fail_on_call: int,
):
    session_holder: dict = {}
    original_session_factory = review_service_module.SessionLocal

    def tracking_session_factory():
        session = original_session_factory()
        session_holder["session"] = session
        return session

    monkeypatch.setattr(review_service_module, "SessionLocal", tracking_session_factory)
    transport = HuaweiReviewTransport(
        fail_on_call=fail_on_call,
        session_holder=session_holder,
    )
    huawei_client = HuaweiMaaSLLMClient(
        base_url="https://mock.test/v2",
        model="glm-5.2",
        api_key="sentinel-huawei-review-key",
        transport=transport,
    )
    app.dependency_overrides[get_llm_client] = lambda: huawei_client

    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client), evidence_count=2)
    finally:
        db.close()

    response = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks",
        json={
            "task_type": "REVIEW",
            "options": {"dimensions": ["SOUNDNESS", "OVERALL"], "language": "zh"},
        },
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    task_response = await db_client.get(f"/api/v1/tasks/{task_id}")
    task_data = task_response.json()
    assert task_data["status"] == "FAILED"
    assert "sentinel-huawei-review-key" not in task_data["error_message"]
    assert "secret-upstream-partial-response" not in task_data["error_message"]
    assert "Authorization" not in task_data["error_message"]
    assert transport.call_count == fail_on_call
    assert transport.transaction_states == [False] * fail_on_call

    db = SessionLocal()
    try:
        assert db.query(ReviewResult).filter(ReviewResult.task_id == task_id).count() == 0
        assert (
            db.query(ReviewFinding)
            .join(ReviewResult)
            .filter(ReviewResult.task_id == task_id)
            .count()
            == 0
        )
        assert (
            db.query(FindingEvidence)
            .join(ReviewFinding)
            .join(ReviewResult)
            .filter(ReviewResult.task_id == task_id)
            .count()
            == 0
        )
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
async def test_processing_paper_cannot_create_task(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = str(uuid.uuid4())
        paper = Paper(
            id=paper_id,
            title="Processing",
            filename="test.pdf",
            storage_key=f"papers/{paper_id}/source.pdf",
            file_size=1000,
            file_hash="b" * 64,
            status=PaperStatus.PROCESSING,
            user_id=_get_test_user_id(db_client),
        )
        db.add(paper)
        db.commit()
    finally:
        db.close()

    resp = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "REVIEW"})
    assert resp.status_code == 409
    assert "PAPER_NOT_READY" in resp.json()["error"]["code"]


@requires_db
@pytest.mark.asyncio
async def test_invalid_task_type_rejected(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client))
    finally:
        db.close()

    resp = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "EXPERIMENT_ANALYSIS"})
    assert resp.status_code == 422
    assert "TASK_TYPE_NOT_SUPPORTED" in resp.json()["error"]["code"]


@requires_db
@pytest.mark.asyncio
async def test_invalid_dimensions_rejected(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client))
    finally:
        db.close()

    resp = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks",
        json={"task_type": "REVIEW", "options": {"dimensions": ["INVALID"]}},
    )
    assert resp.status_code == 422


@requires_db
@pytest.mark.asyncio
async def test_duplicate_dimensions_rejected(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client))
    finally:
        db.close()

    resp = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks",
        json={"task_type": "REVIEW", "options": {"dimensions": ["OVERALL", "OVERALL"]}},
    )
    assert resp.status_code == 422


@requires_db
@pytest.mark.asyncio
async def test_unknown_alias_finding_unverified(db_client: AsyncClient):
    unknown_alias_llm = FakeUnknownAliasLLM()
    app.dependency_overrides[get_llm_client] = lambda: unknown_alias_llm

    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client), evidence_count=2)
    finally:
        db.close()

    task_resp = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "REVIEW"})
    task_id = task_resp.json()["id"]

    import time
    deadline = time.time() + 15
    while time.time() < deadline:
        r = await db_client.get(f"/api/v1/tasks/{task_id}")
        if r.json()["status"] in ("SUCCEEDED", "FAILED"):
            break
        time.sleep(0.5)

    assert r.json()["status"] == "SUCCEEDED"

    reviews_resp = await db_client.get(f"/api/v1/papers/{paper_id}/reviews")
    reviews = reviews_resp.json()["reviews"]
    for rev in reviews:
        assert len(rev["findings"]) == 0

    db = SessionLocal()
    try:
        findings = db.query(ReviewFinding).filter(ReviewFinding.verification_status == "UNVERIFIED").all()
        assert len(findings) >= 1
        fe_count = db.query(FindingEvidence).join(ReviewFinding).filter(ReviewFinding.verification_status == "UNVERIFIED").count()
        assert fe_count == 0
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
async def test_bad_json_llm_task_fails(db_client: AsyncClient):
    bad_json_llm = FakeBadJsonLLM()
    app.dependency_overrides[get_llm_client] = lambda: bad_json_llm

    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client), evidence_count=2)
    finally:
        db.close()

    task_resp = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "REVIEW"})
    task_id = task_resp.json()["id"]

    import time
    deadline = time.time() + 15
    while time.time() < deadline:
        r = await db_client.get(f"/api/v1/tasks/{task_id}")
        if r.json()["status"] in ("SUCCEEDED", "FAILED"):
            break
        time.sleep(0.5)

    assert r.json()["status"] == "FAILED"
    error_msg = r.json()["error_message"]
    assert "/tmp/" not in error_msg
    assert "Traceback" not in error_msg
    assert "SELECT" not in error_msg

    db = SessionLocal()
    try:
        review_count = db.query(ReviewResult).filter(ReviewResult.task_id == task_id).count()
        assert review_count == 0
        finding_count = db.query(ReviewFinding).join(ReviewResult).filter(ReviewResult.task_id == task_id).count()
        assert finding_count == 0
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
@pytest.mark.parametrize("fail_on_call", [1, 2])
async def test_embedding_failure_rolls_back_entire_result_batch(
    db_client: AsyncClient,
    fail_on_call: int,
):
    failing_embedding = FakeFailingEmbeddingClient(fail_on_call)
    app.dependency_overrides[get_embedding_client] = lambda: failing_embedding

    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client), evidence_count=2)
    finally:
        db.close()

    response = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks",
        json={"task_type": "REVIEW", "options": {"dimensions": ["OVERALL"]}},
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    task_response = await db_client.get(f"/api/v1/tasks/{task_id}")
    task_data = task_response.json()
    assert task_data["status"] == "FAILED"
    assert "secret-embedding-failure" not in task_data["error_message"]

    db = SessionLocal()
    try:
        assert db.query(ReviewResult).filter(ReviewResult.task_id == task_id).count() == 0
        assert (
            db.query(ReviewFinding)
            .join(ReviewResult)
            .filter(ReviewResult.task_id == task_id)
            .count()
            == 0
        )
        assert (
            db.query(FindingEvidence)
            .join(ReviewFinding)
            .join(ReviewResult)
            .filter(ReviewResult.task_id == task_id)
            .count()
            == 0
        )
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
async def test_list_tasks_for_paper(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client))
    finally:
        db.close()

    resp = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "REVIEW"})
    assert resp.status_code == 201

    list_resp = await db_client.get(f"/api/v1/papers/{paper_id}/tasks")
    assert list_resp.status_code == 200
    tasks = list_resp.json()["items"]
    assert len(tasks) >= 1


@requires_db
@pytest.mark.asyncio
async def test_second_dimension_failure_rolls_back_entire_result_batch(db_client: AsyncClient):
    failing_llm = FakeSecondDimensionBadLLM()
    app.dependency_overrides[get_llm_client] = lambda: failing_llm

    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client))
    finally:
        db.close()

    response = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks",
        json={
            "task_type": "REVIEW",
            "options": {"dimensions": ["SOUNDNESS", "OVERALL"], "language": "zh"},
        },
    )
    task_id = response.json()["id"]

    task_response = await db_client.get(f"/api/v1/tasks/{task_id}")
    assert task_response.json()["status"] == "FAILED"
    assert "secret-second-dimension" not in task_response.json()["error_message"]

    db = SessionLocal()
    try:
        assert db.query(ReviewResult).filter(ReviewResult.task_id == task_id).count() == 0
        assert (
            db.query(ReviewFinding)
            .join(ReviewResult)
            .filter(ReviewResult.task_id == task_id)
            .count()
            == 0
        )
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
async def test_invalid_review_options_rejected(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db, user_id=_get_test_user_id(db_client))
    finally:
        db.close()

    invalid_bodies = [
        {"task_type": "REVIEW", "options": {"dimensions": [], "language": "zh"}},
        {"task_type": "REVIEW", "options": {"dimensions": ["OVERALL"], "language": "fr"}},
        {"options": {"dimensions": ["OVERALL"]}},
        {"task_type": "REVIEW", "unexpected": True},
    ]
    for body in invalid_bodies:
        response = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json=body)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@requires_db
@pytest.mark.asyncio
async def test_other_user_resources_are_isolated(db_client: AsyncClient):
    db = SessionLocal()
    try:
        other_user = User(
            id="other-user",
            email="other@example.com",
            email_normalized="other@example.com",
            display_name="Other User",
            password_hash=hash_password("OtherUserPass123!@#"),
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            failed_login_count=0,
        )
        db.add(other_user)
        db.flush()
        paper_id = _create_parsed_paper_with_evidence(db, user_id="other-user")
        task = AnalysisTask(
            paper_id=paper_id,
            task_type="REVIEW",
            status="PENDING",
            progress=0,
            user_id="other-user",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
    finally:
        db.close()

    create_response = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks",
        json={"task_type": "REVIEW"},
    )
    assert create_response.status_code == 403
    assert (await db_client.get(f"/api/v1/papers/{paper_id}/tasks")).status_code == 403
    assert (await db_client.get(f"/api/v1/papers/{paper_id}/reviews")).status_code == 403
    assert (await db_client.get(f"/api/v1/tasks/{task_id}")).status_code == 404


@requires_db
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/api/v1/tasks/not-a-uuid", None),
        ("get", "/api/v1/papers/not-a-uuid/tasks", None),
        ("get", "/api/v1/papers/not-a-uuid/reviews", None),
        ("post", "/api/v1/papers/not-a-uuid/tasks", {"task_type": "REVIEW"}),
    ],
)
async def test_invalid_uuid_paths_return_422(
    db_client: AsyncClient,
    method: str,
    path: str,
    body: dict | None,
):
    response = await db_client.request(method, path, json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@requires_db
@pytest.mark.asyncio
async def test_evidence_candidate_order_and_top_k(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = str(uuid.uuid4())
        db.add(
            Paper(
                id=paper_id,
                title="Candidate order",
                filename="candidate.pdf",
                storage_key=f"papers/{paper_id}/source.pdf",
                file_size=1000,
                file_hash="d" * 64,
                status=PaperStatus.PARSED,
                user_id=_get_test_user_id(db_client),
            )
        )
        base_time = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        expected = []
        for index in range(10):
            evidence_id = str(uuid.UUID(int=index + 1))
            page_number = 1 if index < 9 else 2
            db.add(
                Evidence(
                    id=evidence_id,
                    paper_id=paper_id,
                    quoted_text=f"ordered-{index}",
                    page_number=page_number,
                    evidence_type=EvidenceType.TEXT,
                    created_at=base_time + datetime.timedelta(seconds=index),
                )
            )
            if index < 8:
                expected.append(evidence_id)
        db.commit()

        candidates = select_evidence_candidates(paper_id, db)
        assert [evidence_id for evidence_id, _text in candidates] == expected
        assert len(candidates) == 8
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
async def test_task_not_found_returns_404(db_client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await db_client.get(f"/api/v1/tasks/{fake_id}")
    assert resp.status_code == 404


@requires_db
@pytest.mark.asyncio
async def test_paper_not_found_returns_404(db_client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await db_client.post(f"/api/v1/papers/{fake_id}/tasks", json={"task_type": "REVIEW"})
    assert resp.status_code == 404


@requires_db
@pytest.mark.asyncio
async def test_reviews_for_nonexistent_paper_returns_404(db_client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await db_client.get(f"/api/v1/papers/{fake_id}/reviews")
    assert resp.status_code == 404
