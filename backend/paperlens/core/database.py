from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from paperlens.core.config import settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def _build_engine_kwargs() -> dict:
    return dict(
        echo=False,
        hide_parameters=True,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_pool_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_recycle=settings.db_pool_recycle_seconds,
    )


def _ensure_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(settings.database_url, **_build_engine_kwargs())
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def configure_engine(database_url: str) -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(database_url, **_build_engine_kwargs())
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_engine():
    _ensure_engine()
    return _engine


class _SessionLocalProxy:
    def __call__(self, *args, **kwargs):
        _ensure_engine()
        return _SessionLocal(*args, **kwargs)

    def configure(self, **kwargs):
        _ensure_engine()
        _SessionLocal.configure(**kwargs)


SessionLocal = _SessionLocalProxy()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
