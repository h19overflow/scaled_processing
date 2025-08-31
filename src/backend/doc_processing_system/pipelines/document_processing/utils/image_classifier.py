"""Image classifier for smart filtering of relevant images."""

import asyncio
import logging
from typing import Dict
from PIL import Image
from google import genai

from .vision_config import VisionConfig


class ImageClassifier:
    """Smart classifier to filter images before expensive analysis."""
    
    def __init__(self, config: VisionConfig = None):
        """Initialize with configuration."""
        self.config = config or VisionConfig()
        self.logger = logging.getLogger(__name__)
        self.client = genai.Client()
        
    async def classify_image(self, image: Image.Image, context: str = "") -> Dict[str, any]:
        """Classify if image needs full analysis.
        
        Returns:
            dict: {'action': 'analyze'|'skip', 'confidence': float, 'reason': str}
        """
        try:
            # Use minimal prompt to reduce tokens
            prompt = self.config.classification_prompt.format(context=context)
            
            response = await self.client.models.generate_content(
                model=self.config.model_name,
                contents=[image, prompt],
                generation_config={
                    "max_output_tokens": self.config.classification_max_tokens,
                    "temperature": 0.1,
                }
            )
            
            # Parse minimal response
            result = self._parse_classification(response.text)
            result['tokens_used'] = len(response.text.split())
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Classification failed: {e}")
            # Conservative default: analyze when uncertain
            return {
                'action': 'analyze',
                'confidence': 0.5,
                'reason': f'Classification failed: {e}',
                'tokens_used': 0
            }
    
    def _parse_classification(self, response: str) -> Dict[str, any]:
        """Parse classification response."""
        try:
            parts = response.strip().upper().split()
            action = parts[0]
            confidence = float(parts[1]) if len(parts) > 1 else 0.7
            
            return {
                'action': 'analyze' if action == 'ANALYZE' else 'skip',
                'confidence': confidence,
                'reason': f'Classified as {action}'
            }
        except:
            return {
                'action': 'analyze',
                'confidence': 0.5,
                'reason': 'Parse failed, defaulting to analyze'
            }