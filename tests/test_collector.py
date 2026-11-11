"""Сборщик с фейковым клиентом ВК: без сети, на in-memory SQLite."""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from collector import vk_client
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
            make_post(2, "Конкурс без даты\nПриглашаем всех участвовать\n#творчество", ts=future),
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


# 14 октября 2026, 12:00 по Томску (UTC+7)
OCT_14 = int(datetime(2026, 10, 14, 5, 0, tzinfo=timezone.utc).timestamp())


def events(factory):
    with factory() as db:
        return db.scalars(select(Event).order_by(Event.id)).all()


def test_broken_post_in_the_middle_keeps_earlier_ones(session_factory):
    fake = FakeClient({-44845822: [
        make_post(1, "Турнир по футболу 20 октября в 18:00", ts=OCT_14),
        {"id": 2, "text": "Турнир", "date": None},
        make_post(3, "Турнир по волейболу 21 октября в 18:00", ts=OCT_14),
    ]})
    stats = run(limit_per_community=10, client=fake)
    assert (stats["events_new"], stats["errors"]) == (2, 1)
    assert len(events(session_factory)) == 2


def test_repost_is_parsed_from_the_original_post(session_factory):
    repost = make_post(5, ".", ts=OCT_14)
    repost["copy_history"] = [{"id": 777, "owner_id": -555, "text": "Лекция о дронах 20 октября в 18:00\nГде: корпус 10"}]
    run(limit_per_community=10, client=FakeClient({-19220040: [repost]}))
    [event] = events(session_factory)
    assert event.title == "Лекция о дронах 20 октября в 18:00"
    assert event.original_post_link == "https://vk.com/wall-555_777"
    assert (event.location, event.status) == ("Корпус 10", "published")


def test_repost_of_a_collected_post_does_not_duplicate_the_event(session_factory):
    original = make_post(52494, "Турнир по футболу 20 октября в 18:00", ts=OCT_14)
    repost = make_post(5, "", ts=OCT_14)
    repost["copy_history"] = [{"id": 52494, "owner_id": -44845822, "text": original["text"]}]
    stats = run(limit_per_community=10, client=FakeClient({-44845822: [original], -19220040: [repost]}))
    assert (stats["events_new"], stats["repeat"]) == (1, 1)
    with session_factory() as db:
        assert len(db.scalars(select(VkPost)).all()) == 2  # сам репост тоже сохранён


def test_news_reports_and_ads_do_not_become_events(session_factory):
    ad = make_post(4, "Скидки 20 октября", ts=OCT_14)
    ad["marked_as_ads"] = 1
    fake = FakeClient({-44845822: [
        make_post(1, "Поздравляем команду с победой!", ts=OCT_14),
        make_post(2, "1 октября прошёл турнир по футболу, спасибо всем", ts=OCT_14),
        make_post(3, "Конкурс фотографий\nПриглашаем присылать работы", ts=OCT_14),
        make_post(5, "ТПУ и ТГУ создадут совместную лабораторию: участники встречи подписали соглашение", ts=OCT_14),
        ad,
    ]})
    stats = run(limit_per_community=10, client=fake)
    assert (stats["post_only"], stats["ads"], stats["events_new"]) == (3, 1, 1)
    [contest] = events(session_factory)
    assert (contest.title, contest.status) == ("Конкурс фотографий", "pending")


def test_publication_day_is_counted_in_tomsk_time(session_factory):
    # 14 октября 19:30 UTC — в Томске уже 15 октября, 02:30. «Сегодня» — это 15-е
    late = int(datetime(2026, 10, 14, 19, 30, tzinfo=timezone.utc).timestamp())
    run(limit_per_community=10, client=FakeClient({-44845822: [make_post(1, "Сегодня в 19:00 турнир по футболу", ts=late)]}))
    [event] = events(session_factory)
    assert event.event_date == date(2026, 10, 15)


def test_ambiguous_date_waits_for_admin(session_factory):
    text = "Турнир по футболу\n24 октября — групповой этап\n31 октября — финал"
    run(limit_per_community=10, client=FakeClient({-44845822: [make_post(1, text, ts=OCT_14)]}))
    [event] = events(session_factory)
    assert (event.event_date, event.status) == (date(2026, 10, 24), "pending")


def test_vk_markup_does_not_reach_the_site(session_factory):
    text = "[club14752902|Профком ТПУ] зовёт на турнир по футболу 20 октября в 18:00 #Мероприятие@postpu"
    run(limit_per_community=10, client=FakeClient({-44845822: [make_post(1, text, ts=OCT_14)]}))
    [event] = events(session_factory)
    assert event.title.startswith("Профком ТПУ зовёт") and "[club" not in event.description


# Клиент ВК

class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_vk_client_retries_rate_limit_and_keeps_token_out_of_url(monkeypatch):
    calls = []
    answers = [{"error": {"error_code": 6, "error_msg": "Too many requests per second"}},
               {"response": {"items": [{"id": 1}]}}]

    def fake_post(url, data, timeout):
        calls.append((url, data))
        return FakeResponse(answers[len(calls) - 1])

    monkeypatch.setattr(vk_client.httpx, "post", fake_post)
    monkeypatch.setattr(vk_client.time, "sleep", lambda _: None)
    client = vk_client.VkClient(token="secret", min_interval=0)
    assert client.get_posts(-1, count=1) == [{"id": 1}]
    assert len(calls) == 2
    url, data = calls[0]
    assert "secret" not in url and data["access_token"] == "secret" and data["filter"] == "owner"


def test_vk_client_does_not_retry_access_errors(monkeypatch):
    monkeypatch.setattr(vk_client.httpx, "post", lambda url, data, timeout: FakeResponse(
        {"error": {"error_code": 15, "error_msg": "Access denied"}}))
    client = vk_client.VkClient(token="secret", min_interval=0)
    with pytest.raises(vk_client.VkError, match="15"):
        client.get_posts(-1)
