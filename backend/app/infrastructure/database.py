from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.outbound.db.sqlalchemy_models import Base
from app.infrastructure.config import Settings, get_settings


def create_db_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()

    return create_engine(
        settings.database_url,
        echo=False,
        future=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def create_all_tables(engine: Engine | None = None) -> None:
    engine = engine or create_db_engine()
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    engine = create_db_engine()
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        yield session
