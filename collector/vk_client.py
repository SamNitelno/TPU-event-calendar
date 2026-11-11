"""Тонкая обёртка над wall.get. Никакой бизнес-логики — только HTTP, паузы и повторы."""
import os
import time

import httpx

API_URL = "https://api.vk.com/method/wall.get"
# 6 — слишком много запросов в секунду, 10 — внутренняя ошибка ВК: стоит повторить
RETRY_CODES = {6, 10}
RETRIES = 3


class VkError(RuntimeError):
    """ВК вернул error в теле ответа (ключ, лимиты, приватность)."""

    def __init__(self, code: int | None, message: str):
        super().__init__(f"VK error {code}: {message}")
        self.code = code


class VkClient:
    """Клиент ВК. Между запросами держит паузу: лимит метода — 3 запроса в секунду."""

    def __init__(self, token: str | None = None, version: str | None = None, min_interval: float = 0.34):
        self.token = token or os.environ.get("VK_TOKEN")
        if not self.token:
            raise VkError(None, "Не задан VK_TOKEN: положите его в .env или передайте в VkClient")
        self.version = version or os.environ.get("VK_API_VERSION", "5.199")
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def _call(self, params: dict) -> dict:
        for attempt in range(1, RETRIES + 1):
            self._throttle()
            # POST, а не GET: ключ уходит в теле запроса и не попадает в адрес,
            # а значит, и в тексты ошибок и логи
            response = httpx.post(API_URL, data={**params, "access_token": self.token, "v": self.version},
                                  timeout=15)
            response.raise_for_status()
            data = response.json()
            if "error" not in data:
                return data["response"]
            error = VkError(data["error"].get("error_code"), data["error"].get("error_msg", ""))
            if error.code not in RETRY_CODES or attempt == RETRIES:
                raise error
            time.sleep(attempt)
        raise AssertionError("unreachable")

    def get_posts(self, owner_id: int, count: int = 50, offset: int = 0) -> list[dict]:
        """Посты самого сообщества (без предложенных и чужих). owner_id отрицательный, как в vk_communities."""
        return self._call({"owner_id": owner_id, "count": count, "offset": offset, "filter": "owner"})["items"]

    def get_posts_paged(self, owner_id: int, total: int = 100, page_size: int = 100) -> list[dict]:
        """Несколько страниц подряд, по 100 — больше wall.get не отдаёт. Для первого наполнения базы."""
        posts: list[dict] = []
        for offset in range(0, total, page_size):
            batch = self.get_posts(owner_id, count=min(page_size, total - offset), offset=offset)
            posts.extend(batch)
            if len(batch) < min(page_size, total - offset):
                break
        return posts
