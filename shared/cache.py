import asyncio
from typing import Any

class SharedCache:
    def __init__(self):
        self._data: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._data[key] = value

    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            return self._data.get(key, default)

    async def get_all(self) -> dict:
        async with self._lock:
            return dict(self._data)

cache = SharedCache()