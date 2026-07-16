import uuid

import pytest

from paperlens.core.database import SessionLocal
from paperlens.core.enums import UserRole, UserStatus
from paperlens.models.models import AdminAuditLog, AuthSession, User
from paperlens.services.password_service import hash_password
from paperlens.services import admin_service
from tests.db_helpers import (
    db_available,
    ensure_test_database,
    get_test_db_url,
    is_test_db_required,
    run_alembic_migrations,
    truncate_test_tables,
    verify_no_test_residuals,
)

pytestmark = pytest.mark.skipif(
    not db_available() and not is_test_db_required(),
    reason="需要 PAPERLENS_TEST_DATABASE_URL",
)


def _make_user(db, email=None, role=UserRole.USER, status=UserStatus.ACTIVE):
    uid = str(uuid.uuid4())
    email = email or f"cli-test-{uid[:8]}@example.com"
    user = User(
        id=uid,
        email=email,
        email_normalized=email.strip().lower(),
        display_name=f"CLI {uid[:4]}",
        password_hash=hash_password("StrongPass123!@#"),
        role=role,
        status=status,
        failed_login_count=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_admin_bootstrap_success():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    db = SessionLocal()
    try:
        user = _make_user(db)
        audit_id = admin_service.admin_bootstrap(db, user_id=user.id, reason="first admin bootstrap test")
        assert audit_id is not None
        db.expire_all()
        refreshed = db.get(User, user.id)
        assert refreshed.role == UserRole.ADMIN
        audit = db.query(AdminAuditLog).filter(AdminAuditLog.id == audit_id).one()
        assert audit.action == "ADMIN_BOOTSTRAPPED"
        assert audit.actor_user_id == user.id
        assert audit.resource_id == user.id
    finally:
        db.close()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_admin_bootstrap_fails_with_existing_admin():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    db = SessionLocal()
    try:
        admin = _make_user(db, role=UserRole.ADMIN)
        user = _make_user(db)
        with pytest.raises(Exception) as exc_info:
            admin_service.admin_bootstrap(db, user_id=user.id, reason="should fail with existing admin")
        assert exc_info.value.status_code == 409
    finally:
        db.close()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_admin_bootstrap_fails_for_nonexistent_user():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    db = SessionLocal()
    try:
        with pytest.raises(Exception) as exc_info:
            admin_service.admin_bootstrap(db, user_id=str(uuid.uuid4()), reason="nonexistent user bootstrap")
        assert exc_info.value.status_code == 404
    finally:
        db.close()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_admin_bootstrap_fails_for_disabled_user():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    db = SessionLocal()
    try:
        user = _make_user(db, status=UserStatus.DISABLED)
        with pytest.raises(Exception) as exc_info:
            admin_service.admin_bootstrap(db, user_id=user.id, reason="disabled user cannot be bootstrapped")
        assert exc_info.value.status_code == 422
    finally:
        db.close()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_admin_bootstrap_revokes_existing_sessions():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    db = SessionLocal()
    try:
        user = _make_user(db)
        from paperlens.services.password_service import generate_token, hash_token
        import datetime
        session = AuthSession(
            sid=str(uuid.uuid4()),
            family_id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=hash_token(generate_token()),
            expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1),
            created_at=datetime.datetime.now(datetime.timezone.utc),
            last_used_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(session)
        db.commit()
        admin_service.admin_bootstrap(db, user_id=user.id, reason="bootstrap revokes sessions test")
        db.expire_all()
        active = db.query(AuthSession).filter(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
        ).count()
        assert active == 0
    finally:
        db.close()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_admin_bootstrap_short_reason_fails():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    db = SessionLocal()
    try:
        user = _make_user(db)
        with pytest.raises(Exception) as exc_info:
            admin_service.admin_bootstrap(db, user_id=user.id, reason="short")
        assert exc_info.value.status_code == 422
    finally:
        db.close()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_admin_bootstrap_concurrent_only_one_succeeds():
    import threading
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    db = SessionLocal()
    try:
        user = _make_user(db)
        results = [None, None]

        def bootstrap_thread(idx):
            tdb = SessionLocal()
            try:
                admin_service.admin_bootstrap(tdb, user_id=user.id, reason=f"concurrent bootstrap attempt {idx}")
                results[idx] = "success"
            except Exception:
                results[idx] = "conflict"
            finally:
                tdb.close()

        t1 = threading.Thread(target=bootstrap_thread, args=(0,))
        t2 = threading.Thread(target=bootstrap_thread, args=(1,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        success_count = sum(1 for r in results if r == "success")
        assert success_count <= 1, f"Expected at most 1 success, got {success_count}"
    finally:
        db.close()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)