from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from paperlens.core.config import Settings


_TEST_JWT_SECRET = "9N!vQ2#sL7@xR4%pT8&kM3*eC6-zA1_yH5+jD0=wF7!uB4$qS"


def _production_settings(**overrides) -> Settings:
    values = {
        "jwt_secret": _TEST_JWT_SECRET,
        "env": "production",
        "debug": False,
        "database_url": (
            "postgresql+psycopg2://paperlens:test-password@rds.internal:5432/"
            "paperlens?sslmode=verify-full&sslrootcert=/run/secrets/rds_ca"
        ),
        "storage_backend": "obs",
        "obs_endpoint": "https://obs.test-region.myhuaweicloud.com",
        "obs_bucket": "paperlens-test-bucket",
        "obs_prefix": "paperlens",
        "obs_credential_mode": "ENV",
        "obs_access_key_id": "TEST_ACCESS_KEY",
        "obs_secret_access_key": "TEST_SECRET_KEY",
        "llm_backend": "huawei_maas",
        "llm_base_url": "https://api.modelarts-maas.com/v2",
        "llm_api_key": "TEST_LLM_KEY",
        "embedding_provider": "huawei_maas",
        "embedding_base_url": "https://api.modelarts-maas.com/v1",
        "embedding_api_key": "TEST_EMBEDDING_KEY",
        "trusted_proxy_cidrs": "172.30.0.0/24,192.168.10.0/24",
        "recovery_enabled": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_obs_storage_contract_rejects_failures_and_cleans_temp_files(tmp_path):
    from paperlens.utils.storage import OBSStorage, _validate_storage_key

    for invalid_key in ("", "/absolute", "path\\bad", "a/../b", "a/./b", "a//b", "a/", "a\x00b"):
        with pytest.raises(ValueError):
            _validate_storage_key(invalid_key)

    class Response:
        def __init__(self, status: int):
            self.status = status

    class FakeObsClient:
        def __init__(self):
            self.status = 200
            self.calls = []
            self.closed = False

        def putFile(self, bucket, key, file_path=None, headers=None, **kwargs):
            self.calls.append(("put", bucket, key, headers))
            return Response(self.status)

        def getFile(self, bucket, key, downloadPath=None, **kwargs):
            self.calls.append(("get", bucket, key))
            if self.status == 200:
                Path(downloadPath).write_bytes(b"stored-content")
            return Response(self.status)

        def deleteObject(self, bucket, key, **kwargs):
            self.calls.append(("delete", bucket, key))
            return Response(self.status)

        def close(self):
            self.closed = True

    config = Settings(
        _env_file=None,
        jwt_secret=_TEST_JWT_SECRET,
        storage_backend="obs",
        obs_endpoint="https://obs.test-region.myhuaweicloud.com",
        obs_bucket="paperlens-test-bucket",
        obs_prefix="paperlens",
        obs_credential_mode="ENV",
        obs_access_key_id="TEST_ACCESS_KEY",
        obs_secret_access_key="TEST_SECRET_KEY",
        obs_download_tmp_dir=str(tmp_path),
    )
    client = FakeObsClient()
    storage = OBSStorage(client=client, config=config)
    source = tmp_path / "source.pdf"
    source.write_bytes(b"source-content")

    storage.save("papers/test-id/source.pdf", str(source))
    put_headers = client.calls[0][3]
    assert put_headers.acl == "private"
    assert put_headers.sseHeader.encryption == "AES256"

    with storage.materialize("papers/test-id/source.pdf") as local_path:
        materialized = Path(local_path)
        assert materialized.read_bytes() == b"stored-content"
    assert not materialized.exists()

    storage.delete("papers/test-id/source.pdf")
    storage.close()
    assert client.closed is True
    with pytest.raises(NotImplementedError):
        storage.read_path("papers/test-id/source.pdf")

    client.status = 503
    with pytest.raises(OSError, match="存储操作失败"):
        storage.save("papers/test-id/source.pdf", str(source))
    with pytest.raises(OSError, match="存储操作失败"):
        with storage.materialize("papers/test-id/source.pdf"):
            pass
    with pytest.raises(OSError, match="存储操作失败"):
        storage.delete("papers/test-id/source.pdf")
    assert list(tmp_path.glob("paperlens_obs_*")) == []


def test_production_settings_fail_closed_without_leaking_secrets():
    valid = _production_settings()
    assert valid.docs_enabled is False

    insecure_cases = (
        {"debug": True},
        {"auth_cookie_secure": False},
        {"storage_backend": "local"},
        {"obs_endpoint": "http://obs.test.myhuaweicloud.com"},
        {"obs_sse_mode": "KMS", "obs_kms_key_id": ""},
        {"jwt_secret": "a" * 64},
        {"database_url": "postgresql+psycopg2://u:p@localhost:5432/paperlens?sslmode=verify-full"},
        {"database_url": "postgresql+psycopg2://u:p@rds.internal:5432/paperlens?sslmode=require"},
        {"database_url": "postgresql+psycopg2://u:p@rds.internal:5432/paperlens?sslmode=verify-full"},
        {"llm_backend": "mock", "llm_api_key": None},
        {"embedding_provider": "mock", "embedding_api_key": None},
        {"trusted_proxy_cidrs": "0.0.0.0/0"},
    )
    for overrides in insecure_cases:
        with pytest.raises(ValidationError) as exc_info:
            _production_settings(**overrides)
        rendered = str(exc_info.value)
        assert _TEST_JWT_SECRET not in rendered
        assert "TEST_SECRET_KEY" not in rendered


def test_storage_factory_lifecycle_and_production_docs_are_closed(monkeypatch, tmp_path):
    import paperlens.core.config as config_mod
    import paperlens.main as main_mod
    import paperlens.utils.storage as storage_mod

    local_settings = Settings(
        _env_file=None,
        jwt_secret=_TEST_JWT_SECRET,
        storage_backend="local",
        storage_root=str(tmp_path),
        recovery_enabled=False,
    )
    storage_mod.close_storage()
    monkeypatch.setattr(config_mod, "settings", local_settings)
    monkeypatch.setattr(storage_mod, "settings", local_settings)
    first = storage_mod.get_storage()
    assert storage_mod.get_storage() is first
    storage_mod.close_storage()
    assert storage_mod.get_storage() is not first
    storage_mod.close_storage()

    production_settings = _production_settings()
    monkeypatch.setattr(main_mod, "settings", production_settings)
    app = main_mod.create_app()
    paths = {route.path for route in app.routes}
    assert "/api/docs" not in paths
    assert "/api/redoc" not in paths
    assert "/api/openapi.json" not in paths
