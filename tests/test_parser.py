"""Разбор текста постов. Сеть не нужна — на входе словари, как из wall.get."""
from datetime import date, datetime, time

import pytest

from collector.dates import parse_dates, parse_times, parse_when
from collector.extract import auto_publish, extract_image_url, extract_title, is_announcement, is_report, parse_post

PUBLISHED = datetime(2026, 10, 20, 12, 0)


def test_range_date_and_range_time():
    p = parse_post({
        "text": "Фестиваль «Событие»\n3–5 ноября\nНачало в 18:00–20:00\nГде: МКЦ ТПУ",
    }, PUBLISHED)
    assert p.event_date == date(2026, 11, 3)
    assert p.end_date == date(2026, 11, 5)
    assert (p.start_time, p.end_time) == (time(18, 0), time(20, 0))
    assert p.location == "МКЦ ТПУ"
    assert p.category == "creativity"


def test_single_russian_date_with_year():
    p = parse_post({"text": "Олимпиада 15 ноября 2027 года"}, PUBLISHED)
    assert p.event_date == date(2027, 11, 15)
    assert p.end_date is None


def test_numeric_date():
    p = parse_post({"text": "Субботник 09.11.2026\nНачало в 11:00"}, PUBLISHED)
    assert p.event_date == date(2026, 11, 9)


def test_month_already_past_rolls_to_next_year():
    # В октябре «3 марта» — это март 2027
    p = parse_post({"text": "Концерт 3 марта"}, PUBLISHED)
    assert p.event_date == date(2027, 3, 3)


def test_no_date_means_none():
    p = parse_post({"text": "Конкурс «Ход талантам»\nЗаявки до 11 ноября"}, PUBLISHED)
    assert p.event_date is None


def test_single_time_is_only_start():
    assert parse_times("Начало в 18:00") == (time(18, 0), None)


def test_no_time_in_text():
    assert parse_times("приходите, будет интересно") == (None, None)


def test_title_skips_greeting_and_hashtags():
    text = "Друзья, привет!\n#спорт\nМастер-класс по алтимату\nГде: Карпова, 4"
    assert extract_title(text) == "Мастер-класс по алтимату"


def test_category_from_hashtag():
    p = parse_post({"text": "Турнир\n#спорт"}, PUBLISHED)
    assert p.category == "sport"


def test_unknown_category_is_none():
    p = parse_post({"text": "Просто объявление"}, PUBLISHED)
    assert p.category is None


def test_image_url_picks_largest_size():
    attachments = [{
        "type": "photo",
        "photo": {"sizes": [
            {"width": 100, "height": 100, "url": "small"},
            {"width": 800, "height": 600, "url": "big"},
            {"width": 320, "height": 240, "url": "medium"},
        ]},
    }]
    assert extract_image_url(attachments) == "big"
    assert extract_image_url([]) is None
    assert extract_image_url(None) is None


def test_dates_reject_garbage():
    assert parse_dates("31.02.2026", PUBLISHED) == (None, None)
    assert parse_dates("Встреча 31 ноября в 18:00", PUBLISHED) == (None, None)


# Выбор даты среди нескольких

WEDNESDAY = datetime(2026, 10, 14, 12, 0)


def when(text, published=PUBLISHED):
    return parse_when(text, published)


def test_deadline_is_not_event_date():
    assert when("Регистрация открыта до 15 ноября").event_date is None
    w = when("Приём заявок: до 1 декабря\nФинал — 12 декабря в 15:00")
    assert (w.event_date, w.start_time) == (date(2026, 12, 12), time(15, 0))


def test_selection_stage_loses_to_main_event():
    w = when("Отборочный этап: 1–2 ноября\nФинал: 20 ноября")
    assert w.event_date == date(2026, 11, 20)


def test_short_numeric_date_needs_a_sign_of_date():
    assert when("📅 05.12 в 17:00").event_date == date(2026, 12, 5)
    assert when("Дата - 07.11 (суббота)").event_date == date(2026, 11, 7)
    assert when("Счёт матча 3.12, приходи болеть").event_date is None
    assert when("Начало в 18.30").start_time == time(18, 30)


@pytest.mark.parametrize("text, start, end", [
    ("Школа пройдёт со 2 по 6 декабря", date(2026, 12, 2), date(2026, 12, 6)),
    ("С 26 по 30 ноября — неделя науки", date(2026, 11, 26), date(2026, 11, 30)),
    ("Сезон: 28 декабря 2026 — 15 января 2027", date(2026, 12, 28), date(2027, 1, 15)),
    ("Первый этап: 21 декабря 2026 — 26 марта 2027 года", date(2026, 12, 21), date(2027, 3, 26)),
])
def test_ranges(text, start, end):
    assert parse_dates(text, PUBLISHED) == (start, end)


def test_historical_date_is_ignored():
    text = "В память о событиях 1–3 сентября 2004 года\nАкция пройдёт 3 сентября в 12:00"
    assert when(text, datetime(2026, 9, 1, 12, 0)).event_date == date(2026, 9, 3)


def test_weekday_counts_from_publication_day():
    assert when("В эту субботу — турнир по футболу", WEDNESDAY).event_date == date(2026, 10, 17)
    assert when("📍Воскресенье, 18:00, стадион «Политехник»", WEDNESDAY).event_date == date(2026, 10, 18)
    assert when("Сегодня в 19:00 — кинопоказ", WEDNESDAY).event_date == date(2026, 10, 14)
    # «сегодня» без времени и без слова-события — не дата
    assert when("Сегодня расскажем о новом проекте", WEDNESDAY).event_date is None


def test_explicit_date_beats_weekday():
    assert when("В эту субботу, 24 октября, ждём всех", WEDNESDAY).event_date == date(2026, 10, 24)


def test_recent_past_date_keeps_the_year():
    # Месяц раньше публикации, но меньше 30 дней назад — это прошлое событие, а не следующий год
    assert when("1 октября прошла встреча клуба").event_date == date(2026, 10, 1)


def test_two_equal_dates_are_ambiguous():
    w = when("4 марта — первый этап\n11 марта — второй этап")
    assert w.event_date == date(2027, 3, 4) and w.ambiguous
    assert not when("С 26 по 30 ноября\n• 26–27 ноября — лекции\n• 28–30 ноября — практика").ambiguous


def test_time_rules():
    assert when("Встреча 5 ноября в 12:00 по МСК").start_time == time(16, 0)
    assert (when("5 ноября, 18:00–20:00").start_time, when("5 ноября, 18:00–20:00").end_time) == (time(18, 0), time(20, 0))
    # Конец — только диапазон на той же строке, а не последнее время в тексте
    w = when("5 ноября\nСбор в 10:00\nAfter-party в 21:00")
    assert (w.start_time, w.end_time) == (time(10, 0), None)
    # Время со строки про заявки не берём
    assert when("Заявки до 12:00 4 ноября\n5 ноября в 17:00 финал").start_time == time(17, 0)


# Место

@pytest.mark.parametrize("text, place", [
    ("Где: МКЦ ТПУ", "МКЦ ТПУ"),
    ("📍 Корпус 10, ауд. 305", "Корпус 10, ауд. 305"),
    ("5 ноября, 16:00, Спорткомплекс ТПУ.", "Спорткомплекс ТПУ"),
    ("Ждём вас 5 ноября в 18:00 в аудитории 112 (Ленина, 30) будет интересно", "Аудитории 112 (Ленина, 30)"),
    ("Приходи 7 ноября на Усова, 7", "Усова, 7"),
    ("▫ Стадион «Политехник» — место проведения", "Стадион «Политехник»"),
    ("Место: бизнес-инкубатор «Б51» (ул. Белинского, 51). Регистрация: clck.ru/x", "Бизнес-инкубатор «Б51» (ул. Белинского, 51)"),
    ("Финал пройдёт 5 мая в г. Новосибирск", "г. Новосибирск"),
    ("Вебинар 5 ноября в 15:00, ссылка в комментариях", "Онлайн"),
])
def test_place(text, place):
    assert parse_post({"text": text}, PUBLISHED).location == place


@pytest.mark.parametrize("text", [
    "Дата и место:\n🗓 5 ноября (пятница)",  # метка без значения не берёт следующую строку
    "▫теплая компания в уютной аудитории",  # не конкретное место
    "Анкету присылайте на почту, корпус 11, офис 232",  # контакты, а не место мероприятия
    "Отборочный этап (онлайн): 1 ноября\nКонкурсные дни: 20 ноября",  # «онлайн» не в строке с датой
])
def test_no_place(text):
    assert parse_post({"text": text}, PUBLISHED).location is None


# Категория, разметка ВК, анонс

def test_category_counts_all_words_not_the_first_one():
    text = "Соревнования по 1С для студентов\nКарьера, работодатели и стажировки"
    assert parse_post({"text": text}, PUBLISHED).category == "career"
    assert parse_post({"text": "Хакатон по ИИ и нейросетям"}, PUBLISHED).category == "science"


def test_community_hints_category():
    assert parse_post({"text": "Встреча клуба в четверг", "owner_id": -44845822}, PUBLISHED).category == "sport"
    assert parse_post({"text": "Встреча клуба в четверг", "owner_id": -1}, PUBLISHED).category is None


def test_vk_markup_is_cleaned():
    p = parse_post({"text": "[club14752902|Профком ТПУ] приглашает на квиз\n#Мероприятие@postpu"}, PUBLISHED)
    assert p.title == "Профком ТПУ приглашает на квиз"
    assert "#Мероприятие@" not in p.description and "#Мероприятие" in p.description


def test_announcement_report_and_publishing():
    news = parse_post({"text": "Поздравляем коллектив с юбилеем!"}, PUBLISHED)
    assert not is_announcement(news)
    contest = parse_post({"text": "Конкурс фотографий\nПриглашаем присылать работы"}, PUBLISHED)
    assert is_announcement(contest) and not auto_publish(contest)  # без даты — администратору
    # Без даты и без приглашения — новость; с приглашением, но о прошедшем — отчёт
    assert not is_announcement(parse_post({"text": "Участники встречи подписали соглашение"}, PUBLISHED))
    assert not is_announcement(parse_post({"text": "Конкурс прошёл, спасибо всем! Ждём вас в следующем году"}, PUBLISHED))
    # Поздравление с датой — не мероприятие, а с приглашением — мероприятие
    assert not is_announcement(parse_post({"text": "С Днём народного единства! 4 ноября — наш общий праздник"}, PUBLISHED))
    assert is_announcement(parse_post({"text": "С праздником! Приглашаем на концерт 4 ноября в 18:00"}, PUBLISHED))
    # «Дедлайн: 23 ноября» — срок, а не день мероприятия
    assert parse_post({"text": "Опрос о карьере\n📅 Дедлайн: 23 ноября"}, PUBLISHED).event_date is None
    # История и рубрики — не мероприятия
    assert not is_announcement(parse_post({"text": "Сегодня, 7 ноября, в истории науки: 159 лет назад родилась Мария"}, PUBLISHED))
    assert not is_announcement(parse_post({"text": "Ко Дню волонтёра, который отмечается 5 декабря, запускаем рубрику"}, PUBLISHED))
    # Призовые места — не место проведения; «Формат: полностью онлайн» — онлайн
    assert parse_post({"text": "Розыгрыш 1 ноября\n1-3 место — Толстовка ТПУ"}, PUBLISHED).location is None
    assert parse_post({"text": "Старт курса: 6 ноября\nФормат: полностью онлайн"}, PUBLISHED).location == "Онлайн"
    # Ссылка на сообщество ВКонтакте — не место
    assert parse_post({"text": "Следить за программой можно в сообществе МКЦ ТПУ в социальной сети ВКонтакте"},
                      PUBLISHED).location is None
    report = parse_post({"text": "1 октября прошёл турнир по футболу"}, PUBLISHED)
    assert is_report(report, PUBLISHED)
    ready = parse_post({"text": "Турнир по футболу 5 ноября в 18:00"}, PUBLISHED)
    assert auto_publish(ready) and not is_report(ready, PUBLISHED)
    ambiguous = parse_post({"text": "Турнир по футболу\n4 ноября — групповой этап\n11 ноября — финал"}, PUBLISHED)
    assert ambiguous.date_ambiguous and not auto_publish(ambiguous)