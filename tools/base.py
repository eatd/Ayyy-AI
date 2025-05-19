# tools/base.py
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, Callable, Awaitable, List
import logging

@dataclass
class ToolDefinition:
    """
    Represents a tool definition with its name, description, parameters, and implementation.
    """
    
    name: str
    description: str
    parameters: Dict[str, Dict[str, Any]]
    implementation: Callable[..., Awaitable[Any]]
    required_fields: List[str] = None

    def __post_init__(self):
        self.validate_parameters()
        self.validate_implementation()

    def validate_parameters(self):
        if not isinstance(self.parameters, dict):
            raise ValueError("Parameters must be a dictionary")
        for param_name, param_def in self.parameters.items():
            if not isinstance(param_name, str):
                raise ValueError(f"Parameter name '{param_name}' must be a string")
            if not isinstance(param_def, dict):
                raise ValueError(f"Parameter definition for '{param_name}' must be a dictionary")

    def validate_implementation(self):
        if not callable(self.implementation):
            raise ValueError("Implementation must be a callable function")
            

class ToolRegistry:
    """
    A registry for managing tool definitions, allowing registration and execution of tools.
    """
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self.logger.info("ToolRegistry initialized")
    
    
    def register(self, tool: ToolDefinition) -> None:
        """
        Register a new tool definition.
        If a tool with the same name already exists, it will log a warning and skip registration.
        """
        self.logger.info(f"Registering tool: {tool.name}")
        tool.required_fields = [k for k, v in tool.parameters.items() if v.get("required", True)]
        self._tools[tool.name] = tool
        self.logger.warning(f"Tool '{tool.name}' is already registered. Registration skipped.")
        return


    def get_lm_studio_schemas(self) -> List[Dict[str, Any]]:
        """
        Get the schemas for all registered tools in a format compatible with LM Studio.
        """
        return [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                    "properties": tool.parameters,
                    "required": [k for k, v in tool.parameters.items() 
                                if v.get("required", True)]
                }
            }
            for tool in self._tools.values()
        ]
        
    
    async def execute(self, name: str, **kwargs) -> Any:
        # Execute async and sync implementations
        tool = self._tools.get(name)
        if not tool:
            if callable(tool.implementation):
                if asyncio.iscoroutinefunction(tool.implementation):
                    return await tool.implementation(**kwargs)
                return tool.implementation(**kwargs)
            raise ValueError(f"Implementation for tool '{name}' is not callable")
        
        return await tool.implementation(**kwargs)