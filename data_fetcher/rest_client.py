import asyncio
from typing import Any, Dict, Optional, Callable
import aiohttp
from loguru import logger

class RESTClient:
    def __init__(self, base_url: str, timeout: int = 10, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None,
                  transform: Optional[Callable[[Any], Any]] = None) -> Any:
        await self._ensure()
        url = f"{self.base_url}/{path.lstrip('/')}"
        for attempt in range(1, self.max_retries + 1):
            try:
                async with self._session.get(url, params=params, timeout=self.timeout) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return transform(data) if transform else data
            except Exception as e:
                wait = min(30, attempt * 0.75)
                logger.warning(f"REST GET {url} failed (attempt {attempt}): {e}; retry in {wait:.2f}s")
                await asyncio.sleep(wait)
        raise RuntimeError(f"Failed GET after {self.max_retries} attempts: {url}")

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
