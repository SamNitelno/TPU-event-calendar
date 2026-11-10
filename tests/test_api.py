from datetime import time, timedelta

import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import CORS_ORIGINS, app
from db.database import get_db, make_engine
from db.models import Event


def ids(response):
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


# Лента

def test_feed_shows_only_published_upcoming_events(client, add_event, today):
    ongoing = add_event(event_date=today - timedelta(days=2), end_date=today + timedelta(days=1))
    current = add_event(event_date=today)
    add_event(event_date=today - timedelta(days=1))  # уже прошло
    add_event(status="pending", event_date=today + timedelta(days=1))
    add_event(status="rejected", event_date=today + timedelta(days=1))
    add_event(status="pending", event_date=None)  # дату не нашли
    assert ids(client.get("/api/events")) == [ongoing, current]


def test_feed_is_sorted_by_date_then_time_and_events_without_time_go_last(client, add_event, today):
    tomorrow = today + timedelta(days=1)
    evening = add_event(event_date=tomorrow, start_time=time(18, 0))
    no_time = add_event(event_date=tomorrow)
    morning = add_event(event_date=tomorrow, start_time=time(10, 0))
    first = add_event(event_date=today, start_time=time(20, 0))
    assert ids(client.get("/api/events")) == [first, morning, evening, no_time]


def test_feed_response_matches_event_format(client, add_event, today):
    event_id = add_event(
        title="Мастер-класс по алтимату",
        organizer="Спортклуб «Сибирские львы»",
        start_time=time(18, 0),
        location="ул. Карпова, 4",
        original_post_link="https://vk.com/wall-44845822_52494",
        description="Полный текст поста",
        contact="test@example.com",
    )
    assert client.get("/api/events").json() == {
        "items": [{
            "id": event_id,
            "title": "Мастер-класс по алтимату",
            "organizer": "Спортклуб «Сибирские львы»",
            "category": {"slug": "sport", "name": "Спорт"},
            "source": "vk",
            "event_date": today.isoformat(),
            "end_date": None,
            "start_time": "18:00",
            "end_time": None,
            "location": "ул. Карпова, 4",
            "original_post_link": "https://vk.com/wall-44845822_52494",
        }],
        "page": 1,
        "per_page": 20,
        "total": 1,
    }


def test_filter_by_category(client, add_event):
    sport = add_event(category="sport")
    add_event(category="science")
    assert ids(client.get("/api/events", params={"category": "sport"})) == [sport]
    assert ids(client.get("/api/events", params={"category": "unknown"})) == []


def test_date_range_includes_multi_day_events_that_overlap_it(client, add_event, today):
    def day(n):
        return today + timedelta(days=n)

    long_event = add_event(event_date=day(1), end_date=day(5))
    add_event(event_date=day(2))
    add_event(event_date=day(10))
    params = {"date_from": day(3).isoformat(), "date_to": day(7).isoformat()}
    assert ids(client.get("/api/events", params=params)) == [long_event]


def test_date_from_returns_past_events_for_calendar(client, add_event, today):
    past = add_event(event_date=today - timedelta(days=5))
    assert ids(client.get("/api/events")) == []
    month_start = (today - timedelta(days=10)).isoformat()
    assert ids(client.get("/api/events", params={"date_from": month_start})) == [past]


def test_date_from_after_date_to_is_an_error(client, today):
    params = {"date_from": (today + timedelta(days=2)).isoformat(), "date_to": today.isoformat()}
    assert client.get("/api/events", params=params).status_code == 422


def test_search_in_title_and_description_ignores_case(client, add_event):
    tournament = add_event(title="Турнир по баскетболу")
    ultimate = add_event(title="Мастер-класс", description="Учим бросать диск фрисби")
    add_event(title="Лекция")
    assert ids(client.get("/api/events", params={"q": "турнир"})) == [tournament]
    assert ids(client.get("/api/events", params={"q": "ФРИСБИ"})) == [ultimate]
    assert ids(client.get("/api/events", params={"q": "%"})) == []


def test_pagination(client, add_event):
    for _ in range(25):
        add_event()
    first = client.get("/api/events").json()
    second = client.get("/api/events", params={"page": 2}).json()
    assert (len(first["items"]), len(second["items"])) == (20, 5)
    assert first["total"] == second["total"] == 25
    assert client.get("/api/events", params={"page": 0}).status_code == 422


# Одно мероприятие

def test_event_detail_adds_description_and_image_but_not_contact(client, add_event):
    event_id = add_event(
        start_time=time(9, 30),
        description="Полный текст поста",
        image_url="https://example.com/poster.jpg",
        contact="test@example.com",
    )
    body = client.get(f"/api/events/{event_id}").json()
    assert body["description"] == "Полный текст поста"
    assert body["image_url"] == "https://example.com/poster.jpg"
    assert body["start_time"] == "09:30"
    assert "contact" not in body


def test_past_event_still_opens_by_link(client, add_event, today):
    event_id = add_event(event_date=today - timedelta(days=30))
    assert client.get(f"/api/events/{event_id}").status_code == 200


def test_hidden_or_missing_event_is_404(client, add_event):
    pending = add_event(status="pending")
    rejected = add_event(status="rejected")
    for event_id in (pending, rejected, 999):
        assert client.get(f"/api/events/{event_id}").status_code == 404


# Категории

def test_categories_count_only_events_from_the_feed(client, add_event, today):
    add_event(category="sport")
    add_event(category="sport", event_date=today + timedelta(days=3))
    add_event(category="sport", event_date=today - timedelta(days=1))
    add_event(category="science", status="pending")
    body = client.get("/api/categories").json()
    assert body[0] == {"slug": "sport", "name": "Спорт", "events_count": 2}
    assert [c["slug"] for c in body] == ["sport", "science", "creativity", "volunteering", "career", "student_life"]
    assert [c["events_count"] for c in body[1:]] == [0, 0, 0, 0, 0]


# Заявки из формы

def submission(today, **fields):
    return {
        "title": "Субботник «Чистый берег»",
        "organizer": "Волонтёрский центр",
        "category": "volunteering",
        "event_date": (today + timedelta(days=5)).isoformat(),
        "start_time": "11:00",
        "contact": "test@example.com",
        **fields,
    }


def test_submission_is_saved_as_pending_and_not_shown(client, session_factory, today):
    response = client.post("/api/submissions", json=submission(today))
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    with session_factory() as db:
        event = db.get(Event, response.json()["id"])
        assert (event.source, event.status, event.contact) == ("form", "pending", "test@example.com")
    assert client.get("/api/events").json()["total"] == 0


@pytest.mark.parametrize("fields", [
    {"category": "unknown"},
    {"event_date": "2026-11-01"},  # вчера
    {"end_date": "2026-11-03"},  # раньше event_date (7 ноября)
    {"contact": ""},
    {"title": "   "},
])
def test_invalid_submission_is_rejected(client, today, fields):
    assert client.post("/api/submissions", json=submission(today, **fields)).status_code == 422


# Для фронтенда

def test_per_page_lets_calendar_take_a_month_at_once(client, add_event):
    for _ in range(25):
        add_event()
    body = client.get("/api/events", params={"per_page": 100}).json()
    assert (len(body["items"]), body["per_page"], body["total"]) == (25, 100, 25)
    for wrong in (0, 101):
        assert client.get("/api/events", params={"per_page": wrong}).status_code == 422


def test_source_tells_vk_post_from_form_submission(client, add_event):
    vk = add_event()
    form = add_event(source="form")
    assert client.get(f"/api/events/{vk}").json()["source"] == "vk"
    assert client.get(f"/api/events/{form}").json()["source"] == "form"


def test_published_event_without_category_is_not_shown(client, add_event):
    event_id = add_event(category="нет такой")
    assert ids(client.get("/api/events")) == []
    assert client.get(f"/api/events/{event_id}").status_code == 404
    assert all(c["events_count"] == 0 for c in client.get("/api/categories").json())


def field_errors(response):
    assert response.status_code == 422, response.text
    return {tuple(e["loc"]): e["msg"] for e in response.json()["detail"]}


def test_errors_point_to_the_field_and_are_in_russian(client, today):
    def post(**fields):
        return field_errors(client.post("/api/submissions", json=submission(today, **fields)))

    assert post(event_date="2026-11-01") == {("body", "event_date"): "Дата мероприятия уже прошла"}
    assert post(category="unknown") == {("body", "category"): "Неизвестная категория"}
    assert post(end_date="2026-11-03") == {("body", "end_date"): "Дата окончания раньше даты начала"}
    assert post(organizer="A") == {("body", "organizer"): "Слишком коротко: нужно не меньше 2 символов"}
    assert post(start_time="25:00") == {("body", "start_time"): "Время в формате ЧЧ:ММ"}

    body = submission(today)
    del body["title"]
    response = client.post("/api/submissions", json=body)
    assert field_errors(response) == {("body", "title"): "Обязательное поле"}
    # Введённые значения в ответ не попадают: среди них контакт автора
    assert "input" not in response.json()["detail"][0]


def test_query_errors_have_the_same_format(client, today):
    assert field_errors(client.get("/api/events", params={"date_from": "завтра"})) == {
        ("query", "date_from"): "Дата в формате ГГГГ-ММ-ДД",
    }
    params = {"date_from": (today + timedelta(days=2)).isoformat(), "date_to": today.isoformat()}
    assert field_errors(client.get("/api/events", params=params)) == {
        ("query", "date_from"): "Дата «с» позже даты «по»",
    }


def test_empty_form_fields_are_saved_as_not_specified(client, session_factory, today):
    empty = dict(end_date="", start_time="", end_time="", location="  ", original_post_link="", description="")
    response = client.post("/api/submissions", json=submission(today, **empty))
    assert response.status_code == 201, response.text
    with session_factory() as db:
        event = db.get(Event, response.json()["id"])
        saved = (event.end_date, event.start_time, event.end_time, event.location,
                 event.original_post_link, event.description)
        assert saved == (None,) * 6


def test_submission_keeps_link_to_vk_post(client, session_factory, today):
    link = "https://vk.com/wall-44845822_52494"
    response = client.post("/api/submissions", json=submission(today, original_post_link=link))
    assert response.status_code == 201, response.text
    with session_factory() as db:
        assert db.get(Event, response.json()["id"]).original_post_link == link


@pytest.mark.parametrize("link", ["https://example.com/wall-1_2", "vk.com/wall-1_2", "javascript:alert(1)"])
def test_submission_link_must_lead_to_vk(client, today, link):
    errors = field_errors(client.post("/api/submissions", json=submission(today, original_post_link=link)))
    assert ("body", "original_post_link") in errors


def test_end_time_must_be_after_start_within_one_day(client, today):
    same_day = submission(today, start_time="18:00", end_time="17:00")
    assert field_errors(client.post("/api/submissions", json=same_day)) == {
        ("body", "end_time"): "Время окончания должно быть позже начала",
    }
    # У многодневного мероприятия «до 10:00 последнего дня» — нормально
    multi_day = submission(today, end_date=(today + timedelta(days=7)).isoformat(), start_time="18:00", end_time="10:00")
    assert client.post("/api/submissions", json=multi_day).status_code == 201


def test_cors_lets_dev_server_of_frontend_call_api(client):
    origin = CORS_ORIGINS[0]
    response = client.get("/api/categories", headers={"Origin": origin})
    assert response.headers["access-control-allow-origin"] == origin
    preflight = client.options("/api/submissions", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert preflight.status_code == 200
    foreign = client.get("/api/categories", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" not in foreign.headers


def test_unknown_api_path_is_404(client):
    assert client.get("/api/nope").status_code == 404


# Проверка работы

def test_health_is_ok_when_database_is_ready(client):
    response = client.get("/api/health")
    assert (response.status_code, response.json()) == (200, {"status": "ok"})


def test_health_is_503_when_tables_are_not_created(client):
    engine = make_engine("sqlite://", poolclass=StaticPool)  # база без таблиц
    empty = sessionmaker(bind=engine)

    def override_get_db():
        with empty() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    response = client.get("/api/health")
    assert response.status_code == 503
    assert "python -m db.init_db" in response.json()["detail"]
    engine.dispose()
