"""Administrator login and moderation. Public responses never expose contacts or sessions."""

import secrets
from datetime import date, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from api.auth import (
    COOKIE_NAME,
    SESSION_SECONDS,
    check_origin,
    csrf_token,
    hash_password,
    new_session,
    require_admin,
    secure_cookie,
    token_hash,
    utcnow,
    verify_password,
)
from api.errors import invalid
from api.schemas import HHMM, CategoryOut, Submission
from db.database import get_db
from db.models import AdminSession, Category, Event, LoginAttempt, User

router = APIRouter(prefix="/api/admin", tags=["Администратор"])
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


class Login(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class AdminEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    organizer: str
    source: str
    status: str
    category: CategoryOut | None
    event_date: date | None
    end_date: date | None
    start_time: HHMM | None
    end_time: HHMM | None
    location: str | None
    description: str | None
    original_post_link: str | None
    image_url: str | None
    contact: str | None


class Moderation(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=300)
    organizer: str = Field(min_length=2, max_length=200)
    category: str | None = None
    event_date: date | None = None
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    location: str | None = Field(None, max_length=300)
    description: str | None = Field(None, max_length=5000)
    original_post_link: str | None = Field(None, max_length=300)
    status: Literal["pending", "published", "rejected"]

    @field_validator(
        "category",
        "event_date",
        "end_date",
        "start_time",
        "end_time",
        "location",
        "description",
        "original_post_link",
        mode="before",
    )
    @classmethod
    def empty_is_none(cls, value):
        return None if value == "" else value

    @field_validator("original_post_link")
    @classmethod
    def valid_vk_link(cls, value):
        return Submission.vk_link(value)

    @model_validator(mode="after")
    def check_range(self):
        if self.end_date and self.event_date and self.end_date < self.event_date:
            raise invalid(("body", "end_date"), "Дата окончания раньше даты начала")
        if (
            self.start_time
            and self.end_time
            and (not self.end_date or self.end_date == self.event_date)
            and self.end_time <= self.start_time
        ):
            raise invalid(("body", "end_time"), "Время окончания должно быть позже начала")
        if self.status == "published":
            if not self.event_date:
                raise invalid(("body", "event_date"), "Укажите дату перед публикацией")
            if not self.category:
                raise invalid(("body", "category"), "Укажите категорию перед публикацией")
        return self


@router.post("/login")
def login(data: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    check_origin(request)
    username = data.username.strip().lower()
    key = token_hash(username)
    now = utcnow()
    attempt = db.get(LoginAttempt, key)
    if attempt and attempt.window_start + timedelta(minutes=15) > now and attempt.failures >= 5:
        raise HTTPException(429, "Слишком много попыток. Повторите через 15 минут.")
    user = db.scalar(select(User).where(User.username == username))
    valid = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if not valid or user is None:
        if not attempt:
            attempt = LoginAttempt(key=key, failures=0, window_start=now)
            db.add(attempt)
        if attempt.window_start + timedelta(minutes=15) <= now:
            attempt.window_start, attempt.failures = now, 0
        attempt.failures += 1
        db.commit()
        raise HTTPException(401, "Неверный логин или пароль")
    if attempt:
        db.delete(attempt)
    db.execute(delete(AdminSession).where(AdminSession.expires_at <= now))
    previous = request.cookies.get(COOKIE_NAME)
    if previous:
        db.execute(delete(AdminSession).where(AdminSession.token_hash == token_hash(previous)))
    token, session = new_session(user.id)
    db.add(session)
    db.commit()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=secure_cookie(),
        samesite="lax",
        path="/api/admin",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"username": user.username, "csrf_token": csrf_token(token)}


@router.get("/me")
def me(request: Request, response: Response, session: AdminSession = Depends(require_admin)):
    response.headers["Cache-Control"] = "no-store"
    return {"username": session.user.username, "csrf_token": csrf_token(request.cookies[COOKIE_NAME])}


@router.post("/logout", status_code=204)
def logout(response: Response, session: AdminSession = Depends(require_admin), db: Session = Depends(get_db)):
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/api/admin", secure=secure_cookie(), httponly=True, samesite="lax")


@router.get("/events", dependencies=[Depends(require_admin)])
def events(
    response: Response,
    status: Literal["pending", "published", "rejected", "all"] = "pending",
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    conditions = [] if status == "all" else [Event.status == status]
    total = db.scalar(select(func.count()).select_from(Event).where(*conditions))
    items = db.scalars(
        select(Event)
        .options(joinedload(Event.category))
        .where(*conditions)
        .order_by(Event.created_at.desc(), Event.id.desc())
        .offset((page - 1) * 20)
        .limit(20)
    ).all()
    response.headers["Cache-Control"] = "no-store"
    return {"items": [AdminEvent.model_validate(event) for event in items], "total": total, "page": page}


@router.put("/events/{event_id}", response_model=AdminEvent, dependencies=[Depends(require_admin)])
def moderate(event_id: int, data: Moderation, response: Response, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Мероприятие не найдено")
    category = db.scalar(select(Category).where(Category.slug == data.category)) if data.category else None
    if data.category and category is None:
        raise invalid(("body", "category"), "Неизвестная категория")
    for key, value in data.model_dump(exclude={"category"}).items():
        setattr(event, key, value)
    event.category = category
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return AdminEvent.model_validate(event)
