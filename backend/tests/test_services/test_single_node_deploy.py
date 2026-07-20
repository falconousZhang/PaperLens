from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_single_node_compose_keeps_database_and_backend_private() -> None:
    compose = (ROOT / "deploy/huawei/docker-compose.single.yml").read_text(
        encoding="utf-8"
    )
    environment = (ROOT / "deploy/huawei/.env.single.example").read_text(
        encoding="utf-8"
    )

    assert '"0.0.0.0:80:8080"' in compose
    assert '"5432:5432"' not in compose
    assert '"8000:8000"' not in compose
    assert "PAPERLENS_STORAGE_BACKEND: local" in compose
    assert "PAPERLENS_EMBEDDING_PROVIDER: mock" in compose
    assert "PAPERLENS_LLM_API_KEY: ${PAPERLENS_LLM_API_KEY:?" in compose
    assert "storage-init:" in compose
    assert "chown -R paperlens:paperlens /app/data" in compose
    assert "condition: service_completed_successfully" in compose
    assert "replace-with-rotated-huawei-maas-key" in environment


def test_single_node_nginx_uses_http_proxy_metadata_and_hides_docs() -> None:
    nginx = (ROOT / "deploy/huawei/nginx.single.conf").read_text(encoding="utf-8")

    assert "proxy_set_header X-Forwarded-Proto $scheme;" in nginx
    assert "Strict-Transport-Security" not in nginx
    assert "client_body_temp_path /tmp/client_temp;" in nginx
    assert "proxy_temp_path /tmp/proxy_temp;" in nginx
    assert "location = /api/docs" in nginx
    assert "location = /api/redoc" in nginx
    assert "location = /api/openapi.json" in nginx
