# tools/__init__.py
from .base import ToolRegistry
from .file_operations import FILE_TOOLS
from .web_operations import WEB_TOOLS
# Import other tool modules as needed

def create_registry() -> ToolRegistry:
    registry = ToolRegistry()
    
    # Register all tools
    for tool in FILE_TOOLS:
        registry.register(tool)
    for tool in WEB_TOOLS:
        registry.register(tool)
    # Register other tool groups
    
    return registry
