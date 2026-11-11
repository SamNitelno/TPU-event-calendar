"""Разбор текста поста в поля мероприятия.

Регулярки, а не ML: посты ТПУ пишутся по шаблонам «когда / где / во сколько».
Задача — не идеальный разбор, а честный: что не нашли — None, и пост уйдёт
администратору (pending). Дата и время — в collector/dates.py.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime, time

from collector.dates import (
    CROSS_RANGE_RE, NUM_FULL_RE, NUM_SHORT_RE, RANGE_RE, SINGLE_RE, TIME_RE, parse_when,
)

# Разметка ВК: «[club14752902|Профком ТПУ]», «[id1|Иван]», «#Мероприятие@postpu»
VK_MENTION_RE = re.compile(r"\[(?:id|club|public|event)\d+\|([^\]]+)\]")
VK_LINK_RE = re.compile(r"\[(?:https?://)?[^\]|]+\|([^\]]+)\]")
VK_HASHTAG_SUFFIX_RE = re.compile(r"(#[\wА-Яа-яЁё]+)@[\w.]+")

HASHTAG_RE = re.compile(r"#([\wА-Яа-яЁё]+)")
EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF" "←-⇿■-◿️‍" "]+"
)
MARKDOWN_RE = re.compile(r"[*_`>]+")

# Место

# «Где: МКЦ», «Место проведения — ауд. 301», «📍 Адрес: …». Значение — на той же строке
LABEL_RE = re.compile(
    r"(?<![а-яё])(?:где|место(?:\s+проведения)?|локация|адрес)\s*[:—–-]\s*(\S.*)$", re.IGNORECASE,
)
# «COLIZEUM Лампочка — место проведения»
REVERSE_LABEL_RE = re.compile(r"^(.+?)\s*[—–-]\s*место\s+проведения", re.IGNORECASE)
CITY_RE = re.compile(r"(?<![а-яё])в\s+(г\.\s*[А-ЯЁ][\w-]+(?:[\s-][А-ЯЁ][\w-]+)?)")
# Улицы рядом с корпусами ТПУ: их часто пишут без «ул.» — «на Белинского, 51»
CAMPUS_STREETS = (
    "Белинского|Ленина|Усова|Карпова|Вершинина|Пирогова|Советская|Советской|Кирова|Войкова|Савиных|"
    "Учебная|Учебной|Тимакова|Красноармейская|Красноармейской|Лыткина|Студенческая|Никитина|"
    "Елизаровых|Мокрушина|Нахимова|Гагарина|Фрунзе|Киевская|Киевской"
)
STREET_RE = re.compile(
    r"(?:(?<![а-яё])(?:ул\.?|улица|пр\.|пр-т|просп\.?|проспект|пер\.|переулок|наб\.)\s*[А-ЯЁ][\w-]+"
    rf"|(?<![а-яё])(?:{CAMPUS_STREETS})(?=,?\s*\d))"
)
# Слова, по которым видно, что это место. Ищутся с начала слова
PLACE_WORD_RE = re.compile(
    r"(?<![а-яёa-z])(?:корпус|ауд\.|аудитори|зал(?![а-яё])|коворкинг|кварк|площад|библиотек|нтб|мкц|б51|"
    r"бизнес-инкубатор|стадион|спорткомплекс|спортзал|манеж|бассейн|пространств|ботаническ|сад(?![а-яё])|"
    r"парк(?![а-яё])|музе|дворец|штаб|кабинет|офис|холл|фойе|гк(?![а-яё]))",
    re.IGNORECASE,
)
# Место должно быть конкретным: число, название с большой буквы или известная площадка.
# Иначе «в уютной аудитории» стало бы местом
KNOWN_VENUE_RE = re.compile(r"(?<![а-яё])(?:мкц|нтб|б51|кварк|гк)(?![а-яё])", re.IGNORECASE)
# Строки с контактами и ссылками на соцсети: «корпус 11, офис 232» там — адрес для анкет,
# а «в сообществе МКЦ ТПУ ВКонтакте» — не место мероприятия
LINE_SKIP_RE = re.compile(
    r"тел\.|телефон|почт|e-?mail|@|анкет|\[почта\]|\[телефон\]|вконтакте|социальной\s+сети|соцсет|телеграм|telegram",
    re.IGNORECASE,
)
WEEKDAY_NAME_RE = re.compile(
    r"\(?(?<![а-яё])(?:понедельник|вторник|среда|среду|четверг|пятница|пятницу|суббота|субботу|воскресенье|"
    r"пн|вт|ср|чт|пт|сб|вс)(?![а-яё])\)?",
    re.IGNORECASE,
)
TIME_SPAN_RE = re.compile(
    r"(?:(?<![а-яё])(?:с|в|во)\s+)?\d{1,2}[:.]\d{2}(?:\s*(?:[–—-]|до)\s*\d{1,2}[:.]\d{2})?"
    r"(?:\s*\(?\s*(?:по\s+)?(?:мск|московскому)\)?)?",
    re.IGNORECASE,
)
PREPOSITION_RE = re.compile(r"(?:^|[\s,(])(?:в|во|на)\s+", re.IGNORECASE)
# Где место заканчивается: глагол или новая часть предложения
PLACE_STOP_RE = re.compile(
    r"\s(?:будет|будут|состоится|пройд|ждём|ждем|приходи|регистр|подробнее|чтобы|где\s|который|которая|"
    r"(?:на|для|с|со)\s+(?!ул\.|пр\.|просп|пер\.|наб\.|мкр\.)[а-яё])"
    r"|\s[—–]\s|[!?;]|\.(?=\s+[А-ЯЁA-Z])|(?<![А-ЯЁ])\.$|\s(?:Регистрация|Ссылка|Подробнее)|clck\.ru|vk\.cc|https?://",
)
ABBREVIATIONS = ("ул", "пр", "просп", "ауд", "г", "д", "стр", "мкр", "пер", "наб", "каб", "корп", "им")
ONLINE_STRONG_RE = re.compile(
    r"вебинар|онлайн-встреч|онлайн-трансляц|прям\w+\s+эфир|ссылка\s+для\s+подключения|подключайтесь|zoom|ktalk|"
    r"формат\s*[:—–-]?\s*(?:полностью\s+)?онлайн|полностью\s+онлайн|в\s+онлайн-формате",
    re.IGNORECASE,
)
# «1-3 место — Толстовка ТПУ»: призовое место в рейтинге, а не место проведения
RANK_BEFORE_RE = re.compile(r"\d\s*[–—-]?\s*\d*\s*$")
ONLINE_WEAK_RE = re.compile(r"онлайн|дистанционн", re.IGNORECASE)

# Категория. Основы слов ищутся с начала слова; слово в первой строке весит вдвое больше
CATEGORY_WORDS: dict[str, list[str]] = {
    "sport": ["спорт", "турнир", "матч", "соревнован", "футбол", "баскетбол", "волейбол", "теннис", "фрисби",
              "алтимат", "забег", "лыж", "плаван", "шахмат", "киберспорт", "cs2", "фитнес", "тренировк", "siblions"],
    "science": ["наук", "научн", "лекци", "конференц", "семинар", "диссертац", "доклад", "исследова",
                "лаборатор", "хакатон", "олимпиад", "дрон", "беспилот", "ии", "нейросет", "физик", "математ"],
    "creativity": ["культур", "творч", "концерт", "фестивал", "мкц", "выступлен", "кастинг", "танц", "вокал",
                   "театр", "кино", "книжн", "литератур", "экомод", "дефиле", "выставк", "музык", "хореограф",
                   "искусств", "dance"],
    "volunteering": ["волонт", "добро", "субботник", "благотвор", "акци", "донор", "животн", "приют", "эколог"],
    "career": ["карьер", "стажировк", "ваканси", "работодател", "професси", "предприним", "стартап", "бизнес",
               "резюме", "кадров", "трудоустр", "предприят", "кейс", "1с"],
    "student_life": ["студсовет", "общежит", "общаг", "школа актива", "студжизн", "первокурсник", "знакомств",
                     "открытых дверей", "ярмарк", "отряд", "разговорн", "speaking", "йог", "оздоров", "здоров",
                     "зрени", "скрининг"],
}
_CATEGORY_PATTERNS = {
    slug: [re.compile(r"(?<![а-яёa-z0-9])" + re.escape(stem)) for stem in stems]
    for slug, stems in CATEGORY_WORDS.items()
}
# Сообщества с ясным профилем: подсказка весом в одно слово и решающий голос при равенстве
COMMUNITY_CATEGORY = {
    -44845822: "sport",          # Спортклуб «Сибирские львы»
    -24890431: "career",         # Центр карьеры ТПУ
    -2713603: "volunteering",    # ВО «Стиль Жизни»
    -215750011: "volunteering",  # Экологический клуб
    -80072684: "creativity",     # МКЦ ТПУ
    -222585418: "career",        # Студенты Росатома
    -215901557: "career",        # Энергетический клуб
    -222469101: "student_life",  # Оздоровительная комиссия
    -14752902: "student_life",   # Профком
    -31264870: "student_life",   # Движение первых
    -109388070: "student_life",  # Команда ТПУ
}

# Пост без даты ждёт администратора, только если зовёт участвовать. Слова «конкурс», «встреча»
# для этого слишком общие: на живом прогоне по ним в очередь попадали новости университета
INVITE_RE = re.compile(
    r"(?<![а-яё])(?:приглаша|приходи|ждём\s+(?:тебя|вас)|ждем\s+(?:тебя|вас)|ждут\s+(?:тебя|вас)|регистрируй|"
    r"регистрация\s+(?:открыта|продолжается)|подавай|подай\s+заявк|подать\s+заявк|участвуй|присоединяй|"
    r"записывай|успей|не\s+пропусти|зови\s+друзей|до\s+встречи|будем\s+рады|встречаемся)",
    re.IGNORECASE,
)
# Не анонс: отчёт о прошедшем, поздравление, история, рубрика. «С Днём народного единства! 4 ноября — …»,
# «Сегодня, 7 ноября, в истории науки… 159 лет назад родилась», «запускаем рубрику ко Дню волонтёра, 5 декабря»
REPORT_RE = re.compile(
    r"(?<![а-яё])(?:прош[её]л|прошла|прошло|провели|состоял(?:ся|ась|ось|ись)|заверш[её]н|спасибо\s+всем|"
    r"поздравля|с\s+дн[её]м|с\s+праздником|лет\s+назад|родил(?:ся|ась)|в\s+истории|рубрик|отмечается)",
    re.IGNORECASE,
)


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
    # В тексте есть другая дата почти так же похожая на день мероприятия
    date_ambiguous: bool = False


def clean_vk_markup(text: str) -> str:
    """API отдаёт ссылки на сообщества как «[club1|Название]»: на сайте нужно только название."""
    text = VK_MENTION_RE.sub(r"\1", text)
    text = VK_LINK_RE.sub(r"\1", text)
    return VK_HASHTAG_SUFFIX_RE.sub(r"\1", text)


def _clean_title(line: str) -> str:
    line = MARKDOWN_RE.sub("", line)
    line = EMOJI_RE.sub("", line)
    return " ".join(line.split())


def extract_title(text: str) -> str:
    """Первая содержательная строка. Служебные приветствия пропускаем."""
    skip_starts = ("друзья", "привет", "уважаемые", "дорогие", "внимание")
    for raw in text.splitlines():
        line = _clean_title(raw)
        if not line or line.startswith("#") or not re.search(r"[A-Za-zА-Яа-яЁё]{2}", line):
            continue
        if line.lower().startswith(skip_starts) and len(line) < 60:
            continue
        return line[:300]
    return "Мероприятие"


# Категория

def extract_category(text: str, owner_id: int | None = None) -> str | None:
    low = text.lower().replace("ё", "е")
    title = low.split("\n", 1)[0]
    scores: dict[str, float] = {}
    first_pos: dict[str, int] = {}
    for slug, patterns in _CATEGORY_PATTERNS.items():
        score = 0.0
        for pattern in patterns:
            if m := pattern.search(low):
                score += 2 if pattern.search(title) else 1
                first_pos[slug] = min(first_pos.get(slug, m.start()), m.start())
        scores[slug] = score
    prior = COMMUNITY_CATEGORY.get(owner_id) if owner_id is not None else None
    if prior:
        scores[prior] += 1
    best = max(scores.values())
    if best <= 0:
        return None
    tied = [slug for slug, score in scores.items() if score == best]
    if len(tied) == 1:
        return tied[0]
    if prior in tied:
        return prior
    return min(tied, key=lambda slug: first_pos.get(slug, len(low)))


# Место

def _without_date_and_time(line: str) -> str:
    for pattern in (CROSS_RANGE_RE, RANGE_RE, SINGLE_RE, NUM_FULL_RE, NUM_SHORT_RE, TIME_SPAN_RE, WEEKDAY_NAME_RE):
        line = pattern.sub(" ", line)
    line = re.sub(r"(?<![а-яё])(?:когда|дата|время|во сколько)\s*[:—–-]?", " ", line, flags=re.IGNORECASE)
    return line


def _strip_lead(line: str) -> str:
    return re.sub(r"^[^\wА-Яа-яЁё«\"(]+", "", EMOJI_RE.sub(" ", line))


def _is_specific(value: str) -> bool:
    return bool(re.search(r"\d", value) or re.search(r"(?<!^)[«\"]?[А-ЯЁA-Z][\wа-яё]", value[1:])
                or KNOWN_VENUE_RE.search(value) or STREET_RE.search(value))


def _cut_end(value: str) -> str:
    for m in PLACE_STOP_RE.finditer(value):
        if m.group(0).startswith("."):
            word = re.search(r"([А-Яа-яЁё]+)\.$", value[:m.start() + 1])
            if word and word.group(1).lower() in ABBREVIATIONS:
                continue
        return value[:m.start()]
    return value


def _clean_place(value: str) -> str | None:
    value = _strip_lead(value)
    value = _cut_end(value)
    value = re.sub(r"\s+", " ", value).strip(" ,;:—–-|")
    if value.count(")") > value.count("("):
        value = value.rstrip(")")
    if value.count("(") > value.count(")"):
        value += ")"
    value = value.rstrip(" .,;:")
    if len(value) < 2 or not _is_specific(value):
        return None
    return (value[0].upper() + value[1:])[:150]


def _place_in_line(line: str, need_preposition: bool) -> str | None:
    if LINE_SKIP_RE.search(line):
        return None
    rest = _without_date_and_time(_strip_lead(line))
    signal = PLACE_WORD_RE.search(rest) or STREET_RE.search(rest)
    if not signal:
        return None
    start = None
    for prep in PREPOSITION_RE.finditer(rest[:signal.start()]):
        gap = rest[prep.end():signal.start()]
        if len(gap) <= 60 and not re.search(r"[.!?:]", gap):
            start = prep.end()
    if start is None:
        if need_preposition:
            return None
        before = rest[:signal.start()]
        # Без предлога место должно начинать строку: «Танцевальный зал МКЦ», «2-й корпус»
        if len(before.strip()) > 25 or re.search(r"[.!?:]", before):
            return None
        start = 0
    return _clean_place(rest[start:])


def _is_structured(line: str) -> bool:
    """Строка-реквизит: начинается со значка, содержит дату или время либо сразу с места или адреса."""
    stripped = line.strip()
    if not stripped:
        return False
    if not re.match(r"[\wА-Яа-яЁё«\"(]", stripped):
        return True
    if TIME_RE.search(stripped) or SINGLE_RE.search(stripped) or RANGE_RE.search(stripped):
        return True
    head = stripped[:25]
    return bool(PLACE_WORD_RE.match(head) or STREET_RE.match(head) or re.match(r"\d+-?[йя]?\s+корпус", head))


def extract_location(text: str, date_line: str | None = None) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # 1. Явная метка «Где:», «Место:», «… — место проведения»
    for line in lines:
        if LINE_SKIP_RE.search(line):
            continue
        m = LABEL_RE.search(line)
        if m and not RANK_BEFORE_RE.search(line[:m.start()]) and (value := _clean_place(m.group(1))):
            return value
        if (m := REVERSE_LABEL_RE.search(_strip_lead(line))) and (value := _clean_place(m.group(1))):
            return value
    # 2. Строки-реквизиты: «📍 Танцевальный зал МКЦ ТПУ», «10 октября, 16:00, МКЦ ТПУ»
    for line in lines:
        if _is_structured(line) and (value := _place_in_line(line, need_preposition=False)):
            return value
    # 3. Внутри фразы: «узнаем в учебном корпусе №9»
    for line in lines:
        if value := _place_in_line(line, need_preposition=True):
            return value
    # 4. Другой город: «в г. Санкт-Петербург»
    for line in lines:
        if not LINE_SKIP_RE.search(line) and (m := CITY_RE.search(line)):
            return m.group(1)
    # 5. Онлайн. Слабые признаки («онлайн», «дистанционно») — только в строке с датой мероприятия
    if ONLINE_STRONG_RE.search(text) or (date_line and ONLINE_WEAK_RE.search(date_line)):
        return "Онлайн"
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
    """Один пост wall.get -> поля мероприятия. owner_id поста подсказывает категорию."""
    text = clean_vk_markup(item.get("text", "") or "")
    when = parse_when(text, published)
    return Parsed(
        title=extract_title(text),
        description=text,
        event_date=when.event_date,
        end_date=when.end_date,
        start_time=when.start_time,
        end_time=when.end_time,
        location=extract_location(text, when.line),
        category=extract_category(text, item.get("owner_id")),
        image_url=extract_image_url(item.get("attachments")),
        date_ambiguous=when.ambiguous,
    )


# Что делать с постом

def is_announcement(parsed: Parsed) -> bool:
    """Похоже на анонс. Без даты — нужно приглашение и никаких признаков отчёта.
    С датой — достаточно, чтобы это не был отчёт или поздравление без приглашения."""
    text = parsed.description
    invites = bool(INVITE_RE.search(text))
    report = bool(REPORT_RE.search(text))
    if parsed.event_date is None:
        return invites and not report
    return invites or not report


def is_report(parsed: Parsed, published: datetime) -> bool:
    """Мероприятие закончилось до публикации поста — это отчёт, а не анонс."""
    if parsed.event_date is None:
        return False
    return (parsed.end_date or parsed.event_date) < published.date()


def auto_publish(parsed: Parsed) -> bool:
    """Публиковать сразу: есть дата и категория, и дата не спорная. Иначе — на проверку администратору."""
    return bool(parsed.event_date and parsed.category and not getattr(parsed, "date_ambiguous", False))
