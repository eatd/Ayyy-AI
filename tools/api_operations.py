from .base import ToolDefinition
from typing import Dict
import aiohttp

async def call_external_api(url: str, method: str, headers: Dict = None, 
                          data: Dict = None) -> Dict:
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers, json=data) as resp:
            return {
                "status": resp.status,
                "data": await resp.json()
            }

API_TOOLS = [
    ToolDefinition(
        name="call_external_api",
        description="Make HTTP requests to external APIs",
        parameters={
            "url": {
                "type": "string",
                "description": "API endpoint URL"
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE"],
                "description": "HTTP method"
            },
            "headers": {
                "type": "object",
                "description": "Request headers",
                "required": False
            },
            "data": {
                "type": "object",
                "description": "Request body data",
                "required": False
            }
        },
        implementation=call_external_api
    )
]
