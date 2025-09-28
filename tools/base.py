from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Awaitable, List, Union
import logging


@dataclass
class ToolDefinition:
    """
    Represents a tool definition with its name, description, parameters, and implementation.
    """
    
    name: str
    description: str
    parameters: Dict[str, Dict[str, Any]]
    implementation: Callable[..., Union[Awaitable[Any], Any]]
    required_fields: List[str] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.validate_parameters()
        self.validate_implementation()
        # Set required fields after validation
        self.required_fields = [k for k, v in self.parameters.items() if v.get("required", True)]

    def validate_parameters(self) -> None:
        """Validate parameter definitions."""
        if not isinstance(self.parameters, dict):
            raise ValueError("Parameters must be a dictionary")
        for param_name, param_def in self.parameters.items():
            if not isinstance(param_name, str):
                raise ValueError(f"Parameter name '{param_name}' must be a string")
            if not isinstance(param_def, dict):
                raise ValueError(f"Parameter definition for '{param_name}' must be a dictionary")

    def validate_implementation(self) -> None:
        """Validate tool implementation."""
        if not callable(self.implementation):
            raise ValueError("Implementation must be a callable function")
            

class ToolRegistry:
    """
    A registry for managing tool definitions, allowing registration and execution of tools.
    """
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        self.logger = logging.getLogger(__name__)
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO)
        self.logger.info("ToolRegistry initialized")
    
    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool definition."""
        self.logger.info(f"Registering tool: {tool.name}")
        if tool.name in self._tools:
            self.logger.warning(f"Tool '{tool.name}' is already registered. Skipping.")
            return
        self._tools[tool.name] = tool

    def get_lm_studio_schemas(self) -> List[Dict[str, Any]]:
        """
        Get the schemas for all registered tools in a format compatible with LM Studio.
        """
        schemas = []
        for tool in self._tools.values():
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters,
                        "required": tool.required_fields,
                    },
                },
            }
            schemas.append(schema)
        return schemas
        
    async def execute(self, name: str, **kwargs: Any) -> Any:
        """Execute a registered tool by name."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' is not registered")

        missing = [field for field in tool.required_fields if field not in kwargs]
        if missing:
            raise ValueError(
                f"Missing required arguments for '{name}': {', '.join(missing)}"
            )

        impl = tool.implementation
        if asyncio.iscoroutinefunction(impl):
            return await impl(**kwargs)
        return impl(**kwargs)
