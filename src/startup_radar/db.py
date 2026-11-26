"""Database engine/session and schema creation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings, home
from .models import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _url() -> str:
    url = get_settings().database_url
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        rel = url.removeprefix("sqlite:///")
        path = (home() / rel).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = _url()
        kwargs: dict[str, Any] = {"future": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
    return _engine


def get_session() -> Session:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory()


def init_db() -> None:
    Base.metadata.create_all(get_engine())
