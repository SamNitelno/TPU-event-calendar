"""Разбор текста поста в поля мероприятия.

Регулярки, а не ML: посты ТПУ пишутся по шаблонам «когда / где / во сколько».
Задача — не идеальный разбор, а честный: что не нашли — None, и пост уйдёт
администратору (pending).
"""
import re
from dataclasses import dataclass
from datetime import date, datetime, time

from collector.dates import parse_dates, parse_times

PLACE_RE = re.compile(
    r"(?:где|место(?:\s+проведения)?|локация|адрес)\s*[:\-—]\s*(.+)",
    re.IGNORECASE,
)
HASHTAG_RE = re.compile(r"#([\wА-Яа-яЁё]+)")
EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF" "]+"
)
MARKDOWN_RE = re.compile(r"[*_`>]+")

# Ключи — подстроки (в нижнем регистре) или хэштеги без «#». Порядок важен: первое совпадение выигрывает.
CATEGORY_KEYS: dict[str, list[str]] = {
    "sport": ["спорт", "турнир", "матч", "соревнован", "фрисби", "алтимат", "теннис", "баскетбол", "волейбол"],
    "science": ["наука", "лекция", "конференц", "диссертац", "дрон", "олимпиад", "хакатон", "интенсив"],
    "creativity": ["культур", "творч", "концерт", "фестивал", "мкц", "выступлен", "конкурс творч"],
    "volunteering": ["волонт", "добро", "субботник", "благотвор"],
    "career": ["карьер", "стажировк", "ваканси", "работодател", "профессия", "олимпиада я — профессионал"],
    "student_life": ["студсовет", "общежит", "школа актива", "студжизнь", "первокурсник"],
}


@dataclass
class Parsed:
    """Результат разбора. Все поля необязательные, кроме title и description."""

    title: str
    description: str
    event_date: date | None
    end_date: date | None
    start_time: time | None
    end_time: time | None
    location: str | None
    category: str | None
    image_url: str | None


def _clean_title(line: str) -> str:
    line = MARKDOWN_RE.sub("", line)
    line = EMOJI_RE.sub("", line)
    return " ".join(line.split())


def extract_title(text: str) -> str:
    """Первая содержательная строка. Служебные приветствия пропускаем."""
    skip_starts = ("друзья", "привет", "уважаемые", "дорогие", "внимание")
    for raw in text.splitlines():
        line = _clean_title(raw)
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith(skip_starts) and len(line) < 60:
            continue
        return line[:300]
    return "Мероприятие"


def extract_category(text: str) -> str | None:
    low = text.lower()
    tags = {t.lower() for t in HASHTAG_RE.findall(text)}
    for slug, keys in CATEGORY_KEYS.items():
        if any(k in low or k in tags for k in keys):
            return slug
    return None


def extract_location(text: str) -> str | None:
    if m := PLACE_RE.search(text):
        return m.group(1).strip().rstrip(".")[:300]
    return None


def extract_image_url(attachments: list[dict] | None) -> str | None:
    """Самая крупная фотография из вложений поста."""
    if not attachments:
        return None
    best_url, best_area = None, 0
    for att in attachments:
        photo = att.get("photo")
        if not photo:
            continue
        for size in photo.get("sizes", []):
            area = size.get("width", 0) * size.get("height", 0)
            if area > best_area:
                best_area = area
                best_url = size.get("url")
    return best_url


def parse_post(item: dict, published: datetime) -> Parsed:
    """Один пост wall.get -> поля мероприятия."""
    text = item.get("text", "") or ""
    start, end = parse_dates(text, published)
    start_t, end_t = parse_times(text)
    return Parsed(
        title=extract_title(text),
        description=text,
        event_date=start,
        end_date=end,
        start_time=start_t,
        end_time=end_t,
        location=extract_location(text),
        category=extract_category(text),
        image_url=extract_image_url(item.get("attachments")),
    )