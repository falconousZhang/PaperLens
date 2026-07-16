import hashlib
import json
import os
import subprocess
import uuid

import pytest
from sqlalchemy import create_engine, text

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
    env = os.environ.copy()
    env["PAPERLENS_DATABASE_URL"] = test_url
    return subprocess.run(
        ["alembic", *args],
        capture_output=True,
        text=True,
        env=env,
    )


@requires_db
def test_export_report_migration_legacy_and_lossless_abort():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        downgraded = _alembic(test_url, "downgrade", "009_exp_analysis_task_link")
        assert downgraded.returncode == 0, downgraded.stderr

        user_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, email, email_normalized, display_name, role, status, failed_login_count) "
                    "VALUES (:id, :email, :email, 'legacy', 'USER', 'ACTIVE', 0)"
                ),
                {"id": user_id, "email": f"legacy-{user_id}@example.com"},
            )
            connection.execute(
                text(
                    "INSERT INTO papers "
                    "(id, title, filename, storage_key, file_size, file_hash, status, user_id) "
                    "VALUES (:id, 'Legacy', 'legacy.pdf', 'legacy/source.pdf', 1, :hash, 'PARSED', :user_id)"
                ),
                {"id": paper_id, "hash": "a" * 64, "user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO export_reports "
                    "(id, paper_id, report_type, status, user_id) "
                    "VALUES (:id, :paper_id, 'PDF', 'PENDING', :user_id)"
                ),
                {"id": report_id, "paper_id": paper_id, "user_id": user_id},
            )

        upgraded = _alembic(test_url, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr
        with engine.connect() as connection:
            legacy = connection.execute(
                text(
                    "SELECT report_type, source_snapshot, source_hash "
                    "FROM export_reports WHERE id = :id"
                ),
                {"id": report_id},
            ).one()
        assert legacy == ("PDF", None, None)

        refused_legacy = _alembic(test_url, "downgrade", "009_exp_analysis_task_link")
        assert refused_legacy.returncode != 0
        current_after_pdf_refusal = _alembic(test_url, "current")
        assert current_after_pdf_refusal.returncode == 0
        assert "017_admin_audit_logs" in current_after_pdf_refusal.stdout
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT count(*) FROM export_reports WHERE id = :id"),
                {"id": report_id},
            ).scalar_one() == 1

        run_alembic_migrations(test_url)
        truncate_test_tables(test_url)

        at_010 = _alembic(test_url, "downgrade", "010_export_report_p61")
        assert at_010.returncode == 0, at_010.stderr
        user_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())
        old_snapshot = {"review_task_id": str(uuid.uuid4())}
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, email, email_normalized, display_name, role, status, failed_login_count) "
                    "VALUES (:id, :email, :email, 'old-p61', 'USER', 'ACTIVE', 0)"
                ),
                {"id": user_id, "email": f"old-p61-{user_id}@example.com"},
            )
            connection.execute(
                text(
                    "INSERT INTO papers "
                    "(id, title, filename, storage_key, file_size, file_hash, status, user_id) "
                    "VALUES (:id, 'Old P61', 'old.pdf', 'old/source.pdf', 1, :hash, 'PARSED', :user_id)"
                ),
                {"id": paper_id, "hash": "c" * 64, "user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO export_reports "
                    "(id, paper_id, report_type, language, include_metrics, "
                    "include_experiment_analysis, source_snapshot, status, user_id) "
                    "VALUES (:id, :paper_id, 'MARKDOWN', 'zh', true, true, "
                    "CAST(:snapshot AS jsonb), 'PENDING', :user_id)"
                ),
                {
                    "id": report_id,
                    "paper_id": paper_id,
                    "snapshot": json.dumps(old_snapshot),
                    "user_id": user_id,
                },
            )
        upgraded_old_p61 = _alembic(test_url, "upgrade", "head")
        assert upgraded_old_p61.returncode == 0, upgraded_old_p61.stderr
        with engine.connect() as connection:
            old_p61 = connection.execute(
                text(
                    "SELECT status, source_hash, completed_at, error_message "
                    "FROM export_reports WHERE id = :id"
                ),
                {"id": report_id},
            ).one()
        assert old_p61[0] == "FAILED"
        assert old_p61[1] == hashlib.sha256(
            json.dumps(
                old_snapshot,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        assert old_p61[2] is not None
        assert old_p61[3] == "报告生成失败，请稍后重试"
        truncate_test_tables(test_url)

        user_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())
        snapshot = {"review_task_id": str(uuid.uuid4())}
        encoded_snapshot = json.dumps(
            snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, email, email_normalized, display_name, role, status, failed_login_count) "
                    "VALUES (:id, :email, :email, 'p61', 'USER', 'ACTIVE', 0)"
                ),
                {"id": user_id, "email": f"p61-{user_id}@example.com"},
            )
            connection.execute(
                text(
                    "INSERT INTO papers "
                    "(id, title, filename, storage_key, file_size, file_hash, status, user_id) "
                    "VALUES (:id, 'P61', 'p61.pdf', 'p61/source.pdf', 1, :hash, 'PARSED', :user_id)"
                ),
                {"id": paper_id, "hash": "b" * 64, "user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO export_reports "
                    "(id, paper_id, report_type, language, include_metrics, "
                    "include_experiment_analysis, source_snapshot, source_hash, status, "
                    "content_hash, user_id) "
                    "VALUES (:id, :paper_id, 'MARKDOWN', 'zh', false, false, "
                    "CAST(:snapshot AS jsonb), :source_hash, 'PENDING', :content_hash, :user_id)"
                ),
                {
                    "id": report_id,
                    "paper_id": paper_id,
                    "snapshot": json.dumps(snapshot),
                    "source_hash": hashlib.sha256(encoded_snapshot).hexdigest(),
                    "content_hash": hashlib.sha256(b"report").hexdigest(),
                    "user_id": user_id,
                },
            )

        refused_p61 = _alembic(test_url, "downgrade", "010_export_report_p61")
        assert refused_p61.returncode != 0
        current = _alembic(test_url, "current")
        assert current.returncode == 0
        assert "017_admin_audit_logs" in current.stdout
    finally:
        engine.dispose()
        run_alembic_migrations(test_url)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)
