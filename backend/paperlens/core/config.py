from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PaperLens"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = "postgresql+psycopg2://paperlens:paperlens@localhost:5432/paperlens"

    llm_backend: str = Field(default="mock", pattern=r"^(mock|huawei_maas)$")
    llm_base_url: str = "https://api.modelarts-maas.com/v2"
    llm_model: str = "glm-5.2"
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)
    llm_max_completion_tokens: int = Field(default=2048, ge=1, le=16384)

    max_pdf_size_mb: int = 50
    max_experiment_file_size_mb: int = 20
    max_page_count: int = 500

    storage_backend: str = "local"
    storage_root: str = "./data"

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

    embedding_provider: str = Field(default="mock", pattern=r"^(mock|huawei_maas)$")
    embedding_base_url: str = "https://api.modelarts-maas.com/v1"
    embedding_model: str = "bge-m3"
    embedding_api_key: SecretStr | None = None
    embedding_timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    embedding_batch_size: int = Field(default=32, ge=1, le=256)

    model_config = {"env_prefix": "PAPERLENS_", "env_file": ".env", "extra": "ignore"}

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("PAPERLENS_JWT_SECRET must contain at least 32 bytes")
        return value


settings = Settings()
