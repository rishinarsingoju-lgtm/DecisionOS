from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine: Engine | None = (
    create_engine(settings.database_url, pool_pre_ping=True)
    if settings.database_url
    else None
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False) if engine else None


def get_session() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()