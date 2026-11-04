"""Создаёт таблицы, заполняет категории и сообщества. Запуск: python -m db.init_db

Можно запускать повторно: существующие записи не дублируются.
"""
from sqlalchemy import select

from db.database import SessionLocal, engine
from db.models import Base, Category, VkCommunity

# Коды и названия — из docs/event_format.md
CATEGORIES = [
    ("sport", "Спорт"),
    ("science", "Наука"),
    ("creativity", "Культура"),
    ("volunteering", "Волонтёрство"),
    ("career", "Карьера"),
    ("student_life", "Студенческая жизнь"),
]

COMMUNITIES = [
    (-19220040, "ТПУ | Томский политехнический университет"),
    (-109388070, "Команда ТПУ"),
    (-44845822, "Спортклуб «Сибирские львы»"),
]


def init_db() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        existing = set(db.scalars(select(Category.slug)))
        db.add_all(Category(slug=slug, name=name) for slug, name in CATEGORIES if slug not in existing)

        existing = set(db.scalars(select(VkCommunity.owner_id)))
        db.add_all(
            VkCommunity(owner_id=owner_id, name=name, link=f"https://vk.com/club{-owner_id}")
            for owner_id, name in COMMUNITIES
            if owner_id not in existing
        )
        db.commit()


if __name__ == "__main__":
    init_db()
    print("Таблицы созданы, категории и сообщества добавлены")
