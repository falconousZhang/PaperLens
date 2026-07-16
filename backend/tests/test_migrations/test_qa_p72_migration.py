import os
import subprocess
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

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


def _alembic(test_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PAPERLENS_DATABASE_URL"] = test_url
    return subprocess.run(
        ["alembic", *args],
        capture_output=True,
        text=True,
        env=environment,
    )


def _insert_owner_graph(connection):
    user_id = str(uuid.uuid4())
    paper_id = str(uuid.uuid4())
    evidence_id = str(uuid.uuid4())
    connection.execute(
        text(
            "INSERT INTO users "
            "(id, email, email_normalized, display_name, role, status, failed_login_count) "
            "VALUES (:id, :email, :email, 'qa migration', 'USER', 'ACTIVE', 0)"
        ),
        {"id": user_id, "email": f"qa-migration-{user_id}@example.com"},
    )
    connection.execute(
        text(
            "INSERT INTO papers "
            "(id, title, filename, storage_key, file_size, file_hash, status, user_id) "
            "VALUES (:id, 'QA migration', 'qa.pdf', 'qa/source.pdf', 1, :hash, 'PARSED', :user_id)"
        ),
        {"id": paper_id, "hash": "f" * 64, "user_id": user_id},
    )
    connection.execute(
        text(
            "INSERT INTO evidences "
            "(id, paper_id, quoted_text, page_number, evidence_type) "
            "VALUES (:id, :paper_id, 'migration evidence', 1, 'TEXT')"
        ),
        {"id": evidence_id, "paper_id": paper_id},
    )
    return user_id, paper_id, evidence_id


@requires_db
def test_qa_migration_round_trip_and_lossless_abort():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        at_014 = _alembic(test_url, "downgrade", "014_learning_contract_hardening")
        assert at_014.returncode == 0, at_014.stderr
        with engine.begin() as connection:
            user_id, paper_id, _ = _insert_owner_graph(connection)

        upgraded = _alembic(test_url, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT count(*) FROM users WHERE id = :id"),
                {"id": user_id},
            ).scalar_one() == 1
            assert connection.execute(
                text("SELECT count(*) FROM papers WHERE id = :id"),
                {"id": paper_id},
            ).scalar_one() == 1

        empty_down = _alembic(test_url, "downgrade", "014_learning_contract_hardening")
        assert empty_down.returncode == 0, empty_down.stderr
        empty_up = _alembic(test_url, "upgrade", "head")
        assert empty_up.returncode == 0, empty_up.stderr

        conversation_id = str(uuid.uuid4())
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO paper_qa_conversations (id, user_id, paper_id) "
                    "VALUES (:id, :user_id, :paper_id)"
                ),
                {
                    "id": conversation_id,
                    "user_id": user_id,
                    "paper_id": paper_id,
                },
            )

        refused = _alembic(test_url, "downgrade", "014_learning_contract_hardening")
        assert refused.returncode != 0
        current = _alembic(test_url, "current")
        assert current.returncode == 0
        assert "017_admin_audit_logs" in current.stdout
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT count(*) FROM paper_qa_conversations WHERE id = :id"),
                {"id": conversation_id},
            ).scalar_one() == 1
    finally:
        engine.dispose()
        run_alembic_migrations(test_url)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


@requires_db
def test_qa_database_constraints_and_active_turn_uniqueness():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        conversation_id = str(uuid.uuid4())
        with engine.begin() as connection:
            user_id, paper_id, _ = _insert_owner_graph(connection)
            connection.execute(
                text(
                    "INSERT INTO paper_qa_conversations (id, user_id, paper_id) "
                    "VALUES (:id, :user_id, :paper_id)"
                ),
                {
                    "id": conversation_id,
                    "user_id": user_id,
                    "paper_id": paper_id,
                },
            )

        invalid_rows = [
            {
                "question": "   ",
                "status": "PENDING",
                "hash": None,
                "answer": None,
                "grounded": None,
                "error": None,
                "started": None,
                "completed": None,
            },
            {
                "question": "question",
                "status": "SUCCEEDED",
                "hash": None,
                "answer": "answer",
                "grounded": True,
                "error": None,
                "started": "2026-01-01T00:00:00Z",
                "completed": "2026-01-01T00:01:00Z",
            },
            {
                "question": "question",
                "status": "SUCCEEDED",
                "hash": "a" * 64,
                "answer": " ",
                "grounded": False,
                "error": None,
                "started": "2026-01-01T00:00:00Z",
                "completed": "2026-01-01T00:01:00Z",
            },
            {
                "question": "question",
                "status": "FAILED",
                "hash": None,
                "answer": None,
                "grounded": None,
                "error": "raw exception",
                "started": "2026-01-01T00:00:00Z",
                "completed": "2026-01-01T00:01:00Z",
            },
        ]
        for sequence, row in enumerate(invalid_rows, start=1):
            with pytest.raises(IntegrityError):
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            "INSERT INTO paper_qa_turns "
                            "(id, conversation_id, user_id, paper_id, sequence, client_request_id, "
                            "question, output_language, status, context_hash, answer, grounded, "
                            "error_message, started_at, completed_at) "
                            "VALUES (:id, :conversation_id, :user_id, :paper_id, :sequence, :request_id, "
                            ":question, 'zh', :status, :hash, :answer, :grounded, :error, :started, :completed)"
                        ),
                        {
                            **row,
                            "id": str(uuid.uuid4()),
                            "conversation_id": conversation_id,
                            "user_id": user_id,
                            "paper_id": paper_id,
                            "sequence": sequence,
                            "request_id": str(uuid.uuid4()),
                        },
                    )

        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO paper_qa_turns "
                    "(id, conversation_id, user_id, paper_id, sequence, client_request_id, "
                    "question, output_language, status) "
                    "VALUES (:id, :conversation_id, :user_id, :paper_id, 1, :request_id, "
                    "'first question', 'zh', 'PENDING')"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "paper_id": paper_id,
                    "request_id": str(uuid.uuid4()),
                },
            )
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO paper_qa_turns "
                        "(id, conversation_id, user_id, paper_id, sequence, client_request_id, "
                        "question, output_language, status) "
                        "VALUES (:id, :conversation_id, :user_id, :paper_id, 2, :request_id, "
                        "'second question', 'zh', 'PENDING')"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "paper_id": paper_id,
                        "request_id": str(uuid.uuid4()),
                    },
                )
    finally:
        engine.dispose()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)
