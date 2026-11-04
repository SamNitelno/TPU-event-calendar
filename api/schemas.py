"""Формат запросов и ответов API. Имена полей — как в docs/event_format.md."""
from datetime import date, time
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

# Время в ответах — «18:00», а не «18:00:00»
HHMM = Annotated[time, PlainSerializer(lambda t: t.strftime("%H:%M"), return_type=str)]


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
    description: str | None = Field(None, max_length=5000)
    contact: str = Field(min_length=3, max_length=200, description="Как связаться с автором. В API не отдаётся")

    @model_validator(mode="after")
    def end_not_before_start(self):
        if self.end_date and self.end_date < self.event_date:
            raise ValueError("end_date раньше event_date")
        return self


class SubmissionCreated(BaseModel):
    id: int
    status: str
