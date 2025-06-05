from .base import ToolRegistry, ToolDefinition
from .file_operations import FILE_TOOLS
# Optional tool modules. They may not exist in every deployment.
try:
    from .system_tools import SYSTEM_TOOLS
except Exception:
    SYSTEM_TOOLS = []

# Web-related tools (e.g., fetching URLs). Older versions expected browser_tools.
try:
    from .web_operations import WEB_TOOLS
except Exception:
    WEB_TOOLS = []

try:
    from .vision_tools import IMAGE_TOOLS
except Exception:
    IMAGE_TOOLS = []

try:
    from .embedding_tools import DATABASE_TOOLS
except Exception:
    DATABASE_TOOLS = []

try:
    from .api_tools import API_TOOLS
except Exception:
    API_TOOLS = []

# In a real application, you might want to add logging here
# from utils import get_configured_logger
# logger = get_configured_logger(__name__)

def initialize_tool_registry() -> ToolRegistry:
    """
    Creates and populates the ToolRegistry with all available tools.
    """
    # logger.info("Initializing the central ToolRegistry...")
    master_registry = ToolRegistry()

    all_tool_lists = [
        FILE_TOOLS,
        SYSTEM_TOOLS,
        WEB_TOOLS,
        IMAGE_TOOLS,
        DATABASE_TOOLS,
        API_TOOLS,
    ]

    for tool_list in all_tool_lists:
        for tool_def in tool_list or []:
            if isinstance(tool_def, ToolDefinition):
                master_registry.register(tool_def)
    
    # registered_tool_names = list(master_registry._tools.keys())
    # logger.info(
    #     f"ToolRegistry initialization complete. {len(registered_tool_names)} tools registered: "
    #     f"{', '.join(registered_tool_names) if registered_tool_names else 'None'}"
    # )
    return master_registry

__all__ = [
    "initialize_tool_registry",
    "ToolRegistry",
    "ToolDefinition",
    "FILE_TOOLS",
    "SYSTEM_TOOLS",
    "WEB_TOOLS",
    "IMAGE_TOOLS",
    "DATABASE_TOOLS",
    "API_TOOLS",
]
