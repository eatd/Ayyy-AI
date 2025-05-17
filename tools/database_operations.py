# tools/database_operations.py
import aiosqlite
from typing import List, Dict, Any
from .base import ToolDefinition
import psutil
import platform

async def query_database(query: str, database_path: str) -> List[Dict]:
    async with aiosqlite.connect(database_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        async with db.execute(query) as cursor:
            return await cursor.fetchall()

DATABASE_TOOLS = [
    ToolDefinition(
        name="query_database",
        description="Execute a SQL query on a SQLite database",
        parameters={
            "query": {
                "type": "string",
                "description": "SQL query to execute"
            },
            "database_path": {
                "type": "string",
                "description": "Path to SQLite database"
            }
        },
        implementation=query_database
    )
]

# tools/system_operations.py


async def get_system_info() -> Dict[str, Any]:
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_usage": dict(psutil.virtual_memory()._asdict()),
        "disk_usage": dict(psutil.disk_usage('/')._asdict()),
        "platform": platform.platform()
    }

SYSTEM_TOOLS = [
    ToolDefinition(
        name="get_system_info",
        description="Get system resource information",
        parameters={},
        implementation=get_system_info
    )
]