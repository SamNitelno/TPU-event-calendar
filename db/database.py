"""Подключение к базе по DATABASE_URL из .env."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


def normalize_url(url: str) -> str:
    """Render и Neon выдают адрес вида postgres://..., а SQLAlchemy понимает только postgresql://."""
    if url.startswith("postgres://"):
        return "postgresql://" + url.removeprefix("postgres://")
    return url


DATABASE_URL = normalize_url(os.getenv("DATABASE_URL", "sqlite:///calendar.db"))


def make_engine(url: str, **kwargs) -> Engine:
    url = normalize_url(url)
    if not url.startswith("sqlite"):
        # pool_pre_ping: бесплатный PostgreSQL рвёт простаивающие соединения, а мы переподключаемся
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
