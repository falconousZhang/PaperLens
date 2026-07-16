import os
import subprocess
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from paperlens.models.models import PaperBookmark, PaperHighlight, PaperKnowledgeCard, PaperLibraryEntry, PaperNote
from tests.db_helpers import db_available, ensure_test_database, get_test_db_url, is_test_db_required, run_alembic_migrations, truncate_test_tables, verify_no_test_residuals


pytestmark = pytest.mark.skipif(
    not db_available() and not is_test_db_required(),
    reason="需要 PAPERLENS_TEST_DATABASE_URL",
)


def _alembic(test_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PAPERLENS_DATABASE_URL"] = test_url
    return subprocess.run(["alembic", *args], capture_output=True, text=True, env=environment)


def _owner_graph(connection):
    user_id = str(uuid.uuid4())
    paper_id = str(uuid.uuid4())
    connection.execute(
        text("INSERT INTO users (id, email, email_normalized, display_name, role, status, failed_login_count) VALUES (:id, :email, :email, 'P7.3 migration', 'USER', 'ACTIVE', 0)"),
        {"id": user_id, "email": f"p73-{user_id}@example.com"},
    )
    connection.execute(
        text("INSERT INTO papers (id, title, filename, storage_key, file_size, file_hash, page_count, status, user_id) VALUES (:id, 'P7.3', 'p73.pdf', 'p73/source.pdf', 1, :hash, 1, 'PARSED', :user_id)"),
        {"id": paper_id, "hash": "e" * 64, "user_id": user_id},
    )
    return user_id, paper_id


def test_personal_learning_migration_round_trip_preserves_existing_graph():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        downgraded = _alembic(test_url, "downgrade", "015_paper_qa_conversations")
        assert downgraded.returncode == 0, downgraded.stderr
        with engine.begin() as connection:
            user_id, paper_id = _owner_graph(connection)
        upgraded = _alembic(test_url, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM users WHERE id=:id"), {"id": user_id}).scalar_one() == 1
            assert connection.execute(text("SELECT count(*) FROM papers WHERE id=:id"), {"id": paper_id}).scalar_one() == 1
        assert _alembic(test_url, "downgrade", "015_paper_qa_conversations").returncode == 0
        assert _alembic(test_url, "upgrade", "head").returncode == 0
    finally:
        engine.dispose()
        run_alembic_migrations(test_url)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


@pytest.mark.parametrize(
    ("table_name", "insert_sql", "params"),
    [
        ("paper_library_entries", "INSERT INTO paper_library_entries (user_id,paper_id) VALUES (:user_id,:paper_id)", {}),
        ("paper_highlights", "INSERT INTO paper_highlights (id,user_id,paper_id,page_number,char_start,char_end,quoted_text,source_hash,color) VALUES (:id,:user_id,:paper_id,1,0,4,'text',:hash,'YELLOW')", {"hash": "a" * 64}),
        ("paper_bookmarks", "INSERT INTO paper_bookmarks (id,user_id,paper_id,page_number) VALUES (:id,:user_id,:paper_id,1)", {}),
        ("paper_notes", "INSERT INTO paper_notes (id,user_id,paper_id,anchor_type,content) VALUES (:id,:user_id,:paper_id,'PAPER','note')", {}),
        ("paper_knowledge_cards", "INSERT INTO paper_knowledge_cards (id,user_id,paper_id,front,back) VALUES (:id,:user_id,:paper_id,'front','back')", {}),
    ],
)
def test_personal_learning_nonempty_table_refuses_lossy_downgrade(table_name, insert_sql, params):
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        with engine.begin() as connection:
            user_id, paper_id = _owner_graph(connection)
            connection.execute(text(insert_sql), {"id": str(uuid.uuid4()), "user_id": user_id, "paper_id": paper_id, **params})
        refused = _alembic(test_url, "downgrade", "015_paper_qa_conversations")
        assert refused.returncode != 0
        current = _alembic(test_url, "current")
        assert current.returncode == 0
        assert "017_admin_audit_logs" in current.stdout
        with engine.connect() as connection:
            assert connection.execute(text(f'SELECT count(*) FROM "{table_name}"')).scalar_one() == 1
    finally:
        engine.dispose()
        run_alembic_migrations(test_url)
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)


def test_personal_learning_migration_and_orm_constraint_index_names_match():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    engine = create_engine(test_url)
    try:
        inspector = inspect(engine)
        for model in (PaperLibraryEntry, PaperHighlight, PaperBookmark, PaperNote, PaperKnowledgeCard):
            table = model.__table__
            database_checks = {item["name"] for item in inspector.get_check_constraints(table.name)}
            orm_checks = {item.name for item in table.constraints if item.__class__.__name__ == "CheckConstraint"}
            database_indexes = {item["name"] for item in inspector.get_indexes(table.name)}
            orm_indexes = {item.name for item in table.indexes}
            assert database_checks == orm_checks
            assert database_indexes == orm_indexes | {item["name"] for item in inspector.get_unique_constraints(table.name) if item["name"] in database_indexes}
    finally:
        engine.dispose()


def test_personal_learning_database_rejects_invalid_text_and_anchor_rows():
    test_url = get_test_db_url()
    assert test_url is not None and test_url.endswith("paperlens_test")
    ensure_test_database()
    run_alembic_migrations(test_url)
    truncate_test_tables(test_url)
    engine = create_engine(test_url)
    try:
        with engine.begin() as connection:
            user_id, paper_id = _owner_graph(connection)
        invalid_statements = [
            ("INSERT INTO paper_library_entries (user_id,paper_id,collection_name) VALUES (:user_id,:paper_id,'  bad  ')", {}),
            ("INSERT INTO paper_highlights (id,user_id,paper_id,page_number,char_start,char_end,quoted_text,source_hash,color) VALUES (:id,:user_id,:paper_id,1,0,1,' ',:hash,'YELLOW')", {"hash": "b" * 64}),
            ("INSERT INTO paper_notes (id,user_id,paper_id,anchor_type,page_number,content) VALUES (:id,:user_id,:paper_id,'PAPER',1,'note')", {}),
            ("INSERT INTO paper_knowledge_cards (id,user_id,paper_id,front,back) VALUES (:id,:user_id,:paper_id,' ','back')", {}),
        ]
        for statement, params in invalid_statements:
            with pytest.raises(IntegrityError):
                with engine.begin() as connection:
                    connection.execute(text(statement), {"id": str(uuid.uuid4()), "user_id": user_id, "paper_id": paper_id, **params})
    finally:
        engine.dispose()
        truncate_test_tables(test_url)
        verify_no_test_residuals(test_url)
