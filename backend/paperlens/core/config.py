from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PaperLens"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = "postgresql+psycopg2://paperlens:paperlens@localhost:5432/paperlens"

    llm_backend: str = "mock"

    max_pdf_size_mb: int = 50
    max_experiment_file_size_mb: int = 20
    max_page_count: int = 500

    storage_backend: str = "local"
    storage_root: str = "./data"

    demo_user_id: str = "demo-user"

    chunk_max_chars: int = 1500
    chunk_overlap_chars: int = 200

    model_config = {"env_prefix": "PAPERLENS_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
