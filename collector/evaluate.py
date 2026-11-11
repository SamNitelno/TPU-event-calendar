"""Проверка разбора объявлений на эталоне (риск Р-04, требование НФТ-04).

Берёт тексты постов из data/reference_50.csv, разбирает их тем же кодом, что и сборщик
(collector.extract.parse_post), и сверяет дату, время и место с записанными вручную.
Код сборщика не меняет и в базу не пишет.

Запуск из корня репозитория:

    python -m collector.evaluate                       # сводка и все расхождения
    python -m collector.evaluate --csv data/другая.csv  # та же проверка на другой выборке

Правила сверки:
- дата верна, если совпал день начала (event_date). Совпадение конца (end_date) считается отдельно;
- время верно, если совпало время начала (start_time);
- место верно, если совпадает по смыслу: после приведения к одному виду общих слов не меньше
  половины от более короткого варианта и среди них есть не только общие слова вроде «ТПУ» или «корпус»;
- если в посте поля нет (в эталоне пусто) и разбор его не выдумал — это верный ответ.
"""
import argparse
import csv
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path

from collector.extract import Parsed, parse_post

REFERENCE = Path(__file__).resolve().parent.parent / "data" / "reference_50.csv"
COLUMNS = ["link", "community", "published_at", "text", "is_event", "event_date", "end_date",
           "start_time", "location", "category"]
# Порог решения по Р-04 и требование к итоговой версии (НФТ-04)
MANUAL_EDIT_BELOW = 0.70
TARGET = 0.85

# Слова, которые есть почти в каждом месте и сами по себе место не определяют
GENERIC_WORDS = {
    "тпу", "томск", "г", "ул", "улица", "пр", "просп", "проспект", "т", "д", "дом", "стр", "корпус", "корп",
    "ауд", "аудитория", "каб", "кабинет", "этаж", "зал", "и", "в", "на", "по", "с", "у", "площадка",
}
WORD_RE = re.compile(r"[a-zа-я0-9]+")

Parser = Callable[[dict, datetime], Parsed]


@dataclass
class Reference:
    link: str
    community: str
    published_at: datetime
    text: str
    is_event: bool
    event_date: date | None
    end_date: date | None
    start_time: time | None
    location: str | None
    category: str | None


@dataclass
class FieldResult:
    """Сколько раз разбор прав, не нашёл, ошибся или выдумал поле, которого в посте нет."""

    correct: int = 0
    missed: int = 0
    wrong: int = 0
    invented: int = 0

    @property
    def total(self) -> int:
        return self.correct + self.missed + self.wrong + self.invented

    @property
    def share(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def add(self, expected, got, same: bool) -> str:
        if same:
            self.correct += 1
            return "верно"
        if got is None:
            self.missed += 1
            return "не нашёл"
        if expected is None:
            self.invented += 1
            return "лишнее"
        self.wrong += 1
        return "ошибся"


@dataclass
class Report:
    date: FieldResult = field(default_factory=FieldResult)
    end_date: FieldResult = field(default_factory=FieldResult)
    time: FieldResult = field(default_factory=FieldResult)
    place: FieldResult = field(default_factory=FieldResult)
    category: FieldResult = field(default_factory=FieldResult)
    # Как в collector/run.py: есть дата и категория — публикуется сразу, иначе ждёт администратора
    published: int = 0
    published_wrong_date: list[str] = field(default_factory=list)
    not_events: int = 0
    not_events_with_date: list[str] = field(default_factory=list)
    crashes: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)


# Чтение эталона

def _optional(value: str) -> str | None:
    value = (value or "").strip()
    return value or None


def _date(value: str) -> date | None:
    value = _optional(value)
    return date.fromisoformat(value) if value else None


def _time(value: str) -> time | None:
    value = _optional(value)
    return time.fromisoformat(value) if value else None


def _published(value: str) -> datetime:
    value = value.strip()
    # В эталоне бывает только день публикации. Тогда считаем, что пост вышел в полдень
    return datetime.fromisoformat(value) if len(value) > 10 else datetime.fromisoformat(value + "T12:00")


def load_reference(path: Path = REFERENCE) -> list[Reference]:
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = set(COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"В {path} нет колонок: {', '.join(sorted(missing))}. Формат — data/README.md")
        return [
            Reference(
                link=row["link"].strip(),
                community=row["community"].strip(),
                published_at=_published(row["published_at"]),
                text=row["text"],
                is_event=row["is_event"].strip().lower() == "да",
                event_date=_date(row["event_date"]),
                end_date=_date(row["end_date"]),
                start_time=_time(row["start_time"]),
                location=_optional(row["location"]),
                category=_optional(row["category"]),
            )
            for row in reader
        ]


# Сверка

def place_words(place: str) -> set[str]:
    return set(WORD_RE.findall(place.lower().replace("ё", "е")))


def same_place(expected: str | None, got: str | None) -> bool:
    if expected is None or got is None:
        return expected is None and got is None
    a, b = place_words(expected), place_words(got)
    if not (a - GENERIC_WORDS):
        # В эталоне только общие слова, например «ТПУ», — засчитываем лишь точное совпадение
        return a == b
    common = a & b
    if not (common - GENERIC_WORDS):
        return False
    return len(common) / min(len(a), len(b)) >= 0.5


def _show(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value)


def evaluate(rows: list[Reference], parse: Parser = parse_post) -> Report:
    report = Report()
    for row in rows:
        try:
            parsed = parse({"text": row.text}, row.published_at)
        except Exception as exc:  # падение разбора на посте — тоже неверный ответ
            report.crashes.append(f"{row.link}: {type(exc).__name__}: {exc}")
            parsed = Parsed(title="", description=row.text, event_date=None, end_date=None, start_time=None,
                            end_time=None, location=None, category=None, image_url=None)

        if not row.is_event:
            report.not_events += 1
            if parsed.event_date:
                report.not_events_with_date.append(f"{row.link}: разбор нашёл дату {parsed.event_date}")
            continue

        verdicts = [
            ("дата", report.date.add(row.event_date, parsed.event_date, row.event_date == parsed.event_date),
             row.event_date, parsed.event_date),
            ("конец", report.end_date.add(row.end_date, parsed.end_date, row.end_date == parsed.end_date),
             row.end_date, parsed.end_date),
            ("время", report.time.add(row.start_time, parsed.start_time, row.start_time == parsed.start_time),
             row.start_time, parsed.start_time),
            ("место", report.place.add(row.location, parsed.location, same_place(row.location, parsed.location)),
             row.location, parsed.location),
            ("категория", report.category.add(row.category, parsed.category, row.category == parsed.category),
             row.category, parsed.category),
        ]
        if parsed.event_date and parsed.category:
            report.published += 1
            if parsed.event_date != row.event_date:
                report.published_wrong_date.append(
                    f"{row.link}: опубликовано с датой {parsed.event_date}, верно — {_show(row.event_date)}"
                )
        for name, verdict, expected, got in verdicts:
            if verdict != "верно":
                report.mismatches.append(
                    f"{row.link} | {name}: {verdict} | эталон: {_show(expected)} | разбор: {_show(got)}"
                )
    return report


# Вывод

def _line(name: str, result: FieldResult) -> str:
    return (f"{name:<6} {result.correct:>3} из {result.total:<3} {result.share:>6.1%}   "
            f"не нашёл {result.missed}, ошибся {result.wrong}, лишнее {result.invented}")


def decision(report: Report) -> str:
    worst = min(report.date.share, report.place.share)
    if worst < MANUAL_EDIT_BELOW:
        return (f"Р-04: доля верных дат или мест ниже {MANUAL_EDIT_BELOW:.0%} — нужна ручная правка "
                f"даты, времени и места в админке (ФТ-12)")
    if worst < TARGET:
        return (f"Р-04: ручная правка не обязательна, но до требования {TARGET:.0%} (НФТ-04) "
                f"разбор нужно доработать")
    return f"Р-04: снят, дата и место верны не реже чем в {TARGET:.0%} случаев"


def print_report(report: Report, total: int) -> None:
    events = report.date.total
    print(f"Объявлений: {total}, из них анонсов мероприятий: {events}, не анонсов: {report.not_events}")
    print(_line("Дата", report.date))
    print(_line("Конец", report.end_date))
    print(_line("Время", report.time))
    print(_line("Место", report.place))
    print(_line("Катег.", report.category))
    print(f"Сборщик опубликовал бы сразу (есть дата и категория): {report.published} из {events}, "
          f"из них с неверной датой: {len(report.published_wrong_date)}. "
          f"Ушли бы администратору: {events - report.published}")
    print(f"Не анонсы, у которых разбор нашёл дату: {len(report.not_events_with_date)} из {report.not_events}")
    print(f"Падений разбора: {len(report.crashes)}")
    print(decision(report))
    for title, lines in (("Падения", report.crashes), ("Опубликовано с неверной датой", report.published_wrong_date),
                         ("Расхождения", report.mismatches), ("Не анонсы с датой", report.not_events_with_date)):
        if lines:
            print(f"\n{title}:")
            for line in lines:
                print(f"  {line}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Проверка разбора объявлений на эталоне")
    parser.add_argument("--csv", type=Path, default=REFERENCE, help="Эталон в формате data/README.md")
    args = parser.parse_args(argv)
    rows = load_reference(args.csv)
    print_report(evaluate(rows), len(rows))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # консоль Windows по умолчанию не в UTF-8
    main()
