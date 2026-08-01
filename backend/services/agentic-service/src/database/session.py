"""SQLAlchemy engine and session factory.

The engine is created ONCE at import and shared for the process lifetime. It
owns a connection pool; building one per request would open a fresh TCP + TLS
handshake to Neon on every call.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings

url = settings.database_url 

engine = create_engine(
    url,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
