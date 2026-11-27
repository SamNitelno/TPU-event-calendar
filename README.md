# Календарь мероприятий ТПУ

Веб-сервис для студентов, студенческих организаций и клубов. Он сам собирает анонсы мероприятий из сообществ ВКонтакте, извлекает из текста дату, время и место и показывает всё одной лентой с фильтрами по категориям.

- Доска задач: [YouGile](https://ru.yougile.com/team/2f7e58440237/Календарь-мероприятий)
- Макет: https://event-calendar-tpu.poehali.ws/
- Как мы работаем с репозиторием: [CONTRIBUTING.md](CONTRIBUTING.md)
- Как пользоваться Git: [.github/GIT_GUIDE.md](.github/GIT_GUIDE.md)
- Карты проекта и инструкции: [docs/README.md](docs/README.md)
- Формат события (общий для всех частей): [docs/event_format.md](docs/event_format.md)

## Как устроен сервис

React запрашивает афишу и отправляет заявки в FastAPI. Сборщик ВКонтакте запускается отдельно, а его результаты и заявки хранятся в общей базе. Связи компонентов, стек и путь заявки до публикации показаны в [архитектуре](docs/architecture.md).

## Структура репозитория

| Папка        | Что в ней                                                              | Отвечает     |
| ------------ | ---------------------------------------------------------------------- | ------------ |
| `docs/`      | Формат события, описание API, сообщества, макеты, отчёты проверок      | Все          |
| `data/`      | Эталонная выборка 50 объявлений                                        | Шехина К.    |
| `db/`        | Таблицы, подключение к базе, создание и наполнение базы                | Шехина К.    |
| `collector/` | Загрузка постов из ВК, разбор даты, времени и места, проверка качества | Шехина К.    |
| `api/`       | FastAPI: запросы `/api/...` и выдача страниц                           | Дугарова А.  |
| `web/`       | React-приложение, страницы и стили                                                | Селенкова Е. |

В каждой папке есть свой README: что туда класть и как запускать.

## Как запустить

Все команды выполняются из корня репозитория.

```bash
py -3.12 -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install --require-hashes -r requirements-dev.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env — и вписать ключ VK
python -m db.init_db             # создать таблицы, категории и сообщества
python -m db.seed_test           # тестовые мероприятия — только для разработки
python -m uvicorn api.main:app --reload  # API: http://127.0.0.1:8000/docs
python -m collector.run          # загрузить новые посты из ВК
python -m pytest                 # тесты
```

Фронтенд запускается во втором терминале:

```bash
cd web
npm ci
npm run dev                     # http://127.0.0.1:5173, запросы /api проксируются в FastAPI
```

Для раздачи сайта из FastAPI выполните `npm run build` из `web` и перезапустите API. Сборка создаётся в `web/dist`, после этого сайт доступен на http://127.0.0.1:8000. Для dev и build нужен Node.js 22.x (не ниже 22.22.2). Подробности, переменные и проверки — в [web/README.md](web/README.md).

Запросы API и подключение фронтенда — в [docs/api.md](docs/api.md).

## Production и администратор

Полная инструкция с названиями пунктов Vercel, созданием Neon, переменными и ежедневным сбором: [docs/deployment.md](docs/deployment.md).

Администратор создаётся отдельно: `python -m db.create_admin semyon`. Ввод пароля скрыт; пароль по умолчанию отсутствует. Вход и очередь проверки — `/admin`.

Проверки перед PR: `ruff check .`, `ruff format --check .`, `python -m pytest`, `npm --prefix web run lint`, `npm --prefix web test`, `npm --prefix web run build`. В GitHub Actions эти проверки выполняются с Python 3.12 и Node.js 22, тесты сервера — на SQLite и PostgreSQL 16.

Production-манифест Vercel: `pyproject.toml` + `uv.lock`. CI отдельно выполняет `uv sync --locked --no-dev` и импорт приложения в чистом окружении. При обновлении Python-зависимостей синхронизируйте манифест, uv.lock и requirements-файлы; `scripts/check_runtime.py` проверяет совпадение основных версий.
