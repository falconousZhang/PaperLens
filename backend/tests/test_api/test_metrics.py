import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from paperlens.core.database import SessionLocal, configure_engine, get_engine
from paperlens.core.enums import (
    CheckpointType,
    PaperStatus,
    TaskStatus,
    TaskType,
    UserRole,
    UserStatus,
)
from paperlens.main import app
from paperlens.models.models import AnalysisTask, Evidence, MetricRecord, Paper, PaperTable, User
from paperlens.services.auth_service import create_session_for_user
from paperlens.services.embedding_client import EmbeddingClient, get_embedding_client
from paperlens.services.llm_client import LLMClient, get_llm_client
from paperlens.services.metric_service import run_metric_extraction_task
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


class _FakeLLMClient(LLMClient):
    def chat(self, messages: list[dict], **kwargs) -> dict:
        return {"role": "assistant", "content": "{}"}


class _FakeEmbeddingClient(EmbeddingClient):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 8 for _ in texts]


def _add_user(db, email: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        email_normalized=email.casefold(),
        display_name=email.split("@", 1)[0],
        password_hash=hash_password("MetricTestPassword123!"),
        role=role,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )
    db.add(user)
    db.flush()
    return user


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
    assert "paperlens_test" in str(get_engine().url)

    app.dependency_overrides[get_llm_client] = lambda: _FakeLLMClient()
    app.dependency_overrides[get_embedding_client] = lambda: _FakeEmbeddingClient()
    db = SessionLocal()
    try:
        user = _add_user(db, "metric-owner@example.com")
        access_token, _ = create_session_for_user(db, user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {access_token}"},
        ) as client:
            client._test_user_id = user_id
            yield client
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
        app.dependency_overrides.pop(get_embedding_client, None)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def _user_id(client: AsyncClient) -> str:
    value = getattr(client, "_test_user_id", None)
    assert value is not None
    return value


def _create_paper(
    db,
    user_id: str,
    status: PaperStatus = PaperStatus.PARSED,
    with_metrics: bool = True,
) -> tuple[str, str | None, str | None]:
    paper_id = str(uuid.uuid4())
    db.add(
        Paper(
            id=paper_id,
            title="Metric Test Paper",
            filename=f"{paper_id}.pdf",
            storage_key=f"papers/{paper_id}/source.pdf",
            file_size=1000,
            file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
            status=status,
            user_id=user_id,
        )
    )
    db.flush()
    table_id = None
    evidence_id = None
    if with_metrics:
        table = PaperTable(
            paper_id=paper_id,
            page_number=1,
            table_index=1,
            caption="Best checkpoint results",
            structured_data={
                "headers": ["Model", "Dataset", "Accuracy", "F1", "Loss"],
                "rows": [
                    ["BERT-base", "SQuAD 2.0", "92.5%", "90.1%", "0.15"],
                    ["RoBERTa", "SQuAD 2.0", "94.1%", "92.3%", "0.12"],
                ],
            },
            raw_text="Model | Dataset | Accuracy | F1 | Loss",
        )
        db.add(table)
        db.flush()
        table_id = table.id
        evidence = Evidence(
            paper_id=paper_id,
            quoted_text="At the final checkpoint, accuracy = 95.3%.",
            page_number=2,
            evidence_type="TEXT",
        )
        db.add(evidence)
        db.flush()
        evidence_id = evidence.id
    db.commit()
    return paper_id, table_id, evidence_id


def _add_finished_task(db, paper_id: str, user_id: str) -> AnalysisTask:
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        paper_id=paper_id,
        task_type=TaskType.METRIC_EXTRACTION,
        status=TaskStatus.SUCCEEDED,
        progress=100,
        user_id=user_id,
    )
    db.add(task)
    db.flush()
    return task


def _add_metric(
    db,
    paper_id: str,
    task_id: str,
    user_id: str,
    table_id: str,
    metric_name: str = "accuracy",
    metric_value: float = 0.95,
    dataset_name: str | None = "SQuAD 2.0",
    checkpoint_type: CheckpointType = CheckpointType.UNKNOWN,
) -> MetricRecord:
    record = MetricRecord(
        id=str(uuid.uuid4()),
        paper_id=paper_id,
        task_id=task_id,
        user_id=user_id,
        model_name="BERT-base",
        dataset_name=dataset_name,
        metric_name=metric_name,
        metric_value=metric_value,
        checkpoint_type=checkpoint_type,
        checkpoint_source=None,
        table_id=table_id,
        row_index=0,
        evidence_id=None,
        raw_text=f"{metric_name}: {metric_value}",
    )
    db.add(record)
    db.flush()
    return record


@requires_db
async def test_metric_task_reaches_succeeded_with_traceable_records(db_client):
    db = SessionLocal()
    try:
        paper_id, table_id, evidence_id = _create_paper(db, _user_id(db_client))
    finally:
        db.close()

    response = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks",
        json={"task_type": "METRIC_EXTRACTION", "options": {}},
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    db = SessionLocal()
    try:
        task = db.get(AnalysisTask, task_id)
        records = db.query(MetricRecord).filter(MetricRecord.task_id == task_id).all()
        assert task.status == TaskStatus.SUCCEEDED
        assert task.progress == 100
        assert task.error_message is None
        assert len(records) == 7
        assert {record.table_id for record in records if record.table_id} == {table_id}
        assert {record.evidence_id for record in records if record.evidence_id} == {evidence_id}
        assert all((record.table_id is None) != (record.evidence_id is None) for record in records)
        assert all(record.checkpoint_type in {item.value for item in CheckpointType} for record in records)
        assert all(record.raw_text for record in records)
        bert_accuracy = next(
            record
            for record in records
            if record.model_name == "BERT-base" and record.metric_name == "accuracy"
        )
        assert bert_accuracy.dataset_name == "SQuAD 2.0"
        assert bert_accuracy.metric_value == pytest.approx(0.925)
    finally:
        db.close()


@requires_db
@pytest.mark.parametrize(
    "body",
    [
        {"task_type": "METRIC_EXTRACTION", "options": {"dimensions": ["OVERALL"]}},
        {"task_type": "METRIC_EXTRACTION", "options": {"unknown": True}},
        {"task_type": "METRIC_EXTRACTION", "unexpected": True},
        {"task_type": "EXPERIMENT_ANALYSIS"},
    ],
)
async def test_metric_task_body_is_discriminated_and_strict(db_client, body):
    db = SessionLocal()
    try:
        paper_id, _, _ = _create_paper(db, _user_id(db_client))
    finally:
        db.close()
    response = await db_client.post(f"/api/v1/papers/{paper_id}/tasks", json=body)
    assert response.status_code == 422


@requires_db
async def test_no_real_candidates_returns_409_without_task(db_client):
    db = SessionLocal()
    try:
        paper_id, _, _ = _create_paper(db, _user_id(db_client), with_metrics=False)
        db.add(
            Evidence(
                paper_id=paper_id,
                quoted_text="This paragraph contains no experimental metric.",
                page_number=1,
                evidence_type="TEXT",
            )
        )
        db.commit()
    finally:
        db.close()
    response = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "METRIC_EXTRACTION"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NO_CANDIDATES"
    db = SessionLocal()
    try:
        assert db.query(AnalysisTask).filter(AnalysisTask.paper_id == paper_id).count() == 0
    finally:
        db.close()


@requires_db
async def test_non_parsed_paper_returns_409(db_client):
    db = SessionLocal()
    try:
        paper_id, _, _ = _create_paper(
            db, _user_id(db_client), status=PaperStatus.PROCESSING, with_metrics=False
        )
    finally:
        db.close()
    response = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "METRIC_EXTRACTION"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PAPER_NOT_READY"


@requires_db
async def test_duplicate_active_metric_task_returns_409(db_client):
    db = SessionLocal()
    try:
        paper_id, _, _ = _create_paper(db, _user_id(db_client))
        db.add(
            AnalysisTask(
                id=str(uuid.uuid4()),
                paper_id=paper_id,
                task_type=TaskType.METRIC_EXTRACTION,
                status=TaskStatus.PENDING,
                progress=0,
                user_id=_user_id(db_client),
            )
        )
        db.commit()
    finally:
        db.close()
    response = await db_client.post(
        f"/api/v1/papers/{paper_id}/tasks", json={"task_type": "METRIC_EXTRACTION"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_ALREADY_RUNNING"


@requires_db
async def test_database_rejects_second_active_metric_task(db_client):
    db = SessionLocal()
    try:
        paper_id, _, _ = _create_paper(db, _user_id(db_client))
        first = AnalysisTask(
            id=str(uuid.uuid4()),
            paper_id=paper_id,
            task_type=TaskType.METRIC_EXTRACTION,
            status=TaskStatus.RUNNING,
            progress=10,
            user_id=_user_id(db_client),
        )
        db.add(first)
        db.commit()
        db.add(
            AnalysisTask(
                id=str(uuid.uuid4()),
                paper_id=paper_id,
                task_type=TaskType.METRIC_EXTRACTION,
                status=TaskStatus.PENDING,
                progress=0,
                user_id=_user_id(db_client),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


@requires_db
async def test_metric_list_filters_pagination_and_query_strictness(db_client):
    db = SessionLocal()
    try:
        paper_id, table_id, _ = _create_paper(db, _user_id(db_client))
        task = _add_finished_task(db, paper_id, _user_id(db_client))
        first = _add_metric(db, paper_id, task.id, _user_id(db_client), table_id)
        _add_metric(
            db,
            paper_id,
            task.id,
            _user_id(db_client),
            table_id,
            metric_name="F1",
            metric_value=0.9,
            checkpoint_type=CheckpointType.BEST,
        )
        _add_metric(
            db,
            paper_id,
            task.id,
            _user_id(db_client),
            table_id,
            metric_name="loss",
            metric_value=-0.2,
            dataset_name="Other",
        )
        db.commit()
        task_id = task.id
        first_id = first.id
    finally:
        db.close()

    response = await db_client.get(
        f"/api/v1/papers/{paper_id}/metrics",
        params={
            "task_id": task_id,
            "metric_name": "accuracy",
            "dataset_name": "SQuAD 2.0",
            "checkpoint_type": "UNKNOWN",
            "page": 1,
            "page_size": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == first_id
    assert response.json()["items"][0]["metric_value"] == pytest.approx(0.95)

    assert (
        await db_client.get(
            f"/api/v1/papers/{paper_id}/metrics", params={"unknown": "value"}
        )
    ).status_code == 422
    assert (
        await db_client.get(
            f"/api/v1/papers/{paper_id}/metrics", params={"page_size": 101}
        )
    ).status_code == 422
    assert (
        await db_client.get(
            f"/api/v1/papers/{paper_id}/metrics", params={"task_id": "not-a-uuid"}
        )
    ).status_code == 422


@requires_db
async def test_metric_detail_and_list_enforce_user_and_admin_ownership(db_client):
    db = SessionLocal()
    try:
        owner_id = _user_id(db_client)
        paper_id, table_id, _ = _create_paper(db, owner_id)
        task = _add_finished_task(db, paper_id, owner_id)
        record = _add_metric(db, paper_id, task.id, owner_id, table_id)
        other = _add_user(db, "metric-other@example.com")
        other_token, _ = create_session_for_user(db, other)
        admin = _add_user(db, "metric-admin@example.com", UserRole.ADMIN)
        admin_token, _ = create_session_for_user(db, admin)
        db.commit()
        record_id = record.id
    finally:
        db.close()

    own_response = await db_client.get(f"/api/v1/metrics/{record_id}")
    assert own_response.status_code == 200
    assert own_response.json()["id"] == record_id

    for token in (other_token, admin_token):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            assert (await client.get(f"/api/v1/metrics/{record_id}")).status_code == 404
            assert (await client.get(f"/api/v1/papers/{paper_id}/metrics")).status_code == 403

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/papers/{paper_id}/metrics")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


@requires_db
async def test_invalid_second_source_fails_atomically_without_leaking_error(db_client, monkeypatch):
    db = SessionLocal()
    try:
        paper_id, table_id, _ = _create_paper(db, _user_id(db_client))
        task = AnalysisTask(
            id=str(uuid.uuid4()),
            paper_id=paper_id,
            task_type=TaskType.METRIC_EXTRACTION,
            status=TaskStatus.PENDING,
            progress=0,
            user_id=_user_id(db_client),
        )
        db.add(task)
        db.commit()
        task_id = task.id
    finally:
        db.close()

    valid = {
        "paper_id": paper_id,
        "model_name": None,
        "dataset_name": None,
        "metric_name": "accuracy",
        "metric_value": 0.9,
        "checkpoint_type": CheckpointType.UNKNOWN,
        "checkpoint_source": None,
        "table_id": table_id,
        "row_index": 0,
        "evidence_id": None,
        "raw_text": "Accuracy: 90%",
    }
    invalid = {
        **valid,
        "table_id": None,
        "row_index": None,
        "evidence_id": str(uuid.uuid4()),
        "raw_text": "Accuracy: 91%",
        "metric_value": 0.91,
    }
    monkeypatch.setattr(
        "paperlens.services.metric_service.extract_metrics_from_sources",
        lambda *_args: [valid, invalid],
    )
    run_metric_extraction_task(task_id)

    db = SessionLocal()
    try:
        task = db.get(AnalysisTask, task_id)
        assert task.status == TaskStatus.FAILED
        assert task.progress == 100
        assert task.error_message == "指标提取失败，请稍后重试"
        assert "Accuracy" not in task.error_message
        assert db.query(MetricRecord).filter(MetricRecord.task_id == task_id).count() == 0
    finally:
        db.close()


@requires_db
@pytest.mark.parametrize(
    "invalid_record",
    [
        {"metric_value": float("nan")},
        {"metric_value": float("inf")},
        {"table_id": None, "row_index": None, "evidence_id": None},
    ],
)
async def test_database_rejects_non_finite_or_untraceable_metric(db_client, invalid_record):
    db = SessionLocal()
    try:
        paper_id, table_id, _ = _create_paper(db, _user_id(db_client))
        task = _add_finished_task(db, paper_id, _user_id(db_client))
        db.commit()
        values = {
            "id": str(uuid.uuid4()),
            "paper_id": paper_id,
            "task_id": task.id,
            "user_id": _user_id(db_client),
            "metric_name": "loss",
            "metric_value": 0.1,
            "checkpoint_type": CheckpointType.UNKNOWN,
            "table_id": table_id,
            "row_index": 0,
            "evidence_id": None,
            "raw_text": "loss: 0.1",
        }
        values.update(invalid_record)
        db.add(MetricRecord(**values))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()
