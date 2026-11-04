"""Тестовые мероприятия для проверки ленты. Запуск: python -m db.seed_test

Даты считаются от сегодняшнего дня, поэтому в ленте всегда есть что показать.
Среди записей есть прошедшая, многодневная, без времени, без даты и заявки из формы.
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select

from db.database import SessionLocal
from db.init_db import init_db
from db.models import (
    SOURCE_FORM, SOURCE_VK, STATUS_PENDING, STATUS_PUBLISHED, STATUS_REJECTED,
    Category, Event, VkCommunity, VkPost,
)

# start и end — сдвиг в днях от сегодня. Без start дата в посте не найдена
VK_EVENTS = [
    dict(owner_id=-44845822, post=52494, category="sport", title="Мастер-класс по алтимату",
         start=3, start_time=time(18, 0), location="ул. Карпова, 4",
         text="Обучение базовым тактикам, правилам и броскам диска фрисби: форхенд, бэкхенд, хаммер, скубер."),
    dict(owner_id=-44845822, post=52458, category="sport", title="Турнир по настольному теннису среди первокурсников",
         start=7, location="Учебный корпус №9",
         text="Турнир в рамках фестиваля «Атомная энергия спорта»."),
    dict(owner_id=-19220040, post=99954, category="science", title="Дроны, ИИ и инженерные соревнования",
         start=-1, end=3, location="Бизнес-инкубатор ТПУ «Б51»",
         text="Соревнования в симуляторе, хакатон и интенсив по роевому управлению беспилотниками."),
    dict(owner_id=-19220040, post=99949, category="creativity", title="День открытых дверей МКЦ",
         start=5, start_time=time(18, 30), location="Танцевальный зал МКЦ ТПУ",
         text="Мастер-классы и старт проекта «Новые лица» для первокурсников и второкурсников."),
    dict(owner_id=-19220040, post=99947, category="science", title="Открытая защита докторской диссертации",
         start=10, start_time=time(14, 30), location="2-й корпус (просп. Ленина, 43А), ауд. 301",
         text="Защита по теме «Разработка основ технологии синтеза гликольурила»."),
    dict(owner_id=-109388070, post=7111, category="creativity", title="Творческий фестиваль «Событие»",
         start=-5, start_time=time(16, 0), location="МКЦ ТПУ",
         text="Выступления политехников: коллективы, малая форма и инструментал."),
    dict(owner_id=-109388070, post=7120, category="student_life", title="Конкурс «Общага» на лучший студсовет общежития",
         start=14, end=16, location="Общежития Политеха",
         text="Три этапа проверки в рамках Школы актива."),
    dict(owner_id=-19220040, post=99627, category="career", title="Олимпиада «Я — профессионал»: отборочный этап",
         start=20, end=36, location="Онлайн",
         text="Направление «Инновационное предпринимательство», кейсы от Бизнес-школы ТПУ."),
    dict(owner_id=-109388070, post=7128, category="creativity", title="Конкурс творческих номеров «Ход талантам»",
         text="Заявки до 11 ноября. Дата выступления в посте не указана."),
]

FORM_EVENTS = [
    dict(status=STATUS_PENDING, category="volunteering", title="Субботник «Чистый берег»",
         organizer="Волонтёрский центр ТПУ", start=9, start_time=time(11, 0),
         location="Набережная реки Ушайки", contact="volunteers@example.com"),
    dict(status=STATUS_REJECTED, category="career", title="Курсы подготовки к экзаменам со скидкой",
         organizer="Частная школа", start=4, contact="ads@example.com"),
]


def day(offset: int | None) -> date | None:
    return None if offset is None else date.today() + timedelta(days=offset)


def seed() -> None:
    init_db()
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Event)):
            print("В базе уже есть мероприятия, тестовые не добавлены")
            return

        categories = {c.slug: c for c in db.scalars(select(Category))}
        communities = {c.owner_id: c for c in db.scalars(select(VkCommunity))}

        for item in VK_EVENTS:
            community = communities[item["owner_id"]]
            db.add(Event(
                post=VkPost(community=community, vk_post_id=item["post"], text=item["text"],
                            published_at=datetime.now() - timedelta(days=2)),
                source=SOURCE_VK,
                # Пост с найденной датой публикуется сразу, без даты — ждёт администратора
                status=STATUS_PUBLISHED if "start" in item else STATUS_PENDING,
                category=categories[item["category"]],
                title=item["title"],
                description=item["text"],
                event_date=day(item.get("start")),
                end_date=day(item.get("end")),
                start_time=item.get("start_time"),
                location=item.get("location"),
                organizer=community.name,
                original_post_link=f"https://vk.com/wall{community.owner_id}_{item['post']}",
            ))

        for item in FORM_EVENTS:
            db.add(Event(
                source=SOURCE_FORM,
                status=item["status"],
                category=categories[item["category"]],
                title=item["title"],
                organizer=item["organizer"],
                event_date=day(item["start"]),
                start_time=item.get("start_time"),
                location=item.get("location"),
                contact=item["contact"],
            ))

        db.commit()
        print(f"Добавлено мероприятий: {len(VK_EVENTS) + len(FORM_EVENTS)}")


if __name__ == "__main__":
    seed()
