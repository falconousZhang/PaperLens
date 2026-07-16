import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event

from paperlens.core.database import SessionLocal, configure_engine, get_engine
from paperlens.core.enums import (
    CheckpointType,
    ExperimentFileType,
    PaperStatus,
    TaskStatus,
    TaskType,
    UserRole,
    UserStatus,
)
from paperlens.core.errors import AppError
from paperlens.main import app
from paperlens.models.models import (
    AnalysisTask,
    ExperimentFile,
    ExperimentResult,
    MetricRecord,
    Paper,
    PaperTable,
    User,
)
from paperlens.services.auth_service import create_session_for_user
from paperlens.services.experiment_comparison_service import create_comparisons
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


def _add_user(db, email: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        email_normalized=email.casefold(),
        display_name=email.split("@", 1)[0],
        password_hash=hash_password("CompTest123!"),
        role=role,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )
    db.add(user)
    db.flush()
    return user


def _add_paper(db, user_id: str, title="Comparison Test Paper") -> Paper:
    paper = Paper(
        id=str(uuid.uuid4()),
        title=title,
        filename=f"{uuid.uuid4()}.pdf",
        storage_key=f"papers/{uuid.uuid4()}/source.pdf",
        file_size=1000,
        file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        status=PaperStatus.PARSED,
        user_id=user_id,
    )
    db.add(paper)
    db.flush()
    return paper


def _numeric_column(name="accuracy", mean=0.9, maximum=0.92, dtype="float"):
    return {
        "name": name,
        "dtype": dtype,
        "count": 3,
        "null_count": 0,
        "stats": {
            "mean": mean,
            "stddev": 0.02,
            "min": min(mean, maximum),
            "max": maximum,
            "median": mean,
        },
    }


def _add_experiment_graph(db, paper: Paper, columns=None):
    columns = columns or [_numeric_column()]
    file_id = str(uuid.uuid4())
    exp_file = ExperimentFile(
        id=file_id,
        paper_id=paper.id,
        filename="data.csv",
        storage_key=f"experiments/{paper.user_id}/{paper.id}/{file_id}/source.csv",
        file_size=32,
        file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        file_type=ExperimentFileType.CSV,
        row_count=3,
        column_count=len(columns),
        columns_info={
            "version": 1,
            "encoding": "utf-8",
            "delimiter": ",",
            "sheet_name": None,
            "columns": [
                {
                    "name": column["name"],
                    "dtype": column["dtype"],
                    "nullable": False,
                    "null_count": 0,
                }
                for column in columns
            ],
        },
        user_id=paper.user_id,
    )
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        paper_id=paper.id,
        task_type=TaskType.EXPERIMENT_ANALYSIS,
        status=TaskStatus.SUCCEEDED,
        progress=100,
        user_id=paper.user_id,
        experiment_file_id=file_id,
    )
    result = ExperimentResult(
        id=str(uuid.uuid4()),
        file_id=file_id,
        task_id=task.id,
        summary_stats={
            "version": 1,
            "row_count": 3,
            "column_count": len(columns),
            "columns": columns,
        },
        column_analysis=None,
        metric_comparisons=None,
    )
    db.add(exp_file)
    db.flush()
    db.add(task)
    db.flush()
    db.add(result)
    db.flush()
    return exp_file, task, result


def _add_metric_task(
    db,
    paper: Paper,
    metrics,
    status=TaskStatus.SUCCEEDED,
    task_type=TaskType.METRIC_EXTRACTION,
    table_index=1,
    user_id=None,
):
    owner_id = user_id or paper.user_id
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        paper_id=paper.id,
        task_type=task_type,
        status=status,
        progress=100 if status == TaskStatus.SUCCEEDED else 0,
        user_id=owner_id,
    )
    db.add(task)
    db.flush()
    records = []
    if metrics:
        table = PaperTable(
            id=str(uuid.uuid4()),
            paper_id=paper.id,
            page_number=1,
            table_index=table_index,
            structured_data={"headers": ["metric", "value"], "rows": [["accuracy", "0.9"]]},
            raw_text="accuracy: 0.9",
        )
        db.add(table)
        db.flush()
        for index, metric in enumerate(metrics):
            record = MetricRecord(
                id=str(uuid.uuid4()),
                paper_id=paper.id,
                task_id=task.id,
                user_id=owner_id,
                metric_name=metric.get("name", "accuracy"),
                metric_value=metric.get("value", 0.9),
                checkpoint_type=metric.get("checkpoint", CheckpointType.MEAN),
                raw_text="private source text",
                table_id=table.id,
                row_index=index,
            )
            db.add(record)
            records.append(record)
    db.flush()
    return task, records


def _token_for(db, user: User) -> str:
    access_token, _ = create_session_for_user(db, user)
    db.flush()
    return access_token


@pytest_asyncio.fixture
async def db_client(tmp_path, monkeypatch):
    test_url = get_test_db_url()
    if not test_url:
        if is_test_db_required():
            pytest.fail("PAPERLENS_REQUIRE_TEST_DB=true but PAPERLENS_TEST_DATABASE_URL is not set")
        pytest.skip("需要 PAPERLENS_TEST_DATABASE_URL")
    ensure_test_database()
    run_alembic_migrations(test_url)
    configure_engine(test_url)
    assert "paperlens_test" in str(get_engine().url)
    monkeypatch.setattr("paperlens.core.config.settings.storage_root", str(tmp_path / "storage"))
    db = SessionLocal()
    try:
        user = _add_user(db, "comparison-owner@example.com")
        token = _token_for(db, user)
        db.commit()
        user_id = user.id
    finally:
        db.close()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            client._test_user_id = user_id
            yield client
    finally:
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def _owner_id(client: AsyncClient) -> str:
    return client._test_user_id


def _setup_ready_comparison(client: AsyncClient, metrics=None, columns=None, table_index=1):
    db = SessionLocal()
    try:
        paper = _add_paper(db, _owner_id(client))
        exp_file, analysis_task, result = _add_experiment_graph(db, paper, columns)
        metric_task, records = _add_metric_task(
            db,
            paper,
            metrics if metrics is not None else [{"name": "accuracy", "value": 0.9}],
            table_index=table_index,
        )
        db.commit()
        return paper.id, exp_file.id, analysis_task.id, result.id, metric_task.id, [record.id for record in records]
    finally:
        db.close()


def _thread_call(file_id: str, metric_task_id: str, user_id: str, barrier: threading.Barrier):
    db = SessionLocal()
    try:
        barrier.wait(timeout=10)
        outcome = create_comparisons(file_id, metric_task_id, user_id, db)
        return "ok", outcome.duplicate, outcome.metric_task_id
    except AppError as exc:
        return "error", exc.status_code, exc.code
    finally:
        db.close()


@requires_db
class TestExperimentComparisonApi:
    async def test_requires_authentication(self, db_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/experiment-files/{uuid.uuid4()}/comparisons",
                json={"metric_task_id": str(uuid.uuid4())},
            )
        assert response.status_code == 401

    @pytest.mark.parametrize(
        "payload",
        [
            {"metric_task_id": "not-a-uuid"},
            {"metric_task_id": str(uuid.uuid4()), "extra": True},
            {},
        ],
    )
    async def test_request_schema_is_strict(self, db_client, payload):
        response = await db_client.post(
            f"/api/v1/experiment-files/{uuid.uuid4()}/comparisons",
            json=payload,
        )
        assert response.status_code == 422

    async def test_first_create_returns_strict_201(self, db_client):
        _, file_id, _, result_id, metric_task_id, _ = _setup_ready_comparison(db_client)
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": metric_task_id},
        )
        assert response.status_code == 201
        data = response.json()
        assert set(data) == {
            "file_id",
            "experiment_result_id",
            "metric_task_id",
            "comparisons",
            "duplicate",
        }
        assert data["file_id"] == file_id
        assert data["experiment_result_id"] == result_id
        assert data["metric_task_id"] == metric_task_id
        assert data["duplicate"] is False
        comparison = data["comparisons"][0]
        assert set(comparison) == {
            "metric_record_id",
            "metric_task_id",
            "metric_name",
            "checkpoint_type",
            "column_name",
            "statistic",
            "paper_value",
            "experiment_value",
            "diff",
            "absolute_diff",
            "relative_diff",
            "allowed_diff",
            "status",
            "reason",
        }
        assert comparison["status"] == "MATCH"
        assert comparison["statistic"] == "MEAN"
        assert "raw_text" not in str(data)

    async def test_same_task_is_idempotent_200(self, db_client):
        _, file_id, _, _, metric_task_id, _ = _setup_ready_comparison(db_client)
        first = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": metric_task_id},
        )
        second = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": metric_task_id},
        )
        assert first.status_code == 201
        assert second.status_code == 200
        assert second.json()["duplicate"] is True
        assert second.json()["comparisons"] == first.json()["comparisons"]

    async def test_different_task_cannot_overwrite(self, db_client):
        paper_id, file_id, _, _, first_task_id, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        try:
            paper = db.get(Paper, paper_id)
            second_task, _ = _add_metric_task(
                db,
                paper,
                [{"name": "accuracy", "value": 0.8}],
                table_index=2,
            )
            db.commit()
            second_task_id = second_task.id
        finally:
            db.close()
        assert (
            await db_client.post(
                f"/api/v1/experiment-files/{file_id}/comparisons",
                json={"metric_task_id": first_task_id},
            )
        ).status_code == 201
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": second_task_id},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "COMPARISON_ALREADY_EXISTS"

    async def test_get_result_is_null_before_and_strict_after(self, db_client):
        _, file_id, _, _, metric_task_id, _ = _setup_ready_comparison(db_client)
        before = await db_client.get(f"/api/v1/experiment-files/{file_id}/result")
        assert before.status_code == 200
        assert before.json()["metric_comparisons"] is None
        await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": metric_task_id},
        )
        after = await db_client.get(f"/api/v1/experiment-files/{file_id}/result")
        assert after.status_code == 200
        assert after.json()["metric_comparisons"][0]["metric_task_id"] == metric_task_id

    async def test_missing_analysis_result_returns_404(self, db_client):
        db = SessionLocal()
        try:
            paper = _add_paper(db, _owner_id(db_client))
            metric_task, _ = _add_metric_task(db, paper, [{"name": "accuracy", "value": 0.9}])
            exp_file = ExperimentFile(
                id=str(uuid.uuid4()),
                paper_id=paper.id,
                filename="data.csv",
                storage_key="experiments/missing/source.csv",
                file_size=10,
                file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                file_type=ExperimentFileType.CSV,
                row_count=1,
                column_count=1,
                columns_info={
                    "version": 1,
                    "encoding": "utf-8",
                    "delimiter": ",",
                    "sheet_name": None,
                    "columns": [{"name": "accuracy", "dtype": "float", "nullable": False, "null_count": 0}],
                },
                user_id=paper.user_id,
            )
            db.add(exp_file)
            db.commit()
            file_id = exp_file.id
            metric_task_id = metric_task.id
        finally:
            db.close()
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": metric_task_id},
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESULT_NOT_READY"

    async def test_no_metrics_is_409_and_does_not_persist(self, db_client):
        paper_id, file_id, _, result_id, _, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        try:
            paper = db.get(Paper, paper_id)
            empty_task, _ = _add_metric_task(db, paper, [], table_index=2)
            db.commit()
            empty_task_id = empty_task.id
        finally:
            db.close()
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": empty_task_id},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "NO_METRICS"
        verify = SessionLocal()
        try:
            assert verify.get(ExperimentResult, result_id).metric_comparisons is None
        finally:
            verify.close()

    @pytest.mark.parametrize(
        ("task_type", "status", "expected_code"),
        [
            (TaskType.REVIEW, TaskStatus.SUCCEEDED, "TASK_TYPE_MISMATCH"),
            (TaskType.METRIC_EXTRACTION, TaskStatus.FAILED, "TASK_NOT_SUCCEEDED"),
        ],
    )
    async def test_wrong_metric_task_type_or_status(self, db_client, task_type, status, expected_code):
        paper_id, file_id, _, _, _, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        try:
            paper = db.get(Paper, paper_id)
            task, _ = _add_metric_task(db, paper, [], task_type=task_type, status=status, table_index=2)
            db.commit()
            task_id = task.id
        finally:
            db.close()
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": task_id},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == expected_code

    async def test_metric_task_for_other_paper_is_409(self, db_client):
        _, file_id, _, _, _, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        try:
            other_paper = _add_paper(db, _owner_id(db_client), "Other paper")
            task, _ = _add_metric_task(db, other_paper, [{"name": "accuracy", "value": 0.9}])
            db.commit()
            task_id = task.id
        finally:
            db.close()
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": task_id},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PAPER_MISMATCH"

    async def test_admin_cannot_read_another_users_file(self, db_client):
        _, file_id, _, _, metric_task_id, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        try:
            admin = _add_user(db, "comparison-admin@example.com", UserRole.ADMIN)
            token = _token_for(db, admin)
            db.commit()
        finally:
            db.close()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as admin_client:
            response = await admin_client.post(
                f"/api/v1/experiment-files/{file_id}/comparisons",
                json={"metric_task_id": metric_task_id},
            )
        assert response.status_code == 404

    async def test_other_users_metric_task_is_hidden(self, db_client):
        paper_id, file_id, _, _, _, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        try:
            other_user = _add_user(db, "comparison-other@example.com")
            paper = db.get(Paper, paper_id)
            task, _ = _add_metric_task(
                db,
                paper,
                [{"name": "accuracy", "value": 0.9}],
                user_id=other_user.id,
                table_index=2,
            )
            db.commit()
            task_id = task.id
        finally:
            db.close()
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": task_id},
        )
        assert response.status_code == 404

    async def test_duplicate_paper_metrics_persist_honest_unverifiable_items(self, db_client):
        _, file_id, _, _, task_id, _ = _setup_ready_comparison(
            db_client,
            metrics=[
                {"name": "F1_score", "value": 0.9},
                {"name": "f1 score", "value": 0.91},
            ],
            columns=[_numeric_column("f1 score")],
        )
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": task_id},
        )
        assert response.status_code == 201
        items = response.json()["comparisons"]
        assert len(items) == 2
        assert {item["status"] for item in items} == {"UNVERIFIABLE"}
        assert {item["reason"] for item in items} == {"AMBIGUOUS_PAPER_METRIC"}

    async def test_all_unsupported_checkpoints_still_persist(self, db_client):
        _, file_id, _, _, task_id, _ = _setup_ready_comparison(
            db_client,
            metrics=[
                {"name": "accuracy", "value": 0.9, "checkpoint": CheckpointType.BEST},
                {"name": "loss", "value": 0.2, "checkpoint": CheckpointType.FINAL},
            ],
            columns=[_numeric_column(), _numeric_column("loss", mean=0.2, maximum=0.3)],
        )
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": task_id},
        )
        assert response.status_code == 201
        assert {item["reason"] for item in response.json()["comparisons"]} == {"UNSUPPORTED_CHECKPOINT"}

    async def test_metric_source_relation_tampering_is_rejected(self, db_client):
        paper_id, file_id, _, result_id, task_id, record_ids = _setup_ready_comparison(db_client)
        db = SessionLocal()
        try:
            other_paper = _add_paper(db, _owner_id(db_client), "Source mismatch")
            other_table = PaperTable(
                id=str(uuid.uuid4()),
                paper_id=other_paper.id,
                page_number=1,
                table_index=1,
                structured_data={"headers": ["metric"], "rows": [["accuracy"]]},
                raw_text="private",
            )
            db.add(other_table)
            db.flush()
            db.get(MetricRecord, record_ids[0]).table_id = other_table.id
            db.commit()
        finally:
            db.close()
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": task_id},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "METRIC_STATE_INVALID"
        verify = SessionLocal()
        try:
            assert verify.get(ExperimentResult, result_id).metric_comparisons is None
        finally:
            verify.close()

    async def test_analysis_relation_tampering_is_rejected(self, db_client):
        _, file_id, analysis_task_id, _, metric_task_id, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        try:
            other_paper = _add_paper(db, _owner_id(db_client), "Analysis mismatch")
            db.get(AnalysisTask, analysis_task_id).paper_id = other_paper.id
            db.commit()
        finally:
            db.close()
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": metric_task_id},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "COMPARISON_STATE_INVALID"

    async def test_corrupt_stored_comparison_is_hidden(self, db_client):
        _, file_id, _, result_id, _, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        try:
            db.get(ExperimentResult, result_id).metric_comparisons = [{"raw_text": "private"}]
            db.commit()
        finally:
            db.close()
        response = await db_client.get(f"/api/v1/experiment-files/{file_id}/result")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "ANALYSIS_STATE_INVALID"
        assert "private" not in response.text

    async def test_same_source_true_concurrency_returns_201_and_200_semantics(self, db_client):
        _, file_id, _, _, metric_task_id, _ = _setup_ready_comparison(db_client)
        barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(_thread_call, file_id, metric_task_id, _owner_id(db_client), barrier)
                for _ in range(2)
            ]
            results = [future.result(timeout=20) for future in futures]
        assert sorted((result[0], result[1]) for result in results) == [("ok", False), ("ok", True)]

    async def test_different_sources_true_concurrency_allows_only_one(self, db_client):
        paper_id, file_id, _, _, first_task_id, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        try:
            paper = db.get(Paper, paper_id)
            second_task, _ = _add_metric_task(
                db,
                paper,
                [{"name": "accuracy", "value": 0.8}],
                table_index=2,
            )
            db.commit()
            second_task_id = second_task.id
        finally:
            db.close()
        barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(_thread_call, file_id, task_id, _owner_id(db_client), barrier)
                for task_id in (first_task_id, second_task_id)
            ]
            results = [future.result(timeout=20) for future in futures]
        assert sum(result[0] == "ok" for result in results) == 1
        error = next(result for result in results if result[0] == "error")
        assert error[1:] == (409, "COMPARISON_ALREADY_EXISTS")

    async def test_flush_failure_rolls_back_json(self, db_client, monkeypatch):
        _, file_id, _, result_id, metric_task_id, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        monkeypatch.setattr(db, "flush", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("flush failed")))
        try:
            with pytest.raises(RuntimeError, match="flush failed"):
                create_comparisons(file_id, metric_task_id, _owner_id(db_client), db)
        finally:
            db.close()
        verify = SessionLocal()
        try:
            assert verify.get(ExperimentResult, result_id).metric_comparisons is None
        finally:
            verify.close()

    async def test_pre_commit_failure_rolls_back_json(self, db_client, monkeypatch):
        _, file_id, _, result_id, metric_task_id, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))
        try:
            with pytest.raises(RuntimeError, match="commit failed"):
                create_comparisons(file_id, metric_task_id, _owner_id(db_client), db)
        finally:
            db.close()
        verify = SessionLocal()
        try:
            assert verify.get(ExperimentResult, result_id).metric_comparisons is None
        finally:
            verify.close()

    async def test_post_commit_exception_recovers_committed_success(self, db_client, monkeypatch):
        _, file_id, _, result_id, metric_task_id, _ = _setup_ready_comparison(db_client)
        db = SessionLocal()
        real_commit = db.commit

        def commit_then_raise():
            real_commit()
            raise RuntimeError("connection result unknown")

        monkeypatch.setattr(db, "commit", commit_then_raise)
        try:
            outcome = create_comparisons(file_id, metric_task_id, _owner_id(db_client), db)
        finally:
            db.close()
        assert outcome.duplicate is False
        assert outcome.metric_task_id == metric_task_id
        verify = SessionLocal()
        try:
            assert verify.get(ExperimentResult, result_id).metric_comparisons is not None
        finally:
            verify.close()

    async def test_comparison_does_not_construct_model_clients(self, db_client, monkeypatch):
        _, file_id, _, _, metric_task_id, _ = _setup_ready_comparison(db_client)

        def forbidden(*args, **kwargs):
            raise AssertionError("model client must not be constructed")

        monkeypatch.setattr("paperlens.services.llm_client.get_llm_client", forbidden)
        monkeypatch.setattr("paperlens.services.embedding_client.get_embedding_client", forbidden)
        statements = []

        def capture_statement(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement.casefold())

        event.listen(get_engine(), "before_cursor_execute", capture_statement)
        response = await db_client.post(
            f"/api/v1/experiment-files/{file_id}/comparisons",
            json={"metric_task_id": metric_task_id},
        )
        event.remove(get_engine(), "before_cursor_execute", capture_statement)
        assert response.status_code == 201
        metric_selects = [statement for statement in statements if "from metric_records" in statement]
        table_selects = [statement for statement in statements if "from paper_tables" in statement]
        assert metric_selects and all("raw_text" not in statement for statement in metric_selects)
        assert table_selects and all("raw_text" not in statement and "structured_data" not in statement for statement in table_selects)
