from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = settings.DATABASE_URL.strip()
        if not db_url:
            raise RuntimeError(
                "DATABASE_URL não configurada! Por favor, defina a variável DATABASE_URL "
                "no arquivo backend/.env com a sua connection string do Supabase. "
                "Consulte docs/ENVIRONMENT.md para instruções."
            )
        # Se fornecido postgresql:// sem driver, ajusta para postgresql+psycopg://
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Dependency injection para sessões do banco de dados no FastAPI."""
    session_factory = get_session_factory()
    db: Session = session_factory()
    try:
        yield db
    finally:
        db.close()
