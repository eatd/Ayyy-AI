# tools/file_operations.py
from __future__ import annotations

from pathlib import Path
from .base import ToolDefinition


async def read_file(file_path: str) -> str:
    """Read content from a file."""
    try:
        return Path(file_path).read_text(encoding='utf-8')
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found."
    except PermissionError:
        return f"Error: Permission denied reading '{file_path}'."
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


async def write_file(file_path: str, content: str) -> str:
    """Write content to a file."""
    try:
        Path(file_path).write_text(content, encoding='utf-8')
        return f"Successfully written to {file_path}"
    except PermissionError:
        return f"Error: Permission denied writing to '{file_path}'."
    except Exception as e:
        return f"Error writing to file '{file_path}': {str(e)}"


FILE_TOOLS = [
    ToolDefinition(
        name="read_file",
        description="Read content from a file",
        parameters={
            "file_path": {
                "type": "string",
                "description": "Path to the file"
            }
        },
        implementation=read_file
    ),
    ToolDefinition(
        name="write_file",
        description="Write content to a file",
        parameters={
            "file_path": {
                "type": "string",
                "description": "Path to the file"
            },
            "content": {
                "type": "string",
                "description": "Content to write"
            }
        },
        implementation=write_file
    )
]
