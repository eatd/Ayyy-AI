from __future__ import annotations

import json
from typing import Dict, Any, Optional
import asyncio

from .base import ToolDefinition

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


async def make_api_request(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, 
                          data: Optional[str] = None, timeout: int = 30) -> str:
    """Make an HTTP API request."""
    if not AIOHTTP_AVAILABLE:
        return "Error: aiohttp library is required for API requests. Please install it."
    
    headers = headers or {}
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.request(method, url, headers=headers, data=data) as response:
                content = await response.text()
                return json.dumps({
                    "status": response.status,
                    "headers": dict(response.headers),
                    "content": content
                }, indent=2)
    except Exception as e:
        return f"Error making API request: {str(e)}"


# Export API tools
API_TOOLS = [
    ToolDefinition(
        name="make_api_request",
        description="Make an HTTP API request",
        parameters={
            "url": {"type": "string", "description": "API endpoint URL"},
            "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)", "required": False},
            "headers": {"type": "object", "description": "HTTP headers", "required": False},
            "data": {"type": "string", "description": "Request body data", "required": False},
            "timeout": {"type": "integer", "description": "Request timeout in seconds", "required": False},
        },
        implementation=make_api_request,
    ),
]