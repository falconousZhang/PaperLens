import os
import subprocess
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError, InternalError

from paperlens.models.models import AdminAuditLog
from tests.db_helpers import db_available, ensure_test_database, get_test_db_url, is_test_db_required, run_alembic_migrations, truncate_test_tables, verify_no_test_residuals


pytestmark = pytest.mark.skipif(
    not db_available() and not is_test_db_required(),
    reason="需要 PAPERLENS_TEST_DATABASE_URL",
)


def _alembic(test_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PAPERLENS_DATABASE_URL"] = test_url
    return subprocess.run(["alembic", *args], capture_output=True, text=True, env=environment)


def _insert_user(connection, email_suffix=None):
    user_id = str(uuid.uuid4())
    suffix = email_suffix or user_id[:8]
    connection.execute(
        text(
            "INSERT INTO users (id, email, email_normalized, display_name, role, status, failed_login_count) "
            "VALUES (:id, :email, :email, 'P8.1 migration', 'USER', 'ACTIVE', 0)"
        ),
        {"id": user_id, "email": f"p81-{suffix}@example.com"},
    )
    return user_id


def test_017_migration_round_trip_empty_table():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        downgraded = _alembic(test_url, "downgrade", "016_personal_learning_library")
        assert downgraded.returncode == 0, downgraded.stderr
        upgraded = _alembic(test_url, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr
        assert _alembic(test_url, "downgrade", "016_personal_learning_library").returncode == 0
        assert _alembic(test_url, "upgrade", "head").returncode == 0
    finally:
        engine.dispose()
        run_alembic_migrations(test_url)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_017_nonempty_audit_refuses_downgrade():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        with engine.begin() as connection:
            user_id = _insert_user(connection)
            connection.execute(
                text(
                    "INSERT INTO admin_audit_logs (id, actor_user_id, action, resource_type, resource_id, reason, before_state, after_state) "
                    "VALUES (:id, :actor, 'ADMIN_BOOTSTRAPPED', 'USER', :res, 'test reason for downgrade', '{}', '{}')"
                ),
                {"id": str(uuid.uuid4()), "actor": user_id, "res": user_id},
            )
        refused = _alembic(test_url, "downgrade", "016_personal_learning_library")
        assert refused.returncode != 0
        current = _alembic(test_url, "current")
        assert current.returncode == 0
        assert "017_admin_audit_logs" in current.stdout
    finally:
        engine.dispose()
        run_alembic_migrations(test_url)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_017_orm_and_migration_constraint_index_names_match():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    engine = create_engine(test_url)
    try:
        inspector = inspect(engine)
        table = AdminAuditLog.__table__
        database_checks = {item["name"] for item in inspector.get_check_constraints(table.name)}
        orm_checks = {item.name for item in table.constraints if item.__class__.__name__ == "CheckConstraint"}
        database_indexes = {item["name"] for item in inspector.get_indexes(table.name)}
        orm_indexes = {item.name for item in table.indexes}
        assert database_checks == orm_checks
        assert database_indexes == orm_indexes
    finally:
        engine.dispose()


def test_017_trigger_rejects_update_and_delete():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        with engine.begin() as connection:
            user_id = _insert_user(connection)
            audit_id = str(uuid.uuid4())
            connection.execute(
                text(
                    "INSERT INTO admin_audit_logs (id, actor_user_id, action, resource_type, resource_id, reason, before_state, after_state) "
                    "VALUES (:id, :actor, 'ADMIN_BOOTSTRAPPED', 'USER', :res, 'test reason for trigger', '{}', '{}')"
                ),
                {"id": audit_id, "actor": user_id, "res": user_id},
            )
        with pytest.raises((IntegrityError, InternalError)):
            with engine.begin() as connection:
                connection.execute(
                    text("UPDATE admin_audit_logs SET reason = 'nope' WHERE id = :id"),
                    {"id": audit_id},
                )
        with pytest.raises((IntegrityError, InternalError)):
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM admin_audit_logs WHERE id = :id"),
                    {"id": audit_id},
                )
    finally:
        engine.dispose()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_017_check_constraints_enforce_action_and_resource_type():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        with engine.begin() as connection:
            user_id = _insert_user(connection)
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO admin_audit_logs (id, actor_user_id, action, resource_type, resource_id, reason, before_state, after_state) "
                        "VALUES (:id, :actor, 'INVALID_ACTION', 'USER', :res, 'testreason1234567890', '{}', '{}')"
                    ),
                    {"id": str(uuid.uuid4()), "actor": user_id, "res": user_id},
                )
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO admin_audit_logs (id, actor_user_id, action, resource_type, resource_id, reason, before_state, after_state) "
                        "VALUES (:id, :actor, 'ADMIN_BOOTSTRAPPED', 'PAPER', :res, 'testreason1234567890', '{}', '{}')"
                    ),
                    {"id": str(uuid.uuid4()), "actor": user_id, "res": user_id},
                )
    finally:
        engine.dispose()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_017_check_constraints_enforce_reason_length():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        with engine.begin() as connection:
            user_id = _insert_user(connection)
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO admin_audit_logs (id, actor_user_id, action, resource_type, resource_id, reason, before_state, after_state) "
                        "VALUES (:id, :actor, 'ADMIN_BOOTSTRAPPED', 'USER', :res, 'short', '{}', '{}')"
                    ),
                    {"id": str(uuid.uuid4()), "actor": user_id, "res": user_id},
                )
    finally:
        engine.dispose()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)