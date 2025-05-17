# tools/web_operations.py
import aiohttp
from .base import ToolDefinition

async def fetch_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

WEB_TOOLS = [
    ToolDefinition(
        name="fetch_url",
        description="Fetch content from a URL",
        parameters={
            "url": {
                "type": "string",
                "description": "URL to fetch"
            }
        },
        implementation=fetch_url
    )
]
