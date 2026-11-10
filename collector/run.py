"""Сбор постов из активных сообществ и сохранение их в базу.

Запуск из корня репозитория: python -m collector.run
Раз в сутки по cron / Планировщику задач Windows.
"""
import logging
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import select

from collector.extract import parse_post
from collector.vk_client import VkClient
from db.database import SessionLocal
from db.models import (
    SOURCE_VK, STATUS_PENDING, STATUS_PUBLISHED,
    Category, Event, VkCommunity, VkPost,
)

load_dotenv()
log = logging.getLogger("collector")


def save_post(db, community: VkCommunity, item: dict, categories: dict[str, Category]) -> bool:
    """Сохраняет один пост. Возвращает True, если создан новый Event."""
    vk_post_id = item["id"]
    if db.scalar(select(VkPost.id).where(
        VkPost.community_id == community.id,
        VkPost.vk_post_id == vk_post_id,
    )):
        return False  # уже сохраняли

    published = datetime.fromtimestamp(item["date"])
    parsed = parse_post(item, published)

    # Категорию не нашли — пост ждёт админа, как «пост ВК без даты» в схеме статусов
    category = categories.get(parsed.category) if parsed.category else None
    status = STATUS_PUBLISHED if (parsed.event_date and category) else STATUS_PENDING

    db.add(Event(
        post=VkPost(
            community=community,
            vk_post_id=vk_post_id,
            text=item.get("text", ""),
            published_at=published,
        ),
        source=SOURCE_VK,
        status=status,
        category=category,
        title=parsed.title,
        description=parsed.description,
        event_date=parsed.event_date,
        end_date=parsed.end_date,
        start_time=parsed.start_time,
        end_time=parsed.end_time,
        location=parsed.location,
        organizer=community.name,
        original_post_link=f"https://vk.com/wall{community.owner_id}_{vk_post_id}",
        image_url=parsed.image_url,
    ))
    return True


def run(limit_per_community: int = 50, client: VkClient | None = None) -> dict[str, int]:
    """Проход по активным сообществам. Возвращает счётчики для лога."""
    client = client or VkClient()
    stats = {"communities": 0, "posts_seen": 0, "events_new": 0, "skipped": 0}

    with SessionLocal() as db:
        categories = {c.slug: c for c in db.scalars(select(Category))}
        communities = db.scalars(
            select(VkCommunity).where(VkCommunity.is_active.is_(True))
        ).all()

        for community in communities:
            stats["communities"] += 1
            try:
                items = client.get_posts(community.owner_id, count=limit_per_community)
            except Exception as exc:  # сеть, токен, приватность — не валим весь проход
                log.warning("Сообщество %s пропущено: %s", community.owner_id, exc)
                continue

            for item in items:
                stats["posts_seen"] += 1
                try:
                    if save_post(db, community, item, categories):
                        stats["events_new"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception as exc:  # один битый пост не должен ронять сообщество
                    log.warning("Пост %s_%s пропущен: %s", community.owner_id, item.get("id"), exc)
                    db.rollback()

            db.commit()

    log.info(
        "Готово: сообществ %(communities)d, постов %(posts_seen)d, "
        "новых мероприятий %(events_new)d, дублей %(skipped)d",
        stats,
    )
    return stats


if __name__ == "__main__":
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    run()
