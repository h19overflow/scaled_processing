"""Image classifier for smart filtering of relevant images."""

import asyncio
import logging
from typing import Dict
from PIL import Image
from google import genai
from google.genai import types
import io
import concurrent.futures

from .vision_config import VisionConfig
from dotenv import load_dotenv
load_dotenv()

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
            
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Run the sync API call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.config.model_name,
                    contents=[
                        types.Part.from_bytes(data=img_byte_arr, mime_type='image/png'),
                        prompt
                    ]
                )
            )
            
            # Parse minimal response
            result = self._parse_classification(response.text)
            result['tokens_used'] = len(response.text.split())
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Classification failed: {e}")
            # Aggressive default: skip when classification fails
            return {
                'action': 'skip',
                'confidence': 0.3,
                'reason': f'Classification failed: {e} - defaulting to skip (aggressive mode)',
                'tokens_used': 0
            }
    
    def _parse_classification(self, response: str) -> Dict[str, any]:
        """Parse classification response with aggressive filtering."""
        try:
            parts = response.strip().upper().split()
            action = parts[0]
            confidence = float(parts[1]) if len(parts) > 1 else 0.7
            
            # Be more aggressive - require high confidence for analysis
            if action == 'ANALYZE':
                # Only analyze if confidence is reasonably high
                if confidence < 0.6:
                    return {
                        'action': 'skip',
                        'confidence': confidence,
                        'reason': f'Low confidence analysis ({confidence}) - skipping'
                    }
                else:
                    return {
                        'action': 'analyze',
                        'confidence': confidence,
                        'reason': f'High confidence analysis ({confidence})'
                    }
            else:
                # Default to skip for anything that's not clearly analyze
                return {
                    'action': 'skip',
                    'confidence': confidence,
                    'reason': f'Classified as {action}'
                }
                
        except Exception as e:
            # Be aggressive on parse failure - default to skip instead of analyze
            return {
                'action': 'skip',
                'confidence': 0.3,
                'reason': f'Parse failed: {e} - defaulting to skip (aggressive mode)'
            }