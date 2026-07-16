import datetime
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from paperlens.main import app
from paperlens.core.database import configure_engine, get_engine, SessionLocal
from paperlens.core.enums import UserRole, UserStatus
from paperlens.models.models import (
    AdminAuditLog,
    AnalysisTask,
    AuthSession,
    ExportReport,
    Paper,
    PasswordResetToken,
    User,
)
from paperlens.services.password_service import hash_password, generate_token, hash_token
from paperlens.services.token_service import create_access_token
from paperlens.services import auth_service
from tests.db_helpers import (
    db_available,
    ensure_test_database,
    get_test_db_url,
    is_test_db_required,
    run_alembic_migrations,
    truncate_test_tables,
)

requires_db = pytest.mark.skipif(
    not db_available() and not is_test_db_required(),
    reason="需要 PAPERLENS_TEST_DATABASE_URL 且 PostgreSQL 可连接",
)


@pytest_asyncio.fixture
async def admin_client():
    test_url = get_test_db_url()
    if not test_url:
        if is_test_db_required():
            pytest.fail("PAPERLENS_REQUIRE_TEST_DB=true but PAPERLENS_TEST_DATABASE_URL is not set")
        pytest.skip("需要 PAPERLENS_TEST_DATABASE_URL")

    ensure_test_database()
    run_alembic_migrations(test_url)
    configure_engine(test_url)
    actual_url = str(get_engine().url)
    assert "paperlens_test" in actual_url

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        truncate_test_tables(test_url)


def _make_user(db, email=None, role=UserRole.USER, status=UserStatus.ACTIVE):
    uid = str(uuid.uuid4())
    email = email or f"admin-test-{uid[:8]}@example.com"
    user = User(
        id=uid,
        email=email,
        email_normalized=email.strip().lower(),
        display_name=f"Test {uid[:4]}",
        password_hash=hash_password("StrongPass123!@#"),
        role=role,
        status=status,
        failed_login_count=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_admin_token(db, user):
    family_id = str(uuid.uuid4())
    raw_token = generate_token()
    now = datetime.datetime.now(datetime.timezone.utc)
    session = AuthSession(
        sid=str(uuid.uuid4()),
        family_id=family_id,
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=now + datetime.timedelta(days=1),
        created_at=now,
        last_used_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    access_token, _ = create_access_token(sub=user.id, sid=session.sid)
    return access_token


def _make_user_token(db, user):
    return _make_admin_token(db, user)


@requires_db
@pytest.mark.asyncio
class TestAdminDashboard:
    async def test_dashboard_requires_admin(self, admin_client):
        db = SessionLocal()
        try:
            user = _make_user(db)
            token = _make_user_token(db, user)
            resp = await admin_client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
        finally:
            db.close()

    async def test_dashboard_requires_auth(self, admin_client):
        resp = await admin_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 401

    async def test_dashboard_returns_counts(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            assert "users_by_role" in data
            assert "users_by_status" in data
            assert "papers_by_status" in data
            assert "tasks_by_type" in data
            assert "tasks_by_status" in data
            assert "exports_by_type" in data
            assert "exports_by_status" in data
        finally:
            db.close()


@requires_db
@pytest.mark.asyncio
class TestAdminUserList:
    async def test_list_users_requires_admin(self, admin_client):
        db = SessionLocal()
        try:
            user = _make_user(db)
            token = _make_user_token(db, user)
            resp = await admin_client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
        finally:
            db.close()

    async def test_list_users_returns_paginated(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
            assert data["page"] == 1
        finally:
            db.close()

    async def test_list_users_filter_by_role(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            _make_user(db)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get(
                "/api/v1/admin/users",
                params={"role": "ADMIN"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert item["role"] == "ADMIN"
        finally:
            db.close()

    async def test_list_users_filter_by_status(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get(
                "/api/v1/admin/users",
                params={"status": "ACTIVE"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert item["status"] == "ACTIVE"
        finally:
            db.close()

    async def test_list_users_no_forbidden_fields(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert "password_hash" not in item
                assert "email_normalized" not in item
                assert "password_changed_at" not in item
        finally:
            db.close()



@requires_db
@pytest.mark.asyncio
class TestAdminUserDetail:
    async def test_get_user_not_found(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get(
                f"/api/v1/admin/users/{str(uuid.uuid4())}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 404
        finally:
            db.close()

    async def test_get_user_returns_detail(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user = _make_user(db)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get(
                f"/api/v1/admin/users/{user.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == user.id
            assert data["email"] == user.email
            assert "active_session_count" in data
            assert "paper_count" in data
        finally:
            db.close()


@requires_db
@pytest.mark.asyncio
class TestAdminUserPatch:
    async def test_patch_user_change_role(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user = _make_user(db)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{user.id}",
                json={"role": "ADMIN", "reason": "promote user to admin for testing"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["changed"] is True
            assert len(data["audit_ids"]) == 1
            assert data["user"]["role"] == "ADMIN"
        finally:
            db.close()

    async def test_patch_user_change_status(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user = _make_user(db)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{user.id}",
                json={"status": "DISABLED", "reason": "disable user for policy violation"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["changed"] is True
            assert data["user"]["status"] == "DISABLED"
        finally:
            db.close()

    async def test_patch_user_no_change(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user = _make_user(db)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{user.id}",
                json={"role": "USER", "reason": "no change because already user"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["changed"] is False
            assert data["audit_ids"] == []
        finally:
            db.close()

    async def test_patch_user_self_demotion_forbidden(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{admin.id}",
                json={"role": "USER", "reason": "self demotion should be blocked"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 409
        finally:
            db.close()

    async def test_patch_user_self_disable_forbidden(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{admin.id}",
                json={"status": "DISABLED", "reason": "self disable should be blocked"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 409
        finally:
            db.close()

    async def test_patch_user_last_admin_protection(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user2 = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{user2.id}",
                json={"role": "USER", "reason": "demote second admin should work"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.json()["changed"] is True
        finally:
            db.close()

    async def test_patch_user_last_admin_cannot_be_removed(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user2 = _make_user(db, role=UserRole.USER)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{admin.id}",
                json={"status": "DISABLED", "reason": "cannot disable last admin"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 409
        finally:
            db.close()

    async def test_patch_user_revokes_sessions(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user = _make_user(db)
            _make_user_token(db, user)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{user.id}",
                json={"role": "ADMIN", "reason": "promote and revoke sessions"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            db.expire_all()
            active = db.query(AuthSession).filter(
                AuthSession.user_id == user.id,
                AuthSession.revoked_at.is_(None),
            ).count()
            assert active == 0
        finally:
            db.close()

    async def test_patch_user_disable_invalidates_reset_tokens(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user = _make_user(db)
            raw = generate_token()
            reset = PasswordResetToken(
                id=str(uuid.uuid4()),
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(reset)
            db.commit()
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{user.id}",
                json={"status": "DISABLED", "reason": "disable user and invalidate tokens"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            db.expire_all()
            db.refresh(reset)
            assert reset.used_at is not None
        finally:
            db.close()

    async def test_patch_user_extra_field_422(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user = _make_user(db)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{user.id}",
                json={"role": "ADMIN", "reason": "test extra", "extra": "bad"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 422
        finally:
            db.close()

    async def test_patch_user_short_reason_422(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user = _make_user(db)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{user.id}",
                json={"role": "ADMIN", "reason": "short"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 422
        finally:
            db.close()

    async def test_patch_user_not_found(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{str(uuid.uuid4())}",
                json={"role": "ADMIN", "reason": "user not found test case"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 404
        finally:
            db.close()

    async def test_patch_user_writes_audit(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            user = _make_user(db)
            token = _make_admin_token(db, admin)
            resp = await admin_client.patch(
                f"/api/v1/admin/users/{user.id}",
                json={"role": "ADMIN", "reason": "audit trail test for role change"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            audits = db.query(AdminAuditLog).filter(AdminAuditLog.resource_id == user.id).all()
            assert len(audits) >= 1
            audit = audits[-1]
            assert audit.action == "USER_ROLE_CHANGED"
            assert audit.before_state == {"role": "USER"}
            assert audit.after_state == {"role": "ADMIN"}
            assert audit.actor_user_id == admin.id
        finally:
            db.close()


@requires_db
@pytest.mark.asyncio
class TestAdminPapers:
    async def test_list_papers_requires_admin(self, admin_client):
        db = SessionLocal()
        try:
            user = _make_user(db)
            token = _make_user_token(db, user)
            resp = await admin_client.get("/api/v1/admin/papers", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
        finally:
            db.close()

    async def test_list_papers_returns_safe_fields(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get("/api/v1/admin/papers", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert "storage_key" not in item
                assert "file_hash" not in item
                assert "owner_email" in item
        finally:
            db.close()


@requires_db
@pytest.mark.asyncio
class TestAdminTasks:
    async def test_list_tasks_requires_admin(self, admin_client):
        db = SessionLocal()
        try:
            user = _make_user(db)
            token = _make_user_token(db, user)
            resp = await admin_client.get("/api/v1/admin/tasks", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
        finally:
            db.close()

    async def test_list_tasks_returns_safe_fields(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get("/api/v1/admin/tasks", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert "error_message" not in item
                assert "progress" not in item
        finally:
            db.close()


@requires_db
@pytest.mark.asyncio
class TestAdminExports:
    async def test_list_exports_requires_admin(self, admin_client):
        db = SessionLocal()
        try:
            user = _make_user(db)
            token = _make_user_token(db, user)
            resp = await admin_client.get("/api/v1/admin/exports", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
        finally:
            db.close()

    async def test_list_exports_returns_safe_fields(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get("/api/v1/admin/exports", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            for item in data["items"]:
                assert "storage_key" not in item
                assert "source_snapshot" not in item
                assert "content_hash" not in item
        finally:
            db.close()


@requires_db
@pytest.mark.asyncio
class TestAdminAuditLogs:
    async def test_list_audit_logs_requires_admin(self, admin_client):
        db = SessionLocal()
        try:
            user = _make_user(db)
            token = _make_user_token(db, user)
            resp = await admin_client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
        finally:
            db.close()

    async def test_list_audit_logs_returns_items(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data
            assert "total" in data
        finally:
            db.close()

    async def test_list_audit_logs_invalid_action_422(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get(
                "/api/v1/admin/audit-logs",
                params={"action": "INVALID"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 422
        finally:
            db.close()

    async def test_list_audit_logs_created_from_after_to_422(self, admin_client):
        db = SessionLocal()
        try:
            admin = _make_user(db, role=UserRole.ADMIN)
            token = _make_admin_token(db, admin)
            resp = await admin_client.get(
                "/api/v1/admin/audit-logs",
                params={
                    "created_from": "2026-12-31T00:00:00Z",
                    "created_to": "2026-01-01T00:00:00Z",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 422
        finally:
            db.close()


@requires_db
@pytest.mark.asyncio
class TestAdminConcurrentProtection:
    async def test_two_admins_demote_each_other_only_one_succeeds(self, admin_client):
        import asyncio
        db = SessionLocal()
        try:
            admin1 = _make_user(db, role=UserRole.ADMIN)
            admin2 = _make_user(db, role=UserRole.ADMIN)
            token1 = _make_admin_token(db, admin1)
            token2 = _make_admin_token(db, admin2)

            async def demote(target_id, token, reason):
                return await admin_client.patch(
                    f"/api/v1/admin/users/{target_id}",
                    json={"role": "USER", "reason": reason},
                    headers={"Authorization": f"Bearer {token}"},
                )

            results = await asyncio.gather(
                demote(admin1.id, token2, "admin2 demotes admin1 concurrently"),
                demote(admin2.id, token1, "admin1 demotes admin2 concurrently"),
            )

            success_count = sum(1 for r in results if r.status_code == 200)
            conflict_count = sum(1 for r in results if r.status_code == 409)
            assert success_count <= 1, f"Expected at most 1 success, got {success_count}"
            assert conflict_count >= 1, f"Expected at least 1 conflict, got {conflict_count}"

            db.expire_all()
            active_admins = db.query(User).filter(
                User.role == UserRole.ADMIN,
                User.status == UserStatus.ACTIVE,
            ).count()
            assert active_admins >= 1
        finally:
            db.close()