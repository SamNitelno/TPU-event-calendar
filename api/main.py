"""API календаря мероприятий ТПУ. Данные — только из базы, через модели db/.

Запуск из корня репозитория: uvicorn api.main:app --reload
Описание запросов: docs/api.md и http://127.0.0.1:8000/docs
"""
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, joinedload

from api.errors import database_error_handler, invalid, validation_error_handler
from api.frontend import mount_frontend
from api.schemas import CategoryWithCount, EventDetail, EventShort, EventsPage, Submission, SubmissionCreated
from db.database import get_db
from db.models import SOURCE_FORM, STATUS_PENDING, STATUS_PUBLISHED, Category, Event

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
PER_PAGE = 20
MAX_PER_PAGE = 100
# В Томске UTC+7 круглый год. Сервер может стоять в другом поясе, поэтому «сегодня» считаем по Томску
TOMSK_TZ = timezone(timedelta(hours=7))
# С каких адресов фронтенду можно ходить в API напрямую. Vite по умолчанию запускается на 5173
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

app = FastAPI(title="Календарь мероприятий ТПУ", version="1.1.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(OperationalError, database_error_handler)

router = APIRouter(prefix="/api")


def get_today() -> date:
    return datetime.now(TOMSK_TZ).date()


def is_public():
    """На сайте видны только опубликованные мероприятия с известной датой и категорией."""
    return and_(
        Event.status == STATUS_PUBLISHED,
        Event.event_date.is_not(None),
        Event.category_id.is_not(None),
    )


def last_day():
    """Последний день мероприятия: у многодневного — end_date."""
    return func.coalesce(Event.end_date, Event.event_date)


@router.get("/health", summary="API и база работают")
def health(db: Session = Depends(get_db)):
    # Если базы нет или таблицы не созданы, обработчик ошибок базы ответит 503
    db.scalar(select(func.count()).select_from(Category))
    return {"status": "ok"}


@router.get("/events", response_model=EventsPage, summary="Лента мероприятий")
def list_events(
    category: str | None = Query(None, description="Код категории: sport, science, creativity, ..."),
    date_from: date | None = Query(None, description="Идут в этот день или позже. Без параметра — с сегодняшнего дня"),
    date_to: date | None = Query(None, description="Начинаются не позже этого дня"),
    q: str | None = Query(None, max_length=100, description="Поиск по названию и описанию"),
    page: int = Query(1, ge=1),
    per_page: int = Query(PER_PAGE, ge=1, le=MAX_PER_PAGE, description="Сколько на странице. Календарю на месяц — 100"),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
):
    if date_from and date_to and date_from > date_to:
        raise invalid(("query", "date_from"), "Дата «с» позже даты «по»")

    # Прошедшие мероприятия в ленту не попадают. Явный date_from их возвращает:
    # календарю на месяц нужны и уже прошедшие дни
    conditions = [is_public(), last_day() >= (date_from or today)]
    if date_to:
        conditions.append(Event.event_date <= date_to)
    if category:
        conditions.append(Event.category.has(Category.slug == category))
    search = (q or "").strip()
    if search:
        conditions.append(or_(
            Event.title.icontains(search, autoescape=True),
            Event.description.icontains(search, autoescape=True),
        ))

    total = db.scalar(select(func.count()).select_from(Event).where(*conditions))
    events = db.scalars(
        select(Event)
        .options(joinedload(Event.category))
        .where(*conditions)
        .order_by(Event.event_date, Event.start_time.asc().nulls_last(), Event.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return EventsPage(
        items=[EventShort.model_validate(e) for e in events],
        page=page,
        per_page=per_page,
        total=total,
    )


@router.get(
    "/events/{event_id}",
    response_model=EventDetail,
    summary="Одно мероприятие",
    responses={404: {"description": "Мероприятия нет или оно не опубликовано"}},
)
def get_event(event_id: int, db: Session = Depends(get_db)):
    # Прошедшее мероприятие открывается по ссылке, а заявки на проверке и отклонённые — нет
    event = db.scalar(
        select(Event).options(joinedload(Event.category)).where(Event.id == event_id, is_public())
    )
    if event is None:
        raise HTTPException(404, "Мероприятие не найдено")
    return EventDetail.model_validate(event)


@router.get("/categories", response_model=list[CategoryWithCount], summary="Категории с числом мероприятий в ленте")
def list_categories(db: Session = Depends(get_db), today: date = Depends(get_today)):
    counts = dict(db.execute(
        select(Event.category_id, func.count())
        .where(is_public(), last_day() >= today)
        .group_by(Event.category_id)
    ).all())
    return [
        CategoryWithCount(slug=c.slug, name=c.name, events_count=counts.get(c.id, 0))
        for c in db.scalars(select(Category).order_by(Category.id))
    ]


@router.post("/submissions", response_model=SubmissionCreated, status_code=201, summary="Подать мероприятие через форму")
def create_submission(data: Submission, db: Session = Depends(get_db), today: date = Depends(get_today)):
    if data.event_date < today:
        raise invalid(("body", "event_date"), "Дата мероприятия уже прошла")
    category = db.scalar(select(Category).where(Category.slug == data.category))
    if category is None:
        raise invalid(("body", "category"), "Неизвестная категория")

    # Заявка ждёт проверки администратором и до этого на сайте не видна
    event = Event(source=SOURCE_FORM, status=STATUS_PENDING, category=category, **data.model_dump(exclude={"category"}))
    db.add(event)
    db.commit()
    return SubmissionCreated(id=event.id, status=event.status)


app.include_router(router)
# Последним: раздача собранного фронтенда перехватывает все остальные адреса
mount_frontend(app, Path(os.getenv("WEB_DIST_DIR", ROOT / "web" / "dist")))
