"""Сборщик с фейковым клиентом ВК: без сети, на in-memory SQLite."""
from datetime import datetime

import pytest
from sqlalchemy import select

from collector.run import run, save_post
from db.models import Event, VkPost


class FakeClient:
    def __init__(self, posts_by_owner: dict[int, list[dict]]):
        self.posts_by_owner = posts_by_owner
        self.calls: list[int] = []

    def get_posts(self, owner_id: int, count: int = 50, offset: int = 0):
        self.calls.append(owner_id)
        return self.posts_by_owner.get(owner_id, [])[:count]


def make_post(vk_post_id: int, text: str, ts: int = 1_700_000_000) -> dict:
    return {"id": vk_post_id, "text": text, "date": ts, "attachments": []}


@pytest.fixture
def session_factory(monkeypatch):
    """Своя база в памяти плюс подмена SessionLocal в collector.run."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from db.database import make_engine
    from db.models import Base, Category, VkCommunity
    from db.init_db import CATEGORIES

    engine = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all(Category(slug=s, name=n) for s, n in CATEGORIES)
        db.add(VkCommunity(owner_id=-44845822, name="Спортклуб «Сибирские львы»", link="https://vk.com/club44845822"))
        db.add(VkCommunity(owner_id=-19220040, name="ТПУ", link="https://vk.com/club19220040"))
        db.commit()

    import collector.run as run_module
    monkeypatch.setattr(run_module, "SessionLocal", factory)
    yield factory
    engine.dispose()


def test_run_creates_published_and_pending(session_factory):
    future = int(datetime(2027, 11, 3, 12, 0).timestamp())
    fake = FakeClient({
        -44845822: [
            make_post(1, "Турнир по теннису\n3 ноября 2027\n#спорт", ts=future),
            make_post(2, "Конкурс без даты\n#творчество", ts=future),
        ],
        -19220040: [
            make_post(3, "Лекция про ИИ 10 ноября 2027 18:00", ts=future),
        ],
    })

    stats = run(limit_per_community=10, client=fake)
    assert stats["events_new"] == 3
    assert stats["communities"] == 2

    with session_factory() as db:
        events = {e.title: e for e in db.scalars(select(Event))}
        assert events["Турнир по теннису"].status == "published"
        assert events["Конкурс без даты"].status == "pending"
        assert events["Лекция про ИИ 10 ноября 2027 18:00"].status == "published"
        # ссылка на пост
        assert events["Турнир по теннису"].original_post_link.endswith("wall-44845822_1")


def test_run_is_idempotent(session_factory):
    fake = FakeClient({-44845822: [make_post(1, "Турнир 3 ноября 2027 #спорт", ts=1_800_000_000)]})
    first = run(limit_per_community=10, client=fake)
    second = run(limit_per_community=10, client=fake)
    assert first["events_new"] == 1
    assert second["events_new"] == 0
    assert second["skipped"] == 1
    with session_factory() as db:
        assert db.scalar(select(VkPost).where(VkPost.vk_post_id == 1)) is not None


def test_broken_post_does_not_stop_others(session_factory):
    fake = FakeClient({-44845822: [
        {"id": 1, "text": "", "date": None, "attachments": []},  # упадёт на fromtimestamp
        make_post(2, "Турнир 3 ноября 2027 #спорт", ts=1_800_000_000),
    ]})
    stats = run(limit_per_community=10, client=fake)
    assert stats["events_new"] == 1
