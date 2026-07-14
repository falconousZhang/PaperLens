from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import SecretStr

from paperlens.core.config import settings
from paperlens.cli import _classify_smoke_failure, maas_smoke
from paperlens.services.llm_client import LLMError, validate_llm_config


def _compose_text() -> str:
    test_file = Path(__file__).resolve()
    candidates = [
        test_file.parents[3] / "docker-compose.yml",
        test_file.parents[2] / "docker-compose.yml",
        Path("/app/docker-compose.yml"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    pytest.fail("docker-compose.yml must be available for the Docker test suite")


class TestValidateLLMConfig:
    def test_pytest_session_forces_offline_backends(self):
        assert settings.llm_backend == "mock"
        assert settings.llm_api_key is None
        assert settings.embedding_provider == "mock"
        assert settings.embedding_api_key is None

    def test_mock_backend_returns_backend_mock(self):
        original = settings.llm_backend
        settings.llm_backend = "mock"
        try:
            result = validate_llm_config()
            assert result["backend"] == "mock"
            assert result["api_key_configured"] is False
        finally:
            settings.llm_backend = original

    def test_huawei_maas_with_valid_config(self):
        original_backend = settings.llm_backend
        original_key = settings.llm_api_key
        settings.llm_backend = "huawei_maas"
        object.__setattr__(settings, "llm_api_key", SecretStr("test-key-that-is-long-enough"))
        try:
            result = validate_llm_config()
            assert result["backend"] == "huawei_maas"
            assert result["api_key_configured"] is True
            assert "base_url" in result
            assert "model" in result
            assert "timeout_seconds" in result
            assert "max_completion_tokens" in result
        finally:
            settings.llm_backend = original_backend
            object.__setattr__(settings, "llm_api_key", original_key)

    @pytest.mark.parametrize(
        "api_key",
        [" ", "<your-api-key>", "your_api_key", "replace-me", "由用户环境安全注入"],
    )
    def test_huawei_maas_rejects_blank_and_placeholder_api_keys(self, api_key):
        from paperlens.services.huawei_maas_llm import HuaweiMaaSLLMClient

        with pytest.raises(LLMError, match="api_key"):
            HuaweiMaaSLLMClient(
                base_url="https://api.example.invalid/v2",
                model="offline-test-model",
                api_key=api_key,
            )

    def test_huawei_maas_rejects_full_chat_completions_url(self):
        from paperlens.services.huawei_maas_llm import HuaweiMaaSLLMClient

        with pytest.raises(LLMError, match="must not include /chat/completions"):
            HuaweiMaaSLLMClient(
                base_url="https://api.example.invalid/v2/chat/completions",
                model="offline-test-model",
                api_key="offline-test-only",
            )

    def test_huawei_maas_without_api_key_raises(self):
        original_backend = settings.llm_backend
        original_key = settings.llm_api_key
        settings.llm_backend = "huawei_maas"
        object.__setattr__(settings, "llm_api_key", None)
        try:
            with pytest.raises(LLMError, match="llm_api_key"):
                validate_llm_config()
        finally:
            settings.llm_backend = original_backend
            object.__setattr__(settings, "llm_api_key", original_key)

    def test_unknown_backend_raises(self):
        original = settings.llm_backend
        settings.llm_backend = "unknown"
        try:
            with pytest.raises(LLMError, match="Unknown LLM backend"):
                validate_llm_config()
        finally:
            settings.llm_backend = original


class TestCLIConfigCheck:
    def test_mock_config_check_succeeds(self):
        result = subprocess.run(
            [sys.executable, "-m", "paperlens.cli", "maas-config-check"],
            capture_output=True,
            text=True,
            env={**dict(__import__("os").environ), "PAPERLENS_LLM_BACKEND": "mock"},
        )
        assert result.returncode == 0
        assert "backend: mock" in result.stdout
        assert "api_key_configured: false" in result.stdout
        assert "OK:" in result.stdout

    def test_config_check_no_secret_in_output(self):
        fake_secret = "offline-config-secret-must-not-appear"
        result = subprocess.run(
            [sys.executable, "-m", "paperlens.cli", "maas-config-check"],
            capture_output=True,
            text=True,
            env={
                **dict(__import__("os").environ),
                "PAPERLENS_LLM_BACKEND": "huawei_maas",
                "PAPERLENS_LLM_BASE_URL": "https://api.example.invalid/v2",
                "PAPERLENS_LLM_MODEL": "offline-test-model",
                "PAPERLENS_LLM_API_KEY": fake_secret,
                "PAPERLENS_EMBEDDING_PROVIDER": "mock",
            },
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0
        assert "base_url_scheme: https" in output
        assert "base_url_host: api.example.invalid" in output
        assert "base_url_path: /v2" in output
        assert "api_key_configured: true" in output
        assert fake_secret not in output
        assert "Bearer" not in output
        assert "Authorization" not in output


class TestCLISmoke:
    def test_smoke_without_confirm_rejects(self):
        result = subprocess.run(
            [sys.executable, "-m", "paperlens.cli", "maas-smoke"],
            capture_output=True,
            text=True,
            env={**dict(__import__("os").environ), "PAPERLENS_LLM_BACKEND": "mock"},
        )
        assert result.returncode != 0
        assert "confirm-billable" in result.stderr

    def test_smoke_without_confirm_does_not_construct_client(self):
        calls = 0

        def factory():
            nonlocal calls
            calls += 1
            raise AssertionError("client must not be constructed")

        with pytest.raises(SystemExit):
            maas_smoke(False, client_factory=factory)
        assert calls == 0

    def test_smoke_non_maas_backend_rejects(self):
        result = subprocess.run(
            [sys.executable, "-m", "paperlens.cli", "maas-smoke", "--confirm-billable"],
            capture_output=True,
            text=True,
            env={**dict(__import__("os").environ), "PAPERLENS_LLM_BACKEND": "mock"},
        )
        assert result.returncode != 0
        assert "huawei_maas" in result.stderr

    def test_smoke_with_fake_client_calls_once(self):
        class FakeClient:
            def __init__(self):
                self.call_count = 0

            def chat(self, messages, **kwargs):
                self.call_count += 1
                assert messages == [{"role": "user", "content": "Hi"}]
                assert kwargs == {"thinking_type": "disabled"}
                return {"role": "assistant", "content": "Hello"}

        original = settings.llm_backend
        client = FakeClient()
        settings.llm_backend = "huawei_maas"
        try:
            maas_smoke(True, client_factory=lambda: client)
        finally:
            settings.llm_backend = original
        assert client.call_count == 1

    def test_smoke_default_client_caps_completion_tokens(self, monkeypatch):
        from paperlens.services import huawei_maas_llm

        created_with = {}

        class FakeClient:
            def __init__(self, **kwargs):
                created_with.update(kwargs)

            def chat(self, messages, **kwargs):
                assert kwargs == {"thinking_type": "disabled"}
                return {"role": "assistant", "content": "Hello"}

        monkeypatch.setattr(huawei_maas_llm, "HuaweiMaaSLLMClient", FakeClient)
        original_backend = settings.llm_backend
        original_max_tokens = settings.llm_max_completion_tokens
        settings.llm_backend = "huawei_maas"
        settings.llm_max_completion_tokens = 2048
        try:
            maas_smoke(True)
        finally:
            settings.llm_backend = original_backend
            settings.llm_max_completion_tokens = original_max_tokens
        assert created_with["max_completion_tokens"] == 32

    def test_smoke_empty_content_fails(self):
        class EmptyClient:
            def chat(self, messages, **kwargs):
                return {"role": "assistant", "content": "   "}

        original = settings.llm_backend
        settings.llm_backend = "huawei_maas"
        try:
            with pytest.raises(SystemExit):
                maas_smoke(True, client_factory=EmptyClient)
        finally:
            settings.llm_backend = original

    def test_smoke_exception_no_secret_leak(self, capsys):
        fake_secret = "offline-smoke-secret-must-not-appear"

        class ErrorClient:
            def chat(self, messages, **kwargs):
                raise LLMError(f"service rejected {fake_secret}")

        original = settings.llm_backend
        settings.llm_backend = "huawei_maas"
        try:
            with pytest.raises(SystemExit):
                maas_smoke(True, client_factory=ErrorClient)
        finally:
            settings.llm_backend = original
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert fake_secret not in output
        assert "MaaS smoke test failed" in output

    @pytest.mark.parametrize(
        ("message", "category"),
        [
            ("LLM service returned status 401", "authentication"),
            ("LLM service returned status 403", "permission"),
            ("LLM service returned status 402", "quota_or_billing"),
            ("LLM service returned status 429", "rate_or_quota"),
            ("LLM service returned status 400", "request"),
            ("LLM service returned status 503", "service"),
            ("LLM request timed out", "timeout"),
            ("LLM service connection failed", "connection"),
            ("LLM response truncated (finish_reason=length)", "truncated"),
            ("LLM response missing choices array", "response"),
            ("unexpected sensitive detail", "unknown"),
        ],
    )
    def test_smoke_failure_categories_are_fixed(self, message, category):
        assert _classify_smoke_failure(LLMError(message)) == category


class TestComposeDefaults:
    def test_compose_llm_variables_are_individually_forwarded(self):
        compose = _compose_text()
        expected = [
            "PAPERLENS_LLM_BACKEND: ${PAPERLENS_LLM_BACKEND:-mock}",
            "PAPERLENS_LLM_BASE_URL: ${PAPERLENS_LLM_BASE_URL:-https://api.modelarts-maas.com/v2}",
            "PAPERLENS_LLM_MODEL: ${PAPERLENS_LLM_MODEL:-glm-5.2}",
            "PAPERLENS_LLM_API_KEY: ${PAPERLENS_LLM_API_KEY:-}",
            "PAPERLENS_LLM_TIMEOUT_SECONDS: ${PAPERLENS_LLM_TIMEOUT_SECONDS:-60}",
            "PAPERLENS_LLM_MAX_COMPLETION_TOKENS: ${PAPERLENS_LLM_MAX_COMPLETION_TOKENS:-2048}",
        ]
        for line in expected:
            assert line in compose

    def test_compose_llm_defaults_to_mock(self):
        compose = _compose_text()
        assert "PAPERLENS_LLM_BACKEND: ${PAPERLENS_LLM_BACKEND:-mock}" in compose

    def test_compose_embedding_forced_mock(self):
        compose = _compose_text()
        assert "PAPERLENS_EMBEDDING_PROVIDER: mock" in compose

    def test_compose_llm_api_key_default_empty(self):
        compose = _compose_text()
        assert "PAPERLENS_LLM_API_KEY: ${PAPERLENS_LLM_API_KEY:-}" in compose
        assert "env_file:" not in compose
