from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app, get_today
from db.database import get_db, make_engine
from db.init_db import CATEGORIES
from db.models import Base, Category, Event

TODAY = date(2026, 11, 2)


@pytest.fixture
def today():
    return TODAY


@pytest.fixture
def session_factory():
    # Своя база в памяти на каждый тест. StaticPool держит одно соединение, иначе база пропадёт
    engine = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all(Category(slug=slug, name=name) for slug, name in CATEGORIES)
        db.commit()
    yield factory
    engine.dispose()


@pytest.fixture
def client(session_factory):
    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_today] = lambda: TODAY
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def add_event(session_factory):
    """Добавляет мероприятие и возвращает его id. По умолчанию — опубликованный пост ВК на сегодня."""

    def add(category="sport", **fields):
        defaults = dict(source="vk", status="published", title="Мероприятие", organizer="Команда ТПУ", event_date=TODAY)
        with session_factory() as db:
            event = Event(category=db.scalar(select(Category).where(Category.slug == category)), **{**defaults, **fields})
            db.add(event)
            db.commit()
            return event.id

    return add
