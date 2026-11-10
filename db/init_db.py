"""Создаёт таблицы, заполняет категории и сообщества. Запуск: python -m db.init_db

Можно запускать повторно: записи не дублируются, а названия и ссылки обновляются по спискам ниже.
"""
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from db.database import engine as default_engine
from db.models import Base, Category, VkCommunity

# Коды и названия — из docs/event_format.md. Порядок — порядок категорий на сайте
CATEGORIES = [
    ("sport", "Спорт"),
    ("science", "Наука"),
    ("creativity", "Культура"),
    ("volunteering", "Волонтёрство"),
    ("career", "Карьера"),
    ("student_life", "Студенческая жизнь"),
]

# Сообщества-источники — из docs/communities.md. owner_id у сообщества отрицательный
COMMUNITIES = [
    (-19220040, "ТПУ | Томский политехнический университет"),
    (-109388070, "Команда ТПУ"),
    (-44845822, "Спортклуб «Сибирские львы»"),
    (-24890431, "Центр карьеры ТПУ"),
    (-14752902, "Профком студентов и аспирантов ТПУ | ППОСиА ТПУ"),
    (-38738562, "Научно-техническая библиотека"),
    (-104427404, "Комиссия по качеству образования ТПУ | ККО"),
    (-31264870, "Движение первых | Томский политех"),
    (-222585418, "Студенты Росатома | ТПУ"),
    (-2713603, "ВО «Стиль Жизни» | ТПУ"),
    (-215750011, "Экологический клуб ТПУ им. Л. П. Рихванова"),
    (-107511450, "СПОО «Свой подход»"),
    (-80072684, "МКЦ ТПУ"),
    (-215901557, "Энергетический клуб ТПУ"),
    (-222469101, "Оздоровительная комиссия ТПУ"),
]


def community_link(owner_id: int) -> str:
    return f"https://vk.com/club{-owner_id}"


def init_db(engine: Engine = default_engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        categories = {c.slug: c for c in db.scalars(select(Category))}
        for slug, name in CATEGORIES:
            if slug in categories:
                categories[slug].name = name
            else:
                db.add(Category(slug=slug, name=name))

        # is_active не трогаем: сообщество, отключённое вручную, остаётся отключённым
        communities = {c.owner_id: c for c in db.scalars(select(VkCommunity))}
        for owner_id, name in COMMUNITIES:
            community = communities.get(owner_id)
            if community is None:
                db.add(VkCommunity(owner_id=owner_id, name=name, link=community_link(owner_id)))
            else:
                community.name, community.link = name, community_link(owner_id)
        db.commit()


if __name__ == "__main__":
    init_db()
    print(f"Таблицы созданы. Категорий: {len(CATEGORIES)}, сообществ: {len(COMMUNITIES)}")
