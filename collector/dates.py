"""Разбор дат и времени из русского текста поста.

Принцип из db/models.py: «Не нашли дату — пусто. Дату публикации не подставляем».
"""
import re
from datetime import date, datetime, time

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
_MONTH_RE = "|".join(MONTHS)

# «3–5 ноября», «3-5 ноября», «3 — 5 ноября»
RANGE_RE = re.compile(rf"(\d{{1,2}})\s*[–—-]\s*(\d{{1,2}})\s+({_MONTH_RE})", re.IGNORECASE)
# «с 3 по 5 ноября»
FROM_TO_RE = re.compile(rf"с\s+(\d{{1,2}})\s+по\s+(\d{{1,2}})\s+({_MONTH_RE})", re.IGNORECASE)
# «3 ноября», «3 ноября 2026»
SINGLE_RU_RE = re.compile(rf"(?<!\d)(\d{{1,2}})\s+({_MONTH_RE})(?:\s+(\d{{4}}))?", re.IGNORECASE)
# «03.11.2026», «3.11.26»
SINGLE_NUM_RE = re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{2,4})(?!\d)")
# «18:00», «9:30»
TIME_RE = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")
# «18.00», «9.30» — без двоеточия, но рядом должен быть маркер времени
TIME_DOT_RE = re.compile(r"(?<!\d)([01]?\d|2[0-3])\.([0-5]\d)(?!\d)")


def _year_for(month: int, published: datetime) -> int:
    """Если месяц в году публикации уже прошёл, событие, скорее всего, в следующем году."""
    return published.year if month >= published.month else published.year + 1


def parse_dates(text: str, published: datetime) -> tuple[date | None, date | None]:
    """Возвращает (event_date, end_date). Оба None, если дат в тексте нет."""
    if m := (RANGE_RE.search(text) or FROM_TO_RE.search(text)):
        d1, d2 = int(m.group(1)), int(m.group(2))
        month = MONTHS[m.group(3).lower()]
        year = _year_for(month, published)
        start = date(year, month, d1)
        # «28–3 ноября» — переход через месяц; маловероятно для афиш, но не падаем
        end = date(year, month, d2) if d2 >= d1 else date(year + 1, month, d2)
        return start, end

    if m := SINGLE_RU_RE.search(text):
        d = int(m.group(1))
        month = MONTHS[m.group(2).lower()]
        year = int(m.group(3)) if m.group(3) else _year_for(month, published)
        return date(year, month, d), None

    if m := SINGLE_NUM_RE.search(text):
        d, month, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        if not (1 <= month <= 12):
            return None, None
        return date(y, month, d), None

    return None, None


def parse_times(text: str) -> tuple[time | None, time | None]:
    """Возвращает (start_time, end_time). Одно время — только старт."""
    matches = [time(int(h), int(m)) for h, m in TIME_RE.findall(text)]
    if not matches:
        # «в 18.00» — берём только если рядом есть слово-маркер
        if re.search(r"(начало|старт|во сколько|в)\s", text, re.IGNORECASE):
            matches = [time(int(h), int(m)) for h, m in TIME_DOT_RE.findall(text)]
    if not matches:
        return None, None
    if len(matches) == 1:
        return matches[0], None
    return matches[0], matches[-1]