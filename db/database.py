"""Подключение к базе по DATABASE_URL из .env."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///calendar.db")


def make_engine(url: str, **kwargs) -> Engine:
    if not url.startswith("sqlite"):
        return create_engine(url, **kwargs)

    # FastAPI выполняет запросы в разных потоках, а SQLite по умолчанию это запрещает
    engine = create_engine(url, connect_args={"check_same_thread": False}, **kwargs)

    @event.listens_for(engine, "connect")
    def unicode_lower(dbapi_connection, _):
        # Встроенный lower() в SQLite понимает только латиницу, и поиск «турнир»
        # не находит «Турнир». Заменяем его питоновским. В PostgreSQL этой проблемы нет.
        dbapi_connection.create_function(
            "lower", 1, lambda s: s.lower() if isinstance(s, str) else s, deterministic=True
        )

    return engine


engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """Сессия на один запрос: FastAPI закрывает её после ответа."""
    with SessionLocal() as session:
        yield session
