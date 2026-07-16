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
        ["alembic", *args], capture_output=True, text=True, env=environment
    )


@requires_db
def test_learning_migration_round_trip_and_lossless_abort():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        at_012 = _alembic(test_url, "downgrade", "012_export_report_pdf_docx")
        assert at_012.returncode == 0, at_012.stderr

        user_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        section_id = str(uuid.uuid4())
        evidence_id = str(uuid.uuid4())
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, email, email_normalized, display_name, role, status, failed_login_count) "
                    "VALUES (:id, :email, :email, 'legacy', 'USER', 'ACTIVE', 0)"
                ),
                {"id": user_id, "email": f"learning-{user_id}@example.com"},
            )
            connection.execute(
                text(
                    "INSERT INTO papers "
                    "(id, title, filename, storage_key, file_size, file_hash, status, user_id) "
                    "VALUES (:id, 'Legacy learning', 'legacy.pdf', 'legacy/source.pdf', 1, :hash, 'PARSED', :user_id)"
                ),
                {"id": paper_id, "hash": "a" * 64, "user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO paper_sections "
                    "(id, paper_id, section_type, title, level, sequence, start_page, end_page, text_content) "
                    "VALUES (:id, :paper_id, 'INTRODUCTION', 'Intro', 1, 1, 1, 1, 'source')"
                ),
                {"id": section_id, "paper_id": paper_id},
            )
            connection.execute(
                text(
                    "INSERT INTO evidences "
                    "(id, paper_id, section_id, quoted_text, page_number, evidence_type) "
                    "VALUES (:id, :paper_id, :section_id, 'evidence', 1, 'TEXT')"
                ),
                {
                    "id": evidence_id,
                    "paper_id": paper_id,
                    "section_id": section_id,
                },
            )

        upgraded = _alembic(test_url, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT count(*) FROM users WHERE id = :id"), {"id": user_id}
            ).scalar_one() == 1
            assert connection.execute(
                text("SELECT count(*) FROM papers WHERE id = :id"), {"id": paper_id}
            ).scalar_one() == 1
            assert connection.execute(
                text("SELECT count(*) FROM learning_explanations")
            ).scalar_one() == 0

        empty_down = _alembic(test_url, "downgrade", "012_export_report_pdf_docx")
        assert empty_down.returncode == 0, empty_down.stderr
        empty_up = _alembic(test_url, "upgrade", "head")
        assert empty_up.returncode == 0, empty_up.stderr

        explanation_id = str(uuid.uuid4())
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO learning_explanations "
                    "(id, user_id, paper_id, mode, scope_type, output_language, section_id, request_hash, status) "
                    "VALUES (:id, :user_id, :paper_id, 'SUMMARY', 'SECTION', 'zh', :section_id, :request_hash, 'PENDING')"
                ),
                {
                    "id": explanation_id,
                    "user_id": user_id,
                    "paper_id": paper_id,
                    "section_id": section_id,
                    "request_hash": "b" * 64,
                },
            )

        refused = _alembic(test_url, "downgrade", "012_export_report_pdf_docx")
        assert refused.returncode != 0
        current = _alembic(test_url, "current")
        assert current.returncode == 0
        assert "017_admin_audit_logs" in current.stdout
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT count(*) FROM learning_explanations WHERE id = :id"),
                {"id": explanation_id},
            ).scalar_one() == 1
    finally:
        engine.dispose()
        run_alembic_migrations(test_url)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


@requires_db
def test_learning_database_constraints_reject_invalid_terminal_rows():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        user_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        section_id = str(uuid.uuid4())
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, email, email_normalized, display_name, role, status, failed_login_count) "
                    "VALUES (:id, :email, :email, 'constraints', 'USER', 'ACTIVE', 0)"
                ),
                {"id": user_id, "email": f"constraints-{user_id}@example.com"},
            )
            connection.execute(
                text(
                    "INSERT INTO papers "
                    "(id, title, filename, storage_key, file_size, file_hash, status, user_id) "
                    "VALUES (:id, 'Constraints', 'c.pdf', 'c/source.pdf', 1, :hash, 'PARSED', :user_id)"
                ),
                {"id": paper_id, "hash": "c" * 64, "user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO paper_sections "
                    "(id, paper_id, section_type, level, sequence, text_content) "
                    "VALUES (:id, :paper_id, 'INTRODUCTION', 1, 1, 'source')"
                ),
                {"id": section_id, "paper_id": paper_id},
            )

        invalid_rows = [
            {
                "id": str(uuid.uuid4()),
                "hash": "invalid",
                "status": "PENDING",
                "answer": None,
                "points": None,
                "terms": None,
                "started": None,
                "completed": None,
                "error": None,
            },
            {
                "id": str(uuid.uuid4()),
                "hash": "d" * 64,
                "status": "SUCCEEDED",
                "answer": " ",
                "points": "[]",
                "terms": "[]",
                "started": "2026-01-01T00:00:00Z",
                "completed": "2026-01-01T00:01:00Z",
                "error": None,
            },
            {
                "id": str(uuid.uuid4()),
                "hash": "e" * 64,
                "status": "FAILED",
                "answer": None,
                "points": None,
                "terms": None,
                "started": "2026-01-01T00:00:00Z",
                "completed": "2026-01-01T00:01:00Z",
                "error": "raw exception",
            },
        ]
        for row in invalid_rows:
            with pytest.raises(IntegrityError):
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            "INSERT INTO learning_explanations "
                            "(id, user_id, paper_id, mode, scope_type, output_language, section_id, request_hash, status, "
                            "answer, key_points, terms, started_at, completed_at, error_message) "
                            "VALUES (:id, :user_id, :paper_id, 'SUMMARY', 'SECTION', 'zh', :section_id, :hash, :status, "
                            ":answer, CAST(:points AS jsonb), CAST(:terms AS jsonb), :started, :completed, :error)"
                        ),
                        {
                            **row,
                            "user_id": user_id,
                            "paper_id": paper_id,
                            "section_id": section_id,
                        },
                    )
    finally:
        engine.dispose()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)
