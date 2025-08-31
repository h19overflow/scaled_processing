"""
Vision Agent - Simple AI image description using Google Gemini.
Enhanced with async support for better performance.
"""

import logging
from PIL import Image
from google import genai
from google.genai import types
import io
import asyncio

from .vision_config import VisionConfig
from dotenv import load_dotenv
load_dotenv()

class VisionAgent:
    """Simple vision agent using Google Gemini for image descriptions."""
    
    def __init__(self, config: VisionConfig = None):
        """Initialize with Gemini client and configuration."""
        self.config = config or VisionConfig()
        self.logger = logging.getLogger(__name__)
        self.client = genai.Client()
        self.model = self.config.model_name
        self.logger.info("VisionAgent initialized")
    
    def describe_image(self, image: Image.Image, context: str = "") -> str:
        """Generate description for PIL image."""
        try:
            prompt = f"Describe this image in the context of a document. Context: {context}" if context else "Describe this image."
            
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=img_byte_arr, mime_type='image/png'),
                    prompt
                ]
            )
            
            return response.text
            
        except Exception as e:
            self.logger.error(f"Vision analysis failed: {e}")
            return f"Failed to analyze image: {e}"
    
    def describe_from_path(self, image_path: str, context: str = "") -> str:
        """Generate description for image file."""
        try:
            image = Image.open(image_path)
            return self.describe_image(image, context)
        except Exception as e:
            return f"Failed to open image: {e}"
    
    def enhance_markdown_image(self, image_id: int, description: str, original_caption: str = "") -> str:
        """Create enhanced markdown with AI description."""
        parts = [f"![Image {image_id}](image_{image_id})"]
        
        if description and "Failed" not in description:
            parts.append(f"\n\n**AI Description**: {description}")
        
        if original_caption:
            parts.append(f"\n\n**Caption**: *{original_caption}*")
        
        return "".join(parts)
    
    async def describe_image_async(self, image: Image.Image, context: str = "") -> str:
        """Generate description for PIL image asynchronously."""
        try:
            prompt = self.config.analysis_prompt.format(context=context)
            
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Run the sync API call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=[
                        types.Part.from_bytes(data=img_byte_arr, mime_type='image/png'),
                        prompt
                    ]
                )
            )
            
            return response.text
            
        except Exception as e:
            self.logger.error(f"Vision analysis failed: {e}")
            return f"Failed to analyze image: {e}"
    
    async def describe_from_path_async(self, image_path: str, context: str = "") -> str:
        """Generate description for image file asynchronously."""
        try:
            image = Image.open(image_path)
            return await self.describe_image_async(image, context)
        except Exception as e:
            return f"Failed to open image: {e}"