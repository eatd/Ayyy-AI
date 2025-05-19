# tools/file_operations.py
from pathlib import Path
from .base import ToolDefinition

async def read_file(file_path: str) -> str:
    return Path(file_path).read_text()

async def write_file(file_path: str, content: str) -> str:
    Path(file_path).write_text(content)
    return f"Written to {file_path}"



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
