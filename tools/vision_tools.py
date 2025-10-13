# tools/vision_tools.py
from __future__ import annotations
import io
import base64
import urllib.request
from typing import Optional, Dict, Any

from .base import ToolDefinition
from PIL import Image
import pyautogui  # For screenshots

async def process_image(image_path: str, operation: str) -> str:
    """
    Process an image by resizing or converting to grayscale.
    This is a simple image manipulation tool.
    """
    img = Image.open(image_path)
    if operation == "resize":
        img = img.resize((800, 600))
    elif operation == "grayscale":
        img = img.convert('L')
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

async def analyze_image(
    file_path: Optional[str] = None,
    url: Optional[str] = None,
    take_screenshot: bool = False
) -> Dict[str, Any]:
    """
    Analyzes an image from a file, a URL, or a screenshot.
    The tool will return a base64 encoded string of the image.
    This special output will be handled by the main assistant loop to be sent to the vision model.
    """
    # Validate that exactly one argument is provided
    if sum(arg is not None and arg is not False for arg in [file_path, url, take_screenshot]) != 1:
        raise ValueError("Please provide exactly one of 'file_path', 'url', or 'take_screenshot'.")

    img = None
    try:
        if take_screenshot:
            # This will capture the primary screen.
            img = pyautogui.screenshot()
        elif url:
            with urllib.request.urlopen(url) as response:
                image_data = response.read()
            img = Image.open(io.BytesIO(image_data))
        elif file_path:
            img = Image.open(file_path)

        if img is None:
            raise ValueError("Could not load the image.")

        # Convert image to a format that's safe for all models (e.g., PNG) and encode it
        buffered = io.BytesIO()
        # Convert to RGB to remove alpha channel, which can cause issues
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # The dictionary structure is important for the main loop to identify and handle this output.
        return {
            "type": "image_analysis",
            "image_base64": img_base64,
            "text": "Image loaded successfully. The assistant will now analyze the image."
        }

    except Exception as e:
        # Return a structured error that the main loop can potentially handle
        return {
            "type": "error",
            "message": f"Failed to analyze image: {str(e)}"
        }

IMAGE_TOOLS = [
    ToolDefinition(
        name="process_image",
        description="Process an image by resizing or converting to grayscale.",
        parameters={
            "image_path": {
                "type": "string",
                "description": "Path to the image file",
                "required": True
            },
            "operation": {
                "type": "string",
                "description": "Operation to perform on the image (resize or grayscale)",
                "required": True,
                "enum": ["resize", "grayscale"]
            }
        },
        implementation=process_image
    ),
    ToolDefinition(
        name="analyze_image",
        description="Analyzes an image from a file path, a URL, or by taking a screenshot. The assistant can then 'see' this image. Use only one parameter at a time.",
        parameters={
            "file_path": {
                "type": "string",
                "description": "The local path to the image file.",
                "required": False
            },
            "url": {
                "type": "string",
                "description": "The URL of the image to analyze.",
                "required": False
            },
            "take_screenshot": {
                "type": "boolean",
                "description": "Set to true to capture the current screen.",
                "required": False
            }
        },
        implementation=analyze_image
    )
]