"""База: мероприятия, источники и категории сохраняются и читаются обратно; init_db и seed_test на чистой базе."""
import re
from datetime import date, datetime, time
from pathlib import Path

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import make_engine, normalize_url
from db.init_db import CATEGORIES, COMMUNITIES, community_link, init_db
from db.models import Category, Event, User, VkCommunity, VkPost
from db.seed_test import FORM_EVENTS, VK_EVENTS, seed

ROOT = Path(__file__).resolve().parent.parent
SPORT_CLUB = -44845822


@pytest.fixture
def engine(tmp_path):
    # Файл, а не память: init_db и seed_test работают с ним так же, как с calendar.db
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    init_db(engine)
    with Session(engine) as session:
        yield session


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def community(db, owner_id=SPORT_CLUB):
    return db.scalar(select(VkCommunity).where(VkCommunity.owner_id == owner_id))


def category(db, slug="sport"):
    return db.scalar(select(Category).where(Category.slug == slug))


# init_db

def test_init_db_creates_all_tables_on_clean_database(engine):
    init_db(engine)
    assert set(inspect(engine).get_table_names()) == {"vk_communities", "vk_posts", "categories", "events", "users"}


def test_init_db_fills_6_categories_and_15_communities(db):
    assert [(c.slug, c.name) for c in db.scalars(select(Category).order_by(Category.id))] == CATEGORIES
    communities = db.scalars(select(VkCommunity)).all()
    assert len(communities) == 15
    assert all(c.owner_id < 0 and c.is_active and c.link == community_link(c.owner_id) for c in communities)
    assert community(db, -19220040).link == "https://vk.com/club19220040"


def test_init_db_can_run_again_and_updates_names(engine, db):
    community(db).name = "Старое название"
    community(db, -19220040).is_active = False  # отключили вручную
    db.commit()

    init_db(engine)
    db.expire_all()
    assert (count(db, Category), count(db, VkCommunity)) == (6, 15)
    assert community(db).name == "Спортклуб «Сибирские львы»"
    assert community(db, -19220040).is_active is False


def test_communities_in_code_match_docs():
    text = (ROOT / "docs" / "communities.md").read_text(encoding="utf-8")
    documented = [int(n) for n in re.findall(r"\|\s*`(-\d+)`\s*\|", text)]
    assert sorted(documented) == sorted(owner_id for owner_id, _ in COMMUNITIES)
    assert len(set(documented)) == len(documented) == 15


# Сохранить и прочитать обратно

def test_vk_event_with_post_source_and_category_round_trips(db):
    published = datetime(2026, 11, 10, 12, 30)
    event = Event(
        post=VkPost(community=community(db), vk_post_id=52494, text="Текст поста целиком", published_at=published),
        category=category(db),
        source="vk",
        status="published",
        title="Мастер-класс по алтимату",
        description="Текст поста целиком",
        event_date=date(2026, 11, 13),
        start_time=time(18, 0),
        end_date=date(2026, 11, 14),
        end_time=time(20, 30),
        location="ул. Карпова, 4",
        organizer="Спортклуб «Сибирские львы»",
        original_post_link="https://vk.com/wall-44845822_52494",
        image_url="https://example.com/poster.jpg",
    )
    db.add(event)
    db.commit()
    event_id = event.id
    db.expunge_all()  # дальше читаем из базы, а не из памяти сессии

    saved = db.get(Event, event_id)
    assert (saved.event_date, saved.start_time, saved.end_date, saved.end_time) == (
        date(2026, 11, 13), time(18, 0), date(2026, 11, 14), time(20, 30),
    )
    assert (saved.title, saved.location, saved.organizer) == (
        "Мастер-класс по алтимату", "ул. Карпова, 4", "Спортклуб «Сибирские львы»",
    )
    assert saved.original_post_link == "https://vk.com/wall-44845822_52494"
    assert saved.category.slug == "sport"
    assert saved.post.text == "Текст поста целиком"
    assert saved.post.published_at == published
    assert saved.post.community.owner_id == SPORT_CLUB
    assert isinstance(saved.created_at, datetime)


def test_form_submission_is_saved_without_post(db):
    event = Event(source="form", status="pending", category=category(db, "volunteering"),
                  title="Субботник", organizer="Волонтёрский центр", event_date=date(2026, 11, 20),
                  contact="test@example.com")
    db.add(event)
    db.commit()
    event_id = event.id
    db.expunge_all()
    saved = db.get(Event, event_id)
    assert (saved.post, saved.source, saved.status, saved.contact) == (None, "form", "pending", "test@example.com")


def test_event_without_date_and_category_can_wait_for_admin(db):
    # Сборщик не нашёл дату и категорию — запись всё равно сохраняется и ждёт администратора
    db.add(Event(post=VkPost(community=community(db), vk_post_id=1, text="Конкурс",
                             published_at=datetime(2026, 11, 10)),
                 source="vk", status="pending", title="Конкурс", organizer="Команда ТПУ"))
    db.commit()
    assert db.scalar(select(Event)).event_date is None


# База не принимает неверные данные

def test_same_vk_post_cannot_be_saved_twice(db):
    def post(owner_id, text):
        return VkPost(community=community(db, owner_id), vk_post_id=1, text=text, published_at=datetime(2026, 11, 10))

    db.add(post(SPORT_CLUB, "первый раз"))
    db.commit()
    db.add(post(SPORT_CLUB, "второй раз"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    # Тот же номер в другом сообществе — другой пост
    db.add(post(-19220040, "другое сообщество"))
    db.commit()
    assert count(db, VkPost) == 2


@pytest.mark.parametrize("wrong", [
    {"source": "telegram"},
    {"status": "draft"},
    {"category_id": 999},  # такой категории нет
    {"post_id": 999},  # такого поста нет
])
def test_database_rejects_wrong_values(db, wrong):
    fields = {"source": "form", "status": "pending", "title": "Мероприятие", "organizer": "Команда ТПУ",
              "category_id": category(db).id, **wrong}
    db.add(Event(**fields))
    with pytest.raises(IntegrityError):
        db.commit()


def test_admin_username_is_unique(db):
    db.add(User(username="admin", password_hash="pbkdf2_sha256$600000$соль$хеш"))
    db.commit()
    assert db.scalar(select(User)).password_hash.startswith("pbkdf2_sha256$")
    db.add(User(username="admin", password_hash="другой"))
    with pytest.raises(IntegrityError):
        db.commit()


# seed_test

def test_seed_test_on_clean_database(engine):
    added = seed(engine)
    assert added == len(VK_EVENTS) + len(FORM_EVENTS) == 11
    assert seed(engine) == 0  # второй запуск ничего не добавляет
    with Session(engine) as db:
        assert count(db, Event) == 11
        assert count(db, VkPost) == len(VK_EVENTS)
        assert (count(db, Category), count(db, VkCommunity)) == (6, 15)
        # Организатор поста ВК — название сообщества
        assert {e.organizer for e in db.scalars(select(Event).where(Event.source == "vk"))} <= {
            name for _, name in COMMUNITIES
        }


# Подключение

def test_postgres_url_from_hosting_is_accepted():
    assert normalize_url("postgres://user:pass@host/db") == "postgresql://user:pass@host/db"
    assert normalize_url("postgresql://user:pass@host/db") == "postgresql://user:pass@host/db"
    assert normalize_url("sqlite:///calendar.db") == "sqlite:///calendar.db"
