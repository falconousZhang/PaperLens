import json
import uuid
import datetime
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from paperlens.main import app
from paperlens.core.database import configure_engine, get_engine, SessionLocal
from paperlens.core.enums import PaperStatus, EvidenceType
from paperlens.models.models import (
    AnalysisTask,
    Evidence,
    FindingEvidence,
    Paper,
    ReviewFinding,
    ReviewResult,
)
from paperlens.services.llm_client import LLMClient, get_llm_client
from paperlens.services.review_service import select_evidence_candidates
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
    app.dependency_overrides[get_llm_client] = lambda: default_llm

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def _create_parsed_paper_with_evidence(db, user_id="demo-user", evidence_count=2):
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
        paper_id = _create_parsed_paper_with_evidence(db)
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
        paper_id = _create_parsed_paper_with_evidence(db)
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
        paper_id = _create_parsed_paper_with_evidence(db, evidence_count=3)
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
            user_id="demo-user",
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
async def test_no_evidence_paper_cannot_create_task(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = str(uuid.uuid4())
        paper = Paper(
            id=paper_id,
            title="No Evidence",
            filename="test.pdf",
            storage_key=f"papers/{paper_id}/source.pdf",
            file_size=1000,
            file_hash="c" * 64,
            status=PaperStatus.PARSED,
            user_id="demo-user",
        )
        db.add(paper)
        db.commit()
    finally:
        db.close()

    resp = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "REVIEW"})
    assert resp.status_code == 409
    assert "NO_EVIDENCE" in resp.json()["error"]["code"]


@requires_db
@pytest.mark.asyncio
async def test_invalid_task_type_rejected(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db)
    finally:
        db.close()

    resp = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "METRIC_EXTRACTION"})
    assert resp.status_code == 422
    assert "TASK_TYPE_NOT_SUPPORTED" in resp.json()["error"]["code"]


@requires_db
@pytest.mark.asyncio
async def test_invalid_dimensions_rejected(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db)
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
        paper_id = _create_parsed_paper_with_evidence(db)
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
        paper_id = _create_parsed_paper_with_evidence(db, evidence_count=2)
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
        paper_id = _create_parsed_paper_with_evidence(db, evidence_count=2)
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
async def test_list_tasks_for_paper(db_client: AsyncClient):
    db = SessionLocal()
    try:
        paper_id = _create_parsed_paper_with_evidence(db)
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
        paper_id = _create_parsed_paper_with_evidence(db)
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
        paper_id = _create_parsed_paper_with_evidence(db)
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
                user_id="demo-user",
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
