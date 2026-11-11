"""Сбор постов из активных сообществ и сохранение их в базу.

Запуск из корня репозитория: python -m collector.run [--limit 50]
Раз в сутки по расписанию (GitHub Actions, cron или Планировщик задач Windows).

Что происходит с постом:
- уже сохраняли (то же сообщество и номер поста) или реклама — пропускаем;
- репост — разбираем исходный пост из copy_history, ссылка «Подробнее во ВКонтакте» тоже на него;
- похож на анонс — мероприятие: сразу опубликовано, если дата однозначна и категория найдена,
  иначе ждёт администратора;
- новость, поздравление или отчёт о прошедшем — сохраняем только сам пост, без мероприятия;
- тот же исходный пост уже есть в базе (репост из другого нашего сообщества) — второе мероприятие не создаём.

Закреплённый пост разбираем как обычный: часто это анонс ближайшего события, а повтор отсекает проверка выше.
"""
import argparse
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import select

from collector.extract import auto_publish, is_announcement, is_report, parse_post
from collector.vk_client import VkClient
from db.database import SessionLocal
from db.models import (
    SOURCE_VK, STATUS_PENDING, STATUS_PUBLISHED,
    Category, Event, VkCommunity, VkPost,
)

load_dotenv()
log = logging.getLogger("collector")
TOMSK_TZ = timezone(timedelta(hours=7))
DUPLICATE, ADS, POST_ONLY, REPEAT = "duplicate", "ads", "post_only", "repeat"


def published_at(timestamp: int) -> datetime:
    """Время публикации по Томску, а не по поясу сервера: от него считаются «сегодня», «в эту субботу» и год."""
    return datetime.fromtimestamp(timestamp, TOMSK_TZ).replace(tzinfo=None)


def post_link(owner_id: int, post_id: int) -> str:
    return f"https://vk.com/wall{owner_id}_{post_id}"


def save_post(db, community: VkCommunity, item: dict, categories: dict[str, Category]) -> str:
    """Сохраняет один пост. Возвращает, что с ним стало: published, pending, post_only, repeat, duplicate, ads."""
    vk_post_id = item["id"]
    if db.scalar(select(VkPost.id).where(
        VkPost.community_id == community.id,
        VkPost.vk_post_id == vk_post_id,
    )):
        return DUPLICATE
    if item.get("marked_as_ads"):
        return ADS

    published = published_at(item["date"])
    # Репост: текст и картинка — у исходного поста, сам репост обычно пустой или «.»
    source = (item.get("copy_history") or [item])[0]
    link = post_link(source.get("owner_id", community.owner_id), source.get("id", vk_post_id))
    parsed = parse_post(
        {"text": source.get("text", ""), "attachments": source.get("attachments"), "owner_id": community.owner_id},
        published,
    )

    post = VkPost(community=community, vk_post_id=vk_post_id, text=parsed.description, published_at=published)
    db.add(post)
    if not is_announcement(parsed) or is_report(parsed, published):
        return POST_ONLY
    if db.scalar(select(Event.id).where(Event.original_post_link == link)):
        return REPEAT

    category = categories.get(parsed.category) if parsed.category else None
    status = STATUS_PUBLISHED if (category and auto_publish(parsed)) else STATUS_PENDING
    db.add(Event(
        post=post,
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
        original_post_link=link,
        image_url=parsed.image_url,
    ))
    return status


def run(limit_per_community: int = 50, client: VkClient | None = None) -> dict[str, int]:
    """Проход по активным сообществам. Возвращает счётчики для лога."""
    client = client or VkClient()
    stats = Counter({key: 0 for key in (
        "communities", "posts_seen", "events_new", "skipped", STATUS_PUBLISHED, STATUS_PENDING,
        POST_ONLY, REPEAT, ADS, "errors", "failed_communities",
    )})

    with SessionLocal() as db:
        categories = {c.slug: c for c in db.scalars(select(Category))}
        communities = db.scalars(
            select(VkCommunity).where(VkCommunity.is_active.is_(True))
        ).all()

        for community in communities:
            stats["communities"] += 1
            try:
                if limit_per_community > 100:
                    items = client.get_posts_paged(community.owner_id, total=limit_per_community)
                else:
                    items = client.get_posts(community.owner_id, count=limit_per_community)
            except Exception as exc:  # сеть, ключ, приватность — не валим весь проход
                stats["failed_communities"] += 1
                log.warning("Сообщество %s пропущено: %s", community.owner_id, exc)
                continue

            for item in items:
                stats["posts_seen"] += 1
                try:
                    outcome = save_post(db, community, item, categories)
                    # Каждый пост — отдельно: битый пост не откатывает уже сохранённые
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    stats["errors"] += 1
                    log.warning("Пост %s_%s пропущен: %s", community.owner_id, item.get("id"), exc)
                    continue
                stats[outcome] += 1
                if outcome in (STATUS_PUBLISHED, STATUS_PENDING):
                    stats["events_new"] += 1
                elif outcome == DUPLICATE:
                    stats["skipped"] += 1

    log.info(
        "Готово: сообществ %(communities)d (недоступно %(failed_communities)d), постов %(posts_seen)d. "
        "Новых мероприятий %(events_new)d: опубликовано %(published)d, на проверку %(pending)d. "
        "Без мероприятия %(post_only)d, повторы между сообществами %(repeat)d, уже были %(skipped)d, "
        "реклама %(ads)d, ошибок %(errors)d",
        stats,
    )
    return dict(stats)


def main() -> None:
    parser = argparse.ArgumentParser(description="Сбор постов из сообществ ВК")
    parser.add_argument("--limit", type=int, default=50,
                        help="Сколько последних постов брать у сообщества. Больше 100 — постранично")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    run(args.limit)


if __name__ == "__main__":
    main()
