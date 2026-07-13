import os
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_BUSINESS_TABLES = [
    "finding_evidences", "review_findings", "review_results",
    "analysis_tasks", "metric_records", "experiment_files",
    "experiment_results", "export_reports",
    "evidences", "paper_chunks", "paper_tables",
    "paper_sections", "paper_pages", "papers",
]


def get_test_db_url() -> str | None:
    url = os.environ.get("PAPERLENS_TEST_DATABASE_URL")
    if not url:
        return None
    host = os.environ.get("PAPERLENS_DB_HOST", "localhost")
    return url.replace("localhost", host).replace("127.0.0.1", host)


def parse_db_name(url: str) -> str | None:
    try:
        parsed = urlparse(url.replace("+psycopg2", ""))
        path = parsed.path
        if path.startswith("/"):
            path = path[1:]
        return path
    except Exception:
        return None


def _get_maintenance_dsn(test_url: str) -> str:
    parsed = urlparse(test_url.replace("+psycopg2", ""))
    return f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port or 5432}/postgres"


def is_test_db_required() -> bool:
    return os.environ.get("PAPERLENS_REQUIRE_TEST_DB", "").lower() in ("true", "1", "yes")


def assert_test_database():
    url = os.environ.get("PAPERLENS_DATABASE_URL", "")
    db_name = parse_db_name(url)
    if is_test_db_required():
        assert db_name == "paperlens_test", (
            f"PAPERLENS_REQUIRE_TEST_DB=true but database is '{db_name}', expected 'paperlens_test'. "
            f"URL: {url}"
        )


def db_available() -> bool:
    url = get_test_db_url()
    if not url:
        return False
    if is_test_db_required():
        return True
    try:
        import psycopg2
        connect_url = url.replace("+psycopg2", "")
        conn = psycopg2.connect(connect_url, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


def ensure_test_database():
    test_url = get_test_db_url()
    if not test_url:
        if is_test_db_required():
            raise AssertionError("PAPERLENS_REQUIRE_TEST_DB=true but PAPERLENS_TEST_DATABASE_URL is not set")
        return
    db_name = parse_db_name(test_url)
    assert db_name == "paperlens_test", (
        f"Integration test database must be 'paperlens_test', got '{db_name}'"
    )
    import psycopg2
    maintenance_dsn = _get_maintenance_dsn(test_url)
    try:
        conn = psycopg2.connect(maintenance_dsn, connect_timeout=5)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'paperlens_test'")
        if cur.fetchone() is None:
            cur.execute("CREATE DATABASE paperlens_test")
        cur.close()
        conn.close()
    except Exception as e:
        if is_test_db_required():
            raise AssertionError(f"PAPERLENS_REQUIRE_TEST_DB=true: Failed to ensure test database exists: {e}") from e
        raise
    connect_url = test_url.replace("+psycopg2", "")
    try:
        conn = psycopg2.connect(connect_url, connect_timeout=5)
        conn.close()
    except Exception as e:
        if is_test_db_required():
            raise AssertionError(f"PAPERLENS_REQUIRE_TEST_DB=true: Cannot connect to paperlens_test after creation: {e}") from e
        raise


def run_alembic_migrations(test_url: str):
    import subprocess
    env = os.environ.copy()
    env["PAPERLENS_DATABASE_URL"] = test_url
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        if is_test_db_required():
            raise AssertionError(
                f"PAPERLENS_REQUIRE_TEST_DB=true: Alembic migration failed (rc={result.returncode}):\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        raise RuntimeError(f"Alembic migration failed: {result.stderr}")


def verify_alembic_revision(test_url: str, expected: str = "003_normalized_and_error"):
    import subprocess
    env = os.environ.copy()
    env["PAPERLENS_DATABASE_URL"] = test_url
    result = subprocess.run(
        ["alembic", "current"],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        if is_test_db_required():
            raise AssertionError(f"PAPERLENS_REQUIRE_TEST_DB=true: alembic current failed:\n{result.stdout}\n{result.stderr}")
        raise RuntimeError(f"alembic current failed: {result.stderr}")
    assert expected in result.stdout, (
        f"Expected revision '{expected}' not found in alembic current output:\n{result.stdout}"
    )


def truncate_test_tables(test_url: str):
    db_name = parse_db_name(test_url)
    assert db_name == "paperlens_test", (
        f"Refusing to truncate tables in non-test database '{db_name}'"
    )
    import psycopg2
    connect_url = test_url.replace("+psycopg2", "")
    conn = psycopg2.connect(connect_url)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        try:
            table_list = ", ".join(f'"{t}"' for t in _BUSINESS_TABLES)
            cur.execute(f"TRUNCATE TABLE {table_list} CASCADE")
        finally:
            cur.close()
    finally:
        conn.close()


def verify_no_test_residuals(test_url: str):
    db_name = parse_db_name(test_url)
    assert db_name == "paperlens_test", (
        f"Refusing to check residuals in non-test database '{db_name}'"
    )
    import psycopg2
    connect_url = test_url.replace("+psycopg2", "")
    conn = psycopg2.connect(connect_url)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        try:
            for table in _BUSINESS_TABLES:
                cur.execute(f'SELECT count(*) FROM "{table}"')
                count = cur.fetchone()[0]
                assert count == 0, f"Residual data in paperlens_test.{table}: {count} rows"
        finally:
            cur.close()
    finally:
        conn.close()


def count_papers_in_db(url: str) -> int:
    import psycopg2
    connect_url = url.replace("+psycopg2", "")
    conn = psycopg2.connect(connect_url)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM papers")
        count = cur.fetchone()[0]
        return count
    finally:
        cur.close()
        conn.close()


def get_dev_db_url() -> str | None:
    test_url = get_test_db_url()
    if not test_url:
        return None
    dev_url = test_url.replace("paperlens_test", "paperlens")
    host = os.environ.get("PAPERLENS_DB_HOST", "localhost")
    return dev_url.replace("localhost", host).replace("127.0.0.1", host)


def wait_for_paper_status(paper_id: str, timeout: float = 15) -> str:
    from paperlens.core.database import SessionLocal
    from paperlens.models.models import Paper
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        db = SessionLocal()
        try:
            paper = db.get(Paper, paper_id)
            status = paper.status if paper else None
        finally:
            db.close()
        if status in ("PARSED", "FAILED"):
            return status
        time.sleep(0.5)
    raise TimeoutError(f"Paper {paper_id} did not reach terminal status within {timeout}s")