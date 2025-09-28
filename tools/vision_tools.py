
from __future__ import annotations

# tools/image_operations.py
from .base import ToolDefinition
import io
import base64

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


async def process_image(image_path: str, operation: str) -> str:
    """Process an image by resizing or converting to grayscale."""
    if not PIL_AVAILABLE:
        return "Error: Pillow (PIL) library is required for image processing. Please install it."
    
    try:
        img = Image.open(image_path)
        
        if operation == "resize":
            img = img.resize((800, 600))
        elif operation == "grayscale":
            img = img.convert('L')
        else:
            return f"Error: Unknown operation '{operation}'. Supported operations: resize, grayscale"
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        encoded_image = base64.b64encode(buffered.getvalue()).decode()
        
        return f"Image processed ({operation}). Base64 encoded result: {encoded_image[:100]}..."
    except FileNotFoundError:
        return f"Error: Image file '{image_path}' not found."
    except Exception as e:
        return f"Error processing image '{image_path}': {str(e)}"


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
    )
]
