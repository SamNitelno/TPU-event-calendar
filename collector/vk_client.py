"""Тонкая обёртка над wall.get. Никакой бизнес-логики — только HTTP и троттлинг."""
import os
import time

import httpx

API_URL = "https://api.vk.com/method/wall.get"


class VkError(RuntimeError):
    """ВК вернул error в теле ответа (токен, лимиты, приватность)."""


class VkClient:
    """Клиент ВК. Между запросами держит паузу: лимит метода — 3 запроса в секунду."""

    def __init__(self, token: str | None = None, version: str | None = None, min_interval: float = 0.34):
        self.token = token or os.environ.get("VK_TOKEN")
        if not self.token:
            raise VkError("Не задан VK_TOKEN: положите его в .env или передайте в VkClient")
        self.version = version or os.environ.get("VK_API_VERSION", "5.199")
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def get_posts(self, owner_id: int, count: int = 50, offset: int = 0) -> list[dict]:
        """Посты сообщества. owner_id отрицательный, как в vk_communities.owner_id."""
        self._throttle()
        response = httpx.get(
            API_URL,
            params={
                "owner_id": owner_id,
                "count": count,
                "offset": offset,
                "access_token": self.token,
                "v": self.version,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            err = data["error"]
            raise VkError(f"VK error {err.get('error_code')}: {err.get('error_msg')}")
        return data["response"]["items"]

    def get_posts_paged(self, owner_id: int, total: int = 100, page_size: int = 50) -> list[dict]:
        """Несколько страниц подряд. Пригодится для первого наполнения базы."""
        posts: list[dict] = []
        for offset in range(0, total, page_size):
            batch = self.get_posts(owner_id, count=min(page_size, total - offset), offset=offset)
            posts.extend(batch)
            if len(batch) < page_size:
                break
        return posts