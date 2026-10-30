# db — база данных

Отвечает: Дугарова А. Ревьюер: Шехина К.

Единственное место, где описаны таблицы. `collector/` и `api/` берут модели и подключение отсюда и своих таблиц не заводят.

| Файл | Что в нём |
|---|---|
| `database.py` | Подключение к базе по `DATABASE_URL` из `.env` (`engine`, `SessionLocal`) |
| `models.py` | Таблицы SQLAlchemy: `vk_communities`, `vk_posts`, `events`, `categories`, `users`. Поля — по `docs/event_format.md` |
| `init_db.py` | Создаёт таблицы, заполняет категории и сообщества |
| `seed_test.py` | 20–30 тестовых мероприятий из `data/reference_50.csv`, часть дат сдвинута в будущее |

Запуск из корня репозитория: `python -m db.init_db`.

Правила:
- Поменяли таблицу — обновите `docs/event_format.md` в том же PR.
- Локально используется SQLite. При размещении на PostgreSQL меняется только `DATABASE_URL`.
- Пара `community_id` + `vk_post_id` уникальна: повторно загруженный пост не создаёт дубль.
