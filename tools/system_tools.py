from __future__ import annotations

import asyncio
from subprocess import PIPE
import sys

from .base import ToolDefinition


async def run_command(command: str, timeout: int = 20) -> str:
    """Run a shell command and return its output."""
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=PIPE,
        stderr=PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return "Command timed out"
    output = stdout.decode().strip()
    err = stderr.decode().strip()
    if err:
        output += f"\nERR: {err}"
    return output or "No output"


async def run_python(code: str, timeout: int = 20) -> str:
    """Execute Python code using the system interpreter."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-u",
        "-",
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(code.encode()), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return "Execution timed out"
    output = stdout.decode().strip()
    err = stderr.decode().strip()
    if err:
        output += f"\nERR: {err}"
    return output or "No output"


SYSTEM_TOOLS = [
    ToolDefinition(
        name="run_command",
        description="Execute a shell command and return its output",
        parameters={
            "command": {"type": "string", "description": "Command to execute"},
            "timeout": {"type": "integer", "description": "Seconds before timeout", "required": False},
        },
        implementation=run_command,
    )
    ,
    ToolDefinition(
        name="run_python",
        description="Execute Python code and return its output",
        parameters={
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {"type": "integer", "description": "Seconds before timeout", "required": False},
        },
        implementation=run_python,
    )
]
