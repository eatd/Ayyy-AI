from __future__ import annotations

import logging
import json
from typing import Any, Dict, Union, Callable, TypeVar
from functools import wraps

F = TypeVar('F', bound=Callable[..., Any])


def log_execution(func: F) -> F:
    """Decorator to log function execution."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = logging.getLogger(func.__module__)
        logger.info(
            f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}"
        )
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} completed with result: {result}")
        return result
    return wrapper  # type: ignore


def exception_handler(func: F) -> F:
    """Decorator to handle exceptions in tool functions."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {"status": "error", "message": str(e)}
    return wrapper  # type: ignore


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def validate_json(data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Validate and parse JSON data."""
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}") from e
    elif isinstance(data, dict):
        return data
    else:
        raise TypeError("Data must be a JSON string or a dictionary.")
