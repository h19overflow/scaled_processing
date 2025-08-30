"""
Vision Agent - Simple AI image description using Google Gemini.
"""

import logging
from typing import Dict, Any, Optional
from PIL import Image
from google import genai


class VisionAgent:
    """Simple vision agent using Google Gemini for image descriptions."""
    
    def __init__(self):
        """Initialize with Gemini client."""
        self.logger = logging.getLogger(__name__)
        self.client = genai.Client()
        self.model = "gemini-2.5-flash-image-preview"
        self.logger.info("VisionAgent initialized")
    
    def describe_image(self, image: Image.Image, context: str = "") -> str:
        """Generate description for PIL image."""
        try:
            prompt = f"Describe this image in the context of a document. Context: {context}" if context else "Describe this image."
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=[image, prompt]
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