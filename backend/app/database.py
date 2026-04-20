"""
Database engine and session management.
Supports both direct PostgreSQL URLs and Cloud SQL via Unix socket.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# If Cloud SQL connection name is set, use Unix socket
if settings.CLOUD_SQL_CONNECTION_NAME:
    socket_dir = f"/cloudsql/{settings.CLOUD_SQL_CONNECTION_NAME}"
    # DB_URL should be like: postgresql://user:pass@/dbname
    # The socket is passed via connect_args
    engine = create_engine(
        settings.DB_URL,
        pool_pre_ping=True,
        connect_args={"host": socket_dir},
    )
else:
    engine = create_engine(settings.DB_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
