from .base import ToolRegistry, ToolDefinition
from .file_operations import FILE_TOOLS
from .system_tools import SYSTEM_TOOLS # Assuming this is defined in system_operations.py
from .browser_tools import WEB_TOOLS
from .vision_tools import IMAGE_TOOLS
from .embedding_tools import DATABASE_TOOLS # Assuming this is defined in database_operations.py
from .api_tools import API_TOOLS

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
        if tool_list: # Ensure the list is not None or empty
            for tool_def in tool_list:
                if isinstance(tool_def, ToolDefinition):
                    master_registry.register(tool_def)
                # else:
                    # logger.warning(f"Found an item in a tool list that is not a ToolDefinition: {tool_def}")
    
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
