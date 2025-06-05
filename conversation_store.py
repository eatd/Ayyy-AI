from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any


def load_history(path: str) -> List[Dict[str, Any]]:
    file = Path(path)
    if not file.exists():
        return []
    try:
        return json.loads(file.read_text())
    except Exception:
        return []


def save_history(path: str, history: List[Dict[str, Any]]) -> None:
    file = Path(path)
    file.write_text(json.dumps(history, indent=2))
