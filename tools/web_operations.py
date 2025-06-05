from __future__ import annotations

import asyncio
from urllib.request import urlopen

from .base import ToolDefinition


async def fetch_url(url: str) -> str:
    def _fetch() -> str:
        with urlopen(url) as resp:
            return resp.read().decode()

    return await asyncio.to_thread(_fetch)


WEB_TOOLS = [
    ToolDefinition(
        name="fetch_url",
        description="Fetch the contents of a URL via HTTP GET",
        parameters={"url": {"type": "string", "description": "URL to fetch"}},
        implementation=fetch_url,
    )
]
