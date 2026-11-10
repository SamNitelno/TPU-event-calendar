"""Формат запросов и ответов API. Имена полей — как в docs/event_format.md."""
from datetime import date, time
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, ValidationInfo, field_validator

# Время в ответах — «18:00», а не «18:00:00»
HHMM = Annotated[time, PlainSerializer(lambda t: t.strftime("%H:%M"), return_type=str)]

VK_HOSTS = {"vk.com", "www.vk.com", "m.vk.com", "vk.ru", "www.vk.ru", "m.vk.ru"}


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str


class CategoryWithCount(CategoryOut):
    events_count: int


class EventShort(BaseModel):
    """Мероприятие в ленте."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    organizer: str
    category: CategoryOut
    source: Literal["vk", "form"] = Field(description="vk — собрано из ВКонтакте, form — заявка через форму")
    event_date: date
    end_date: date | None
    start_time: HHMM | None
    end_time: HHMM | None
    location: str | None
    original_post_link: str | None


class EventDetail(EventShort):
    """Страница мероприятия: поля ленты плюс описание и картинка."""

    description: str | None
    image_url: str | None


class EventsPage(BaseModel):
    items: list[EventShort]
    page: int
    per_page: int
    total: int


class Submission(BaseModel):
    """Заявка из формы «Подать мероприятие»."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=300)
    organizer: str = Field(min_length=2, max_length=200)
    category: str = Field(description="Код категории, например sport")
    event_date: date
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    location: str | None = Field(None, max_length=300)
    original_post_link: str | None = Field(None, max_length=300, description="Ссылка на пост ВКонтакте, если анонс уже есть")
    description: str | None = Field(None, max_length=5000)
    contact: str = Field(min_length=3, max_length=200, description="Как связаться с автором. В API не отдаётся")

    @field_validator(
        "end_date", "start_time", "end_time", "location", "original_post_link", "description", mode="before"
    )
    @classmethod
    def empty_is_none(cls, value):
        # Форма присылает "" у незаполненных полей. Это не ошибка, а «не указано»
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("end_date")
    @classmethod
    def end_date_not_before_start(cls, value: date | None, info: ValidationInfo):
        start = info.data.get("event_date")
        if value and start and value < start:
            raise ValueError("Дата окончания раньше даты начала")
        return value

    @field_validator("end_time")
    @classmethod
    def end_time_after_start(cls, value: time | None, info: ValidationInfo):
        start = info.data.get("start_time")
        end_date = info.data.get("end_date")
        one_day = end_date is None or end_date == info.data.get("event_date")
        if value and start and one_day and value <= start:
            raise ValueError("Время окончания должно быть позже начала")
        return value

    @field_validator("original_post_link")
    @classmethod
    def vk_link(cls, value: str | None):
        if value is None:
            return value
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or (parts.hostname or "").lower() not in VK_HOSTS:
            raise ValueError("Нужна ссылка на пост ВКонтакте, например https://vk.com/wall-123_456")
        return value


class SubmissionCreated(BaseModel):
    id: int
    status: str
