import ipaddress
import re
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PaperLens"
    app_version: str = "0.1.0"
    debug: bool = False
    env: Literal["local", "test", "production"] = "local"

    database_url: str = "postgresql+psycopg2://paperlens:paperlens@localhost:5432/paperlens"

    llm_backend: str = Field(default="mock", pattern=r"^(mock|huawei_maas)$")
    llm_base_url: str = "https://api.modelarts-maas.com/v2"
    llm_model: str = "glm-5.2"
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)
    learning_llm_timeout_seconds: float = Field(default=180.0, ge=1.0, le=600.0)
    llm_max_completion_tokens: int = Field(default=4096, ge=1, le=16384)

    max_pdf_size_mb: int = 50
    max_experiment_file_size_mb: int = 20
    max_experiment_analysis_numeric_cells: int = Field(default=5_000_000, ge=1, le=10_000_000)
    experiment_comparison_absolute_tolerance: float = Field(default=1e-6, ge=0.0, le=1e12)
    experiment_comparison_relative_tolerance: float = Field(default=0.01, ge=0.0, le=1.0)
    max_page_count: int = 500
    max_report_size_bytes: int = Field(default=5_000_000, ge=100_000, le=50_000_000)
    learning_max_source_chars: int = Field(default=40_000, ge=1_000, le=500_000)
    learning_max_evidences: int = Field(default=12, ge=1, le=50)
    learning_max_evidence_chars: int = Field(default=2_000, ge=100, le=20_000)

    storage_backend: Literal["local", "obs"] = "local"
    storage_root: str = "./data"
    obs_endpoint: str = ""
    obs_bucket: str = ""
    obs_prefix: str = ""
    obs_credential_mode: Literal["ECS", "ENV"] = "ECS"
    obs_access_key_id: SecretStr | None = None
    obs_secret_access_key: SecretStr | None = None
    obs_security_token: SecretStr | None = None
    obs_sse_mode: Literal["OBS", "KMS"] = "OBS"
    obs_kms_key_id: str = ""
    obs_download_tmp_dir: str = ""
    obs_timeout_seconds: int = Field(default=30, ge=10, le=60)
    obs_ca_bundle: str = ""

    demo_user_id: str = "demo-user"

    jwt_secret: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "paperlens"
    jwt_audience: str = "paperlens-api"
    jwt_access_ttl_minutes: int = Field(default=15, ge=5, le=60)
    jwt_refresh_ttl_days: int = Field(default=30, ge=1, le=90)
    jwt_reset_ttl_minutes: int = Field(default=15, ge=5, le=60)
    auth_cookie_secure: bool = True
    auth_max_failed_logins: int = Field(default=5, ge=3, le=20)
    auth_lockout_minutes: int = Field(default=15, ge=1, le=1440)

    chunk_max_chars: int = 1500
    chunk_overlap_chars: int = 200

    review_evidence_top_k: int = Field(default=8, ge=1, le=50)

    qa_evidence_top_k: int = Field(default=8, ge=1, le=50)
    qa_question_max_chars: int = Field(default=2_000, ge=1, le=2_000)
    qa_context_turns: int = Field(default=200, ge=1, le=500)
    qa_context_max_chars: int = Field(default=120_000, ge=1_000, le=500_000)
    qa_evidence_max_chars: int = Field(default=2_000, ge=100, le=20_000)
    qa_full_paper_max_chars: int = Field(default=300_000, ge=10_000, le=500_000)
    qa_current_page_max_chars: int = Field(default=40_000, ge=1_000, le=100_000)
    qa_paper_memory_max_chars: int = Field(default=12_000, ge=1_000, le=30_000)

    highlight_max_chars: int = Field(default=5_000, ge=100, le=50_000)

    recovery_enabled: bool = True
    recovery_stale_seconds: int = Field(default=300, ge=1, le=86400)
    recovery_batch_size: int = Field(default=50, ge=1, le=1000)
    recovery_max_workers: int = Field(default=4, ge=1, le=32)

    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    rate_limit_max_keys: int = Field(default=10000, ge=100, le=1000000)
    rate_limit_read_quota: int = Field(default=300, ge=1, le=100000)
    rate_limit_write_quota: int = Field(default=60, ge=1, le=10000)
    rate_limit_auth_quota: int = Field(default=10, ge=1, le=1000)
    rate_limit_upload_quota: int = Field(default=10, ge=1, le=1000)
    trusted_proxy_cidrs: str = ""

    db_pool_size: int = Field(default=5, ge=1, le=100)
    db_pool_max_overflow: int = Field(default=10, ge=0, le=100)
    db_pool_timeout_seconds: int = Field(default=10, ge=1, le=300)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)

    embedding_provider: str = Field(default="mock", pattern=r"^(mock|huawei_maas)$")
    embedding_base_url: str = "https://api.modelarts-maas.com/v1"
    embedding_model: str = "bge-m3"
    embedding_api_key: SecretStr | None = None
    embedding_timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    embedding_batch_size: int = Field(default=32, ge=1, le=256)

    model_config = {
        "env_prefix": "PAPERLENS_",
        "env_file": ".env",
        "extra": "ignore",
        "hide_input_in_errors": True,
    }

    @property
    def docs_enabled(self) -> bool:
        return self.env != "production"

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("PAPERLENS_JWT_SECRET must contain at least 32 bytes")
        return value

    @field_validator(
        "recovery_max_workers",
        "rate_limit_window_seconds",
        "rate_limit_max_keys",
        "rate_limit_read_quota",
        "rate_limit_write_quota",
        "rate_limit_auth_quota",
        "rate_limit_upload_quota",
        "db_pool_size",
        "db_pool_max_overflow",
        "db_pool_timeout_seconds",
        "db_pool_recycle_seconds",
        "obs_timeout_seconds",
        mode="before",
    )
    @classmethod
    def reject_boolean_integer_settings(cls, value):
        if isinstance(value, bool):
            raise ValueError("boolean is not a valid integer setting")
        return value

    @field_validator("trusted_proxy_cidrs")
    @classmethod
    def validate_trusted_proxy_cidrs(cls, value: str) -> str:
        for part in value.split(","):
            candidate = part.strip()
            if not candidate:
                continue
            try:
                ipaddress.ip_network(candidate, strict=False)
            except ValueError as exc:
                raise ValueError("PAPERLENS_TRUSTED_PROXY_CIDRS contains an invalid CIDR") from exc
        return value

    @field_validator("obs_bucket")
    @classmethod
    def validate_obs_bucket(cls, value: str) -> str:
        if value:
            if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", value):
                raise ValueError("PAPERLENS_OBS_BUCKET is not a valid bucket name")
            if ".." in value or ".-" in value or "-." in value:
                raise ValueError("PAPERLENS_OBS_BUCKET is not a valid bucket name")
            try:
                ipaddress.ip_address(value)
            except ValueError:
                pass
            else:
                raise ValueError("PAPERLENS_OBS_BUCKET is not a valid bucket name")
        return value

    @field_validator("obs_prefix")
    @classmethod
    def validate_obs_prefix(cls, value: str) -> str:
        if value:
            if value != value.strip() or value.startswith("/") or value.endswith("/"):
                raise ValueError("PAPERLENS_OBS_PREFIX must not have leading/trailing slashes")
            segments = value.split("/")
            if any(not segment or segment in {".", ".."} for segment in segments):
                raise ValueError("PAPERLENS_OBS_PREFIX contains an invalid segment")
            if "\\" in value or re.search(r"[\x00-\x1f\x7f]", value) or len(value) > 512:
                raise ValueError("PAPERLENS_OBS_PREFIX is not valid")
        return value

    @field_validator("obs_endpoint")
    @classmethod
    def validate_obs_endpoint(cls, value: str) -> str:
        if not value:
            return value
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("PAPERLENS_OBS_ENDPOINT must be an HTTPS origin")
        try:
            ipaddress.ip_address(parsed.hostname)
        except ValueError:
            pass
        else:
            raise ValueError("PAPERLENS_OBS_ENDPOINT must use a domain name")
        return value.rstrip("/")

    @staticmethod
    def _secret_is_set(value: SecretStr | None) -> bool:
        return value is not None and bool(value.get_secret_value())

    @staticmethod
    def _validate_https_api_url(value: str, field_name: str) -> None:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(f"{field_name} must use a safe HTTPS URL")

    def _validate_production_database(self) -> None:
        parsed = urlsplit(self.database_url)
        if (
            parsed.scheme not in {"postgresql", "postgresql+psycopg2"}
            or not parsed.hostname
            or parsed.fragment
        ):
            raise ValueError("PAPERLENS_DATABASE_URL must be a PostgreSQL DSN in production")
        if not parsed.username or parsed.password is None or parsed.path in {"", "/"}:
            raise ValueError("PAPERLENS_DATABASE_URL is incomplete in production")
        if parsed.hostname.casefold() == "localhost":
            raise ValueError("PAPERLENS_DATABASE_URL must not target localhost in production")
        try:
            database_address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            database_address = None
        if database_address is not None and database_address.is_loopback:
            raise ValueError("PAPERLENS_DATABASE_URL must not target loopback in production")
        query = parse_qs(parsed.query, keep_blank_values=True)
        sslmodes = query.get("sslmode", [])
        if sslmodes != ["verify-full"]:
            raise ValueError("PAPERLENS_DATABASE_URL must use sslmode=verify-full in production")
        sslrootcerts = query.get("sslrootcert", [])
        if len(sslrootcerts) != 1 or not sslrootcerts[0]:
            raise ValueError("PAPERLENS_DATABASE_URL must set sslrootcert in production")

    @model_validator(mode="after")
    def validate_production_and_obs(self) -> "Settings":
        if self.env == "production":
            if self.debug:
                raise ValueError("PAPERLENS_DEBUG must be false in production")
            if not self.auth_cookie_secure:
                raise ValueError("PAPERLENS_AUTH_COOKIE_SECURE must be true in production")
            trusted_networks = [
                ipaddress.ip_network(part.strip(), strict=False)
                for part in self.trusted_proxy_cidrs.split(",")
                if part.strip()
            ]
            if not trusted_networks or any(
                network.prefixlen == 0 for network in trusted_networks
            ):
                raise ValueError("PAPERLENS_TRUSTED_PROXY_CIDRS must be restricted in production")
            if self.storage_backend == "local":
                raise ValueError("PAPERLENS_STORAGE_BACKEND must be obs in production")
            placeholder_patterns = [
                "paperlens-test-only-secret",
                "change-me",
                "placeholder",
                "example",
                "changeme",
                "insecure",
            ]
            secret_raw = self.jwt_secret.get_secret_value()
            secret_val = secret_raw.lower()
            if len(secret_raw.encode("utf-8")) < 48 or len(set(secret_raw)) < 12:
                raise ValueError("PAPERLENS_JWT_SECRET is too weak for production")
            for pattern in placeholder_patterns:
                if pattern in secret_val:
                    raise ValueError("PAPERLENS_JWT_SECRET must not contain placeholder values in production")
            self._validate_production_database()
            if self.llm_backend != "huawei_maas" or not self._secret_is_set(self.llm_api_key):
                raise ValueError("Huawei MaaS LLM configuration is required in production")
            if self.embedding_provider != "huawei_maas" or not self._secret_is_set(self.embedding_api_key):
                raise ValueError("Huawei MaaS embedding configuration is required in production")
            self._validate_https_api_url(self.llm_base_url, "PAPERLENS_LLM_BASE_URL")
            self._validate_https_api_url(self.embedding_base_url, "PAPERLENS_EMBEDDING_BASE_URL")
            if urlsplit(self.llm_base_url).hostname != "api.modelarts-maas.com":
                raise ValueError("PAPERLENS_LLM_BASE_URL must use Huawei Cloud MaaS in production")
            if urlsplit(self.embedding_base_url).hostname != "api.modelarts-maas.com":
                raise ValueError("PAPERLENS_EMBEDDING_BASE_URL must use Huawei Cloud MaaS in production")
        if self.storage_backend == "obs":
            if not self.obs_endpoint:
                raise ValueError("PAPERLENS_OBS_ENDPOINT is required when storage_backend=obs")
            if not self.obs_bucket:
                raise ValueError("PAPERLENS_OBS_BUCKET is required when storage_backend=obs")
            if self.env == "production" and not urlsplit(self.obs_endpoint).hostname.endswith(
                ".myhuaweicloud.com"
            ):
                raise ValueError("PAPERLENS_OBS_ENDPOINT must use Huawei Cloud OBS in production")
            if self.obs_sse_mode == "KMS" and not self.obs_kms_key_id:
                raise ValueError("PAPERLENS_OBS_KMS_KEY_ID is required when obs_sse_mode=KMS")
            if self.obs_credential_mode == "ENV":
                if not self._secret_is_set(self.obs_access_key_id) or not self._secret_is_set(
                    self.obs_secret_access_key
                ):
                    raise ValueError("OBS ENV credentials are required when obs_credential_mode=ENV")
        return self


settings = Settings()
