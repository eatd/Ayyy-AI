from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any


def load_history(path: str) -> List[Dict[str, Any]]:
    """Load conversation history from a JSON file."""
    file = Path(path)
    if not file.exists():
        return []
    try:
        content = file.read_text(encoding='utf-8')
        return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return []


def save_history(path: str, history: List[Dict[str, Any]]) -> None:
    """Save conversation history to a JSON file."""
    file = Path(path)
    try:
        content = json.dumps(history, indent=2, ensure_ascii=False)
        file.write_text(content, encoding='utf-8')
    except OSError as e:
        # If we can't save history, log it but don't crash
        print(f"Warning: Could not save conversation history to {path}: {e}")
