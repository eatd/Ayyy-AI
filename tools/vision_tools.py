
# tools/image_operations.py
from .base import ToolDefinition
from PIL import Image
import io
import base64

async def process_image(image_path: str, operation: str) -> str:
    img = Image.open(image_path)
    if operation == "resize":
        img = img.resize((800, 600))
    elif operation == "grayscale":
        img = img.convert('L')
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

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
