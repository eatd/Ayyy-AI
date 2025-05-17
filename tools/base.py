# tools/base.py
from dataclasses import dataclass
from typing import Dict, Any, Callable, Awaitable, List
import logging

@dataclass

class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Dict[str, Any]]
    implementation: Callable[..., Awaitable[Any]]

    def __post_init__(self):
        if not isinstance(self.parameters, dict):
            raise ValueError("Parameters must be a dictionary")
        if not callable(self.implementation):
            raise ValueError("Implementation must be a callable function")
        
        for param_name, param_def in self.parameters.items():
            if not isinstance(param_name, str):
                raise ValueError(f"Parameter name '{param_name}' must be a string")
            if not isinstance(param_def, dict):
                raise ValueError(f"Parameter definition for '{param_name}' must be a dictionary")
            

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self.logger = logging.getLogger(__name__)

    def register(self, tool: ToolDefinition) -> None:
        self.logger.info(f"Registering tool: {tool.name}")
        self._tools[tool.name] = tool

    def get_lm_studio_schemas(self) -> List[Dict[str, Any]]:
        return [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": [k for k, v in tool.parameters.items() 
                               if v.get("required", True)]
                }
            }
        } for tool in self._tools.values()]

    async def execute(self, name: str, **kwargs) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return await tool.implementation(**kwargs)
