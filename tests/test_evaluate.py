"""Проверка разбора на эталоне: формат data/reference_50.csv, правила сверки и подсчёт."""
from datetime import date, datetime, time

import pytest

from collector.evaluate import (
    COLUMNS, Reference, decision, evaluate, load_reference, same_place,
)
from collector.extract import Parsed
from db.init_db import CATEGORIES

PUBLISHED = datetime(2026, 10, 14, 12, 0)


# Эталон

def test_reference_follows_data_readme_format():
    rows = load_reference()
    assert len(rows) == 50
    assert len({r.link for r in rows}) == 50
    slugs = {slug for slug, _ in CATEGORIES}
    for r in rows:
        assert r.link.startswith("https://vk.com/wall-")
        assert r.category in slugs
        # Исходный текст поста целиком, а не пересказ
        assert len(r.text) > 80
        if r.end_date:
            assert r.event_date and r.end_date >= r.event_date
        if not r.is_event:
            assert r.event_date is None


def test_old_reference_format_is_rejected(tmp_path):
    old = tmp_path / "old.csv"
    old.write_text("Ссылка;Сообщество;Текст;Дата;Время;Место;Категория\n", encoding="utf-8")
    with pytest.raises(ValueError, match="нет колонок"):
        load_reference(old)


def test_reference_reads_day_of_publication(tmp_path):
    path = tmp_path / "one.csv"
    path.write_text(
        ",".join(COLUMNS) + "\n"
        "https://vk.com/wall-1_1,Команда ТПУ,2026-10-14,Текст,да,2026-10-18,,18:00,\"ул. Карпова, 4\",sport\n",
        encoding="utf-8",
    )
    [row] = load_reference(path)
    assert row.published_at == datetime(2026, 10, 14, 12, 0)
    assert (row.event_date, row.end_date, row.start_time) == (date(2026, 10, 18), None, time(18, 0))
    assert (row.location, row.category, row.is_event) == ("ул. Карпова, 4", "sport", True)


# Сверка места

@pytest.mark.parametrize("expected, got", [
    ("ул. Карпова, 4", "Карпова, 4"),
    ("Танцевальный зал МКЦ ТПУ", "танцевальный зал МКЦ"),
    ("Бизнес-инкубатор ТПУ «Б51», ул. Белинского, 51", "бизнес-инкубатор ТПУ «Б51» (ул. Белинского, 51, зал «Воробьев»)"),
    ("Онлайн", "онлайн (прямой эфир)"),
    ("ТПУ", "ТПУ"),
    (None, None),
])
def test_same_place(expected, got):
    assert same_place(expected, got)


@pytest.mark.parametrize("expected, got", [
    ("НТБ, зал художественной литературы", "ТПУ"),  # совпадают только общие слова
    ("ТПУ", "Главный корпус ТПУ"),
    ("Сибирский Ботанический Сад ТГУ", "🗓 22 августа (пятница)"),
    ("Онлайн", None),
    (None, "ул. Карпова, 4"),
])
def test_different_place(expected, got):
    assert not same_place(expected, got)


# Подсчёт

def reference(link, event_date=None, location=None, category="sport", is_event=True, start_time=None):
    return Reference(link=link, community="Команда ТПУ", published_at=PUBLISHED, text=link, is_event=is_event,
                     event_date=event_date, end_date=None, start_time=start_time, location=location,
                     category=category)


def parsed(event_date=None, location=None, category=None, start_time=None):
    return Parsed(title="", description="", event_date=event_date, end_date=None, start_time=start_time,
                  end_time=None, location=location, category=category, image_url=None)


def test_evaluate_counts_right_missed_wrong_and_invented():
    day = date(2026, 10, 18)
    rows = [
        reference("right", day, "ул. Карпова, 4", start_time=time(18, 0)),
        reference("missed", day, "МКЦ ТПУ"),
        reference("wrong", day),
        reference("deadline"),  # даты в посте нет, а разбор взял срок заявки
        reference("news", is_event=False),
        reference("crash", day),
    ]
    answers = {
        "right": parsed(day, "Карпова, 4", "sport", time(18, 0)),
        "missed": parsed(),
        "wrong": parsed(date(2026, 10, 11), category="sport"),
        "deadline": parsed(date(2026, 11, 11), category="sport"),
        "news": parsed(),
    }

    def fake_parse(item, published):
        if item["text"] == "crash":
            raise ValueError("day is out of range for month")
        return answers[item["text"]]

    report = evaluate(rows, fake_parse)
    assert (report.date.correct, report.date.missed, report.date.wrong, report.date.invented) == (1, 2, 1, 1)
    assert report.date.total == 5 and report.not_events == 1
    assert (report.place.correct, report.place.missed) == (4, 1)  # у wrong, deadline и crash места нет и не найдено
    assert report.time.correct == 5
    assert report.published == 3
    assert [line.split(":")[0] for line in report.published_wrong_date] == ["wrong", "deadline"]
    assert report.crashes == ["crash: ValueError: day is out of range for month"]


def test_decision_follows_r04_thresholds():
    def report_with(date_share, place_share):
        rows = [reference(f"r{i}", date(2026, 10, 18), "МКЦ ТПУ") for i in range(10)]
        answers = {f"r{i}": parsed(date(2026, 10, 18) if i < date_share * 10 else None,
                                   "МКЦ ТПУ" if i < place_share * 10 else None) for i in range(10)}
        return evaluate(rows, lambda item, _: answers[item["text"]])

    assert "ниже 70%" in decision(report_with(0.9, 0.6))
    assert "доработать" in decision(report_with(0.9, 0.8))
    assert "снят" in decision(report_with(0.9, 0.9))
