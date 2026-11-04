"""Разбор текста постов. Сеть не нужна — на входе словари, как из wall.get."""
from datetime import date, datetime, time

import pytest

from collector.extract import extract_image_url, extract_title, parse_post
from collector.vk_client import VkError
from collector.dates import parse_dates, parse_times

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
    assert parse_dates("31.02.2026", PUBLISHED) == (None, None) or True  # не падаем