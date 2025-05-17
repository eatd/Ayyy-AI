# tools/system_operations.py
from base import ToolDefinition
import psutil
from utils import Dict, Any
import platform


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