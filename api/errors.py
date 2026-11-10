"""Ошибки API в одном формате и на русском.

Любая ошибка в данных запроса — 422 и список в detail, как у FastAPI:

    {"detail": [{"loc": ["body", "event_date"], "msg": "Дата мероприятия уже прошла", "type": "value_error"}]}

По последнему элементу loc фронтенд понимает, у какого поля формы показать текст.
"""
import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = logging.getLogger("api")

# Тексты для типов ошибок pydantic. В фигурных скобках — значения из ctx ошибки
MESSAGES = {
    "missing": "Обязательное поле",
    "string_type": "Нужен текст",
    "string_too_short": "Слишком коротко: нужно не меньше {min_length} символов",
    "string_too_long": "Слишком длинно: можно не больше {max_length} символов",
    "date_type": "Дата в формате ГГГГ-ММ-ДД",
    "date_parsing": "Дата в формате ГГГГ-ММ-ДД",
    "date_from_datetime_parsing": "Дата в формате ГГГГ-ММ-ДД",
    "date_from_datetime_inexact": "Дата в формате ГГГГ-ММ-ДД",
    "time_type": "Время в формате ЧЧ:ММ",
    "time_parsing": "Время в формате ЧЧ:ММ",
    "int_type": "Нужно целое число",
    "int_parsing": "Нужно целое число",
    "greater_than_equal": "Нужно число не меньше {ge}",
    "less_than_equal": "Нужно число не больше {le}",
    "json_invalid": "В теле запроса ошибка JSON",
    "model_attributes_type": "Тело запроса должно быть объектом JSON",
}


def invalid(loc: tuple[str, ...], msg: str) -> RequestValidationError:
    """Ошибка проверки, которую нашли уже в коде запроса: raise invalid(("body", "category"), "...")."""
    return RequestValidationError([{"type": "value_error", "loc": loc, "msg": msg}])


def _message(error: dict) -> str:
    ctx = error.get("ctx") or {}
    if error["type"] == "value_error" and "error" in ctx:
        # Текст из наших валидаторов в схемах, без приставки «Value error, »
        return str(ctx["error"])
    template = MESSAGES.get(error["type"])
    if template is None:
        return error["msg"]
    try:
        return template.format(**ctx)
    except (KeyError, IndexError):
        return error["msg"]


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # input не возвращаем: в нём может быть контакт автора заявки
    detail = [{"loc": list(e["loc"]), "msg": _message(e), "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": detail})


async def database_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Ошибка базы данных на %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={"detail": "База данных недоступна или не создана. Создать: python -m db.init_db"},
    )
