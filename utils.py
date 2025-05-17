import logging
import json
from typing import Any, Dict, Union, Callable
from functools import wraps


def log_execution(func: Callable) -> Callable:
    """Decorator to log function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.info(f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} completed with result: {result}")
        return result
    return wrapper


def exception_handler(func: Callable) -> Callable:
    """Decorator to handle exceptions in tool functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {"status": "error", "message": str(e)}
    return wrapper


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
            raise ValueError(f"Invalid JSON string: {e}")
    elif isinstance(data, dict):
        return data
    else:
        raise TypeError("Data must be a JSON string or a dictionary.")
    
    