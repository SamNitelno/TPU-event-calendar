"""Таблицы базы. Поля мероприятия — по docs/event_format.md."""
from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

SOURCE_VK, SOURCE_FORM = "vk", "form"
STATUS_PENDING, STATUS_PUBLISHED, STATUS_REJECTED = "pending", "published", "rejected"


class Base(DeclarativeBase):
    pass


class VkCommunity(Base):
    __tablename__ = "vk_communities"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(unique=True)  # у сообществ отрицательный: -44845822
    name: Mapped[str] = mapped_column(String(200))
    link: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)


class VkPost(Base):
    __tablename__ = "vk_posts"
    # Повторно загруженный пост не создаёт дубль
    __table_args__ = (UniqueConstraint("community_id", "vk_post_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(ForeignKey("vk_communities.id"))
    vk_post_id: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime]

    community: Mapped[VkCommunity] = relationship()


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("source IN ('vk', 'form')", name="ck_events_source"),
        CheckConstraint("status IN ('pending', 'published', 'rejected')", name="ck_events_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("vk_posts.id"))  # пусто для заявок из формы
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    source: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    # Не нашли дату — пусто. Дату публикации не подставляем
    event_date: Mapped[date | None] = mapped_column(index=True)
    start_time: Mapped[time | None]
    end_date: Mapped[date | None]
    end_time: Mapped[time | None]
    location: Mapped[str | None] = mapped_column(String(300))
    organizer: Mapped[str] = mapped_column(String(200))
    original_post_link: Mapped[str | None] = mapped_column(String(300))
    image_url: Mapped[str | None] = mapped_column(String(500))
    contact: Mapped[str | None] = mapped_column(String(200))  # только из формы, в API не отдаётся
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    category: Mapped[Category] = relationship()
    post: Mapped[VkPost | None] = relationship()
