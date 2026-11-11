"""Разбор даты и времени мероприятия из русского текста поста.

Как выбирается дата:
1. Собираем все упоминания дат: «3 ноября», «3–5 ноября», «со 2 по 6 декабря»,
   «21 декабря 2026 — 26 марта 2027», «03.11.2026», «22.10» (только рядом с признаком даты),
   «в эту субботу», «Воскресенье, 18:00», «сегодня», «завтра».
2. Отбрасываем сроки заявок («до 11 ноября») и исторические даты (год раньше года публикации).
3. Оцениваем окружение: строка с 📅, «Когда», «Дата», время на той же строке, «состоится» — выше;
   «отборочный этап», «заявки» — ниже. Побеждает лучшая оценка, при равенстве — первая в тексте.

Принцип из db/models.py: не нашли дату — пусто, дату публикации не подставляем.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
# Порядок как у date.weekday(): понедельник — 0
WEEKDAY_STEMS = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот", "воскресень"]

_MONTH = "(" + "|".join(MONTHS) + ")"
_YEAR = r"(?:\s+(\d{4})(?:\s*(?:г\.|года?))?)?"
_DASH = r"\s*[–—-]\s*"
_NOT_AFTER_NUMBER = r"(?<![\d:./])"

# «21 декабря 2026 — 26 марта 2027», «с 30 октября по 2 ноября»
CROSS_RANGE_RE = re.compile(
    rf"{_NOT_AFTER_NUMBER}(?:(?:с|со)\s+)?(\d{{1,2}})\s+{_MONTH}{_YEAR}(?:{_DASH}|\s+по\s+)(\d{{1,2}})\s+{_MONTH}{_YEAR}",
    re.IGNORECASE,
)
# «3–5 ноября», «с 26 по 30 октября», «со 2 по 6 декабря». Граница перед числом:
# иначе в «2026 — 26 марта» окончание года «26» склеится с «26 марта» в диапазон
RANGE_RE = re.compile(
    rf"{_NOT_AFTER_NUMBER}(?:(?:с|со)\s+)?(\d{{1,2}})(?:{_DASH}|\s+по\s+)(\d{{1,2}})\s+{_MONTH}{_YEAR}",
    re.IGNORECASE,
)
# «3 ноября», «3 ноября 2026»
SINGLE_RE = re.compile(rf"{_NOT_AFTER_NUMBER}(\d{{1,2}})\s+{_MONTH}{_YEAR}", re.IGNORECASE)
# «03.11.2026», «3.11.26»
NUM_FULL_RE = re.compile(r"(?<![\d.:/])(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})(?![\d.])")
# «22.10» без года — легко спутать со временем «18.30», поэтому только рядом с признаком даты
NUM_SHORT_RE = re.compile(r"(?<![\d.:/])(\d{1,2})\.(\d{2})(?!\d|\.\d|:\d)")
# «в эту субботу», «в это воскресенье», «уже в понедельник», «в эти выходные»
REL_WEEKDAY_RE = re.compile(
    r"(?<![а-яё])(?:в|во)\s+(?:(?:эт[уоиа]|ближайш\w+)\s+)?"
    r"(понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье|выходные)(?![а-яё])",
    re.IGNORECASE,
)
# «📍Воскресенье, 18:00, ул. Карпова, 4» — день недели в начале строки, сразу за ним время
LINE_WEEKDAY_RE = re.compile(
    r"^[^\wа-яё]*(понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)\s*[,|–—-]?\s*\d{1,2}:\d{2}",
    re.IGNORECASE,
)
REL_DAY_RE = re.compile(r"(?<![а-яё])(сегодня|завтра|послезавтра)(?![а-яё])", re.IGNORECASE)

# «до 11 ноября», «Приём заявок: до 23 октября», «– до 28 октября»
DEADLINE_BEFORE_RE = re.compile(r"(?<![а-яё])до\s*[:–—-]?\s*$", re.IGNORECASE)
# «📅 Дедлайн: 23 ноября», «Срок подачи заявок — 5 декабря»
DEADLINE_WORD_RE = re.compile(r"(?<![а-яё])(?:дедлайн|срок)", re.IGNORECASE)
DATE_MARK_RE = re.compile(r"📅|🗓|📆|(?<![а-яё])(?:дата|когда)(?![а-яё])", re.IGNORECASE)
EVENT_WORD_RE = re.compile(
    r"(?<![а-яё])(?:состо[ия]тся|пройд[её]т|проводим|проведут|провед[её]м|ждём|ждем|приходи|встречаемся|"
    r"стартует|начн[её]тся|конкурсные дни|узнаем|приглашаем)",
    re.IGNORECASE,
)
STAGE_RE = re.compile(r"отбор", re.IGNORECASE)
APPLICATION_RE = re.compile(r"заявк|регистрац", re.IGNORECASE)
# Короткие «пн», «вс» — только отдельным словом, иначе совпадут с «встреча» и «среди»
WEEKDAY_WORD_RE = re.compile(
    r"(?<![а-яё])(?:(?:пн|вт|ср|чт|пт|сб|вс)(?![а-яё])|понедельник|вторник|сред[ауы](?![а-яё])|"
    r"четверг|пятниц|суббот|воскресень)",
    re.IGNORECASE,
)

TIME_RE = re.compile(r"(?<![\d:.])([01]?\d|2[0-3]):([0-5]\d)(?!\d)")
# «в 18.00» — время через точку, только после «в», «с» или «начало»
TIME_DOT_RE = re.compile(r"(?<![а-яё])(?:в|с|начало)\s+([01]?\d|2[0-3])\.([0-5]\d)(?![\d.])", re.IGNORECASE)
MSK_AFTER_RE = re.compile(r"^\s*\(?\s*(?:по\s+)?(?:мск|московскому)", re.IGNORECASE)
RANGE_GLUE_RE = re.compile(r"^\s*(?:[–—-]|до)\s*$", re.IGNORECASE)
MSK_TO_TOMSK = timedelta(hours=4)


@dataclass
class When:
    event_date: date | None = None
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    # Есть другая дата почти с той же оценкой: публиковать сразу рискованно
    ambiguous: bool = False
    # Строка, в которой нашли дату: по ней ищем время и «онлайн»
    line: str | None = None


@dataclass
class _Candidate:
    start: date
    end: date | None
    pos: int
    score: float


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:  # 31.02, 30 февраля — не дата
        return None


def _infer_year(month: int, day: int, published: datetime) -> int:
    """Год не указан: если дата больше чем на месяц раньше публикации, это следующий год."""
    candidate = _safe_date(published.year, month, day)
    if candidate and candidate < published.date() - timedelta(days=30):
        return published.year + 1
    return published.year


def _year(explicit: str | None, month: int, day: int, published: datetime) -> int:
    if explicit:
        return int(explicit)
    return _infer_year(month, day, published)


def _line_bounds(text: str, pos: int) -> tuple[int, int]:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return start, (len(text) if end == -1 else end)


def _score(line: str, before_in_line: str) -> float:
    score = 0.0
    if DATE_MARK_RE.search(line):
        score += 2
    if TIME_RE.search(line) or TIME_DOT_RE.search(line):
        score += 2
    if EVENT_WORD_RE.search(line):
        score += 1
    if WEEKDAY_WORD_RE.search(line):
        score += 1
    if STAGE_RE.search(line):
        score -= 2
    if APPLICATION_RE.search(before_in_line):
        score -= 1
    return score


def _next_weekday(published: datetime, weekday: int) -> date:
    return published.date() + timedelta(days=(weekday - published.weekday()) % 7)


def _weekday_index(word: str) -> int:
    word = word.lower()
    if word == "выходные":
        return 5
    return next(i for i, stem in enumerate(WEEKDAY_STEMS) if word.startswith(stem))


def _candidates(text: str, published: datetime) -> list[_Candidate]:
    found: list[_Candidate] = []
    taken: list[tuple[int, int]] = []  # уже разобранные куски: «3–5 ноября» не должно дать ещё и «5 ноября»

    def free(m: re.Match) -> bool:
        return all(m.end() <= a or m.start() >= b for a, b in taken)

    def add(m: re.Match, start: date | None, end: date | None, bonus: float = 0.0) -> None:
        taken.append((m.start(), m.end()))
        if start is None:
            return
        line_start, line_end = _line_bounds(text, m.start())
        before = text[line_start:m.start()]
        if DEADLINE_BEFORE_RE.search(before) or DEADLINE_WORD_RE.search(before):
            return  # срок подачи заявки, а не день мероприятия
        if end is not None and end < start:
            end = None
        found.append(_Candidate(start, end, m.start(), _score(text[line_start:line_end], before) + bonus))

    def historical(*years: str | None) -> bool:
        return any(y and int(y) < published.year for y in years)

    for m in CROSS_RANGE_RE.finditer(text):
        d1, m1, y1, d2, m2, y2 = m.groups()
        if historical(y1, y2):
            taken.append((m.start(), m.end()))
            continue
        month1, month2 = MONTHS[m1.lower()], MONTHS[m2.lower()]
        year1 = _year(y1, month1, int(d1), published)
        year2 = int(y2) if y2 else (year1 if month2 >= month1 else year1 + 1)
        add(m, _safe_date(year1, month1, int(d1)), _safe_date(year2, month2, int(d2)))

    for m in RANGE_RE.finditer(text):
        if not free(m):
            continue
        d1, d2, month_word, y = m.groups()
        if historical(y):
            taken.append((m.start(), m.end()))
            continue
        month = MONTHS[month_word.lower()]
        year = _year(y, month, int(d1), published)
        add(m, _safe_date(year, month, int(d1)), _safe_date(year, month, int(d2)))

    for m in SINGLE_RE.finditer(text):
        if not free(m):
            continue
        d, month_word, y = m.groups()
        if historical(y):
            taken.append((m.start(), m.end()))
            continue
        month = MONTHS[month_word.lower()]
        add(m, _safe_date(_year(y, month, int(d), published), month, int(d)), None)

    for m in NUM_FULL_RE.finditer(text):
        if not free(m):
            continue
        d, month, y = (int(g) for g in m.groups())
        y = y + 2000 if y < 100 else y
        if y < published.year or not 1 <= month <= 12:
            continue
        add(m, _safe_date(y, month, d), None)

    for m in NUM_SHORT_RE.finditer(text):
        if not free(m):
            continue
        d, month = int(m.group(1)), int(m.group(2))
        if not (1 <= d <= 31 and 1 <= month <= 12):
            continue
        line_start, line_end = _line_bounds(text, m.start())
        line, after = text[line_start:line_end], text[m.end():line_end]
        # Признак даты: 📅/«Дата» в строке, день недели или время сразу после
        if not (DATE_MARK_RE.search(line) or WEEKDAY_WORD_RE.match(after.strip(" (")) or
                re.match(r"\s*(?:в|,|—|-)?\s*\d{1,2}:\d{2}", after)):
            continue
        add(m, _safe_date(_infer_year(month, d, published), month, d), None)

    # Относительные даты — слабее явных: нужны, только если явной даты нет
    for m in REL_WEEKDAY_RE.finditer(text):
        add(m, _next_weekday(published, _weekday_index(m.group(1))), None, bonus=-1)
    for line_match in re.finditer(r"^.*$", text, re.MULTILINE):
        if m := LINE_WEEKDAY_RE.match(line_match.group(0)):
            target = _next_weekday(published, _weekday_index(m.group(1)))
            found.append(_Candidate(target, None, line_match.start(), _score(line_match.group(0), "") - 1))
    for m in REL_DAY_RE.finditer(text):
        line_start, line_end = _line_bounds(text, m.start())
        line = text[line_start:line_end]
        # «сегодня» бывает и не про дату: берём, только если рядом время или слово-событие
        if not (TIME_RE.search(line) or EVENT_WORD_RE.search(line)):
            continue
        shift = {"сегодня": 0, "завтра": 1, "послезавтра": 2}[m.group(1).lower()]
        add(m, published.date() + timedelta(days=shift), None, bonus=-1.5)
    return found


def _choose(candidates: list[_Candidate]) -> tuple[_Candidate | None, bool]:
    if not candidates:
        return None, False
    best = max(candidates, key=lambda c: (c.score, -c.pos))
    last = best.end or best.start
    rivals = [
        c for c in candidates
        if c is not best and not (best.start <= c.start <= last) and c.score >= best.score - 0.5
    ]
    return best, bool(rivals)


def _times_in(segment: str) -> list[tuple[int, int, time]]:
    """Время в куске текста: (начало, конец совпадения, время). С учётом «по МСК»."""
    result = []
    for m in TIME_RE.finditer(segment):
        result.append((m.start(), m.end(), time(int(m.group(1)), int(m.group(2)))))
    for m in TIME_DOT_RE.finditer(segment):
        result.append((m.start(1), m.end(), time(int(m.group(1)), int(m.group(2)))))
    result.sort()
    adjusted = []
    for start, end, value in result:
        if MSK_AFTER_RE.match(segment[end:end + 20]):
            # Томск — МСК+4: «15:00 по МСК» на сайте должно быть 19:00
            value = (datetime.combine(date.min, value) + MSK_TO_TOMSK).time()
        adjusted.append((start, end, value))
    return adjusted


def _start_and_end(segment: str, times: list[tuple[int, int, time]], index: int) -> tuple[time, time | None]:
    start_pos, end_pos, start_time = times[index]
    if index + 1 < len(times):
        next_start, _, next_time = times[index + 1]
        glue = segment[end_pos:next_start]
        if RANGE_GLUE_RE.match(glue) and next_time > start_time:
            return start_time, next_time
    return start_time, None


def _pick_time(text: str, date_pos: int | None) -> tuple[time | None, time | None]:
    lines = text.split("\n")
    if date_pos is not None:
        line_start, line_end = _line_bounds(text, date_pos)
        line = text[line_start:line_end]
        times = _times_in(line)
        if times:
            after = [i for i, t in enumerate(times) if t[0] >= date_pos - line_start]
            return _start_and_end(line, times, after[0] if after else 0)
        # Время на одной из следующих строк после даты, кроме строк про заявки
        offset = line_end + 1
        for line in text[offset:].split("\n"):
            if not APPLICATION_RE.search(line) and (times := _times_in(line)):
                return _start_and_end(line, times, 0)
    for line in lines:
        if not APPLICATION_RE.search(line) and (times := _times_in(line)):
            return _start_and_end(line, times, 0)
    return None, None


def parse_when(text: str, published: datetime) -> When:
    """Дата, время и строка с датой. Чего нет в тексте — None."""
    text = (text or "").replace(" ", " ").replace("​", "")
    candidates = _candidates(text, published)
    best, ambiguous = _choose(candidates)
    if best is None:
        start_time, end_time = _pick_time(text, None)
        return When(start_time=start_time, end_time=end_time)
    # Время ищем от первого упоминания выбранной даты: «▫21 сентября / ▫12:00–14:30 / … ▫21 сентября, в 19:00»
    first_pos = min(c.pos for c in candidates if c.start == best.start)
    start_time, end_time = _pick_time(text, first_pos)
    line_start, line_end = _line_bounds(text, best.pos)
    return When(best.start, best.end, start_time, end_time, ambiguous, text[line_start:line_end])


def parse_dates(text: str, published: datetime) -> tuple[date | None, date | None]:
    """Возвращает (event_date, end_date). Оба None, если дат в тексте нет."""
    when = parse_when(text, published)
    return when.event_date, when.end_date


def parse_times(text: str) -> tuple[time | None, time | None]:
    """Возвращает (start_time, end_time). Одно время — только начало."""
    return _pick_time((text or "").replace(" ", " "), None)
