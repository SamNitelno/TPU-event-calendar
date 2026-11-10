"""Раздача собранного фронтенда (web/dist) тем же сервером, что и API.

Сайт и API живут на одном адресе, поэтому запросы /api/... не упираются в CORS,
а прямые ссылки вида /event/12, /submit и /admin открывают приложение (index.html).
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

# Файлы в assets/ собираются с хешем в имени, их можно кэшировать надолго (НФТ-01)
ASSETS_CACHE = {"Cache-Control": "public, max-age=31536000, immutable"}


def mount_frontend(app: FastAPI, dist: Path) -> None:
    """Подключает фронтенд, если он собран (npm run build). Иначе / ведёт на описание API."""
    root = Path(dist).resolve()
    index = root / "index.html"

    if not index.is_file():
        @app.get("/", include_in_schema=False)
        def no_frontend():
            return RedirectResponse("/docs")

        return

    # Регистрируется последним: /api/..., /docs и /openapi.json объявлены раньше и срабатывают первыми
    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Нет такого запроса API")
        file = (root / path).resolve()
        if path and file.is_file() and file.is_relative_to(root):
            return FileResponse(file, headers=ASSETS_CACHE if path.startswith("assets/") else None)
        # Остальные адреса — страницы приложения, маршрут разбирает сам фронтенд
        return FileResponse(index)
