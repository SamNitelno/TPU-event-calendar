"""Подключение к базе по DATABASE_URL из .env."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()


def normalize_url(url: str) -> str:
    """Render и Neon выдают адрес вида postgres://..., а SQLAlchemy понимает только postgresql://."""
    if url.startswith("postgres://"):
        return "postgresql://" + url.removeprefix("postgres://")
    return url


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if os.getenv("VERCEL") == "1" and (not url or url.startswith("sqlite")):
        raise RuntimeError("Vercel requires a PostgreSQL DATABASE_URL")
    return normalize_url(url or "sqlite:///calendar.db")


DATABASE_URL = database_url()


def make_engine(url: str, **kwargs) -> Engine:
    url = normalize_url(url)
    if not url.startswith("sqlite"):
        # pool_pre_ping: бесплатный PostgreSQL рвёт простаивающие соединения, а мы переподключаемся
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url.removeprefix("postgresql://")
        # Neon PgBouncer управляет соединениями; отдельный пул на каждой функции не нужен.
        kwargs.setdefault("poolclass", NullPool)
        kwargs.setdefault("connect_args", {"connect_timeout": 10})
        return create_engine(url, pool_pre_ping=True, **kwargs)

    # FastAPI выполняет запросы в разных потоках, а SQLite по умолчанию это запрещает
    engine = create_engine(url, connect_args={"check_same_thread": False}, **kwargs)

    @event.listens_for(engine, "connect")
    def sqlite_like_postgres(dbapi_connection, _):
        # SQLite по умолчанию не проверяет внешние ключи, а PostgreSQL проверяет.
        # Включаем, чтобы ошибку вида «категории 999 нет» ловить ещё на своём компьютере
        dbapi_connection.execute("PRAGMA foreign_keys = ON")
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
