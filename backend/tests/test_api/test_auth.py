import datetime
import asyncio
import uuid
from unittest.mock import patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from paperlens.main import app
from paperlens.core.database import configure_engine, get_engine, SessionLocal
from paperlens.core.enums import PaperStatus, UserRole, UserStatus
from paperlens.models.models import (
    AnalysisTask,
    AuthSession,
    ExperimentFile,
    ExportReport,
    Paper,
    PasswordResetToken,
    User,
)
from paperlens.cli import promote_admin
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
async def auth_client():
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


def _make_user(db, email="test@example.com", password="StrongPass123!@#", display_name="Test User", role=UserRole.USER):
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        email_normalized=email.strip().lower(),
        display_name=display_name,
        password_hash=hash_password(password),
        role=role,
        status=UserStatus.ACTIVE,
        failed_login_count=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@requires_db
@pytest.mark.asyncio
async def test_register_success(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "StrongPass123!@#",
        "display_name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900
    assert data["user"]["status"] == "ACTIVE"
    assert "password_hash" not in str(data)
    cookies = resp.cookies
    assert "paperlens_refresh" in cookies
    set_cookie = resp.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/api/v1/auth" in set_cookie


@requires_db
@pytest.mark.asyncio
async def test_register_duplicate_email(auth_client: AsyncClient):
    await auth_client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "StrongPass123!@#",
        "display_name": "First",
    })
    resp = await auth_client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Second",
    })
    assert resp.status_code == 409


@requires_db
@pytest.mark.asyncio
async def test_register_weak_password(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/auth/register", json={
        "email": "weak@example.com",
        "password": "password",
        "display_name": "Weak",
    })
    assert resp.status_code == 422


@requires_db
@pytest.mark.asyncio
async def test_login_success(auth_client: AsyncClient):
    await auth_client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Login User",
    })
    resp = await auth_client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "StrongPass123!@#",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "paperlens_refresh" in resp.cookies


@requires_db
@pytest.mark.asyncio
async def test_login_wrong_password(auth_client: AsyncClient):
    await auth_client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Wrong",
    })
    resp = await auth_client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com",
        "password": "WrongPassword!@#1",
    })
    assert resp.status_code == 401


@requires_db
@pytest.mark.asyncio
async def test_login_nonexistent_email(auth_client: AsyncClient):
    with patch(
        "paperlens.services.auth_service.perform_dummy_password_check",
        wraps=auth_service.perform_dummy_password_check,
    ) as dummy_check:
        resp = await auth_client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "StrongPass123!@#",
        })
    assert resp.status_code == 401
    dummy_check.assert_called_once_with("StrongPass123!@#")


@requires_db
@pytest.mark.asyncio
async def test_refresh_token_rotation(auth_client: AsyncClient):
    reg = await auth_client.post("/api/v1/auth/register", json={
        "email": "refresh@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Refresh User",
    })
    refresh_cookie = reg.cookies.get("paperlens_refresh")
    assert refresh_cookie

    resp = await auth_client.post(
        "/api/v1/auth/refresh",
        cookies={"paperlens_refresh": refresh_cookie},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    new_refresh = resp.cookies.get("paperlens_refresh")
    assert new_refresh


@requires_db
@pytest.mark.asyncio
async def test_refresh_replay_detection(auth_client: AsyncClient):
    reg = await auth_client.post("/api/v1/auth/register", json={
        "email": "replay@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Replay User",
    })
    old_refresh = reg.cookies.get("paperlens_refresh")

    rotated = await auth_client.post(
        "/api/v1/auth/refresh",
        cookies={"paperlens_refresh": old_refresh},
    )
    new_refresh = rotated.cookies.get("paperlens_refresh")
    assert rotated.status_code == 200
    assert new_refresh

    replay = await auth_client.post(
        "/api/v1/auth/refresh",
        cookies={"paperlens_refresh": old_refresh},
    )
    assert replay.status_code == 401

    family_revoked = await auth_client.post(
        "/api/v1/auth/refresh",
        cookies={"paperlens_refresh": new_refresh},
    )
    assert family_revoked.status_code == 401

    db = SessionLocal()
    try:
        sessions = db.query(AuthSession).all()
        assert len(sessions) == 2
        assert all(session.revoked_at is not None for session in sessions)
        replaced = [session for session in sessions if session.replaced_by_id]
        assert len(replaced) == 1
        assert replaced[0].replaced_by_id in {session.sid for session in sessions}
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
async def test_logout(auth_client: AsyncClient):
    reg = await auth_client.post("/api/v1/auth/register", json={
        "email": "logout@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Logout User",
    })
    refresh_cookie = reg.cookies.get("paperlens_refresh")

    resp = await auth_client.post(
        "/api/v1/auth/logout",
        cookies={"paperlens_refresh": refresh_cookie},
        headers={"Authorization": f"Bearer {reg.json()['access_token']}"},
    )
    assert resp.status_code == 200

    rejected = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {reg.json()['access_token']}"},
    )
    assert rejected.status_code == 401


@requires_db
@pytest.mark.asyncio
async def test_logout_all(auth_client: AsyncClient):
    reg = await auth_client.post("/api/v1/auth/register", json={
        "email": "logoutall@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Logout All User",
    })
    access_token = reg.json()["access_token"]

    resp = await auth_client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200

    rejected = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert rejected.status_code == 401


@requires_db
@pytest.mark.asyncio
async def test_get_me(auth_client: AsyncClient):
    reg = await auth_client.post("/api/v1/auth/register", json={
        "email": "me@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Me User",
    })
    access_token = reg.json()["access_token"]

    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["email"] == "me@example.com"
    assert data["display_name"] == "Me User"
    assert data["role"] == "USER"


@requires_db
@pytest.mark.asyncio
async def test_update_profile(auth_client: AsyncClient):
    reg = await auth_client.post("/api/v1/auth/register", json={
        "email": "update@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Old Name",
    })
    access_token = reg.json()["access_token"]

    resp = await auth_client.patch(
        "/api/v1/auth/me",
        json={"display_name": "New Name"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "New Name"


@requires_db
@pytest.mark.asyncio
async def test_change_password(auth_client: AsyncClient):
    reg = await auth_client.post("/api/v1/auth/register", json={
        "email": "chpw@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Change PW",
    })
    access_token = reg.json()["access_token"]

    resp = await auth_client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "StrongPass123!@#", "new_password": "NewStrongPass456!@#"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200

    invalidated = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert invalidated.status_code == 401

    login = await auth_client.post("/api/v1/auth/login", json={
        "email": "chpw@example.com",
        "password": "NewStrongPass456!@#",
    })
    assert login.status_code == 200


@requires_db
@pytest.mark.asyncio
async def test_change_password_wrong_current(auth_client: AsyncClient):
    reg = await auth_client.post("/api/v1/auth/register", json={
        "email": "chpw2@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Change PW2",
    })
    access_token = reg.json()["access_token"]

    resp = await auth_client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "WrongPassword!@#1", "new_password": "NewStrongPass456!@#"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 401


@requires_db
@pytest.mark.asyncio
async def test_forgot_password(auth_client: AsyncClient):
    await auth_client.post("/api/v1/auth/register", json={
        "email": "forgot@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Forgot User",
    })
    class CaptureNotifier:
        def __init__(self):
            self.tokens = []

        def send(self, user, reset_token):
            self.tokens.append((user.id, reset_token))

    capture = CaptureNotifier()
    app.dependency_overrides[auth_service.get_password_reset_notifier] = lambda: capture
    try:
        resp = await auth_client.post("/api/v1/auth/forgot-password", json={
            "email": "forgot@example.com",
        })
    finally:
        app.dependency_overrides.pop(auth_service.get_password_reset_notifier, None)
    assert resp.status_code == 202
    assert len(capture.tokens) == 1
    raw_token = capture.tokens[0][1]
    assert raw_token not in resp.text
    db = SessionLocal()
    try:
        reset = db.query(PasswordResetToken).one()
        assert reset.token_hash == hash_token(raw_token)
        assert reset.token_hash != raw_token
        assert len(reset.token_hash) == 64
    finally:
        db.close()


@requires_db
@pytest.mark.asyncio
async def test_forgot_password_nonexistent_email(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/auth/forgot-password", json={
        "email": "nonexistent@example.com",
    })
    assert resp.status_code == 202


@requires_db
@pytest.mark.asyncio
async def test_reset_password(auth_client: AsyncClient):
    db = SessionLocal()
    try:
        user = _make_user(db, email="reset@example.com")
        raw_token = generate_token()
        now = datetime.datetime.now(datetime.timezone.utc)
        reset = PasswordResetToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + datetime.timedelta(minutes=15),
            created_at=now,
        )
        db.add(reset)
        db.commit()
    finally:
        db.close()

    resp = await auth_client.post("/api/v1/auth/reset-password", json={
        "token": raw_token,
        "new_password": "ResetStrongPass789!@#",
    })
    assert resp.status_code == 200

    login = await auth_client.post("/api/v1/auth/login", json={
        "email": "reset@example.com",
        "password": "ResetStrongPass789!@#",
    })
    assert login.status_code == 200


@requires_db
@pytest.mark.asyncio
async def test_reset_password_invalid_token(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/auth/reset-password", json={
        "token": "x" * 64,
        "new_password": "ResetStrongPass789!@#",
    })
    assert resp.status_code == 400


@requires_db
@pytest.mark.asyncio
async def test_account_lockout_after_failed_logins(auth_client: AsyncClient):
    await auth_client.post("/api/v1/auth/register", json={
        "email": "locked@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Locked User",
    })

    for _ in range(5):
        await auth_client.post("/api/v1/auth/login", json={
            "email": "locked@example.com",
            "password": "WrongPassword!@#1",
        })

    resp = await auth_client.post("/api/v1/auth/login", json={
        "email": "locked@example.com",
        "password": "StrongPass123!@#",
    })
    assert resp.status_code == 401
    assert resp.json()["error"]["message"] == "邮箱或密码错误"


@requires_db
@pytest.mark.asyncio
async def test_access_protected_route_without_token(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/papers")
    assert resp.status_code == 401


@requires_db
@pytest.mark.asyncio
async def test_access_protected_route_with_token(auth_client: AsyncClient):
    reg = await auth_client.post("/api/v1/auth/register", json={
        "email": "protected@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Protected User",
    })
    access_token = reg.json()["access_token"]

    resp = await auth_client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200


@requires_db
@pytest.mark.asyncio
async def test_register_forbids_extra_fields(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/auth/register", json={
        "email": "extra@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Extra",
        "role": "ADMIN",
    })
    assert resp.status_code == 422


@requires_db
@pytest.mark.asyncio
async def test_login_failures_do_not_enumerate_account_state(auth_client: AsyncClient):
    await auth_client.post("/api/v1/auth/register", json={
        "email": "wrong-uniform@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Wrong Uniform",
    })
    db = SessionLocal()
    try:
        disabled = _make_user(db, email="disabled@example.com")
        disabled.status = UserStatus.DISABLED
        locked = _make_user(db, email="locked-uniform@example.com")
        locked.locked_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
        db.commit()
    finally:
        db.close()

    attempts = (
        ("missing@example.com", "StrongPass123!@#"),
        ("wrong-uniform@example.com", "WrongPassword!@#1"),
        ("disabled@example.com", "StrongPass123!@#"),
        ("locked-uniform@example.com", "StrongPass123!@#"),
    )
    results = []
    for email, password in attempts:
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        results.append((
            response.status_code,
            response.json()["error"]["code"],
            response.json()["error"]["message"],
            response.headers.get("www-authenticate"),
        ))
    assert len(set(results)) == 1
    assert results[0] == (401, "INVALID_CREDENTIALS", "邮箱或密码错误", "Bearer")


@requires_db
@pytest.mark.asyncio
async def test_concurrent_refresh_allows_only_one_rotation(auth_client: AsyncClient):
    registration = await auth_client.post("/api/v1/auth/register", json={
        "email": "concurrent-refresh@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Concurrent Refresh",
    })
    old_refresh = registration.cookies.get("paperlens_refresh")
    assert old_refresh

    async def rotate():
        return await auth_client.post(
            "/api/v1/auth/refresh",
            cookies={"paperlens_refresh": old_refresh},
        )

    responses = await asyncio.gather(rotate(), rotate())
    assert sorted(response.status_code for response in responses) == [200, 401]


@requires_db
@pytest.mark.asyncio
async def test_reset_password_is_single_use_and_revokes_access(auth_client: AsyncClient):
    registration = await auth_client.post("/api/v1/auth/register", json={
        "email": "reset-capture@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Reset Capture",
    })
    access_token = registration.json()["access_token"]

    class CaptureNotifier:
        def __init__(self):
            self.token = None

        def send(self, _user, reset_token):
            self.token = reset_token

    capture = CaptureNotifier()
    app.dependency_overrides[auth_service.get_password_reset_notifier] = lambda: capture
    try:
        forgot = await auth_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "reset-capture@example.com"},
        )
    finally:
        app.dependency_overrides.pop(auth_service.get_password_reset_notifier, None)
    assert forgot.status_code == 202
    assert capture.token

    reset = await auth_client.post("/api/v1/auth/reset-password", json={
        "token": capture.token,
        "new_password": "NewResetPassword789!",
    })
    assert reset.status_code == 200

    stale_access = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert stale_access.status_code == 401

    replay = await auth_client.post("/api/v1/auth/reset-password", json={
        "token": capture.token,
        "new_password": "AnotherResetPassword789!",
    })
    assert replay.status_code == 400
    assert replay.json()["error"]["message"] == "无效或已失效的重置令牌"


@requires_db
@pytest.mark.asyncio
async def test_logout_requires_bearer_token(auth_client: AsyncClient):
    response = await auth_client.post("/api/v1/auth/logout")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@requires_db
@pytest.mark.asyncio
async def test_disabled_user_access_is_rejected_as_unauthorized(auth_client: AsyncClient):
    registration = await auth_client.post("/api/v1/auth/register", json={
        "email": "disable-access@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Disable Access",
    })
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.email_normalized == "disable-access@example.com"
        ).one()
        user.status = UserStatus.DISABLED
        db.commit()
    finally:
        db.close()

    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {registration.json()['access_token']}"},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["message"] == "无效的认证凭据"


@requires_db
@pytest.mark.asyncio
async def test_display_name_whitespace_is_rejected(auth_client: AsyncClient):
    registration = await auth_client.post("/api/v1/auth/register", json={
        "email": "blank-name@example.com",
        "password": "StrongPass123!@#",
        "display_name": "   ",
    })
    assert registration.status_code == 422

    valid = await auth_client.post("/api/v1/auth/register", json={
        "email": "profile-name@example.com",
        "password": "StrongPass123!@#",
        "display_name": "Valid Name",
    })
    update = await auth_client.patch(
        "/api/v1/auth/me",
        json={"display_name": "   "},
        headers={"Authorization": f"Bearer {valid.json()['access_token']}"},
    )
    assert update.status_code == 422


@requires_db
@pytest.mark.asyncio
async def test_promote_admin_claims_legacy_data_only_with_explicit_flag(
    auth_client: AsyncClient,
):
    db = SessionLocal()
    try:
        user = _make_user(db, email="claim-admin@example.com")
        if db.get(User, "demo-user") is None:
            db.add(User(
                id="demo-user",
                email="demo@paperlens.local",
                email_normalized="demo@paperlens.local",
                display_name="Demo User (Legacy)",
                password_hash=None,
                role=UserRole.USER,
                status=UserStatus.DISABLED,
                failed_login_count=0,
            ))
            db.flush()
        paper = Paper(
            title="Legacy",
            filename="legacy.pdf",
            storage_key="papers/legacy/source.pdf",
            file_size=1,
            file_hash="a" * 64,
            status=PaperStatus.PARSED,
            user_id="demo-user",
        )
        db.add(paper)
        db.flush()
        task = AnalysisTask(
            paper_id=paper.id,
            task_type="REVIEW",
            status="PENDING",
            progress=0,
            user_id="demo-user",
        )
        experiment = ExperimentFile(
            paper_id=paper.id,
            filename="legacy.csv",
            storage_key="experiments/legacy.csv",
            file_size=1,
            file_hash="b" * 64,
            file_type="CSV",
            row_count=1,
            column_count=1,
            columns_info={"version": 1, "columns": [{"name": "a", "dtype": "string", "nullable": False, "null_count": 0}]},
            user_id="demo-user",
        )
        report = ExportReport(
            paper_id=paper.id,
            report_type="PDF",
            status="PENDING",
            user_id="demo-user",
        )
        db.add_all([task, experiment, report])
        db.commit()
        user_id = user.id
    finally:
        db.close()

    promote_admin("claim-admin@example.com", claim_legacy_data=False)
    db = SessionLocal()
    try:
        assert db.get(User, user_id).role == UserRole.ADMIN
        assert db.query(Paper).filter(Paper.user_id == "demo-user").count() == 1
        assert db.query(AnalysisTask).filter(AnalysisTask.user_id == "demo-user").count() == 1
        assert db.query(ExperimentFile).filter(ExperimentFile.user_id == "demo-user").count() == 1
        assert db.query(ExportReport).filter(ExportReport.user_id == "demo-user").count() == 1
    finally:
        db.close()

    promote_admin("claim-admin@example.com", claim_legacy_data=True)
    db = SessionLocal()
    try:
        for model in (Paper, AnalysisTask, ExperimentFile, ExportReport):
            assert db.query(model).filter(model.user_id == user_id).count() == 1
            assert db.query(model).filter(model.user_id == "demo-user").count() == 0
    finally:
        db.close()
